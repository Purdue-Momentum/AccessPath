"""
The page for Engineer C's apps/pipeline/schema/example.xml, compared with the approved
target in golden/example.html. If C changes the XML, or you change the output on purpose,
this test fails. Regenerate the target with

    UPDATE_GOLDEN=1 pytest apps/exports/tests/test_golden.py          (Mac, Linux)
    $env:UPDATE_GOLDEN = "1"; pytest apps/exports/tests/test_golden.py; Remove-Item Env:UPDATE_GOLDEN   (Windows)

then read the git diff of golden/example.html, line by line, before committing it.

Both shapes of example.xml are read:
  - pipeline format 0.1: <node> has <content> and <extra> children
  - the original shape: <latex>, <description> or <code> inside <node>, language and asset as attributes
"""

import os
import re
from pathlib import Path

from django.conf import settings
from lxml import etree

from apps.exports.rendering import NodeContent, render_lecture

EXAMPLE_XML = Path(settings.BASE_DIR) / "apps" / "pipeline" / "schema" / "example.xml"
GOLDEN = Path(__file__).parent / "golden" / "example.html"
FAKE_PNG = b"\x89PNG\r\n\x1a\nfake"


def _value(el):
    """One XML element as a Python value: null, a list of <item>s, or text."""
    if el.get("null") == "true":
        return None
    items = el.findall("item")
    if items:
        return [_value(item) for item in items]
    return (el.text or "").strip()


def _node_format_0_1(el) -> NodeContent:
    """<content> is content, the children of <extra> go into extra, the image comes from <asset_id>."""
    content = el.findtext("content") or ""
    extra_el = el.find("extra")
    extra = {} if extra_el is None else {c.tag: _value(c) for c in extra_el if isinstance(c.tag, str)}
    if extra.get("heading_level") is not None:
        extra["heading_level"] = int(extra["heading_level"])  # XML has no numbers, the database will
    asset_el = el.find("source_ref/asset_id")
    asset_id = _value(asset_el) if asset_el is not None else None
    asset = f"classes/demo/assets/{asset_id}.png" if asset_id and el.get("kind") in {"image", "graph"} else ""
    return NodeContent(el.get("kind"), content.strip(), extra, asset)


def _node_original(el) -> NodeContent:
    """Inner tag text is content, language goes in extra."""
    child = el.find("*")  # <latex>, <description> or <code>. Text nodes have none.
    content = (child.text if child is not None else el.text) or ""
    extra = {"language": el.get("language")} if el.get("language") else {}
    asset = f"classes/demo/assets/{el.get('asset')}" if el.get("kind") in {"image", "graph"} else ""
    return NodeContent(el.get("kind"), content.strip(), extra, asset)


def nodes_from_example_xml() -> list[NodeContent]:
    nodes = []
    for el in etree.parse(str(EXAMPLE_XML)).getroot().iter("node"):
        nodes.append(_node_format_0_1(el) if el.find("content") is not None else _node_original(el))
    return nodes


def squash(page: str) -> str:
    return re.sub(r">\s+<", "><", page).strip()


def test_example_xml_matches_the_golden_page():
    page = render_lecture(title="Lecture 4. Work and Energy", class_label="ME 27400 Dynamics, Fall 2026",
                          nodes=nodes_from_example_xml(), load_asset=lambda key: FAKE_PNG).html
    if os.environ.get("UPDATE_GOLDEN"):
        GOLDEN.parent.mkdir(exist_ok=True)
        GOLDEN.write_text(page, encoding="utf-8")
    assert squash(page) == squash(GOLDEN.read_text(encoding="utf-8"))