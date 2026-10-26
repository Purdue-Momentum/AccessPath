# Engineer C: project context, work history and handoff

Last verified: **2026-10-26**, America/Indiana/Indianapolis.

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
placeholder home screen. Django and Django REST Framework supply the backend and
API. PostgreSQL is the intended full-stack database; local settings fall back to a
SQLite file. Celery supplies workers, with Redis holding queued work. S3 stores files;
MinIO provides an S3-compatible local substitute.

```text
Browser: React frontend (currently a placeholder)
                  |
                  v
Django API / admin -----> database: records, content versions, review history
       |                 PostgreSQL or local SQLite
       |
       +----> shared storage helpers ----> private S3 / local MinIO: files
       |
       +----> Redis queues ----> Celery worker
                convert          B: conversion/extraction (planned on track-c)
                llm              C: AI processing/revision (planned)
                export           E: HTML creation (planned)
                                      |
                                      +--> Anthropic AI service (planned calls)
```

The diagram shows intended connections. Infrastructure configuration exists; it does
not demonstrate that jobs or external services are running. See
`backend/config/settings.py`, `backend/config/celery.py` and `backend/docker-compose.yml`.

| Engineer | Documented responsibility | Main directories and boundary |
| --- | --- | --- |
| A | Accounts, class membership and permissions, platform configuration and storage helpers | `backend/apps/accounts/`, `classes/`, `storage/`, and `backend/config/`; other lanes use public helpers. |
| B | Upload handling, conversion to Markdown and extraction of figures/equations | `backend/apps/uploads/`; supplies C's input. |
| C | AI drafts, confidence, model selection, node contract, revision and model-usage logging | `backend/apps/pipeline/`; current authorization covers contract work only. |
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
        tasks.py service.py        processing and revision stubs
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
| Original upload | S3 object; `uploads.SourceFile.s3_key` plus name, type, checksum and size | Upload workflow is not connected on this branch. |
| Converted Markdown | S3 object referenced by `ParsedDocument.markdown_s3_key` | Conversion task is a stub on track-c. |
| Extracted assets | S3 objects described by `ParsedDocument.assets` | Exact manifest and coordinate rules need agreement. |
| Generated XML | Proposed S3 snapshot referenced by `ParsedDocument.xml_s3_key` | Serializer exists locally; upload/persistence does not. |
| Nodes and drafts | Database `review.Node` and `review.NodeVersion` | Models and demo seeding exist; C does not create them yet. |
| Reviewer discussion and actions | Database `Comment` and `ReviewAction` | State-change helper exists; review endpoints are missing. |
| File/job progress | `SourceFile.status/error`; `ProcessingJob.stage/status/error/started_at/finished_at` | Status definitions exist; lifecycle ownership and updates are incomplete. |
| AI usage | Database `pipeline.LLMCall` | Fields for model, purpose, tokens, cache reads, cost and latency; no automatic recording yet. |
| Export | `exports.Export.html_s3_key` and `version_ids` | Task to create HTML is a stub. |

Use `apps/storage/s3.py` for storage access. Its `class_key` helper builds names under
`classes/<class_id>/`; it does not itself prove that a caller is authorized for that
class. Permissions and trusted input resolution remain the caller's responsibility.

## 3. Intended journey and actual implementation

```text
[IMPLEMENTED helpers/API] A: accounts, classes and lectures
                       |
[PLANNED connection] B: upload API -> original file in S3
                       |
[STUB on track-c] B: conversion/extraction -> ParsedDocument + Markdown/assets
                       |
[STUB] C: processing -> AI JSON -> validated XML -> Node + version 1
                       |              ^
                       |       [LOCAL DRAFT IMPLEMENTED]
                       |       contract validator/serializer only
                       v
[IMPLEMENTED helper; API missing] D: TA review -> professor review
                       |                               |
                       | send back                     | approve
                       v                               v
[STUB] C: revision -> new version           [STUB] E: approved lecture -> HTML
           |
[BLOCKED interface] return to TA review
```

1. **Set up the course (A).** Existing APIs manage accounts, classes and lectures.
   `Lecture.ta_context` stores the teacher's explanation of what students should learn.
   Only account/class routes are registered in `backend/config/urls.py` on track-c.
2. **Upload (B using A).** Planned upload endpoints obtain a short-lived S3 upload
   link from A's implemented helper. Completion should check the file and queue
   `uploads.tasks.convert_source_file(source_file_id)`. Those endpoints are absent
   here; a helper alone is not a working upload journey.
3. **Extract (B).** The task's TODO specifies MarkItDown conversion, figure/equation
   extraction, a ParsedDocument record, then queueing
   `pipeline.tasks.process_document(parsed_document_id)`. The checked-out function
   raises `NotImplementedError`, meaning it deliberately stops because it is unfinished.
4. **Draft and create nodes (C).** Planned inputs are Markdown, assets and lecture
   context. Structured AI JSON would be checked and converted to XML by application
   code. C would save the XML, nodes and first versions, and log every AI call.
   The task is still a stub. `router.py` already selects the inexpensive model for
   images/graphs and the strong model for other kinds, using settings.
5. **TA review (D).** The implemented `transition` helper permits approval from
   `ta_review` to `prof_review`, editing, flagging and regeneration. A professor may
   also perform the first review. Regeneration moves the state to `processing`;
   it does not itself trigger an AI call. Review API endpoints are still absent.
6. **Revision (D and C).** A professor can send a node back from `prof_review` to
   `revising`, with a required comment. D is intended to call `pipeline.service.revise`.
   That stub describes using the current draft, comment and lecture context to add
   a version and return to TA review. No completion transition currently supports
   that return; this is a D/C interface blocker.
7. **Final approval and export (D and E).** The helper permits only a professor role
   to move a node from `prof_review` to `approved`. Bulk approval is all-or-nothing
   and records an action for each node. E's planned export task must refuse a lecture
   unless all nodes are approved, render accessible HTML and save the exact version
   IDs used. Export triggering/API and rendering remain unfinished.

### Concrete example: work and energy

Imagine a PDF containing a paragraph, `W = ∫ F ds`, and a force/displacement graph.
B would retain the PDF, extract text to Markdown and save a graph crop with its page.
C would draft three nodes: text, equation and graph. The equation's content would
be LaTeX, a text notation for mathematical formulas; E would later convert it to
MathML, markup that represents mathematical structure for accessible reading.

Under the current **proposal**, the graph node contains short alternative text plus
`extra.long_description`, and references an allowlisted asset ID. “Allowlisted” means
it must identify an asset supplied with that document, not an invented storage path.
D's TA checks the description, then the professor asks for the area-under-the-curve
explanation. A future C revision adds a second version rather than replacing the
first. After another review and approval, E exports the selected version. This is
an illustration of the intended flow, not a successful integration test.

### Background work, failures and retries

Settings route upload tasks to `convert`, pipeline tasks to `llm`, and export tasks
to `export`. Docker Compose configures a worker to consume all three queues. This
lets slow processing happen outside an API request. Queues are configured, but the
stubs neither complete jobs nor provide a demonstrated background workflow.

The database defines failed/rejected states and error fields. The contract validator
raises `ContractError` for invalid input; it does not change job or node records.
There is no explicit retry policy in these task stubs, no implemented guarantee
against duplicate node creation when a task runs twice, and no complete AI failure
or success transition. Retry delays, partial-result cleanup, cost logging on failure,
concurrent revisions and who updates job/file status all need design agreement.
Do not infer those behaviors from the presence of Celery or status fields.

## 4. Engineer C working rules and approved scope

- Intended working branch: **`track-c`**. Verified current branch on 2026-10-26:
  **`track-c`**. Original baseline: `a52b3260afb09a77ce37862b572997f4d2c09309`;
  see the commit history below for subsequent C work.
- Actual root: `/Users/Gaurav/Desktop/projects/access-path/AccessPath`. Its remote is
  `https://github.com/hankjacoby9-cpu/AccessPath.git`. The parent `access-path/` has a
  separate empty Git repository; do not confuse its history with this checkout.
- Preserve existing uncommitted work. Do not reset, overwrite, move or commit it
  merely to make the workspace look clean. Check status and branch before editing.
- The user approved the schema/contract increment first: JSON/XML drafts, serializer,
  validation, documentation, synthetic fixtures and focused tests, all inside
  `backend/apps/pipeline/`. Audio/video semantics must remain labeled proposals.
- The user explicitly excluded processing, revision, persistence, state transitions,
  real model calls, shared dependencies and other engineers' code from that increment.
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
  scope/budget. No paid calls have been made in this work.

## 5. Current status, decisions and validation

### What exists today

The inherited pipeline scaffold has a model router, `LLMCall` model, initial migration
and admin registration. `tasks.py` and `service.py` remain stubs. Existing review
models and transition helpers are dependencies, not new C work.

The contract increment supplies `validate_document`, `to_xml` and
`validate_xml` in `contract.py`. These are pure functions: they validate data and
produce/read XML without storage, database or AI access. The schema describes all
eight kinds. Audio/video are rejected by default and require explicit opt-in for
exploring their proposed shapes; that is not operational media support.

The XML proposal changes the original example to uniform `content` and `extra`
fields. It is a proposed breaking format change. Full rules, field tables and
proposed database mappings are in [schema/CONTRACT.md](schema/CONTRACT.md). The JSON
schema has not been verified as directly usable with a provider's structured-output
API. The validator implements only the schema features used by this checked-in draft.

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
| Open with user/team | Next increment authorization, SDK compatibility and any dependency changes | No authorization to implement the full pipeline yet. |

Two wording conflicts deserve explicit attention. `ParsedDocument` describes XML as
exactly what the model returned, contrary to C's JSON-to-XML requirement. Also,
CONTRACT.md says “no ... entities”; the code correctly supports ordinary escaped XML
characters and numeric references while rejecting DTD/custom-entity declarations.
This guide clarifies the observed behavior without changing either reference file.

### Newly verified cross-branch input availability

Earlier inspection found no real B fixtures in the working tree, which remains true.
History inspection for this guide found them in the locally stored `origin/track-b`
reference: `document1.md` through `document4.md`, with two original PowerPoint files
and two original PDFs, under `backend/apps/pipeline/fixtures/`.

They were added in `c672645c728f6eb03ab5ff6f83dbb1ecdc2f46d8`. Their contents and
quality have not been evaluated here; Git reports the Markdown files as binary in
the change summary, so inspect encoding before assuming they are ordinary UTF-8.
They were not copied, merged or checked out. `origin/track-b` also contains later
upload/conversion work absent from track-c. A locally stored remote reference is
not proof of the current server state; no fetch was performed for this guide.

### Validation record

The contract checks were rerun before committing on 2026-10-26:

| Check | Recorded outcome | Limit |
| --- | --- | --- |
| Standard-library unit tests | 9 tests passed, including malformed-input subcases | Synthetic data; no integration or accessibility-quality proof. |
| Independent JSON Schema check | Schema and eight-kind fixture valid with installed `jsonschema` | `jsonschema` was not added as a project dependency. |
| Python 3.12 syntax parsing | Passed using Python 3.14 | Not a Python 3.12 runtime test. |
| `git diff --check` | Passed | Whitespace check, not runtime validation. |
| Markdown links and credential-pattern review | Passed; only eight intended pipeline files identified | Pattern checks are not a guarantee against every possible secret. |
| Full pytest/Django suite and Ruff | Not run: tools/dependencies absent in the inspected environment | Must run in the supported development environment later. |
| PostgreSQL, S3, worker and real AI integration | Not run | No end-to-end pipeline exists yet. |

For the contract-only tests, run from the actual repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend python3 -m unittest discover -s backend/apps/pipeline/tests -v
```

`backend/README.md` documents Python 3.12 setup and broader Ruff, pytest, migration
and OpenAPI checks. Do not run setup/seed commands blindly: setup creates files and
the seed command deletes/recreates its demo class. The README claims CI exists,
but the inspected `.github/` contains CODEOWNERS and no workflow. Treat CI coverage
as unverified rather than promising it. These test outcomes belong to the previous
increment, not to the historical scaffold commits below.

## 6. Commit history and uncommitted work

### How history was verified

Inspected `git log --all`, path-filtered history for `backend/apps/pipeline/`, commit
summaries, branch containment, status, remotes and `git log track-c --not main`.
The checkout is not shallow (its local history is not deliberately truncated).
`track-c` has no commits beyond main. No commit can be verified as a commit made by
this Engineer C effort. The new contract work is still uncommitted.

Author names alone do not establish an engineer's assigned role. The two locally
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

### Uncommitted work log — separate from commits

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

**2026-10-26: pre-commit review.** Verified the existing author configuration, clean
ownership boundary and GitHub destination. Remote main was at the original baseline;
remote track-c did not yet exist. All eight intended files are session-owned C work.
No unrelated work, credentials or generated clutter was identified. Available checks
passed as recorded above; no full backend, paid AI or accessibility evaluation was
run. B/D/E contract approval and lifecycle interfaces remain blockers. Next: review
B's existing samples, confirm the proposed handoffs, and agree the next increment.

## 7. Prioritized next steps and handoff

Labels describe status, not permission to execute future work automatically.

- [x] **Completed:** Establish the correct repository and create track-c. The nested
  checkout has real history; current branch and commit are recorded above.
- [x] **Completed draft:** Build contract shapes, validator, serializer, synthetic
  examples and focused tests. Complete as a local proposal, not a team-approved format.
- [x] **Completed documentation:** Create this continuity guide and audit available
  history without committing or changing other files.
- [ ] **In progress — contract review:** Resolve the open field/format decisions in
  CONTRACT.md with B/D/E. Complete when each accepted decision has a recorded source
  and unresolved fields remain clearly labeled; approval to draft is not approval
  of every proposed field.
- [ ] **Pending, first actionable follow-up:** Read B's existing fixture blobs on
  `origin/track-b` without changing branches. Check encoding, page/asset information
  and representability in the draft. Complete with a small evidence-backed mismatch
  list; importing samples or changing the contract requires a scoped follow-up.
- [ ] **Pending — development validation:** Establish the documented Python 3.12
  environment, then run Ruff, contract tests and applicable backend checks. Coordinate
  setup/dependency changes outside C's folder. Complete when results and limitations
  are recorded, not simply when dependencies install.
- [ ] **Blocked for integration — D lifecycle:** Agree on public completion/failure
  transitions and ownership of authorization/status updates. Complete when the
  responsible engineer supplies an agreed interface; do not bypass state rules.
- [ ] **Pending approval — model adapter and prompts:** After contract review, propose
  a narrow increment using fake model responses and versioned prompts. Depend on a
  tested SDK/schema approach and real input samples. Complete with deterministic tests
  for valid outputs, refusal, truncation and errors, without paid calls by default.
- [ ] **Later — processing, persistence and revision:** Agree on repeated-job safety,
  version numbering, concurrent edits, cost accounting and S3/database failure handling.
  Complete only when tests verify those behaviors against the agreed interfaces.
- [ ] **Later — evaluation and export handoff:** With B's real samples and E's rubric,
  assess meaning and accessibility, not just document shape. Real calls need an agreed
  budget; accessible media requires its own design.

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

1. Read `backend/docs/engineer-c.md`, applicable instructions, this guide and
   [schema/CONTRACT.md](schema/CONTRACT.md). Inspect `contract.py` and its tests.
2. Verify the nested Git root, current branch, `git status`, HEAD and available remote
   references. Preserve any local changes. Do not infer a
   clean checkout or updated remote state from this dated snapshot.
3. Next actionable task: review the four B fixtures already available in local
   `origin/track-b` and report contract mismatches without merging or switching branches.
4. Decisions needed from the user/team: who confirms B/D/E handoffs, whether to adopt
   the proposed breaking XML shape, how to incorporate B's samples, and authorization
   for the next implementation increment. Full pipeline implementation remains deferred.
