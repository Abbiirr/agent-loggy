# Docs (MkDocs)

This repository ships a MkDocs site (Material theme) plus an “AI research pack” intended for fast, link-heavy retrieval by AI agents.

## Local build

```bash
python -m pip install -r requirements-docs.txt
python scripts/check_docs_fresh.py
mkdocs serve
```

## CI freshness enforcement

CI regenerates the agent docs in `docs/ai/` and fails if any generated file would change.

- Regenerator: `python scripts/build_agent_docs.py`
- Pack builder: `python scripts/export_ai_pack.py`
- Freshness gate: `python scripts/check_docs_fresh.py`

## Files

- Hand-maintained: `docs/ai/ENTRYPOINT.md`, `docs/ai/ARCHITECTURE.md`, `docs/ai/GLOSSARY.md`, `docs/ai/QUALITY_BAR.md`, `docs/ai/DECISIONS/*`
- Generated: `docs/ai/REPO_TREE.md`, `docs/ai/MODULE_INDEX.md`, `docs/ai/CONFIG_REFERENCE.md`, `docs/ai/LOG_CATALOG.md`, `docs/ai/AI_PACK.md`
