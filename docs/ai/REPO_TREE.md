<!-- Generated on commit: 11f3d69cd35f822f62ba5b27519f7bd154f5fb6f -->
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
├── .claude/
│   └── settings.local.json
├── .github/
│   └── workflows/
│       ├── docs-ci.yml
│       └── docs-deploy.yml
├── .idea/
│   ├── dataSources/
│   │   ├── 562deee0-fd19-4a67-97cb-8e140a74b037/
│   │   │   └── storage_v2/
│   │   │       └── _src_/
│   │   │           └── database/
│   │   │               ├── agent_loggy.fH2Kdg/
│   │   │               │   └── schema/
│   │   │               │       ├── information_schema.FNRwLQ.meta
│   │   │               │       ├── log_chat.cxP_dw.meta
│   │   │               │       ├── log_chat.cxP_dw.zip
│   │   │               │       ├── pg_catalog.0S1ZNQ.meta
│   │   │               │       └── public.abK9xQ.meta
│   │   │               ├── postgres.edMnLQ/
│   │   │               │   └── schema/
│   │   │               │       ├── information_schema.FNRwLQ.meta
│   │   │               │       └── pg_catalog.0S1ZNQ.meta
│   │   │               ├── agent_loggy.fH2Kdg.meta
│   │   │               └── postgres.edMnLQ.meta
│   │   └── 562deee0-fd19-4a67-97cb-8e140a74b037.xml
│   ├── inspectionProfiles/
│   │   └── profiles_settings.xml
│   ├── queries/
│   │   └── Query.sql
│   ├── .gitignore
│   ├── agent-loggy.iml
│   ├── copilot.data.migration.ask2agent.xml
│   ├── dataSources.local.xml
│   ├── dataSources.xml
│   ├── data_source_mapping.xml
│   ├── misc.xml
│   ├── modules.xml
│   ├── sqldialects.xml
│   ├── vcs.xml
│   └── workspace.xml
├── alembic/
│   ├── versions/
│   │   ├── 1b671ff38c8c_initial_schema.py
│   │   ├── add_app_settings.py
│   │   ├── add_context_rules.py
│   │   ├── add_eval_tables.py
│   │   ├── add_projects.py
│   │   ├── add_prompts_versioned.py
│   │   ├── seed_initial_prompts.py
│   │   ├── setup_database.sql
│   │   └── update_parameter_extraction_prompt.py
│   ├── README
│   ├── env.py
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
│   ├── comprehensive_analysis/
│   │   ├── master_summary_20251217_160732.txt
│   │   ├── master_summary_20251217_163119.txt
│   │   ├── master_summary_20251217_172315.txt
│   │   ├── master_summary_20251218_114607.txt
│   │   ├── trace_report_00aafe6e50eb_20251217_172315.txt
│   │   ├── trace_report_06015867d591_20251218_114344.txt
│   │   ├── trace_report_0991068ded60_20251218_114244.txt
│   │   ├── trace_report_0991068ded60_20251218_115804.txt
│   │   ├── trace_report_15ed3d710a80_20251217_162255.txt
│   │   ├── trace_report_1a2229ba0f20_20251217_160703.txt
│   │   ├── trace_report_1cc0772b748b_20251217_163105.txt
│   │   ├── trace_report_2297105debc3_20251217_160714.txt
│   │   ├── trace_report_242933b667dc_20251217_171557.txt
│   │   ├── trace_report_258a3f847f9f_20251217_162327.txt
│   │   ├── trace_report_324a29d1c936_20251218_114045.txt
│   │   ├── trace_report_324a29d1c936_20251218_115607.txt
│   │   ├── trace_report_32e404fafd83_20251217_162518.txt
│   │   ├── trace_report_34c66eab50b7_20251217_160711.txt
│   │   ├── trace_report_351a4864f120_20251218_113900.txt
│   │   ├── trace_report_351a4864f120_20251218_115500.txt
│   │   ├── trace_report_360ece980348_20251217_160651.txt
│   │   ├── trace_report_3b38dfb10d91_20251218_114311.txt
│   │   ├── trace_report_3b38dfb10d91_20251218_115815.txt
│   │   ├── trace_report_513185e23875_20251218_114139.txt
│   │   ├── trace_report_513185e23875_20251218_115653.txt
│   │   ├── trace_report_562100c36c53_20251217_171353.txt
│   │   ├── trace_report_5a28cbc40558_20251217_162003.txt
│   │   ├── trace_report_5f19919f259a_20251217_171613.txt
│   │   ├── trace_report_6141096fa86c_20251217_163047.txt
│   │   ├── trace_report_62800ceb2993_20251217_172029.txt
│   │   ├── trace_report_632768eabcfe_20251217_162121.txt
│   │   ├── trace_report_69d9136bec43_20251217_171433.txt
│   │   ├── trace_report_6c432ae6c8aa_20251217_160047.txt
│   │   ├── trace_report_6ca1a0a8ad7d_20251218_114607.txt
│   │   ├── trace_report_71e304d315f7_20251218_114420.txt
│   │   ├── trace_report_750dfff180ae_20251217_162226.txt
│   │   ├── trace_report_763cb3a0917c_20251217_162036.txt
│   │   ├── trace_report_77bfbfd5380c_20251218_114534.txt
│   │   ├── trace_report_7a5f52d68878_20251217_160732.txt
│   │   ├── trace_report_7b7e077b0758_20251217_160308.txt
│   │   ├── trace_report_7bdd113de360_20251218_114155.txt
│   │   ├── trace_report_7bdd113de360_20251218_115709.txt
│   │   ├── trace_report_849b16095de0_20251218_114111.txt
│   │   ├── trace_report_849b16095de0_20251218_115636.txt
│   │   ├── trace_report_85d94059a1dc_20251217_160658.txt
│   │   ├── trace_report_86f781ed8092_20251217_163050.txt
│   │   ├── trace_report_8d6656894c25_20251217_171305.txt
│   │   ├── trace_report_9b96eaa6008c_20251217_162054.txt
│   │   ├── trace_report_9c0f956cea60_20251217_163119.txt
│   │   ├── trace_report_9f5f71789e11_20251217_162107.txt
│   │   ├── trace_report_a0f54b817cd1_20251217_160730.txt
│   │   ├── trace_report_a4c2daf751c1_20251218_114403.txt
│   │   ├── trace_report_a53f3a128295_20251218_114056.txt
│   │   ├── trace_report_a53f3a128295_20251218_115623.txt
│   │   ├── trace_report_aa3b0cf97478_20251217_171715.txt
│   │   ├── trace_report_ad959b92516d_20251217_171542.txt
│   │   ├── trace_report_b0d0100b0e67_20251217_171649.txt
│   │   ├── trace_report_b30e20f27beb_20251217_160726.txt
│   │   ├── trace_report_b39327c7d191_20251217_160712.txt
│   │   ├── trace_report_b5734b92bbc1_20251217_160716.txt
│   │   ├── trace_report_b7d1ffa3416f_20251218_114459.txt
│   │   ├── trace_report_b810ebd2afeb_20251217_163112.txt
│   │   ├── trace_report_b923067cbb63_20251217_172032.txt
│   │   ├── trace_report_ba189bd71319_20251217_171631.txt
│   │   ├── trace_report_c1b9c7a808de_20251217_162015.txt
│   │   ├── trace_report_c5e85dbfe220_20251217_162310.txt
│   │   ├── trace_report_c6b16718f881_20251217_172026.txt
│   │   ├── trace_report_c79f021d2bc3_20251217_162435.txt
│   │   ├── trace_report_ca8608a5b4dc_20251218_114516.txt
│   │   ├── trace_report_ca9360501db8_20251217_162146.txt
│   │   ├── trace_report_d41a1fd5e96a_20251217_160722.txt
│   │   ├── trace_report_d7cea32cbd13_20251217_160107.txt
│   │   ├── trace_report_dc65cf904b19_20251218_114442.txt
│   │   ├── trace_report_de0530e5a12e_20251217_163115.txt
│   │   ├── trace_report_e01e9e3f8014_20251217_172035.txt
│   │   ├── trace_report_e0201d6e1e20_20251218_114322.txt
│   │   ├── trace_report_e3760e7423f1_20251217_160656.txt
│   │   ├── trace_report_e4c89fef519e_20251218_114223.txt
│   │   ├── trace_report_e4c89fef519e_20251218_115751.txt
│   │   ├── trace_report_e50a248cb0a4_20251217_171152.txt
│   │   ├── trace_report_ea91ed0ca093_20251218_113957.txt
│   │   ├── trace_report_ea91ed0ca093_20251218_115553.txt
│   │   ├── trace_report_edbcb71553cc_20251218_113920.txt
│   │   ├── trace_report_edbcb71553cc_20251218_115516.txt
│   │   ├── trace_report_eebdd2958400_20251218_113938.txt
│   │   ├── trace_report_eebdd2958400_20251218_115528.txt
│   │   ├── trace_report_f0a7a7c8b0d0_20251217_163058.txt
│   │   ├── trace_report_fe6e71546cf4_20251217_162134.txt
│   │   ├── trace_report_ffd4bca1acdb_20251218_114206.txt
│   │   └── trace_report_ffd4bca1acdb_20251218_115739.txt
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── session.py
│   ├── evals/
│   │   ├── datasets/
│   │   │   ├── parameter_extraction.json
│   │   │   ├── relevance_analysis.json
│   │   │   └── trace_analysis.json
│   │   ├── __init__.py
│   │   ├── cli.py
│   │   ├── metrics.py
│   │   ├── models.py
│   │   ├── runner.py
│   │   └── storage.py
│   ├── loki_logs/
│   │   ├── NCCDEV_2025-12-17_10842cf5364a4ee18524d493fd589fbe.json
│   │   ├── NCCDEV_2025-12-17_66db4ce52bcb4416a793c511b6fb93ec.json
│   │   ├── NCCDEV_2025-12-17_9b8cb3b119404f7c9253938ff0dd94c4.json
│   │   ├── NCCDEV_2025-12-17_e9c81da6d2004c61ab8dcd859315c26c.json
│   │   └── NCCDEV_2025-12-17_fd962ee7f1f34e9ab2e14909e9a74526.json
│   ├── models/
│   │   ├── __init__.py
│   │   ├── context_rule.py
│   │   ├── project.py
│   │   ├── prompt.py
│   │   └── settings.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── analysis.py
│   │   ├── chat.py
│   │   └── files.py
│   ├── schemas/
│   │   ├── ChatRequest.py
│   │   ├── ChatResponse.py
│   │   ├── StreamRequest.py
│   │   └── __init__.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── cache.py
│   │   ├── config_service.py
│   │   ├── llm_cache.py
│   │   ├── project_service.py
│   │   └── prompt_service.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_cache.py
│   │   ├── test_planning_agent.py
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
│   ├── trace_logs/
│   │   ├── trace_00aafe6e50eb23a057665e8ab8f7233f.json
│   │   ├── trace_06015867d5910b3594044ca6bc319e05.json
│   │   ├── trace_0991068ded600215196d6d0a305e8281.json
│   │   ├── trace_15ed3d710a8080644106297304eeed4e.json
│   │   ├── trace_1a2229ba0f2048266e82d0eb1722e1cb.json
│   │   ├── trace_1cc0772b748bac5d1ec82bd8e7abdd15.json
│   │   ├── trace_2297105debc32fdb65edea9e93c0e4cf.json
│   │   ├── trace_242933b667dcc8f61f814d756799022c.json
│   │   ├── trace_258a3f847f9fdfa543f3d0001fa867ec.json
│   │   ├── trace_324a29d1c9367c0b54a401bbd9788ed3.json
│   │   ├── trace_32e404fafd83cf127f47a2984359d147.json
│   │   ├── trace_34c66eab50b7e2813c867606b1f2099f.json
│   │   ├── trace_351a4864f120a26fe0bb85c584d7af02.json
│   │   ├── trace_360ece980348b9f226aec90007f8085d.json
│   │   ├── trace_3b38dfb10d919627cd9e240f7a8348e5.json
│   │   ├── trace_513185e23875e313025e5af6bac79c3d.json
│   │   ├── trace_562100c36c53f205df6a06cb6980c604.json
│   │   ├── trace_5a28cbc405585c5abe383ecc11d00572.json
│   │   ├── trace_5f19919f259a1cf3db3bcb0431e54e35.json
│   │   ├── trace_6141096fa86ce7d3d72f15d62f5e231d.json
│   │   ├── trace_62800ceb2993b389dab37ae33999b678.json
│   │   ├── trace_632768eabcfeb79b00fe712d247d7446.json
│   │   ├── trace_69d9136bec433f69dd7724913aa2c972.json
│   │   ├── trace_6c432ae6c8aaa04d73a0346efd786d09.json
│   │   ├── trace_6ca1a0a8ad7d897422525b17b063bba3.json
│   │   ├── trace_71e304d315f7781b3340773f50d007f5.json
│   │   ├── trace_750dfff180aec28cd1c8cdf46e6f83e4.json
│   │   ├── trace_763cb3a0917c3594c1a6eacde4db12d6.json
│   │   ├── trace_77bfbfd5380c8f0ab9d9b44ccd1408b7.json
│   │   ├── trace_7a5f52d6887868eda0fc1771340f8626.json
│   │   ├── trace_7b7e077b07585dfbf5166c133afed6b6.json
│   │   ├── trace_7bdd113de360951356da69f67102986c.json
│   │   ├── trace_849b16095de0ccc4f8101c9cfd1dc9f3.json
│   │   ├── trace_85d94059a1dcb04195e1144085562101.json
│   │   ├── trace_86f781ed809219f76144d0da04339db9.json
│   │   ├── trace_8d6656894c252464133db3c1a958a986.json
│   │   ├── trace_9b96eaa6008c64c99ac30ba516833d0c.json
│   │   ├── trace_9c0f956cea607e25f40c06f53c846bb0.json
│   │   ├── trace_9f5f71789e11ed02ef98f5e3154b02b6.json
│   │   ├── trace_a0f54b817cd1a2f728b83b3be70e9132.json
│   │   ├── trace_a4c2daf751c1043b973975b822f3a5bd.json
│   │   ├── trace_a53f3a128295f1edbf7149dba7edfaec.json
│   │   ├── trace_aa3b0cf9747856bccee5ff94a1473ecd.json
│   │   ├── trace_ad959b92516d48e634d903070277e1c0.json
│   │   ├── trace_b0d0100b0e67920b8c05debbfc7b3155.json
│   │   ├── trace_b30e20f27beb79adaf3cd4175cf205e5.json
│   │   ├── trace_b39327c7d19154f7f0bab66a73dd751b.json
│   │   ├── trace_b5734b92bbc188039aaef2c176cd2455.json
│   │   ├── trace_b7d1ffa3416f5c45898204d98ce36951.json
│   │   ├── trace_b810ebd2afeb5e8ca45af5a2b2a7f26b.json
│   │   ├── trace_b923067cbb6344e7ddbc8ebb8326a115.json
│   │   ├── trace_ba189bd713192d9be2da5bdb1a8795c5.json
│   │   ├── trace_c1b9c7a808de3e8b245f94aa81a949fa.json
│   │   ├── trace_c5e85dbfe220fc976d17948ea13803a0.json
│   │   ├── trace_c6b16718f881e387950cc5f930bb8500.json
│   │   ├── trace_c79f021d2bc3bc43248d3a3536875cf5.json
│   │   ├── trace_ca8608a5b4dc0cd559636e85a65ce3e5.json
│   │   ├── trace_ca9360501db8ac2d73750925666aee64.json
│   │   ├── trace_d41a1fd5e96a799bb7f7d4f2e016eedc.json
│   │   ├── trace_d7cea32cbd1331b8677d3b8fafe1ddb8.json
│   │   ├── trace_dc65cf904b19d650ad33f07f4e27a943.json
│   │   ├── trace_de0530e5a12e8759955590dbff7bca5a.json
│   │   ├── trace_e01e9e3f8014126c54299aad1645527b.json
│   │   ├── trace_e0201d6e1e2037758e30f83e45f365d6.json
│   │   ├── trace_e3760e7423f1bcad0517bbf73145aba4.json
│   │   ├── trace_e4c89fef519eca2ccda1bd377a1c6e40.json
│   │   ├── trace_e50a248cb0a4069a528ce8970e3d1963.json
│   │   ├── trace_ea91ed0ca09347226d41d3d4637438b3.json
│   │   ├── trace_edbcb71553ccb15e6fd1afc56ff50b17.json
│   │   ├── trace_eebdd2958400732475b1292f28e5ab03.json
│   │   ├── trace_f0a7a7c8b0d0f7184283856b1d06e868.json
│   │   ├── trace_fe6e71546cf4ed5ac42fe3dfceaf10be.json
│   │   └── trace_ffd4bca1acdb7fe9a3e04196d4578c83.json
│   ├── verification_reports/
│   │   ├── relevance_analysis_20251217_161002.json
│   │   ├── relevance_analysis_20251217_163235.json
│   │   └── relevance_analysis_20251217_172407.json
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
│   │   ├── ARCHITECTURE.md
│   │   ├── ENTRYPOINT.md
│   │   ├── GLOSSARY.md
│   │   ├── QUALITY_BAR.md
│   │   └── index.md
│   ├── reference/
│   │   └── index.md
│   ├── API.md
│   ├── ARCHITECTURE.md
│   ├── DEVELOPMENT.md
│   ├── README.md
│   ├── db-config-migration-plan.md
│   ├── db-config-migration-todo.md
│   ├── index.md
│   ├── memory.md
│   ├── rag-implementation-plan.md
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
├── .env
├── .gitignore
├── CLAUDE.md
├── Dockerfile
├── README.md
├── alembic.ini
├── context_rules.csv
├── docker-compose.yml
├── meta_postgres_sql.txt
├── mkdocs.yml
├── pyproject.toml
├── requirements-docs.txt
└── uv.lock
```
