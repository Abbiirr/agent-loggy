# ADR-0001: Docs and AI research pack

## Status

Accepted

## Context

AI agents working on this repo need a fast way to understand structure, config surface, and log semantics without crawling the entire source tree.

We also want CI to enforce that these agent docs are always up to date.

## Decision

We maintain:

- A MkDocs (Material) site for humans + agents.
- A small set of hand-authored “entry” docs (Entrypoint/Architecture/Glossary/Quality bar/ADRs).
- A deterministic generator that produces:
  - repo tree
  - module index (from docstrings/file headers)
  - config reference (env var discovery)
  - log catalog (logging call discovery)
- A single-file export (`docs/ai/AI_PACK.md`) for retrieval and offline use.

CI fails if any generated artifact is stale.

## Consequences

- Any change that affects modules/config/logging should be accompanied by regenerated agent docs.
- Generated files should remain stable (sorted, deterministic) to keep diffs small.
