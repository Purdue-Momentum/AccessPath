# Node contract 0.1-proposal

**Draft for B, C, D and E review, not an agreed cross-team interface.** Nothing in
this increment processes documents, persists rows, changes states or calls a model.
`example.xml` and both files in `../fixtures/` are entirely synthetic; they are not
MarkItDown output or evidence of accessibility quality. Audio/video are proposals,
not supported processing capabilities.

## Repository-backed requirements

- `docs/engineer-c.md` assigns C the XML format, structured JSON generation,
  application-built XML, initial Node/NodeVersion creation and call logging.
- `apps/uploads/models.py` supplies ParsedDocument.markdown_s3_key and assets;
  the illustrative asset fields are key, kind, page and box.
- `apps/review/models.py` declares text, code, equation, image, graph, table, video
  and audio. Node holds order, confidence and source_ref. NodeVersion holds content,
  extra, model and prompt_version; versions are append-only.
- `apps/classes/models.py` supplies lecture ta_context.
- `docs/engineer-e.md` calls for short image alt text, longer descriptions, equation
  MathML at export, and table headers. E owns rendering and accessibility acceptance.
- The pipeline task requires XML validation and S3 storage. The uploads comment
  saying XML is exactly the model response conflicts with application-built XML.
  This proposal follows C's explicit JSON-to-XML requirement; B must confirm.

Everything below is a proposal unless explicitly tied to those requirements.

## JSON contract and application context

`nodes.schema.json` is a Draft 2020-12 JSON Schema, with discriminated branches for
all eight kinds. It describes an interchange format, **not a verified provider API
request schema**. A later model adapter must test or adapt it to provider-supported
schema features. `contract.py` validates the subset used here with the standard
library; it also enforces semantic rules JSON Schema alone does not express.

The root has exactly `schema_version` (literal `0.1-proposal`) and `nodes` (array).
Every node has exactly these fields; nullable fields remain present:

| Field | Proposed rule |
| --- | --- |
| id | Document-local identifier matching `n[1-9][0-9]*`; unique, not a database UUID |
| order | Zero-based, contiguous array position within this document |
| kind | One of the eight shared Node kinds |
| confidence | Finite number from 0 to 1; model estimate, not calibrated probability |
| source_ref | Exactly page, asset_id and box |
| content | Nonempty string interpreted according to kind; never trusted HTML |
| extra | Exactly the kind-specific fields below; no unknown fields |

`page` is a one-based integer or null when unknown/not applicable. `asset_id` is
an opaque input-manifest ID or null, never a model-generated storage key or URL.
`box` is null or four finite nonnegative numbers `[x0,y0,x1,y1]` with positive area;
a box requires both page and asset_id. Proposed coordinate convention: original
page units, top-left origin, before crop resizing. Units, rotation and scaling must
be settled with B; this validator cannot verify bounds against a real page.

Asset IDs must be present in the application's `assets` mapping. Image, graph,
audio and video require an asset; other kinds may reference one. The validator
checks membership only: it does not authenticate a manifest, validate its values,
fetch S3 objects or prove asset-kind/page compatibility. The future adapter must
construct this allowlist from the same document's trusted B handoff and check class
ownership. A PDF image crop may represent a graph or equation, so asset kind need
not equal node kind.

Application context is separate from model JSON: exactly `document`, `lecture`,
`source` and `prompt_version`, all nonempty strings. Proposed meanings: parsed
Document UUID, Lecture UUID, original filename (display only), and generating
prompt version. Synthetic example IDs intentionally are not real UUIDs. UUID and
ownership verification belong to a later integration layer, not this serializer.

## Content and proposed NodeVersion mapping

All rows map JSON `content` to NodeVersion.content and `extra` to NodeVersion.extra,
without conversion or whitespace trimming. JSON strings must contain legal XML
1.0 characters. Generated HTML must still be escaped/sanitized by E.

| Kind | content | Exact extra fields |
| --- | --- | --- |
| text | Plain paragraph or heading text | heading_level: null or integer 1–6 |
| code | Literal code, including whitespace | language: nonempty string |
| equation | LaTeX source, without display delimiters | empty object |
| image | Short alt text | long_description: nonempty string |
| graph | Short alt text | long_description: nonempty string |
| table | Caption | headers: nonempty array of nonempty strings; rows: arrays of strings |
| audio — proposal only | Recording title/summary | transcript: nonempty untimed text |
| video — proposal only | Clip title/summary | transcript and visual_description: nonempty untimed text |

Tables must be rectangular. Empty data rows are allowed. Merged cells, multi-level
headers, row headers, inline text semantics, decorative images and blank captions
are not expressible yet; E must confirm the first-version subset. Media proposals
omit timestamps, caption tracks, speaker identity and synchronization, so they
cannot establish accessible audio/video support. Validation and serialization
reject media by default. `allow_proposed_media=True` is only an explicit opt-in to
explore these draft shapes; the synthetic example uses it.

Other proposed persistence mappings (not implemented):

- kind/confidence/order map to Node fields. Document/class/lecture come from trusted
  application context, not model output. Document-local order needs a D/E decision
  on ordering across multiple source files in one lecture.
- source_ref.page and box retain their values; asset_id resolves through B's manifest
  to source_ref.asset_key. Whether to retain asset_id too needs agreement.
- New initial versions would have number=1, author_type=ai and provider-reported
  model plus prompt_version. No database identity is inferred from a local node ID.
- Per-kind calls may use different models. This contract does not yet represent
  per-node call provenance; the later adapter/persistence design must supply it.
- xml_s3_key would refer to this validated, application-generated snapshot. Whether
  revisions produce new XML snapshots is unresolved; E should read current approved
  versions as its brief specifies, not assume initial XML stays current.

## XML vocabulary

UTF-8 XML 1.0, no namespaces, DTDs, entities, comments or processing instructions.
The initial XML declaration is permitted. `to_xml` returns bytes using ElementTree
escaping; `validate_xml` parses and applies the same structural/semantic checks as
JSON. There is no XSD or external XML dependency. The executable validator plus
this vocabulary define the proposed XML contract.

| Element | Attributes | Contents |
| --- | --- | --- |
| document | schema_version, document, lecture, source, prompt_version (all required) | zero or more node elements in reading order |
| node | id, order, kind, confidence (all required) | exactly one source_ref, content and extra |
| source_ref | none | exactly one page, asset_id and box |
| page, asset_id | `null="true"` only when null | scalar text otherwise |
| box | `null="true"` only when null | otherwise four item elements containing coordinates |
| content | none | escaped character data, preserving content whitespace |
| extra | none | exact fields for that kind from the preceding table |
| heading_level | `null="true"` only when null | integer text otherwise |
| language, long_description, transcript, visual_description | none | string text |
| headers | none | item elements containing header text |
| rows | none | item elements for rows, each containing item elements for cells |
| item | none | scalar text or nested items as specified above |

Null elements have no content. Empty objects/arrays use empty elements. Required
fields cannot be omitted. Unknown/duplicate elements or attributes are rejected;
scalar elements cannot contain markup. Formatting whitespace between container
children is permitted, but mixed content is rejected. Field order within objects
is not semantic; array and node order is semantic. Serialization is not intended
as a cryptographic canonicalization format. Empty documents are structurally valid;
whether conversion to zero nodes is an operational error remains a pipeline policy.

This replaces the original illustrative XML (`latex`, `description`, nested `code`,
and page/asset attributes) with a uniform content/extra mapping. **It is a proposed
breaking format change**, not an agreed migration. D/E must review before adoption.

## Handoffs and blockers to confirm

### B: input and provenance

Supply real Markdown, stable source/page markers and an asset manifest. Proposed
C adapter assigns stable local IDs to B asset entries, preserving key, kind, page
and box; it does not require B to silently adopt the synthetic manifest format.
Agree on Markdown reading order, missing page treatment, crop units/rotation,
asset MIME types and equation/graph discovery. Synthetic fixtures demonstrate only
the output contract and asset allowlist, not a production ingestion contract.

### D: model mapping and lifecycle

Confirm metadata fields, multi-document ordering, unknown confidence policy and
access to shared models. The existing public state machine lacks AI completion and
failure transitions; it cannot currently complete processing/revision without an
interface addition. This increment deliberately leaves that out-of-scope blocker
untouched. Authorizing requests, revision concurrency and idempotent persistence
also remain for a subsequent agreed design.

### E: accessibility and export

Confirm text structure, image/graph descriptions, table subset and equation inputs.
Review the breaking XML proposal and agree on a rubric before evaluating generated
content. Audio/video require a separate accessibility and extraction design.

### Shared configuration

No dependencies change here. Provider SDK compatibility and model configuration
must be established before a later model adapter increment; changes to shared
requirements/settings need explicit coordination outside C's folder.

## Validation

From the repository root, without Django, pytest, S3 or API credentials:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend python3 -m unittest discover -s backend/apps/pipeline/tests -v
```

These unittest tests are also discoverable by pytest once the backend development
environment is installed. Tests cover eight-kind round trips, media opt-in, JSON
shape and semantic rejection, escaping, references, table shape and hostile/malformed
XML. `jsonschema` can independently check the fixture against nodes.schema.json,
but it is not a new runtime dependency. Full backend checks remain those in the
backend README; contract-only success does not establish pipeline integration.
