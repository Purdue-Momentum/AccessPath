"""
Automated accessibility checks on a finished export. Run on every export before it is saved.

Errors stop the export. Warnings are saved on the Export so a person can look at them.
These catch structural problems only. They do not replace testing with a screen reader.
"""

from dataclasses import asdict, dataclass

import lxml.html

ERROR, WARNING = "error", "warning"


@dataclass(frozen=True)
class Issue:
    level: str  # "error" or "warning"
    rule: str
    message: str

    def as_dict(self) -> dict:
        return asdict(self)


def check_html(page: str) -> list[Issue]:
    doc = lxml.html.document_fromstring(page)
    issues: list[Issue] = []

    def error(rule, message):
        issues.append(Issue(ERROR, rule, message))

    def warn(rule, message):
        issues.append(Issue(WARNING, rule, message))

    # WCAG 3.1.1 Language of page
    if not (doc.get("lang") or "").strip():
        error("html-lang", "The page has no language. Add lang to the html tag.")

    # WCAG 2.4.2 Page titled
    title = doc.find(".//title")
    if title is None or not title.text_content().strip():
        error("page-title", "The page has no title.")

    # Landmarks. Everything a student reads sits inside one main.
    if len(doc.xpath("//main")) != 1:
        error("one-main", "The page must have exactly one main element.")

    # WCAG 1.3.1 and 2.4.6. One h1, no empty headings, no skipped levels.
    headings = doc.xpath("//h1 | //h2 | //h3 | //h4 | //h5 | //h6")
    if sum(1 for h in headings if h.tag == "h1") != 1:
        error("one-h1", "The page must have exactly one h1, the lecture title.")
    previous = 0
    for h in headings:
        level, text = int(h.tag[1]), h.text_content().strip()
        if not text:
            error("empty-heading", f"An h{level} heading is empty.")
        if previous and level > previous + 1:
            error("heading-order", f"Heading '{text}' jumps from h{previous} to h{level}.")
        previous = level

    # WCAG 1.1.1 Non-text content. Every image has alt text and is embedded in the file.
    for img in doc.xpath("//img"):
        alt = img.get("alt")
        if alt is None or not alt.strip():
            error("image-alt", "An image has no alt text.")
        if not (img.get("src") or "").startswith("data:"):
            error("image-embedded", "An image is linked, not embedded. The page must work on its own.")

    # WCAG 1.3.1 Info and relationships. Tables have header cells with a scope.
    for number, table in enumerate(doc.xpath("//table"), start=1):
        header_cells = table.xpath(".//th")
        if not header_cells:
            error("table-headers", f"Table {number} has no header cells.")
        for th in header_cells:
            if th.get("scope") not in {"col", "row", "colgroup", "rowgroup"}:
                error("th-scope", f"A header cell in table {number} has no scope.")
            if not th.text_content().strip():
                warn("empty-table-header", f"Table {number} has an empty header cell.")
        if table.find("caption") is None:
            warn("table-caption", f"Table {number} has no caption.")

    # Math must be real MathML, not leftover LaTeX.
    for math in doc.xpath("//math"):
        if not (math.get("alttext") or "").strip():
            warn("math-alttext", "An equation has no alttext.")
        for el in math.iter():
            if isinstance(el.tag, str) and (el.text or "").strip().startswith("\\"):
                error("math-unconverted", f"An equation still contains LaTeX: {el.text.strip()}")

    # ids are unique and every aria-labelledby points at something real.
    ids = doc.xpath("//@id")
    for duplicate in sorted({i for i in ids if ids.count(i) > 1}):
        error("duplicate-id", f"The id '{duplicate}' is used more than once.")
    for el in doc.xpath("//*[@aria-labelledby]"):
        for ref in el.get("aria-labelledby").split():
            if ref not in ids:
                error("aria-reference", f"aria-labelledby points at a missing id '{ref}'.")

    # WCAG 2.1.1 Keyboard. Regions that scroll sideways can be reached with Tab.
    scrollable = ("//pre | //div[contains(concat(' ', @class, ' '), ' table-wrap ')"
                  " or contains(concat(' ', @class, ' '), ' equation ')]")
    for el in doc.xpath(scrollable):
        if el.get("tabindex") != "0":
            warn("scroll-focus", f"A scrollable <{el.tag}> cannot be reached with the keyboard.")

    # WCAG 2.4.4 Link purpose
    for a in doc.xpath("//a"):
        if not a.text_content().strip():
            error("link-name", "A link has no text.")

    # No scripts, no event handlers, and no node metadata left in the page.
    if doc.xpath("//script"):
        error("no-script", "The page contains a script.")
    for el in doc.iter():
        if not isinstance(el.tag, str):
            continue
        for name in el.attrib:
            if name.startswith("on"):
                error("no-event-handlers", f"<{el.tag}> has an event handler ({name}).")
            if name.startswith("data-"):
                error("no-metadata", f"<{el.tag}> carries metadata ({name}).")

    return issues


def errors_only(issues: list[Issue]) -> list[Issue]:
    return [i for i in issues if i.level == ERROR]