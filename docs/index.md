# agent-loggy docs

This site is optimized for “agent-first” navigation and fast retrieval.

- AI docs: `docs/ai/index.md`
- AI research pack (single file): `docs/ai/AI_PACK.md`

## Build

```bash
python -m pip install -r requirements-docs.txt
python scripts/check_docs_fresh.py
mkdocs build --strict
```
