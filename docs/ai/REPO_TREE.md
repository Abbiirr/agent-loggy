<!-- Generated on commit: 6d7866c6a41b75e100432ec50fbcd565aedb15bc -->
<!-- DO NOT EDIT: Run `python scripts/build_agent_docs.py` -->

# Repo tree (generated)

Excludes:
- `.git/`
- `.mypy_cache/`
- `.pytest_cache/`
- `.ruff_cache/`
- `.venv/`
- `__pycache__/`
- `build/`
- `dist/`
- `node_modules/`
- `site/`

```text
.
├── .github/
│   └── workflows/
│       ├── docs-ci.yml
│       └── docs-deploy.yml
├── alembic/
│   ├── versions/
│   │   ├── 1b671ff38c8c_initial_schema.py
│   │   ├── add_app_settings.py
│   │   ├── add_eval_tables.py
│   │   ├── add_projects.py
│   │   ├── add_prompts_versioned.py
│   │   ├── setup_database.sql
│   │   └── update_parameter_extraction_prompt.py
│   ├── env.py
│   ├── README
│   └── script.py.mako
├── app/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── analyze_agent.py
│   │   ├── file_searcher.py
│   │   ├── parameter_agent.py
│   │   ├── planning_agent.py
│   │   ├── report_writer.py
│   │   └── verify_agent.py
│   ├── app_settings/
│   │   ├── context_rules.csv
│   │   └── negate_keys.csv
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── project.py
│   │   ├── prompt.py
│   │   └── settings.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── analysis.py
│   │   ├── chat.py
│   │   └── files.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── ChatRequest.py
│   │   ├── ChatResponse.py
│   │   └── StreamRequest.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── cache.py
│   │   ├── config_service.py
│   │   ├── project_service.py
│   │   └── prompt_service.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_cache.py
│   │   └── test_trace_id_extractor.py
│   ├── tools/
│   │   ├── loki/
│   │   │   ├── __init__.py
│   │   │   ├── loki_log_analyser.py
│   │   │   ├── loki_log_report_generator.py
│   │   │   ├── loki_query_builder.py
│   │   │   └── loki_trace_id_extractor.py
│   │   ├── __init__.py
│   │   ├── full_log_finder.py
│   │   ├── log_searcher.py
│   │   └── trace_id_extractor.py
│   ├── __init__.py
│   ├── config.py
│   ├── dependencies.py
│   ├── main.py
│   ├── orchestrator.py
│   └── startup.py
├── docs/
│   ├── ai/
│   │   ├── DECISIONS/
│   │   │   └── ADR-0001-docs-and-agent-pack.md
│   │   ├── AI_PACK.md
│   │   ├── ARCHITECTURE.md
│   │   ├── CONFIG_REFERENCE.md
│   │   ├── ENTRYPOINT.md
│   │   ├── GLOSSARY.md
│   │   ├── index.md
│   │   ├── LOG_CATALOG.md
│   │   ├── MODULE_INDEX.md
│   │   ├── QUALITY_BAR.md
│   │   └── REPO_TREE.md
│   ├── reference/
│   │   └── index.md
│   ├── db-config-migration-plan.md
│   ├── db-config-migration-todo.md
│   ├── index.md
│   ├── memory.md
│   ├── README.md
│   ├── schema-setup-guide.md
│   ├── session.md
│   └── specs.md
├── scripts/
│   ├── build_agent_docs.py
│   ├── check_docs_fresh.py
│   ├── create_schema.py
│   ├── drop_schema.py
│   ├── export_ai_pack.py
│   ├── seed_projects.py
│   ├── seed_prompts.py
│   ├── seed_settings.py
│   └── verify_schema.py
├── .gitignore
├── alembic.ini
├── CLAUDE.md
├── context_rules.csv
├── docker-compose.yml
├── Dockerfile
├── meta_postgres_sql.txt
├── mkdocs.yml
├── pyproject.toml
├── README.md
├── requirements-docs.txt
└── uv.lock
```
