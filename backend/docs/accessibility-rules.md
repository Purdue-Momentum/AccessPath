# Accessibility rules for exports

Every export is one HTML file. `apps/exports/rendering.py` follows these rules
and `apps/exports/checks.py` checks them on every export.

## The whole page

- `<html lang="en">` and a `<title>` of "Lecture title | Class". (WCAG 3.1.1, 2.4.2)
- Exactly one `<main>`. The lecture title is the only `<h1>`. (1.3.1)
- Headings never skip a level. The top heading level used in the text becomes `<h2>`. (1.3.1, 2.4.6)
- No scripts, no event handlers, no external files. Images are embedded as data URIs,
  so the page works in any LMS and no link ever expires.
- No node metadata: no node ids, confidence, state, page numbers, model names or `data-` attributes.
- Text 1.125rem, line height 1.6, lines at most 46rem wide. (1.4.8, 1.4.12)
- Text contrast at least 4.5:1 in light mode and in dark mode. (1.4.3)
- The page reflows at 320px wide with no sideways scrolling. (1.4.10)
- A visible focus outline. Anything that scrolls sideways can be reached with Tab. (2.4.7, 2.1.1)

## Each node kind

### text
- Content: Markdown.
- HTML: paragraphs, lists, links and headings. Raw HTML in the content is shown as text, never run.
  Inline math written as `$...$` becomes MathML.
- Export fails if: inline LaTeX is broken.

### equation
- Content: LaTeX. `$`, `$$`, `\[ \]` and `\( \)` around it are removed.
- HTML: `<div class="equation" tabindex="0"><math display="block" alttext="the LaTeX">...</math></div>`
- Export fails if: the LaTeX is broken, or uses a command latex2mathml does not know (for example `\SI`).

### image
- Content: short alt text. `extra.long_description` is optional.
- HTML: `<figure><img alt="..."><figcaption>Figure N. long description</figcaption></figure>`
- Export fails if: there is no alt text, or the image file can't be loaded.
- Warning if: alt text is over 150 characters, or there is no image file (the description is used as text).

### graph
- Same as image, plus: a long description is expected. Missing it is a warning.

### code
- Content: the code, unchanged. `extra.language` names the language.
- HTML: `<figure><figcaption>Python code</figcaption><pre tabindex="0"><code class="language-python">`
- Export fails if: never.

### table
- Content: a Markdown pipe table with a header row. `extra.caption` and `extra.row_headers` are optional.
- HTML: `<div role="region" aria-labelledby="table-N-caption" tabindex="0">` around a `<table>` with
  `<caption>Table N. caption</caption>`, `<th scope="col">` header cells, and `<th scope="row">`
  for the first column when `row_headers` is true.
- Export fails if: it is not a pipe table, or a row has more cells than the header.

### video and audio (v2)
- Content: the transcript.
- HTML: `<div class="transcript">` with the transcript as paragraphs.

## Writing alt text and long descriptions

This is also the rubric for Engineer C's evaluation set. Score each line 0 (no), 1 (partly) or 2 (yes).

1. Accurate. Says nothing the picture does not show. Numbers and labels match the picture.
2. Purposeful. Says why the picture is in this lecture, using the lecture's ta_context.
3. Concise. Alt text is under 150 characters and never starts with "image of" or "picture of".
4. Complete (graphs). The long description gives the graph type, both axes with units, the range,
   the trend, the key points and the takeaway.
5. Convertible (equations). The LaTeX converts to MathML with no error and keeps its meaning.
6. Structured (tables). Has a header row, units in the headers, one fact per cell.

## How we test

1. Automatically, on every export: `apps/exports/checks.py`. Errors stop the export. Warnings are saved.
2. Before each release: axe DevTools in Chrome on a real export, in light and dark mode, and at 320px wide.
3. By hand: VoiceOver on Mac and NVDA on Windows, using the screen reader checklist.