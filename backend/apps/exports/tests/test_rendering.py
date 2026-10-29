import pytest

from apps.exports.rendering import ExportError, NodeContent, _LectureRenderer, mathml, render_lecture
from apps.review.models import Node

PNG = b"\x89PNG\r\n\x1a\nnot-a-real-image"
FIG = "classes/c1/assets/fig_003.png"


def render(*nodes, assets=None):
    assets = {FIG: PNG} if assets is None else assets
    return render_lecture(title="Lecture 4. Work and Energy", class_label="ME 27400 Dynamics",
                          nodes=list(nodes), load_asset=assets.get)


def test_every_node_kind_has_a_renderer():
    # Fails if Lane D adds a kind to Node.Kind that the export does not handle yet.
    assert set(Node.Kind.values) == set(_LectureRenderer.KINDS)


def test_page_shell():
    page = render(NodeContent("text", "Hello.")).html
    assert page.startswith("<!DOCTYPE html>")
    assert '<html lang="en">' in page
    assert "<title>Lecture 4. Work and Energy | ME 27400 Dynamics</title>" in page
    assert "<main>" in page and "<h1>Lecture 4. Work and Energy</h1>" in page


def test_text_is_escaped_and_never_runs_html():
    page = render(NodeContent("text", "Use <script>alert(1)</script> **carefully**")).html
    assert "<script>alert" not in page
    assert "&lt;script&gt;" in page
    assert "<strong>carefully</strong>" in page


def test_headings_start_at_h2_and_never_skip_a_level():
    page = render(NodeContent("text", "## Work\n\nIntro."), NodeContent("text", "#### Detail"),
                  NodeContent("text", "## Energy")).html
    assert "<h2>Work</h2>" in page
    assert "<h3>Detail</h3>" in page
    assert "<h2>Energy</h2>" in page


def test_inline_math_in_text_becomes_mathml():
    page = render(NodeContent("text", r"Kinetic energy is $\frac{1}{2} m v^2$.")).html
    assert '<math alttext="\\frac{1}{2} m v^2"' in page
    assert 'display="inline"' in page


def test_dollar_amounts_are_not_math():
    assert "<math" not in render(NodeContent("text", "The lab fee is $5 and parking is $10.")).html


def test_equation_is_block_mathml_with_alttext():
    page = render(NodeContent("equation", r"W = \int_{s_1}^{s_2} F \cos\theta \, ds")).html
    assert '<div class="equation" tabindex="0"><math alttext="W = \\int_{s_1}^{s_2} F \\cos\\theta \\, ds"' in page
    assert 'display="block"' in page


def test_equation_delimiters_are_ignored():
    assert mathml("$$x^2$$", display="block") == mathml("x^2", display="block")


@pytest.mark.parametrize("latex", [r"\SI{9.81}{m/s^2}", r"\frac{1}{", "", r"W = \\int F \\, ds"])
def test_bad_latex_is_refused(latex):
    with pytest.raises(ExportError):
        render(NodeContent("equation", latex))


def test_error_names_the_item():
    with pytest.raises(ExportError, match=r"Item 2 \(equation\): Unsupported LaTeX command \\SI"):
        render(NodeContent("text", "Hi."), NodeContent("equation", r"\SI{9.81}{m/s^2}"))


def test_image_is_embedded_with_alt_text():
    page = render(NodeContent("image", "A block on a ramp.", asset_key=FIG)).html
    assert '<img src="data:image/png;base64,' in page
    assert 'alt="A block on a ramp."' in page
    assert '<figcaption><span class="figure-label">Figure 1.</span></figcaption>' in page


def test_long_description_goes_in_the_caption():
    node = NodeContent("graph", "Force against displacement.", {"long_description": "Force rises from 0 to 10 N."},
                       asset_key=FIG)
    result = render(node)
    assert '<span class="figure-label">Figure 1.</span> Force rises from 0 to 10 N.</figcaption>' in result.html
    assert result.warnings == []


def test_graph_without_long_description_warns():
    result = render(NodeContent("graph", "Force against displacement.", asset_key=FIG))
    assert any("no long description" in w for w in result.warnings)


def test_missing_image_file_falls_back_to_description():
    result = render(NodeContent("image", "A block on a ramp."))
    assert '<p class="figure-description">A block on a ramp.</p>' in result.html
    assert "<img" not in result.html
    assert any("no image file" in w for w in result.warnings)


def test_image_without_description_is_refused():
    with pytest.raises(ExportError, match="no description"):
        render(NodeContent("image", "   ", asset_key=FIG))


def test_image_that_cannot_be_loaded_is_refused():
    def broken(key):
        raise OSError("S3 is down")

    with pytest.raises(ExportError, match="could not be loaded"):
        render_lecture(title="T", class_label="", nodes=[NodeContent("image", "A ramp.", asset_key=FIG)],
                       load_asset=broken)


def test_code_is_escaped_and_labelled():
    page = render(NodeContent("code", "if a < b:\n    pass", {"language": "python"})).html
    assert "<figcaption>Python code</figcaption>" in page
    assert '<pre tabindex="0"><code class="language-python">if a &lt; b:\n    pass</code></pre>' in page


def test_table_has_caption_and_scoped_headers():
    table = "| Object | Mass (kg) | Work (J) |\n|---|---|---|\n| Block A | 2 | 40 |"
    page = render(NodeContent("table", table, {"caption": "Work done on each block"})).html
    assert '<caption id="table-1-caption">Table 1. Work done on each block</caption>' in page
    assert '<th scope="col">Mass (kg)</th>' in page
    assert "<td>Block A</td><td>2</td><td>40</td>" in page
    assert 'role="region" aria-labelledby="table-1-caption" tabindex="0"' in page


def test_table_row_headers():
    table = "| Object | Work (J) |\n|---|---|\n| Block A | 40 |"
    page = render(NodeContent("table", table, {"row_headers": True})).html
    assert '<th scope="row">Block A</th><td>40</td>' in page


@pytest.mark.parametrize("table", ["just some text", "| a | b |\n|---|---|\n| 1 | 2 | 3 |"])
def test_bad_table_is_refused(table):
    with pytest.raises(ExportError):
        render(NodeContent("table", table))


def test_unknown_kind_is_refused():
    with pytest.raises(ExportError, match="kind the export does not know"):
        render(NodeContent("hologram", "?"))


# ---- pipeline format 0.1 ---------------------------------------------------------


def test_structured_table_uses_content_as_caption():
    node = NodeContent("table", "Measured work", {"headers": ["Object", "Work (J)"], "rows": [["Block A", "40"]]})
    page = render(node).html
    assert '<caption id="table-1-caption">Table 1. Measured work</caption>' in page
    assert '<th scope="col">Work (J)</th>' in page
    assert "<td>Block A</td><td>40</td>" in page


def test_structured_table_row_longer_than_header_is_refused():
    node = NodeContent("table", "T", {"headers": ["a"], "rows": [["1", "2"]]})
    with pytest.raises(ExportError, match="more cells"):
        render(node)


def test_heading_level_makes_a_real_heading():
    page = render(NodeContent("text", "Work", {"heading_level": 1}),
                  NodeContent("text", "Detail", {"heading_level": 3})).html
    assert "<h2>Work</h2>" in page
    assert "<h3>Detail</h3>" in page


def test_audio_uses_transcript_and_title():
    page = render(NodeContent("audio", "Lecture recording", {"transcript": "Work is force times distance."})).html
    assert "<p><strong>Audio transcript.</strong> Lecture recording</p>" in page
    assert "<p>Work is force times distance.</p>" in page


def test_video_includes_visual_description():
    node = NodeContent("video", "Ramp demonstration",
                       {"transcript": "Watch this.", "visual_description": "A block moves uphill."})
    page = render(node).html
    assert "What the video shows." in page
    assert "<p>A block moves uphill.</p>" in page


def test_equation_has_words_for_read_aloud():
    page = render(NodeContent("equation", r"T = \frac{1}{2} m v^2")).html
    assert ('<p class="math-words"><span class="math-words-label">In words:</span> '
            "T equals one half m v squared</p>") in page


def test_table_can_be_read_as_sentences():
    node = NodeContent("table", "Work", {"headers": ["Force", "Work (J)", "Sign"],
                                         "rows": [["Rope tension", "60.0", "Positive"]]})
    page = render(node).html
    assert "<summary>Table 1 read as sentences</summary>" in page
    assert "<li>Rope tension. Work (J): 60.0; Sign: Positive.</li>" in page


def test_table_with_no_rows_has_no_sentences():
    assert "<details" not in render(NodeContent("table", "Empty", {"headers": ["A", "B"], "rows": []})).html