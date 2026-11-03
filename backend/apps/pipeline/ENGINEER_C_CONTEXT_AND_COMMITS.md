# Engineer C: project context, work history and handoff

Last verified: **2026-11-03**, America/Indiana/Indianapolis.

This is a continuity guide for a new engineer, a new AI session or a reader without
programming experience. It does not override applicable `AGENTS.md` instructions,
the official [Engineer C brief](../../docs/engineer-c.md), or the user's instructions.
Flag conflicts rather than silently choosing a new rule. No applicable `AGENTS.md`
was found during the current inspection; check again before future work.

Paths below are relative to the actual Git repository, `AccessPath/`, unless a link
says otherwise. “Implemented” means code exists, not that a deployed service was
verified. “Planned” means required but not built. “Proposal” means awaiting agreement.

## 1. What AccessPath does

AccessPath aims to turn lecture documents into accessible web pages for blind and
low-vision students. A teaching assistant (TA) uploads materials and checks AI drafts.
A professor gives final approval. Students receive the resulting HTML, the format
used to describe web pages, for use with a screen reader.

For example, a mechanics lecture might show a force-versus-distance graph. A student
who cannot see the graph needs a useful written description of the axes, trend and
meaning of the area under the curve. AI drafts that explanation; people must review
it before publication. This complete journey is **planned**, not operational yet.

### Essential vocabulary

| Term | Plain-language meaning here |
| --- | --- |
| Backend | Server-side software that handles accounts, stored information and processing. |
| API (application programming interface) | Named requests through which the user interface asks the backend to do something or return information. |
| Database | Organized permanent records, such as classes, review decisions and node versions. |
| Worker | A separate program that performs slow jobs without keeping a web request waiting. |
| Queue | A waiting line of jobs for workers. |
| Markdown | Text with simple formatting marks, such as `#` for a heading. Conversion is intended to produce it from lecture files. |
| JSON | A structured text format with named fields and lists, used to exchange data. |
| XML | A structured text format with tags, such as `<content>`, used here for a saved document representation. |
| Schema | Rules defining which fields, values and structures a document may contain. |
| Node | One reviewable piece of lecture content: a paragraph, equation, picture or another supported kind. |
| Node version | One saved draft of a node's content, with its author and generation details. |
| Migration | A versioned instruction file that creates or changes database tables. A migration file is not proof it has been applied to a running database. |
| Branch | A named line of development in Git, the system that tracks source changes. |
| Commit | A saved Git snapshot with an identifier, author, date and message. Uncommitted edits are not part of that history. |
| Asset | An extracted file, such as a figure image or equation crop. |
| S3 key | The name locating a file inside object storage; it is not a public download link. |
| Model | In AI discussions, the system generating content; in Django code, a definition of a database record type. |
| Prompt | Instructions and context supplied to an AI model. |
| Fixture | Example data used for development or tests. “Synthetic” means invented, not extracted from a real lecture. |
| State machine | Code that specifies which review-status changes are allowed and who may request them. |

### What exactly is a node?

The shared definition is `backend/apps/review/models.py`. Its eight kinds are
**text, code, equation, image, graph, table, video and audio**. A declared kind does
not mean its processing or accessible export is implemented.

A Node record identifies its class, lecture and parsed source document. It also
holds its kind, ordering number, review state, confidence estimate, optional reviewer,
flag reason, source location and a pointer to the current NodeVersion. Source location
can describe a page, a rectangular crop and an asset key. Confidence can be absent
in the database; the draft contract currently requires a number from zero to one.

A NodeVersion holds the actual text or description in `content`, additional fields
in `extra`, a version number, human/AI author information, model name, prompt version
and a note. For the graph above, version 1 could describe the axes; version 2 could
add the area-under-the-curve explanation requested by a professor. The Node remains
the same reviewable item while its current-version pointer changes.

Old versions preserve what reviewers saw and what an export used. The documented
rule is append-only. The code rejects saving an existing version and enforces unique
version numbers per node. This is not a universal database immutability guarantee:
bulk updates/deletion are not comprehensively prohibited by that save method.

## 2. Architecture and ownership

The frontend is the browser-facing React/Vite application. On this branch it is a
login/signup and dashboard scaffold. Django and Django REST Framework supply the backend and
API. PostgreSQL is the intended full-stack database; local settings fall back to a
SQLite file. Celery supplies workers, with Redis holding queued work. S3 stores files;
MinIO provides an S3-compatible local substitute.

```text
Browser: React frontend (login/signup scaffold)
                  |
                  v
Django API / admin -----> database: records, content versions, review history
       |                 PostgreSQL or local SQLite
       |
       +----> shared storage helpers ----> private S3 / local MinIO: files
       |
       +----> Redis queues ----> Celery worker
                convert          B: conversion and PDF image extraction
                llm              C: Purdue processing and revision drafts
                export           E: HTML creation and accessibility checks
                                      |
                                      +--> Purdue GenAI Studio (text and image calls)
```

The diagram shows intended connections. Infrastructure configuration exists; it does
not demonstrate that jobs or external services are running. See
`backend/config/settings.py`, `backend/config/celery.py` and `backend/docker-compose.yml`.

| Engineer | Documented responsibility | Main directories and boundary |
| --- | --- | --- |
| A | Accounts, class membership and permissions, platform configuration and storage helpers | `backend/apps/accounts/`, `classes/`, `storage/`, and `backend/config/`; other lanes use public helpers. |
| B | Upload handling, conversion to Markdown and extraction of figures/equations | `backend/apps/uploads/`; supplies C's input. |
| C | AI drafts, confidence, model selection, node contract, revision and model-usage logging | `backend/apps/pipeline/`; new edits remain pipeline-only; D integration is deferred. |
| D | Review API, queues, edits, comments, approvals and review state rules | `backend/apps/review/`; calls C's public revision function. |
| E | Accessible HTML from approved content and accessibility checks | `backend/apps/exports/`; depends on C's content format and D's approved versions. |

The detailed responsibilities are in `backend/docs/engineer-a.md` through
`engineer-e.md`. The frontend team is a separate dependency for D's API consumers.

### Directory guide

```text
AccessPath/                         actual repository root
  .github/CODEOWNERS                lane ownership placeholders
  README.md                        project introduction
  frontend/                        browser application scaffold
  backend/
    README.md                      setup and required development checks
    docs/                          onboarding and engineer briefs
    config/                        Django settings, URLs and Celery setup
    docker-compose.yml             local database, queue, storage, web and worker
    requirements*.txt              shared Python dependencies
    pyproject.toml                 test and lint configuration
    apps/
      accounts/ classes/ storage/  A's platform applications
      uploads/                     B's input models and conversion entry point
      review/                      D's nodes, versions and review rules
      exports/                     E's export record and task
      pipeline/                    C's owned area
        models.py migrations/      model-usage table definition and creation history
        router.py                  inexpensive/strong model selection
        tasks.py service.py        processing and revision-draft tasks
        contract.py                pure validation/serialization code
        schema/                    proposed JSON schema, XML example and contract
        fixtures/                  synthetic draft-output examples on this branch
        tests/test_contract.py     focused contract tests
        ENGINEER_C_CONTEXT_AND_COMMITS.md  this continuity guide
```

### Where information lives

These are verified model fields and intended file locations, not an inventory of
objects in a live storage account.

| Information | Record/location | Current limitation |
| --- | --- | --- |
| Original upload | S3 object; `uploads.SourceFile.s3_key` plus name, type, checksum and size | Upload endpoint and task wiring now exist; B ownership checks remain incomplete. |
| Converted Markdown | S3 object referenced by `ParsedDocument.markdown_s3_key` | B converts Markdown and extracts embedded PDF images. |
| Extracted assets | S3 objects described by `ParsedDocument.assets` | Exact manifest and coordinate rules need agreement. |
| Generated XML | Proposed S3 snapshot referenced by `ParsedDocument.xml_s3_key` | C now uploads a validated initial snapshot; it is not rewritten after revision. |
| Nodes and drafts | Database `review.Node` and `review.NodeVersion` | C creates initial nodes/versions; D must wire revision completion. |
| Reviewer discussion and actions | Database `Comment` and `ReviewAction` | D review endpoints exist; AI completion transitions are still missing. |
| File/job progress | `SourceFile.status/error`; `ProcessingJob.stage/status/error/started_at/finished_at` | C now tracks its process stage and source completion/failure. |
| AI usage | Database `pipeline.LLMCall` | C logs each provider attempt, usage and latency; unknown cost is null. |
| Export | `exports.Export.html_s3_key` and `version_ids` | E renders approved versions, checks HTML and saves the export. |

Use `apps/storage/s3.py` for storage access. Its `class_key` helper builds names under
`classes/<class_id>/`; it does not itself prove that a caller is authorized for that
class. Permissions and trusted input resolution remain the caller's responsibility.

## 3. Current workflow (2026-11-02)

```text
A: accounts/classes/lectures -> B: upload to S3
                                      |
                           B: Markdown + PDF images
                                      |
                     C: Purdue text and vision drafts
                                      |
                         validated JSON -> XML in S3
                                      |
                  C: Node + first NodeVersion -> ta_review
                                      |
                     D: TA review -> professor review -> E: approved HTML
                                      |
                         D: send-back / regenerate
                                      |
                 NOT WIRED: call C's revise public function
                                      |
                      C: validated RevisionDraft (ready)
                                      |
                 D TODO: completion transition + C apply_revision atomically
```

B now queues C's processing task after saving ParsedDocument. The task validates
class-scoped input references, reads Markdown/assets, generates structured drafts,
constructs XML and initializes review nodes. It does not overwrite existing nodes.
E now renders current approved versions, including our content/extra shapes.

For a work-and-energy lecture, C asks the text model to preserve the explanation and
LaTeX equation, and asks the vision model to describe the actual graph image. Each
result is validated and stored as an initial AI version. The resolved asset_key is
saved so E can embed the original image. Human approval remains mandatory.

Revisions are deliberately staged: C prepares a draft against a specific version,
and discards results based on a version that changed. D must wire its endpoints,
add completion/failure state transitions, and call C's apply hook inside the same
transaction as its completion transition. C never changes an existing Node.state.

Claims, bounded provider retries, safe failure fields and S3/database limitations
are documented in [RUNNING.md](RUNNING.md). The full upload-to-export path has not
been exercised against live S3/Redis. SQLite tests and two synthetic Purdue calls
verify narrower behavior; they are not production readiness or accessibility proof.

## 4. Engineer C working rules and approved scope

- Intended working branch: **`track-c`**. Verified current branch on 2026-11-02:
  **`track-c`**. Original baseline: `a52b3260afb09a77ce37862b572997f4d2c09309`;
  fast-forwarded to integration `fbf53ca0c8165c00a1f58d751d296d291e7701ef`;
  the implementation delivery is recorded in section 6 below.
- Actual root: `/Users/Gaurav/Desktop/projects/access-path/AccessPath`. Its remote is
  `https://github.com/hankjacoby9-cpu/AccessPath.git`. The parent `access-path/` has a
  separate empty Git repository; do not confuse its history with this checkout.
- Preserve existing uncommitted work. Do not reset, overwrite, move or commit it
  merely to make the workspace look clean. Check status and branch before editing.
- The user approved the schema/contract increment first: JSON/XML drafts, serializer,
  validation, documentation, synthetic fixtures and focused tests, all inside
  `backend/apps/pipeline/`. Audio/video semantics must remain labeled proposals.
- That initial increment excluded processing and model calls. On 2026-11-02 the user
  authorized implementation using Purdue as the selected provider and integration
  as the baseline. When asked about D's integration changes, the user explicitly
  chose: keep edits in pipeline and document D's remaining work. This boundary remains.
- Provider configuration is pipeline-owned, read from Django-loaded environment
  variables. No shared settings, requirements or review files were edited. Installing
  integration's declared dependencies and local migrations does not change those files.
- The original guide-creation task was documentation-only. On 2026-10-26 the user
  subsequently authorized committing today's C work and pushing only `track-c`,
  including one final documentation commit to record the implementation hash.
  Do not push main, force-push, rewrite history, merge branches or open a pull request.
  Use the existing Git author configuration without AI attribution trailers.
- C's eventual brief includes prompts, node/version creation, confidence, revisions,
  model routing and usage logging. Those future responsibilities are not permission
  to extend the current increment without agreement.
- Use public cross-app entry points listed in `backend/README.md`. Team rules prohibit
  imports of other apps' internals, while C's brief requires shared model writes and
  supplies no persistence API. Flag that ambiguity; do not silently broaden access.
- Flag needed out-of-scope changes before editing. Keep API keys out of Git. Tests
  should fake AI responses; real-model evaluation is separate and requires an agreed
  scope/budget. Two synthetic Purdue generation calls were made on 2026-11-02;
  their cost is unreported, not assumed free. No course documents were sent.

## 5. Current status, decisions and validation

### What exists today

The current implementation adds Purdue configuration/client, versioned
prompts, input normalization/chunking, text and vision drafting, transactional initial
node publication, durable claims, usage/failure logging and revision drafts. See
[RUNNING.md](RUNNING.md) for public functions, commands and exact boundaries.

`models.py` and the pipeline-only 0002 migration add processing claims, revision drafts,
a shared provider throttle and richer LLMCall accounting. The local SQLite migrations
were applied. No shared Node/NodeVersion schemas changed.

The 0.1 contract still labels cross-team semantics as proposals. The user chose to
retain JSON plus XML and selected Purdue as the provider. Integration corrected the
LaTeX fixture and E now supports C's table, heading and transcript fields, but exact
ordering and review completion are not magically resolved by that merge.

### Decisions actually authorized versus open proposals

| Status | Decision or question | Reason / next owner |
| --- | --- | --- |
| Approved by user | Use the existing nested checkout and `track-c` after establishing the baseline | Preserve actual history and existing work. |
| Approved by user | Start with the contract increment, confined to pipeline | Give B/D/E a reviewable format before building processing. |
| Approved by user | Cover all declared kinds, label synthetic fixtures and unresolved media semantics | Avoid presenting invented samples or shapes as real support. |
| Repository requirement | Model returns structured JSON; application constructs XML | Explicit C brief and processing-task TODO. |
| Proposal | Exact content/extra fields, document-local order and asset-ID mapping | B/D/E have not confirmed them. |
| Open with B | Page markers, crop coordinates, stable asset references and manifest ownership | Necessary to trace descriptions back to source material. |
| Open with D | Shared-model access, AI completion/failure API, multi-document ordering and revision concurrency | Current interfaces cannot complete the intended lifecycle. |
| Open with E | Table/heading/description semantics, media accessibility and XML adoption | Structural validity alone does not ensure accessibility. |
| Approved by user | Implement C using Purdue; retain D-owned boundaries | C processing is implemented; D lifecycle remains a handoff. |

Two wording conflicts deserve explicit attention. `ParsedDocument` describes XML as
exactly what the model returned, contrary to C's JSON-to-XML requirement. Also,
CONTRACT.md says “no ... entities”; the code correctly supports ordinary escaped XML
characters and numeric references while rejecting DTD/custom-entity declarations.
This guide clarifies the observed behavior without changing either reference file.

### Real B input availability

The four Markdown samples and source files from B are now present following the
fast-forward to integration. All four Markdown fixtures are BOM-marked UTF-16; slide
samples contain slide markers/image references, while PDF text samples lack explicit
page markers. B's live conversion writes UTF-8. C supports both encodings and does
not fabricate missing page numbers. Full semantic evaluation of those samples is
still pending; the live smoke used synthetic input only.

### Validation record

Validation rerun before publication on 2026-11-03 (live smoke remains the 2026-11-02 result):

| Check | Outcome | Limit |
| --- | --- | --- |
| Pipeline tests | 49 passed, Python 3.12 | Fake provider/storage; simulated claim races rather than PostgreSQL concurrency. |
| Full backend suite | 197 passed, 1 failed | Same pre-existing export golden mismatch; baseline before new tests was 157 passed, 1 failed. |
| Pipeline Ruff | Passed | Whole-backend Ruff reports 8 existing errors outside pipeline. |
| Django system check | Passed | Does not verify deployed external services. |
| Migration drift | No changes detected after pipeline 0002 | Local SQLite migration applied; production database not touched. |
| Live Purdue smoke | Two successful calls; validated text/image nodes and generated XML | Synthetic text and red square only, no course data or S3. |
| Usage evidence | Text: 401 input / 675 output tokens; vision: 580 input / 146 output | Cost remains null because no verified rate is supplied. |

The default models used were `gpt-oss:120b` and `gemma4:26b-a4b`. Purdue inventory
reported 33 available models. The key was not printed or committed. The inherited
README's Anthropic instructions are stale relative to the team's provider decision.

Runtime setup now includes Python 3.12, integration requirements and system libmagic.
Full CI coverage remains unverified: the inspected repository has no workflow file.
The pre-existing golden failure is documented in INTEGRATION_NOTES.md and was not
silenced or repaired by changing another engineer's fixture.

## 6. Commit history and uncommitted work

### How history was verified

Inspected `git log --all`, path-filtered history for `backend/apps/pipeline/`, commit
summaries, branch containment, status, remotes and `git log track-c --not main`.
The checkout is not shallow (its local history is not deliberately truncated).
The initial audit found no C commits beyond main. The authorized contract commit
now exists and is recorded below; its files are no longer uncommitted. A final
documentation-only commit records that hash without attempting to record its own
future hash. Use `git log -1` for the final tip.

Author names alone do not establish an engineer's assigned role. The two pre-existing locally
available commits touching pipeline are recorded below as **relevant inherited or
cross-team history**, not attributed to Engineer C. Unfetched or inaccessible branches
and uncommitted work elsewhere are outside this history audit. Dates below are Git
author dates, both recorded with UTC−04:00 offsets.

### Relevant inherited history: backend scaffold

- **Hash:** `550d2f3d39cbf468ff89ac5896e870decd4b1a6a`
- **Date:** 2026-10-07 19:32:47 −04:00.
- **Title:** Add Django backend scaffold.
- **Author:** ethan Pravato; commit message includes a Claude co-author attribution.
- **Practical effect:** Gave the team common database definitions, application folders
  and callable placeholders from which each lane could start.
- **Reason supported by the commit message:** Establish the Django/DRF, Celery,
  PostgreSQL and S3 foundation for the backend rebuild.
- **Affected areas:** Backend-wide scaffold; within pipeline, the model-usage table,
  migration/admin setup, router, sample XML, task/service stubs and test package.
- **Validation:** No historical test execution result was verified. The commit adds
  tests in other areas; their existence does not establish that they passed then.
- **Limitations:** C's processing/revision remain placeholders. The message mentions
  CI, but a workflow is not present in the inspected checkout. This is shared scaffold
  history, not a verified Engineer C-authored delivery.

### Relevant cross-team history: lecture fixtures on B's branch

- **Hash:** `c672645c728f6eb03ab5ff6f83dbb1ecdc2f46d8`
- **Date:** 2026-10-13 17:18:57 −04:00.
- **Title:** Added sample lecture files.
- **Author:** James Lei.
- **Practical effect:** Makes four Markdown samples and corresponding source documents
  available for inspecting real conversion output instead of relying only on invented
  examples. Available on local `origin/track-b`, not incorporated into track-c.
- **Reason:** The title establishes sample provision; B's brief requests conversion
  samples for C. That connection is consistent with the brief, not a separately
  verified author statement about quality or acceptance.
- **Affected areas:** Eight files under `backend/apps/pipeline/fixtures/`: four `.md`,
  two `.pptx`, two `.pdf` files.
- **Validation:** File names, sizes and branch containment verified; content, encoding,
  conversion accuracy and historical test execution not verified.
- **Limitations:** No confirmed asset manifest or agreed B/C contract follows merely
  from these files existing. Do not merge B's entire branch as an incidental setup step.

### Engineer C delivery: draft contracts and continuity guide

- **Hash:** `dafe1ffe3041a191370098854abbb9ed53087fe1`
- **Git author date:** `2026-10-26T17:43:32-04:00`.
- **Title:** feat(pipeline): draft validated node contracts and Engineer C handoff.
- **Author:** gaurav <gaurav14rsm@gmail.com>, using the repository's existing configuration.
- **Practical effect:** Gives reviewers a concrete eight-kind node format, checks
  that reject malformed drafts, safely generated XML, and a standalone project guide.
- **Reason:** Establish C's first reviewable contract increment before implementing
  model calls or persistence; preserve the handoff outside conversation history.
- **Affected areas:** Eight files, all under `backend/apps/pipeline/`, listed below.
- **Validation:** Nine unit tests passed; independent schema/fixture validation,
  Python 3.12 syntax parsing on Python 3.14, Markdown links, credential-pattern
  review and staged whitespace checks passed. Full Django/pytest, Ruff, Python 3.12
  runtime and external integration checks remain unavailable or unperformed.
- **Limitations:** Cross-team contracts are proposals. Audio/video are gated draft
  shapes. Processing/revision/persistence remain stubs; B/D/E decisions remain open.

### Work included in the delivery commit

The following work began uncommitted and is now included in the commit above.

**2026-10-26: contract increment.** Practical effect: provides a reviewable example
format and checks for exchanging node drafts before AI or persistence is implemented.
The user authorized this narrower first increment to resolve cross-team assumptions.

| File | Change | Remaining limitation |
| --- | --- | --- |
| `contract.py` | New JSON validation and XML serialization/parsing | No model, storage, ownership or database integration. |
| `schema/nodes.schema.json` | New eight-kind draft schema | Provider compatibility and team approval pending. |
| `schema/example.xml` | Modified to illustrate the proposed uniform format | Breaking proposal, not agreed adoption. |
| `schema/CONTRACT.md` | New contract and proposed B/D/E handoffs | Open semantics explicitly remain unresolved. |
| `fixtures/synthetic-nodes.json` | New invented eight-kind draft output | Not real conversion evidence. |
| `fixtures/synthetic-assets.json` | New invented asset allowlist | Not an agreed B input manifest. |
| `tests/test_contract.py` | New focused tests | Validation results and limits recorded above. |

**2026-10-26: continuity guide (this file).** Practical effect: preserves architecture,
status, verified history, working boundaries and next steps outside chat history.
Authorized as documentation-only. No feature files were changed for this task, no
branch was switched and no commit was made. Its review checks are source/history
cross-checking, Markdown link checking and whitespace inspection; it introduces no
runtime behavior. Its original creation was uncommitted; the later commit/push
authorization covers this guide together with the contract increment.

**2026-10-26: pre-commit review (completed).** Verified the existing author configuration, clean
ownership boundary and GitHub destination. Remote main was at the original baseline;
remote track-c did not yet exist. All eight intended files are session-owned C work.
No unrelated work, credentials or generated clutter was identified. Available checks
passed as recorded above; no full backend, paid AI or accessibility evaluation was
run. B/D/E contract approval and lifecycle interfaces remain blockers. Next: review
B's existing samples, confirm the proposed handoffs, and agree the next increment.

### Engineer C delivery: Purdue processing and revisions (2026-11-03)

Practical effect: B's existing processing entry point now generates drafts and creates
reviewable nodes, instead of raising NotImplementedError. C also prepares and can
apply version-safe revision drafts through an explicit D integration contract.

New/changed pipeline areas: configuration.py, router.py, client.py, prompts.py,
drafting.py, processing.py, tasks.py, service.py, models.py, migration 0002, admin.py,
management commands, client/processing tests, RUNNING.md, this guide and the approved
shared `.env.example` update.

- **Hash:** `4dbabd9754a3afc40333518e588f0f5cfd39197f`
- **Date:** 2026-11-03 14:08:59 −05:00.
- **Title:** feat(pipeline): process documents and prepare revisions with Purdue GenAI.
- **Author:** gaurav <gaurav14rsm@gmail.com>, using existing Git configuration.
- **Reason:** Replace C's processing stub and provide a usable Purdue-based path from
  B's extracted content to reviewable nodes, plus version-safe revision drafts.
- **Validation:** 49 pipeline tests passed; full suite 197 passed / 1 known export
  golden failure. Pipeline Ruff, Django system and migration checks passed. Two
  successful synthetic live calls were recorded on 2026-11-02. Secret checks passed.
- **Limitations:** D must connect review completion; the C/E golden example remains
  unresolved. Real S3/Redis end-to-end and PostgreSQL concurrency tests remain pending.

Earlier `dafe1ff` and `b6472c7` remain historical C deliveries. The fast-forward
also brought in 37 existing integration commits; those are not new C-authored work.
A final documentation-only commit records this hash. Its own hash is intentionally
not recorded here to avoid an endless chain of logging commits.

All implementation changes remain inside pipeline. The user separately approved the
shared `backend/.env.example` update on 2026-11-03: Purdue variables with an empty
key and legacy Anthropic labels. The private `.env` was not changed by that edit. Local ignored `.venv`/SQLite state
was updated for dependencies, migrations and synthetic call logs. The API key remains
in ignored `.env`. Validation and limits are recorded above. Initial state is
`ta_review`; existing review states are never written by C. Reading-order fallback,
limits, retry behavior, draft-application prerequisites and S3 orphan possibilities
are documented in RUNNING.md as implementation choices, not implied team consensus.

### Publication review: 2026-11-03

The user authorized committing all pending C implementation/documentation and the
approved `.env.example` change, then pushing only track-c. Existing author identity:
`gaurav <gaurav14rsm@gmail.com>`. New commits have no AI attribution or co-author trailers.
Private `.env`, `.venv` and SQLite data remain ignored and untracked. Compared pending
files and 108 outgoing historical blobs against local credential values and selected
secret patterns; no matches were found. This is a targeted check, not a complete
application security audit. Existing integration history is preserved unchanged.

Pipeline tests, Ruff, Django system/migration checks passed. The known C/E export
golden mismatch remains the only full-suite failure. D endpoint/state integration,
real S3/Redis validation and PostgreSQL concurrency remain outstanding. No new live
model calls were needed for this publication review.

## 7. Prioritized next steps and handoff

- [x] Fast-forward track-c to the integration baseline while preserving the local key.
- [x] Confirm Purdue access and validate text/image structured outputs with synthetic inputs.
- [x] Implement initial processing, XML storage, asset-key mapping and node/version publication.
- [x] Implement bounded provider retries, call accounting and durable document claims.
- [x] Implement authenticated revision requests, ready drafts and guarded application hook.
- [x] Add focused mocked tests and reproduce the known integration test baseline.
- [ ] **D dependency:** wire send-back/regenerate to C; add completion/failure transitions;
  atomically complete state and call apply_revision. See RUNNING.md for exact steps.
- [ ] **C/E decision:** reconcile the eight-node XML and four-node golden HTML fixtures.
- [ ] **B dependency:** richer page/asset ordering and extraction, plus upload ownership checks.
- [ ] **Pending validation:** PostgreSQL concurrency, real S3/Redis processing and representative
  accessibility evaluation. Synthetic success does not complete these checks.
- [x] Review and commit the approved implementation and example configuration.
  Push only track-c; verify the remote tip after publication. The final execution
  report records push verification without adding another self-referential log commit.

## 8. Maintaining this guide

Future Engineer C work should update this document after meaningful changes and
after each commit. Keep the architecture, branch snapshot, current status, decisions
and next steps accurate. Preserve historical commit entries; correct errors with a
clear note rather than rewriting history as though old limitations never existed.

Move work from the uncommitted section into the commit history only after its commit
exists. Record the actual hash, author date, title, practical effect, reason, affected
areas, validation evidence and remaining limits. Use “not verified” when evidence
is unavailable. Do not invent test results from a commit message or assume authorship
means a particular lane. Avoid repeating the entire history in each update.

A commit cannot contain its own final hash. Record that hash in the next normal
working-tree update or meaningful commit; **do not create extra commits solely to
record this log's own latest hash**. Keep any pending update explicitly uncommitted.
Read-only reviews can update this guide only when the user's task permits editing it.

## Start here next session

1. Read the official C brief, applicable instructions, this guide and [RUNNING.md](RUNNING.md).
   The shared brief still mentions Anthropic; the user's Purdue decision supersedes that provider choice.
2. Verify track-c, HEAD and git status. Preserve any new local work; the Purdue implementation is now committed.
3. Run `pytest apps/pipeline/tests -q` and inspect the D handoff before adding more integration.
4. Coordinate D's completion API and the C/E fixture decision. Do not edit either lane without
   authorization. The next meaningful validation is a representative S3/Redis document run and
   PostgreSQL concurrency test, not another synthetic API call.
