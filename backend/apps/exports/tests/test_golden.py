"""
The page for Engineer C's apps/pipeline/schema/example.xml, compared with the approved
target in golden/example.html. If C changes the XML, or you change the output on purpose,
this test fails. Regenerate the target with

    UPDATE_GOLDEN=1 pytest apps/exports/tests/test_golden.py

then read the git diff of golden/example.html, line by line, before committing it.
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


def nodes_from_example_xml() -> list[NodeContent]:
    """Reads example.xml the way Lane C stores it: inner tag text is content, language goes in extra."""
    nodes = []
    for el in etree.parse(str(EXAMPLE_XML)).getroot().iter("node"):
        child = el.find("*")  # <latex>, <description> or <code>. Text nodes have none.
        content = (child.text if child is not None else el.text) or ""
        extra = {"language": el.get("language")} if el.get("language") else {}
        asset = f"classes/demo/assets/{el.get('asset')}" if el.get("kind") in {"image", "graph"} else ""
        nodes.append(NodeContent(el.get("kind"), content.strip(), extra, asset))
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