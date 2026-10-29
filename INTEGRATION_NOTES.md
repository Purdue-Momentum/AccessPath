# Integration branch notes

This branch (`integration`) merges all active track branches on top of `main`
so the team has one comprehensive, bootable branch ahead of the demo.

## Branches merged

- `track-c` — pipeline contracts / schema
- `track-a` — classes: invites, lectures, cross-class isolation, security hardening
- `track-b` — uploads: file-conversion pipeline
- `track-e` — exports: rendering, accessibility, read-aloud (speech)
- `feature/auth-ui` — React frontend: login / signup wired to backend auth
- `feature/engineer-d-review-endpoints` — review: serializers, views, urls

## Fixes applied during integration (committed on this branch)

All owning engineers approved their part.

1. **requirements.txt**: `python-magic-bin==0.4.27` → `python-magic==0.4.27`.
   `python-magic-bin` has no installable distribution on macOS / modern Python.
   `python-magic` is API-compatible (same `import magic`, same `from_buffer`),
   but binds to the system `libmagic` (macOS: `brew install libmagic`;
   Debian/Docker: `apt-get install libmagic1`). Approved by track-b.
2. **apps/uploads/tests/test_upload_files.py**: patch target changed from
   `apps.storage.s3.put_bytes` to `apps.uploads.views.put_bytes` (patch where the
   name is used, not where it is defined). Fixes import-order mock flakiness that
   made the test pass alone but fail in the full suite. Per track-b.
3. **apps/pipeline/schema/example.xml** + **apps/pipeline/fixtures/synthetic-nodes.json**:
   node n3 equation set to canonical single-backslash LaTeX
   `W = \int_{s_1}^{s_2} F \cos\theta \, ds` so the pipeline contract and the
   exports renderer agree. Approved by track-c and track-e.

Trivial additive merge conflicts in `config/urls.py` and `requirements.txt`
were resolved by keeping all sides (each app registers its own URL include /
dependency).

## Test status

Full backend suite: **157 passed, 1 failed.**

### Known issue (1) — `apps/exports/tests/test_golden.py::test_example_xml_matches_the_golden_page`

NOT a merge break and NOT in track-a's scope. Owned by track-c and track-e.

- The **equation now matches** on both sides (byte-identical MathML + read-aloud
  line). Our equation fix resolved the original double-backslash `ExportError`.
- The remaining mismatch is a **cross-app fixture-coupling disagreement**:
  track-c's `example.xml` is a generic 8-node synthetic document (text, code,
  equation, image, graph, table, audio, video), while track-e's golden
  `example.html` is a hand-authored 4-node realistic Work-and-Energy lecture
  with different intro text, different code, and different figures. The two were
  authored independently and were never reconciled into one shared fixture.
- **Decision needed from C and E** (not to be patched unilaterally): should the
  exports golden test render the pipeline's `example.xml`, or should exports keep
  its own standalone example and not depend on track-c's fixture? The latter
  decouples the two apps' tests, which may be the cleaner design.

Until that decision is made, this single failure is expected and documented.

## Running the demo locally

Two long-running processes (run each in its own terminal):

```bash
# Backend (from backend/, with the venv active)
python manage.py migrate      # first time
python manage.py seed_demo    # first time — creates demo accounts
python manage.py runserver    # http://localhost:8000

# Frontend (from frontend/)
npm install                   # first time
npm run dev                   # http://localhost:5173
```

Then open http://localhost:5173 and log in:

- Professor: `prof@demo.edu` / `demo-password-123`
- TA: `ta@demo.edu` / `demo-password-123`

Backend-only views: http://localhost:8000/admin/ and http://localhost:8000/api/docs/

Prerequisites: Python venv with `requirements.txt` installed, system `libmagic`
(`brew install libmagic`), and Node.js (`brew install node`).
