"""Pure, dependency-free validation and XML serialization of the proposed contract.

This is not an ingestion or persistence service. Audio/video require explicit opt-in.
"""

import json
import math
import re
from pathlib import Path
from xml.etree import ElementTree as ET

SCHEMA = json.loads((Path(__file__).parent / "schema/nodes.schema.json").read_text())
NODE_SCHEMAS = {s["properties"]["kind"]["const"]: s for s in SCHEMA["properties"]["nodes"]["items"]["oneOf"]}
XML_ATTRIBUTES = ("id", "order", "kind", "confidence")
CONTEXT_FIELDS = ("document", "lecture", "source", "prompt_version")


class ContractError(ValueError):
    """A proposed contract's structural or semantic constraint was violated."""


def _xml_text(value):
    return all(c in "\t\n\r" or 0x20 <= ord(c) <= 0xD7FF or 0xE000 <= ord(c) <= 0xFFFD
               or 0x10000 <= ord(c) <= 0x10FFFF for c in value)


def _check(value, schema, path):
    """Validate only the JSON Schema subset used by our checked-in schema."""
    for union in ("oneOf", "anyOf"):
        if union in schema:
            matches = 0
            for branch in schema[union]:
                try:
                    _check(value, branch, path)
                    matches += 1
                except ContractError:
                    pass
            if matches == 0 or (union == "oneOf" and matches != 1):
                raise ContractError(f"{path}: no unique valid shape")
            return
    types = schema["type"]
    types = types if isinstance(types, list) else [types]
    actual = {str: "string", dict: "object", list: "array", int: "integer", float: "number", type(None): "null"}
    kind = actual.get(type(value))
    if kind not in types and not (kind == "integer" and "number" in types):
        raise ContractError(f"{path}: expected {types}")
    if "const" in schema and value != schema["const"]:
        raise ContractError(f"{path}: wrong constant")
    if "enum" in schema and value not in schema["enum"]:
        raise ContractError(f"{path}: unknown value")
    if kind == "object":
        if set(value) != set(schema["properties"]):
            raise ContractError(f"{path}: missing or unknown fields")
        for key, child in schema["properties"].items():
            _check(value[key], child, f"{path}.{key}")
    elif kind == "array":
        if not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", len(value)):
            raise ContractError(f"{path}: invalid array length")
        for i, item in enumerate(value):
            _check(item, schema["items"], f"{path}[{i}]")
    elif kind == "string":
        if len(value) < schema.get("minLength", 0) or not _xml_text(value):
            raise ContractError(f"{path}: empty string or illegal XML character")
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            raise ContractError(f"{path}: invalid identifier")
    elif kind in ("integer", "number"):
        if (isinstance(value, float) and not math.isfinite(value)) or not (
            schema.get("minimum", value) <= value <= schema.get("maximum", value)
        ):
            raise ContractError(f"{path}: invalid numeric range")


def validate_document(document, *, assets, allow_proposed_media=False):
    """Validate JSON plus references against an application-supplied asset-ID mapping.

    Asset keys are deliberately neither accepted from the model nor dereferenced here.
    """
    _check(document, SCHEMA, "document")
    ids = set()
    for i, node in enumerate(document["nodes"]):
        if node["id"] in ids or node["order"] != i:
            raise ContractError("Node IDs must be unique; order must be contiguous from zero")
        ids.add(node["id"])
        kind, ref = node["kind"], node["source_ref"]
        if kind in {"audio", "video"} and not allow_proposed_media:
            raise ContractError("Audio/video semantics are proposals; explicit opt-in required")
        if kind in {"image", "graph", "audio", "video"} and ref["asset_id"] is None:
            raise ContractError(f"{kind} requires an asset reference")
        if ref["asset_id"] is not None and ref["asset_id"] not in assets:
            raise ContractError("Unknown asset reference")
        box = ref["box"]
        if box is not None and (ref["page"] is None or ref["asset_id"] is None
                                or min(box) < 0 or box[0] >= box[2] or box[1] >= box[3]):
            raise ContractError("Box requires page, asset and positive area in nonnegative coordinates")
        if kind == "table":
            extra = node["extra"]
            if not extra["headers"] or any(len(row) != len(extra["headers"]) for row in extra["rows"]):
                raise ContractError("Tables need headers and rectangular rows")


def _encode(parent, name, value):
    element = ET.SubElement(parent, name)
    if value is None:
        element.set("null", "true")
    elif isinstance(value, dict):
        for key, child in value.items():
            _encode(element, key, child)
    elif isinstance(value, list):
        for child in value:
            _encode(element, "item", child)
    else:
        element.text = str(value)


def to_xml(document, *, context, assets, allow_proposed_media=False):
    """Build UTF-8 XML; context is supplied by the application, never the model."""
    validate_document(document, assets=assets, allow_proposed_media=allow_proposed_media)
    _check(context, {"type": "object", "properties": {
        key: {"type": "string", "minLength": 1} for key in CONTEXT_FIELDS
    }}, "context")
    root = ET.Element("document", {"schema_version": document["schema_version"], **context})
    for node in document["nodes"]:
        element = ET.SubElement(root, "node", {key: str(node[key]) for key in XML_ATTRIBUTES})
        for key in ("source_ref", "content", "extra"):
            _encode(element, key, node[key])
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).replace(b"\r", b"&#13;")


def _decode(element, schema):
    if element.attrib == {"null": "true"} and not list(element) and not element.text:
        return None  # The shared JSON validator checks whether null is allowed.
    if element.attrib:
        raise ContractError("Unexpected XML attributes")
    if "anyOf" in schema:  # The sole non-null alternative is the box array.
        schema = next(s for s in schema["anyOf"] if s["type"] != "null")
    kind = schema["type"]
    if isinstance(kind, list):
        kind = next(k for k in kind if k != "null")
    if kind in {"object", "array"}:
        if (element.text or "").strip() or any((c.tail or "").strip() for c in element):
            raise ContractError("Mixed XML content is forbidden")
        if kind == "object":
            names = [c.tag for c in element]
            if len(names) != len(set(names)) or set(names) != set(schema["properties"]):
                raise ContractError("Missing, duplicate or unknown XML fields")
            return {c.tag: _decode(c, schema["properties"][c.tag]) for c in element}
        if any(c.tag != "item" for c in element):
            raise ContractError("Arrays contain only item elements")
        return [_decode(c, schema["items"]) for c in element]
    if list(element):
        raise ContractError("Scalar XML fields cannot have children")
    value = element.text or ""
    if kind == "integer":
        return int(value)
    if kind == "number":
        return float(value)
    return value


def validate_xml(data, *, assets, allow_proposed_media=False):
    """Validate application XML and return the equivalent JSON document and context.

    No DTDs, entities, comments, processing instructions or namespaces are part of this format.
    """
    try:
        text = data.decode("utf-8") if isinstance(data, bytes) else data
        text = re.sub(r'^<\?xml version=[^?]+\?>', '', text, count=1)
        if "<!" in text or "<?" in text:
            raise ContractError("XML declarations other than the initial XML header are forbidden")
        root = ET.fromstring(text)
        expected = {"schema_version", *CONTEXT_FIELDS}
        if root.tag != "document" or set(root.attrib) != expected:
            raise ContractError("Invalid document element or attributes")
        if (root.text or "").strip() or any((c.tail or "").strip() for c in root):
            raise ContractError("Mixed document content is forbidden")
        document = {"schema_version": root.attrib["schema_version"], "nodes": []}
        context = {key: root.attrib[key] for key in CONTEXT_FIELDS}
        for element in root:
            if element.tag != "node" or set(element.attrib) != set(XML_ATTRIBUTES):
                raise ContractError("Invalid node element or attributes")
            kind = element.attrib["kind"]
            if kind not in NODE_SCHEMAS:
                raise ContractError("Unknown node kind")
            properties = NODE_SCHEMAS[kind]["properties"]
            fields = {key: schema for key, schema in properties.items() if key not in XML_ATTRIBUTES}
            children = ET.Element("fields")
            children.text = element.text
            children.extend(element)
            node = _decode(children, {"type": "object", "properties": fields})
            node.update(element.attrib)
            node["order"] = int(node["order"])
            node["confidence"] = float(node["confidence"])
            document["nodes"].append(node)
        to_xml(document, context=context, assets=assets, allow_proposed_media=allow_proposed_media)
        return document, context
    except (ET.ParseError, UnicodeError, ValueError, TypeError, OverflowError) as exc:
        raise ContractError(f"Invalid XML contract: {exc}") from exc
