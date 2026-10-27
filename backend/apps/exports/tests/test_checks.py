from apps.exports.checks import check_html
from apps.exports.rendering import NodeContent, render_lecture

GOOD = ('<!DOCTYPE html><html lang="en"><head><title>T</title></head>'
        "<body><main><h1>T</h1><h2>A</h2><p>Text</p></main></body></html>")


def rules(page, level="error"):
    return {issue.rule for issue in check_html(page) if issue.level == level}


def test_good_page_passes():
    assert rules(GOOD) == set()


def test_missing_language():
    assert "html-lang" in rules(GOOD.replace(' lang="en"', ""))


def test_skipped_heading_level():
    assert "heading-order" in rules(GOOD.replace("<h2>A</h2>", "<h3>A</h3>"))


def test_two_h1s():
    assert "one-h1" in rules(GOOD.replace("<h2>A</h2>", "<h1>A</h1>"))


def test_image_without_alt():
    assert "image-alt" in rules(GOOD.replace("<p>Text</p>", '<img src="data:image/png;base64,AA==">'))


def test_linked_image():
    assert "image-embedded" in rules(GOOD.replace("<p>Text</p>", '<img src="https://x.org/a.png" alt="A">'))


def test_table_header_without_scope():
    table = "<table><caption>C</caption><tr><th>H</th></tr><tr><td>1</td></tr></table>"
    assert "th-scope" in rules(GOOD.replace("<p>Text</p>", table))


def test_leftover_latex_in_math():
    assert "math-unconverted" in rules(GOOD.replace("<p>Text</p>", '<math alttext="x"><mi>\\SI</mi></math>'))


def test_node_metadata_left_in_page():
    assert "no-metadata" in rules(GOOD.replace("<p>Text</p>", '<p data-confidence="0.4">Text</p>'))


def test_scrollable_equation_must_be_reachable_by_keyboard():
    page = GOOD.replace("<p>Text</p>", '<div class="equation"><math alttext="x"><mi>x</mi></math></div>')
    assert "scroll-focus" in rules(page, "warning")


def test_script():
    assert "no-script" in rules(GOOD.replace("<p>Text</p>", "<script>x()</script>"))


def test_every_kind_rendered_together_passes():
    png = b"\x89PNG\r\n\x1a\nx"
    nodes = [
        NodeContent("text", "## Work\n\nWork is the integral of force along a path, $W = Fd$."),
        NodeContent("equation", r"W = \int_{s_1}^{s_2} F \cos\theta \, ds"),
        NodeContent("graph", "Force against displacement.", {"long_description": "A straight line."}, "a/fig.png"),
        NodeContent("image", "A block on a ramp.", {}, "a/ramp.jpg"),
        NodeContent("code", "work = sum(f * dx for f, dx in zip(forces, steps))", {"language": "python"}),
        NodeContent("table", "| Object | Work (J) |\n|---|---|\n| Block A | 40 |", {"caption": "Work"}),
        NodeContent("video", "The professor pulls a block up a ramp."),
    ]
    page = render_lecture(title="Lecture 4", class_label="ME 27400 Dynamics", nodes=nodes,
                          load_asset=lambda key: png).html
    assert rules(page) == set()
    assert rules(page, "warning") == set()