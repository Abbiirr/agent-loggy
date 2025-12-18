# Quality bar (agent docs)

These docs are considered “good” when an AI agent can locate code responsibilities quickly and answer “where should this change go?” without opening the source tree.

## Acceptance checks

- `mkdocs build --strict` passes.
- `python scripts/check_docs_fresh.py` exits 0 in CI.
- `docs/ai/MODULE_INDEX.md` contains:
  - stable module list (sorted)
  - brief summaries derived from docstrings/file headers (best-effort)
- `docs/ai/CONFIG_REFERENCE.md` contains:
  - stable IDs (`CFG-...`)
  - keys, defaults (best-effort), and file references
- `docs/ai/LOG_CATALOG.md` contains:
  - stable IDs (`LOG-...`)
  - message templates and file references
- `docs/ai/REPO_TREE.md` is readable and excludes large build/cache directories.

## Change discipline

- Keep hand-authored docs short and link-heavy.
- Prefer stable headings and sorted lists to keep diffs small.
