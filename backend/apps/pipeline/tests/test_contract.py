"""Synthetic contract tests; runnable with unittest without Django or paid APIs."""

import copy
import json
import unittest
from pathlib import Path

from apps.pipeline.contract import ContractError, to_xml, validate_document, validate_xml

PIPELINE = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads((PIPELINE / "fixtures/synthetic-nodes.json").read_text())
        self.assets = json.loads((PIPELINE / "fixtures/synthetic-assets.json").read_text())
        self.context = {"document": "synthetic-doc", "lecture": "synthetic-lecture",
                        "source": "synthetic.pdf", "prompt_version": "synthetic-v1"}

    def xml(self):
        return to_xml(self.document, context=self.context, assets=self.assets, allow_proposed_media=True)

    def test_all_eight_proposed_shapes_round_trip(self):
        document, context = validate_xml(self.xml(), assets=self.assets, allow_proposed_media=True)
        self.assertEqual(document, self.document)
        self.assertEqual(context, self.context)
        self.assertIn(b"&lt;introduction&gt;", self.xml())
        self.assertIn(b"&amp;", self.xml())

    def test_six_content_kinds_do_not_need_media_opt_in(self):
        self.document["nodes"] = self.document["nodes"][:6]
        validate_document(self.document, assets=self.assets)

    def test_media_rejected_by_default(self):
        with self.assertRaisesRegex(ContractError, "proposals"):
            validate_document(self.document, assets=self.assets)

    def test_invalid_json_and_semantics(self):
        mutations = [
            lambda d: d.update(unknown=True),
            lambda d: d.update(schema_version="1.0"),
            lambda d: d["nodes"][0].update(confidence=True),
            lambda d: d["nodes"][0].update(confidence=float("nan")),
            lambda d: d["nodes"][0].update(confidence=1.1),
            lambda d: d["nodes"][0].update(order=1),
            lambda d: d["nodes"][1].update(id="n1"),
            lambda d: d["nodes"][0].update(kind="unknown"),
            lambda d: d["nodes"][0].update(content="\x00"),
            lambda d: d["nodes"][0].update(content=""),
            lambda d: d["nodes"][0]["extra"].update(language="python"),
            lambda d: d["nodes"][3]["source_ref"].update(asset_id="untrusted-key"),
            lambda d: d["nodes"][3]["source_ref"].update(asset_id=None),
            lambda d: d["nodes"][3]["source_ref"].update(box=[2, 2, 1, 3]),
            lambda d: d["nodes"][3]["source_ref"].update(box=[0, 0, 1, 1], page=None),
            lambda d: d["nodes"][5]["extra"].update(rows=[["ragged"]]),
            lambda d: d["nodes"][5]["extra"].update(headers=[]),
        ]
        for i, mutate in enumerate(mutations):
            with self.subTest(case=i):
                document = copy.deepcopy(self.document)
                mutate(document)
                with self.assertRaises(ContractError):
                    validate_document(document, assets=self.assets, allow_proposed_media=True)

    def test_box_and_empty_document(self):
        self.document["nodes"][3]["source_ref"]["box"] = [0, 0, 10.5, 20]
        validate_xml(self.xml(), assets=self.assets, allow_proposed_media=True)
        self.document["nodes"] = []
        validate_xml(self.xml(), assets=self.assets)

    def test_whitespace_unicode_and_carriage_returns_survive(self):
        self.document["nodes"][1]["content"] = "  α < β & γ\r\n\tend  "
        document, _ = validate_xml(self.xml(), assets=self.assets, allow_proposed_media=True)
        self.assertEqual(document, self.document)

    def test_invalid_context(self):
        self.context["source"] = "\x01"
        with self.assertRaises(ContractError):
            self.xml()

    def test_invalid_xml(self):
        xml = self.xml().decode()
        variants = [
            xml.replace('<node ', '<node unexpected="x" ', 1),
            xml.replace('<content>', '<unknown>', 1),
            xml.replace('<extra>', '<content>duplicate</content><extra>', 1),
            xml.replace('confidence="0.8"', 'confidence="Infinity"', 1),
            xml.replace('<source_ref>', '<source_ref>mixed', 1),
            xml.replace('<item>', '<cell>', 1),
            xml.replace('<document ', '<document xmlns="urn:unknown" ', 1),
            '<!DOCTYPE document [<!ENTITY x "value">]>' + xml,
            xml + '<?unexpected value?>',
        ]
        for i, invalid in enumerate(variants):
            with self.subTest(case=i), self.assertRaises(ContractError):
                validate_xml(invalid, assets=self.assets, allow_proposed_media=True)

    def test_example_matches_fixture_and_context(self):
        data = (PIPELINE / "schema/example.xml").read_bytes()
        document, context = validate_xml(data, assets=self.assets, allow_proposed_media=True)
        self.assertEqual(document, self.document)
        self.assertEqual(context, self.context)


if __name__ == "__main__":
    unittest.main()
