# Test fixtures

Two fixture trees exist in this repository, with different jobs:

- `tests/fixtures/` holds contract negative and adversarial inputs. Nothing
  here is demo material: every file exists so a test can prove that the
  schemas, contract checks, or ingestion paths reject or flag it.
- `examples/fixtures/` holds demonstration assets (sample paper text, a run
  manifest, example Skills). They back the worked examples under `examples/`
  and are reused read-only by tests as frozen input content. They must stay
  valid and hash-stable, because example documents pin them by `sha256`.

## Layout

- `invalid/objects/*.json` — one negative fixture per research object type;
  `test_schemas.py` requires each of them to fail the `research_object`
  Schema. The positive counterparts live in `examples/objects/`.
- `valid/` and `invalid/` — paired documents that share a filename (for
  example `simulation-vv-report.yaml`): the `valid/` copy must pass its
  checks, the `invalid/` copy must be rejected. Add or update both halves of
  a pair together when a contract changes.
- `adversarial/` — hostile inputs, such as prompt injection embedded in
  source material, used to prove that ingestion keeps provenance separation.
- `claim-preserving-rewrite/` — a bounded case set (source, claim lock, and
  valid/invalid/empty revisions) for the candidate claim-rewrite checks.

## Conventions

- Every fixture has a consuming test; do not add fixture files without one.
- Positive and negative counterparts keep identical filenames so each pair
  is discoverable.
- Fixtures are synthetic and small; where the document format allows, say so
  inside the document itself (for example in `limitations`).
