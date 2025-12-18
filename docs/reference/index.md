# API reference

This repo uses `mkdocstrings[python]` for API reference pages.

## Adding module pages

Once module paths are stable, add pages under `docs/reference/` that include mkdocstrings directives, for example:

```md
::: app.orchestrator
```

Then add those pages to `mkdocs.yml` under `nav:`.
