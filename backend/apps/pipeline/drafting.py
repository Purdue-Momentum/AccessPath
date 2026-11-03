"""Pure handoff preparation plus provider orchestration. No node/state persistence."""

import base64
import copy
import json
import mimetypes
import re

from . import client, prompts
from .contract import SCHEMA, ContractError, validate_document
from .router import model_for

MAX_MARKDOWN_BYTES = 2_000_000
CHUNK_CHARS = 8000
MAX_CHUNKS = 100
MAX_ASSETS = 100


def scoped_key(key, class_id):
    prefix = f"classes/{class_id}/"
    if not isinstance(key, str) or not key.startswith(prefix) or any(p in {".", ".."} for p in key.split("/")):
        raise ContractError("Storage reference is outside the source class")
    return key


def asset_manifest(assets, class_id):
    if not isinstance(assets, list) or len(assets) > MAX_ASSETS:
        raise ContractError("Invalid asset list or too many assets")
    manifest = {}
    for i, asset in enumerate(assets, 1):
        if not isinstance(asset, dict):
            raise ContractError("Invalid asset entry")
        key = scoped_key(asset.get("key"), class_id)
        kind = asset.get("kind", "image")
        if kind not in {"image", "graph", "equation"}:
            raise ContractError("Unsupported asset kind; audio/video processing is not implemented")
        ref = {"page": asset.get("page"), "asset_id": f"a{i}", "box": asset.get("box")}
        probe = {"schema_version": "0.1-proposal", "nodes": [{
            "id": "n1", "order": 0, "kind": "image", "confidence": 0,
            "source_ref": ref, "content": "validation", "extra": {"long_description": "validation"},
        }]}
        validate_document(probe, assets={f"a{i}": {}})
        manifest[f"a{i}"] = {"key": key, "kind": kind, "source_ref": ref}
    return manifest


def chunks(raw):
    if len(raw) > MAX_MARKDOWN_BYTES:
        raise ContractError("Markdown exceeds processing size limit")
    try:
        text = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
    except UnicodeError:
        raise ContractError("Markdown must be UTF-8 or BOM-marked UTF-16") from None
    # Preserve slide markers; never infer PDF pages from form-feed-free text.
    parts = re.split(r"<!--\s*(?:Slide number|Page(?: number)?):\s*(\d+)\s*-->", text, flags=re.I)
    sections = [(None, parts[0])]
    sections.extend((int(parts[i]), parts[i + 1]) for i in range(1, len(parts), 2))
    result = []
    for page, section in sections:
        while section.strip():
            if len(section) <= CHUNK_CHARS:
                result.append((page, section))
                break
            cut = section.rfind("\n\n", 0, CHUNK_CHARS)
            if cut < CHUNK_CHARS // 2:
                cut = section.rfind("\n", 0, CHUNK_CHARS)
            if cut < CHUNK_CHARS // 2:
                cut = CHUNK_CHARS
            result.append((page, section[:cut]))
            section = section[cut:]
        if len(result) > MAX_CHUNKS:
            raise ContractError("Document has too many chunks")
    return result


def output_schema(kinds):
    schema = copy.deepcopy(SCHEMA)
    schema.pop("$schema", None)
    schema.pop("$id", None)
    branches = schema["properties"]["nodes"]["items"]["oneOf"]
    schema["properties"]["nodes"]["items"]["oneOf"] = [
        b for b in branches if b["properties"]["kind"]["const"] in kinds
    ]
    schema["properties"]["nodes"]["minItems"] = 1
    return schema


def image_block(data, key):
    mime = mimetypes.guess_type(key)[0]
    if mime not in {"image/png", "image/jpeg", "image/webp", "image/gif"}:
        raise ContractError("Provider image must be PNG, JPEG, WebP or GIF")
    if not data or len(data) > 8_000_000:
        raise ContractError("Image is empty or exceeds processing size limit")
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(data).decode()}"}}


def _messages(instruction, data, image=None):
    content = [{"type": "text", "text": instruction + json.dumps(data, ensure_ascii=False)}]
    if image:
        content.append(image)
    return [{"role": "system", "content": prompts.SYSTEM}, {"role": "user", "content": content}]


def draft_document(*, raw, manifest, context, load_asset, accounting, heartbeat=lambda: None):
    records = []
    for page, text in chunks(raw):
        heartbeat()
        result = client.complete(
            model=model_for("text"), messages=_messages(prompts.TEXT, {
                "lecture_context": context, "page": page, "markdown": text,
            }), schema=output_schema({"text", "code", "equation", "table"}),
            purpose="process", prompt_version=prompts.PROCESS_VERSION, **accounting,
        )
        validate_document(result.data, assets={})
        for node in result.data["nodes"]:
            # Page provenance is supplied by the adapter, not guessed by the model.
            node["source_ref"] = {"page": page, "asset_id": None, "box": None}
            records.append((node, result.model))
    for asset in manifest.values():
        heartbeat()
        result = client.complete(
            model=model_for("image"), messages=_messages(prompts.VISION, {
                "lecture_context": context, "source_ref": asset["source_ref"],
            }, image_block(load_asset(asset["key"]), asset["key"])),
            schema=output_schema({"image", "graph", "equation"}), purpose="describe_image",
            prompt_version=prompts.PROCESS_VERSION, **accounting,
        )
        validate_document(result.data, assets=manifest)
        if len(result.data["nodes"]) != 1:
            raise ContractError("An asset must produce exactly one node")
        node = result.data["nodes"][0]
        node["source_ref"] = dict(asset["source_ref"])
        records.append((node, result.model))
    if not records:
        raise ContractError("Document produced no reviewable content")
    # Sort by page only when all pages are known; otherwise retain insertion order.
    # This is an explicit fallback, not a claim to recover layout that B did not supply.
    if all(n["source_ref"]["page"] is not None for n, _ in records):
        records.sort(key=lambda r: r[0]["source_ref"]["page"])
    for i, (node, _) in enumerate(records):
        node.update(id=f"n{i + 1}", order=i)
    document = {"schema_version": "0.1-proposal", "nodes": [n for n, _ in records]}
    validate_document(document, assets=manifest)
    heartbeat()
    return document, [model for _, model in records]


def draft_revision(*, node, comment, context, manifest, load_asset, accounting):
    image = None
    asset_id = node["source_ref"]["asset_id"]
    if asset_id:
        asset = manifest[asset_id]
        image = image_block(load_asset(asset["key"]), asset["key"])
    result = client.complete(
        model=model_for("image" if image else "text"),
        messages=_messages(prompts.REVISION, {"node": node, "comment": comment, "lecture_context": context}, image),
        schema=output_schema({node["kind"]}), purpose="revise", prompt_version=prompts.REVISION_VERSION, **accounting,
    )
    validate_document(result.data, assets=manifest)
    if len(result.data["nodes"]) != 1:
        raise ContractError("Revision must produce one node")
    revised = result.data["nodes"][0]
    if revised["kind"] != node["kind"] or revised["source_ref"] != node["source_ref"]:
        raise ContractError("Revision changed node identity or provenance")
    return revised, result.model
