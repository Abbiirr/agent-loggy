from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


PACK_SOURCES = [
    Path("docs/ai/ENTRYPOINT.md"),
    Path("docs/ai/ARCHITECTURE.md"),
    Path("docs/ai/MODULE_INDEX.md"),
    Path("docs/ai/CONFIG_REFERENCE.md"),
    Path("docs/ai/LOG_CATALOG.md"),
    Path("docs/ai/GLOSSARY.md"),
    Path("docs/ai/REPO_TREE.md"),
    Path("docs/ai/QUALITY_BAR.md"),
    Path("docs/ai/DECISIONS/ADR-0001-docs-and-agent-pack.md"),
]


def _run_git(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    return Path(_run_git(here.parent, ["rev-parse", "--show-toplevel"])).resolve()


def _commit_sha(repo_root: Path) -> str:
    return _run_git(repo_root, ["rev-parse", "HEAD"])


def _strip_header(text: str) -> str:
    lines = text.splitlines()
    i = 0
    while i < len(lines) and lines[i].startswith("<!-- "):
        i += 1
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    return "\n".join(lines[i:]).rstrip() + "\n"


def _demote_headings(text: str, levels: int = 2) -> str:
    out_lines: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^(#{1,6})(\\s+.*)$", line)
        if not m:
            out_lines.append(line)
            continue
        hashes = m.group(1)
        rest = m.group(2)
        new_level = min(6, len(hashes) + levels)
        out_lines.append("#" * new_level + rest)
    return "\n".join(out_lines).rstrip() + "\n"


def _pack_content(repo_root: Path, commit_sha: str) -> str:
    lines: list[str] = []
    lines.append(f"<!-- Pack version: {commit_sha} -->")
    lines.append("<!-- DO NOT EDIT: Run `python scripts/export_ai_pack.py` -->")
    lines.append("")
    lines.append("# AI_PACK")
    lines.append("")
    lines.append("## How an AI agent should use this pack")
    lines.append("")
    lines.append("- Start at `ENTRYPOINT`.")
    lines.append("- Use `MODULE_INDEX` to find relevant modules and file paths.")
    lines.append("- Use `CONFIG_REFERENCE` to discover config/env keys and defaults (best-effort).")
    lines.append("- Use `LOG_CATALOG` to interpret log messages and locate their sources.")
    lines.append("- In responses, cite file paths and headings from this pack.")
    lines.append("")
    lines.append("## Table of contents")
    lines.append("")
    toc = [
        ("ENTRYPOINT", "entrypoint"),
        ("ARCHITECTURE", "architecture"),
        ("MODULE_INDEX", "module-index"),
        ("CONFIG_REFERENCE", "config-reference"),
        ("LOG_CATALOG", "log-catalog"),
        ("GLOSSARY", "glossary"),
        ("REPO_TREE", "repo-tree"),
        ("QUALITY_BAR", "quality-bar"),
        ("ADR-0001", "adr-0001"),
    ]
    for label, anchor in toc:
        lines.append(f"- [{label}](#{anchor})")
    lines.append("")

    for source_path in PACK_SOURCES:
        abs_path = repo_root / source_path
        if not abs_path.exists():
            raise FileNotFoundError(str(source_path))
        raw = abs_path.read_text(encoding="utf-8", errors="replace")
        body = _demote_headings(_strip_header(raw), levels=2)

        if source_path.name == "ENTRYPOINT.md":
            anchor = "entrypoint"
            title = "ENTRYPOINT"
        elif source_path.name == "ARCHITECTURE.md":
            anchor = "architecture"
            title = "ARCHITECTURE"
        elif source_path.name == "MODULE_INDEX.md":
            anchor = "module-index"
            title = "MODULE_INDEX"
        elif source_path.name == "CONFIG_REFERENCE.md":
            anchor = "config-reference"
            title = "CONFIG_REFERENCE"
        elif source_path.name == "LOG_CATALOG.md":
            anchor = "log-catalog"
            title = "LOG_CATALOG"
        elif source_path.name == "GLOSSARY.md":
            anchor = "glossary"
            title = "GLOSSARY"
        elif source_path.name == "REPO_TREE.md":
            anchor = "repo-tree"
            title = "REPO_TREE"
        elif source_path.name == "QUALITY_BAR.md":
            anchor = "quality-bar"
            title = "QUALITY_BAR"
        else:
            anchor = "adr-0001"
            title = "ADR-0001"

        lines.append(f"<a id=\"{anchor}\"></a>")
        lines.append(f"## {title} (`{source_path.as_posix()}`)")
        lines.append("")
        lines.append(body.rstrip())
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    repo_root = _repo_root()
    commit_sha = _commit_sha(repo_root)
    out_path = repo_root / "docs/ai/AI_PACK.md"

    new_content = _pack_content(repo_root, commit_sha)
    if out_path.exists():
        existing = out_path.read_text(encoding="utf-8", errors="replace")
        if _strip_header(existing) == _strip_header(new_content):
            print("ai pack: up to date")
            return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(new_content, encoding="utf-8", newline="\n")
    print("ai pack: updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

