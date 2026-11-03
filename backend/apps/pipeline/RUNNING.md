# Running Engineer C's Purdue pipeline

Implemented on top of integration commit `fbf53ca`, 2026-11-02. All new source edits
are inside `apps/pipeline/`. Purdue GenAI Studio is the selected provider; there is
no fallback to Anthropic. The old shared Claude settings are ignored by C's adapter.

## Configuration and startup

Django already reads `backend/.env`; pipeline-owned configuration reads the resulting
environment without changing shared settings or dependency files. Add the key only
to the ignored `.env`, never a committed file:

```dotenv
GENAI_API_KEY=your-private-key
# Optional defaults (these models passed the small synthetic smoke check):
GENAI_TEXT_MODEL=gpt-oss:120b
GENAI_VISION_MODEL=gemma4:26b-a4b
GENAI_BACKEND=vllm
```

`GENAI_BACKEND=ollama` selects the alternate schema request format when using an
Ollama-hosted model. Do not mix backend types with one setting. The endpoint is fixed
to the official Purdue HTTPS endpoint; redirects are not followed with credentials.
Restart web/worker processes after changing environment variables.

From `backend/`, with Python 3.12 and integration's requirements installed:

```sh
source .venv/bin/activate
python manage.py migrate
celery -A config worker -Q convert,llm,export -l info
```

The web server is a separate process. Real ingestion also needs Redis and configured
S3/MinIO with an existing bucket; SQLite plus `runserver` alone does not supply those
services. The integration branch requires system libmagic in addition to its Python
package (installed locally during this increment). Use PostgreSQL for concurrent
workers; SQLite's coarse locking is suitable for local sequential development only.

B already queues `apps.pipeline.tasks.process_document(parsed_document_id)` after
saving Markdown and its asset manifest. For an existing real ParsedDocument:

```sh
python manage.py process_document DOCUMENT_UUID          # enqueue; requires broker
python manage.py process_document DOCUMENT_UUID --inline # synchronous; real Purdue/S3 calls
```

The demo seed has no real Markdown object in S3 and is not valid processing input.
No upload-to-S3 live end-to-end test was run in this increment.

## What processing now does

1. Claim one durable ProcessingRun for the document. A token and expiring lease keep
   duplicate/late workers from publishing competing results.
2. Validate source/class/lecture consistency and require class-scoped Markdown/asset
   keys. Refuse to replace existing nodes, including approved or edited work.
3. Create the `process` ProcessingJob; set source progress to processing.
4. Decode UTF-8 or BOM-marked UTF-16. Preserve B's explicit slide/page markers.
   Split into bounded chunks and ask the text model for text/code/equation/table nodes.
5. For each supplied image asset, send actual bytes to the vision model and obtain
   one image/graph/equation node. Never invent descriptions from filenames alone.
6. Validate structured results, assign document-local IDs/order, generate XML and
   write an attempt-specific S3 snapshot.
7. In a transaction, append Node and first AI NodeVersion records, point each node
   to its version, publish the XML key, and mark source/job/run successful.
   New nodes start in `ta_review`; this is initialization, not a transition of an
   existing node. Existing review states are never modified by C.

Persisted `source_ref` contains page, box, local asset_id and the resolved asset_key.
E's existing renderer consumes asset_key and therefore can load the actual figure.
XML remains the initial processing snapshot; revisions do not rewrite it. E reads
current approved versions from the database.

Within a document, known pages are sorted only if every node has a known page;
text precedes images on the same page. Otherwise text-chunk order followed by asset
order is retained. This is a documented fallback, not reconstructed layout. B still
needs to supply richer text/asset positions for exact ordering. Database order is
appended across documents under a lecture lock, so separate documents do not collide;
completion order is not necessarily upload order. These are implementation policies
for review, not previously confirmed cross-team decisions.

## Limits, retries and accounting

- Limits: 2 MB Markdown, 100 chunks, 8,000 characters per chunk, 100 assets, 8 MB per
  image, and a 4 MB provider response. PNG/JPEG/WebP/GIF images only. Audio/video
  processing remains disabled. Size violations fail explicitly instead of truncating.
- Paragraph/newline splitting prefers boundaries, but an oversized block can be split
  within code or math. Semantic reconstruction of such blocks is not guaranteed.
- HTTP timeout is 120 seconds. Network errors, HTTP 429/5xx and Purdue JSON-null
  responses get at most three attempts with backoff. Refusal, truncation, invalid
  structured output and other HTTP errors fail explicitly.
- A database-backed per-key slot limits calls made by this application to one every
  3.2 seconds across workers sharing that database. Calls made elsewhere with the same
  key are not counted locally; provider throttling must still be handled.
- Each actual attempted request has an LLMCall, including failed attempts, reported
  token counts when present, latency, provider/model and request ID. No key or source
  prompt is stored there. Cost is null when no verified tariff is available, not zero.
  A crash can leave a call marked started; usage for that interrupted call is unknown.
- Provider-call retries may repeat inference. Node publication is protected, not an
  exactly-once promise for network calls. A failed document can be explicitly queued
  again. Successful documents are a no-op on duplicate delivery.
- Active duplicate jobs are deferred by Celery; expired leases can be reclaimed on
  redelivery/requeue. There is no periodic sweeper. A broker-lost job must be requeued
  manually. Heartbeats refresh the 15-minute lease between model calls.
- S3 and the database are not one transaction. A crash after snapshot upload may leave
  an unreferenced attempt object; no automatic S3 garbage collector is implemented.
- PostgreSQL locking/concurrent-worker behavior has not been load-tested. Sequential
  SQLite tests exercise claims and simulated stale-worker cases.

## Revision API and Engineer D's remaining work

The user explicitly kept D's files out of scope. No review endpoint/state-machine
edits were made. Send-back/regenerate endpoints therefore still do not invoke C.

Public C functions in `service.py`:

- `revise(node_id, comment, requested_by=user)` verifies active membership and expected
  state, records the base version, and queues a draft after transaction commit. For
  `revising`, the requester must be a professor and the comment nonempty. `processing`
  supports regeneration by an active member. Identical pending requests reuse the ID.
- `revision_status(revision_id, requested_by=user)` returns authorized status, safe
  error, base version and the validated payload when ready.
- `apply_revision(revision_id)` appends an AI NodeVersion and updates current_version
  and confidence. It requires an existing transaction, a ready draft, an unchanged
  base version and a node already transitioned to `ta_review` by D. It never writes
  Node.state. This is an internal integration hook, not an authorization endpoint.

D must implement the following through its public state machine:

1. In the send-back/regenerate transaction, record the permitted action then call
   `revise`. C queues work on commit. If publishing to the broker fails after commit,
   the draft remains queued; retry the task for that draft ID. A durable task outbox
   is not included in this increment.
2. Add authorized system success/failure transitions from processing/revising.
3. On a ready draft, atomically lock the node, transition it to TA review through D's
   helper, then call `apply_revision`. Let errors roll back the whole transaction;
   do not catch and swallow apply errors inside it. This preserves history and avoids
   exposing a completed state with an unapplied draft.
4. Handle failed/stale results and expose status/retry behavior. C does not move failed
   revision nodes back to review or overwrite intervening human edits.

Preparing a revision writes only a RevisionDraft; the old NodeVersion and current
pointer remain unchanged until D applies it. Changing the current version during AI
work causes the result to be marked stale. Removed requesters are rejected before
inference. D remains responsible for authorization at its completion entry point.

## Testing and live smoke check

```sh
pytest apps/pipeline/tests -q
ruff check apps/pipeline
python manage.py makemigrations --check --dry-run
```

Unit/integration tests mock all provider and storage calls. For a deliberate live
check with only synthetic text and a programmatically generated red square:

```sh
python manage.py genai_smoke --run-live --class-id CLASS_UUID
```

This makes two logical calls (up to three attempts each), logs usage against the
specified class, validates the JSON and generated XML, and prints synthetic content.
It creates no nodes or S3 objects. The 2026-11-02 run succeeded with both default
models: correct work/force text and a red-square description. This is compatibility
and a minimal semantic check, not a representative accessibility evaluation.

## Outstanding integration work

- D: endpoint wiring and completion/failure lifecycle described above.
- B: exact text/asset reading order, slide-image and equation-crop extraction, and
  the upload handler's missing explicit class/lecture ownership checks.
- C/E: choose a shared example or separate the export golden fixture. The existing
  eight-node XML versus four-node golden HTML failure is unchanged, not hidden.
- Team: full quality evaluation on approved representative materials; PostgreSQL
  concurrency and real S3/Redis end-to-end validation; deployment credential ownership.
