"""
Lane E. Turns approved nodes into one accessible HTML page.

One method per node kind. Each returns HTML that is already escaped, so the page
template can insert it as is. Nothing here touches the database or S3, which keeps
it fast to test. The caller passes in a function that loads image bytes.

Two content formats are accepted, so nothing breaks while the pipeline format settles:
  - pipeline format 0.1 (Engineer C's schema): heading_level on text, tables in
    extra.headers and extra.rows, transcripts in extra.transcript
  - the original format: Markdown headings, Markdown pipe tables, transcript in content

The rules this code follows are written down in docs/accessibility-rules.md.
"""

import base64
import html
import mimetypes
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from django.template.loader import render_to_string
from latex2mathml.converter import convert as latex_to_mathml
from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin

PAGE_LANGUAGE = "en"  # Every class is taught in English for now. See docs/accessibility-rules.md.
ALT_TEXT_SOFT_LIMIT = 150
IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"}
LANGUAGE_NAMES = {"python": "Python", "matlab": "MATLAB", "javascript": "JavaScript", "cpp": "C++", "c": "C",
                  "java": "Java", "r": "R", "julia": "Julia", "sql": "SQL", "bash": "Bash"}

AssetLoader = Callable[[str], bytes | None]


class ExportError(Exception):
    """A problem a TA or professor can fix. The message is shown to them as is."""


@dataclass
class NodeContent:
    """What the renderer needs from one node. Built from a Node and its current NodeVersion."""

    kind: str
    content: str
    extra: dict = field(default_factory=dict)
    asset_key: str = ""


@dataclass
class RenderResult:
    html: str
    warnings: list[str] = field(default_factory=list)


def node_content(node) -> NodeContent:
    """Read a review.Node (with current_version loaded). Never changes the node."""
    version = node.current_version
    # TODO: pipeline format 0.1 has source_ref["asset_id"] instead of a full key. Waiting on B and C
    # for how an asset_id becomes an S3 key. Until then those figures export their description only.
    return NodeContent(kind=node.kind, content=version.content, extra=dict(version.extra or {}),
                       asset_key=(node.source_ref or {}).get("asset_key", ""))


def render_lecture(*, title: str, class_label: str, nodes: list[NodeContent], load_asset: AssetLoader) -> RenderResult:
    """Build the whole page. Raises ExportError with a fixable message if any node can't be rendered."""
    renderer = _LectureRenderer(load_asset)
    renderer.top_heading = min((lvl for n in nodes if n.kind == "text" for lvl in renderer.heading_levels(n)),
                               default=1)
    body = "\n".join(renderer.render(position, node) for position, node in enumerate(nodes, start=1))
    page = render_to_string("exports/lecture.html", {
        "lang": PAGE_LANGUAGE, "title": title, "class_label": class_label, "body": body})
    return RenderResult(html=page, warnings=renderer.warnings)


def mathml(latex: str, *, display: str) -> str:
    """LaTeX to MathML. Refuses anything latex2mathml could not really convert."""
    latex = _strip_math_delimiters(latex)
    if not latex:
        raise ExportError("An equation is empty.")
    # "\\int" is a line break followed by the letters i, n, t. Usually text copied from JSON without decoding.
    if "\\begin" not in latex and re.search(r"\\\\[A-Za-z]", latex):
        raise ExportError(f"This LaTeX has a double backslash before a command. Use one backslash: {latex}")
    try:
        out = latex_to_mathml(latex, display=display)
    except Exception as e:  # latex2mathml raises several types for broken input
        raise ExportError(f"This LaTeX could not be turned into MathML, check its braces: {latex}") from e
    # latex2mathml copies commands it does not know straight into the output, e.g. <mi>\SI</mi>.
    unknown = sorted(set(re.findall(r">\s*(\\[A-Za-z]+)\s*<", out)))
    if unknown:
        raise ExportError(f"Unsupported LaTeX command {', '.join(unknown)} in: {latex}")
    return out.replace("<math ", f'<math alttext="{html.escape(latex, quote=True)}" ', 1)


def _strip_math_delimiters(latex: str) -> str:
    latex = latex.strip()
    for start, end in (("$$", "$$"), ("\\[", "\\]"), ("\\(", "\\)"), ("$", "$")):
        if latex.startswith(start) and latex.endswith(end) and len(latex) > len(start) + len(end):
            return latex[len(start):-len(end)].strip()
    return latex


class _LectureRenderer:
    # Node.Kind value -> method name. Every kind in apps/review/models.py must appear here.
    KINDS = {"text": "text", "equation": "equation", "image": "figure", "graph": "figure",
             "code": "code", "table": "table", "video": "transcript", "audio": "transcript"}

    def __init__(self, load_asset: AssetLoader):
        self.load_asset = load_asset
        self.warnings: list[str] = []
        self.figures = 0
        self.tables = 0
        self.top_heading = 1  # the smallest heading level used in the lecture's text
        self.last_heading = 1  # the lecture title is the only h1
        self.md = MarkdownIt("commonmark", {"html": False})  # raw HTML in content is shown as text, never run
        self.md.disable("image")  # pictures come only from image and graph nodes
        self.md.use(dollarmath_plugin, allow_space=False, allow_digits=False,
                    renderer=lambda latex, opts: mathml(latex, display="block" if opts.get("display_mode")
                                                        else "inline"))

    def render(self, position: int, node: NodeContent) -> str:
        method = self.KINDS.get(node.kind)
        if method is None:
            raise ExportError(f"Item {position} has a kind the export does not know: {node.kind!r}.")
        try:
            return getattr(self, method)(node)
        except ExportError as e:
            raise ExportError(f"Item {position} ({node.kind}): {e}") from e

    # ---- one method per node kind -------------------------------------------------

    def text(self, node: NodeContent) -> str:
        level = node.extra.get("heading_level")
        if isinstance(level, int) and 1 <= level <= 6:
            # Pipeline format 0.1: the whole node is one heading.
            heading = " ".join(node.content.split())
            if not heading:
                raise ExportError("a heading is empty.")
            tag = f"h{self._heading_level(level)}"
            return f"<{tag}>{self._inline(heading)}</{tag}>"
        tokens = self.md.parse(node.content)
        for i, token in enumerate(tokens):
            if token.type == "heading_open":
                # heading_open, inline, heading_close
                token.tag = tokens[i + 2].tag = f"h{self._heading_level(int(token.tag[1]))}"
        return self.md.renderer.render(tokens, self.md.options, {}).strip()

    def equation(self, node: NodeContent) -> str:
        # tabindex: a wide equation scrolls sideways on a phone, and keyboard users must be able to reach it.
        return f'<div class="equation" tabindex="0">{mathml(node.content, display="block")}</div>'

    def figure(self, node: NodeContent) -> str:
        self.figures += 1
        number = self.figures
        alt = " ".join(node.content.split())
        if not alt:
            raise ExportError("there is no description. Write alt text before exporting.")
        if len(alt) > ALT_TEXT_SOFT_LIMIT:
            self.warnings.append(f"Figure {number} alt text is {len(alt)} characters. Aim for under "
                                 f"{ALT_TEXT_SOFT_LIMIT} and move the detail into the long description.")
        long_description = (node.extra.get("long_description") or "").strip()
        if node.kind == "graph" and not long_description:
            self.warnings.append(f"Figure {number} is a graph with no long description. Graphs should explain "
                                 f"their axes, trend and key values.")

        image = self._image(node.asset_key, alt, number)
        if image is None:
            self.warnings.append(f"Figure {number} has no image file, so only its description was exported.")
            image = f'<p class="figure-description">{html.escape(alt)}</p>'
        caption = f'<span class="figure-label">Figure {number}.</span>'
        if long_description:
            caption += " " + self._paragraphs(long_description, inline_first=True)
        return f"<figure>\n{image}\n<figcaption>{caption}</figcaption>\n</figure>"

    def code(self, node: NodeContent) -> str:
        language = re.sub(r"[^a-z0-9+#-]", "", (node.extra.get("language") or "").lower())
        label = LANGUAGE_NAMES.get(language, language.capitalize())
        caption = f"{label} code" if label else "Code"
        css = f' class="language-{language}"' if language else ""
        code = html.escape(node.content.strip("\n"))
        return (f'<figure class="code">\n<figcaption>{caption}</figcaption>\n'
                f'<pre tabindex="0"><code{css}>{code}</code></pre>\n</figure>')

    def table(self, node: NodeContent) -> str:
        if node.extra.get("headers") is not None:
            # Pipeline format 0.1: cells in extra.headers and extra.rows, content is the caption.
            header = [str(cell) for cell in node.extra["headers"]]
            rows = [[str(cell) for cell in row] for row in node.extra.get("rows") or []]
            caption_text = node.extra.get("caption") or node.content
        else:
            # Original format: a Markdown pipe table in content.
            lines = [line for line in node.content.strip().splitlines() if line.strip()]
            if len(lines) < 2 or not _TABLE_SEPARATOR.match(lines[1]):
                raise ExportError("this is not a Markdown table with a header row.")
            header = _split_row(lines[0])
            rows = [_split_row(line) for line in lines[2:]]
            caption_text = node.extra.get("caption")
        if not header:
            raise ExportError("the table has no header row.")
        if any(len(row) > len(header) for row in rows):
            raise ExportError("a row has more cells than the header.")

        self.tables += 1
        number = self.tables
        caption_id = f"table-{number}-caption"
        caption = f"Table {number}."
        if caption_text:
            caption += " " + self._inline(caption_text)
        row_headers = bool(node.extra.get("row_headers"))

        out = [f'<div class="table-wrap" role="region" aria-labelledby="{caption_id}" tabindex="0">',
               "<table>", f'<caption id="{caption_id}">{caption}</caption>', "<thead>",
               "<tr>" + "".join(f'<th scope="col">{self._inline(cell)}</th>' for cell in header) + "</tr>",
               "</thead>", "<tbody>"]
        for row in rows:
            row = row + [""] * (len(header) - len(row))
            cells = [f'<th scope="row">{self._inline(cell)}</th>' if i == 0 and row_headers
                     else f"<td>{self._inline(cell)}</td>" for i, cell in enumerate(row)]
            out.append("<tr>" + "".join(cells) + "</tr>")
        out += ["</tbody>", "</table>", "</div>"]
        return "\n".join(out)

    def transcript(self, node: NodeContent) -> str:
        # Pipeline format 0.1: content is a title and the text is in extra.transcript.
        # Original format: content is the transcript itself.
        kind = "Video" if node.kind == "video" else "Audio"
        transcript = (node.extra.get("transcript") or "").strip()
        title = " ".join(node.content.split()) if transcript else ""
        text = transcript or node.content
        if not text.strip():
            raise ExportError("there is no transcript.")
        label = f"<strong>{kind} transcript.</strong>"
        if title:
            label += " " + self._inline(title)
        out = [f"<p>{label}</p>", self._paragraphs(text)]
        visual = (node.extra.get("visual_description") or "").strip()
        if visual:
            # What happens on screen, for students who can't see the video (WCAG 1.2.3).
            out += ["<p><strong>What the video shows.</strong></p>", self._paragraphs(visual)]
        return '<div class="transcript">\n' + "\n".join(out) + "\n</div>"

    # ---- helpers ------------------------------------------------------------------

    def heading_levels(self, node: NodeContent) -> list[int]:
        level = node.extra.get("heading_level")
        if isinstance(level, int) and 1 <= level <= 6:
            return [level]
        return [int(t.tag[1]) for t in self.md.parse(node.content) if t.type == "heading_open"]

    def _heading_level(self, level: int) -> int:
        """The top level used in the lecture becomes h2, and no level is ever skipped."""
        wanted = level - self.top_heading + 2
        self.last_heading = max(2, min(wanted, self.last_heading + 1, 6))
        return self.last_heading

    def _inline(self, text: str) -> str:
        return self.md.renderInline(str(text)).strip()

    def _paragraphs(self, text: str, *, inline_first: bool = False) -> str:
        parts = [self._inline(p) for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
        if inline_first and len(parts) == 1:
            return parts[0]
        return "\n".join(f"<p>{p}</p>" for p in parts)

    def _image(self, key: str, alt: str, number: int) -> str | None:
        if not key:
            return None
        mime = mimetypes.guess_type(key)[0] or ""
        if mime not in IMAGE_TYPES:
            raise ExportError(f"Figure {number} is not a supported image type ({key.rsplit('/', 1)[-1]}).")
        try:
            data = self.load_asset(key)
        except Exception as e:
            raise ExportError(f"the image for Figure {number} could not be loaded from storage.") from e
        if not data:
            return None
        encoded = base64.b64encode(data).decode("ascii")
        return f'<img src="data:{mime};base64,{encoded}" alt="{html.escape(alt, quote=True)}">'


_TABLE_SEPARATOR = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")


def _split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    return [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", line)]