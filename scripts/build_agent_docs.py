from __future__ import annotations

import ast
import hashlib
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


REPO_URL = "https://github.com/Abbiirr/agent-loggy"

EXCLUDE_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    ".ruff_cache",
    "site",
}


GENERATED_FILES = [
    Path("docs/ai/REPO_TREE.md"),
    Path("docs/ai/MODULE_INDEX.md"),
    Path("docs/ai/CONFIG_REFERENCE.md"),
    Path("docs/ai/LOG_CATALOG.md"),
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
    try:
        root = _run_git(here.parent, ["rev-parse", "--show-toplevel"])
    except Exception:
        print("error: could not locate git repository root", file=sys.stderr)
        raise
    return Path(root).resolve()


def _commit_sha(repo_root: Path) -> str:
    return _run_git(repo_root, ["rev-parse", "HEAD"])


def _strip_generated_header(text: str) -> str:
    lines = text.splitlines()
    i = 0
    while i < len(lines) and lines[i].startswith("<!-- "):
        i += 1
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    return "\n".join(lines[i:]).rstrip() + "\n"


def _write_generated_markdown(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8", errors="replace")
        if _strip_generated_header(existing) == _strip_generated_header(content):
            return False
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def _generated_header(commit_sha: str, generator: str) -> list[str]:
    return [
        f"<!-- Generated on commit: {commit_sha} -->",
        f"<!-- DO NOT EDIT: Run `{generator}` -->",
        "",
    ]


def _posix_relpath(path: Path, base: Path) -> str:
    return path.relative_to(base).as_posix()


def _git_ls_files(repo_root: Path) -> list[str]:
    raw = _run_git(repo_root, ["ls-files"])
    paths = [line.strip() for line in raw.splitlines() if line.strip()]
    return sorted(paths)


def _iter_tracked_files(repo_root: Path, *, suffix: str | None = None) -> Iterator[Path]:
    for rel_posix in _git_ls_files(repo_root):
        if suffix is not None and not rel_posix.endswith(suffix):
            continue
        rel = Path(rel_posix)
        if any(part in EXCLUDE_DIR_NAMES for part in rel.parts):
            continue
        yield repo_root / rel


def _render_repo_tree(repo_root: Path, commit_sha: str) -> str:
    tracked = _git_ls_files(repo_root)

    def add_path(tree: dict, parts: list[str]) -> None:
        cur = tree
        for p in parts:
            cur = cur.setdefault(p, {})

    def render(tree: dict, prefix: str = "") -> list[str]:
        out: list[str] = []
        keys = sorted(tree.keys(), key=lambda k: (not k.endswith("/"), k.lower()))
        for idx, key in enumerate(keys):
            is_last = idx == len(keys) - 1
            connector = "└── " if is_last else "├── "
            out.append(prefix + connector + key)
            subtree = tree[key]
            if subtree:
                extension = "    " if is_last else "│   "
                out.extend(render(subtree, prefix + extension))
        return out

    root_tree: dict = {}
    for rel_posix in tracked:
        rel = Path(rel_posix)
        if any(part in EXCLUDE_DIR_NAMES for part in rel.parts):
            continue
        parts = list(rel.parts)
        if len(parts) > 1:
            parts = [parts[0] + "/"] + [p + "/" for p in parts[1:-1]] + [parts[-1]]
        else:
            parts = [parts[0]]
        add_path(root_tree, parts)

    lines: list[str] = []
    lines.extend(_generated_header(commit_sha, "python scripts/build_agent_docs.py"))
    lines.append("# Repo tree (generated)")
    lines.append("")
    lines.append("Excludes:")
    for name in sorted(EXCLUDE_DIR_NAMES):
        lines.append(f"- `{name}/`")
    lines.append("")
    lines.append("```text")
    lines.append(".")
    lines.extend(render(root_tree))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def _module_name_for_file(repo_root: Path, file_path: Path) -> str | None:
    rel = file_path.relative_to(repo_root)
    if rel.suffix != ".py":
        return None
    if len(rel.parts) < 2:
        return None
    top = repo_root / rel.parts[0]
    if not (top / "__init__.py").exists():
        return None

    pkg_parts: list[str] = []
    for part in rel.parts[:-1]:
        pkg_parts.append(part)
        if not (repo_root.joinpath(*pkg_parts) / "__init__.py").exists():
            return None

    if rel.name == "__init__.py":
        return ".".join(rel.parts[:-1])
    return ".".join([*rel.parts[:-1], rel.stem])


def _module_summary(py_file: Path) -> str:
    try:
        src = py_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        tree = None
    if tree is not None:
        doc = ast.get_docstring(tree) or ""
        first = doc.strip().splitlines()[0].strip() if doc.strip() else ""
        if first:
            return first
    for line in src.splitlines()[:25]:
        stripped = line.strip()
        if stripped.startswith("#"):
            text = stripped.lstrip("#").strip()
            if text:
                return text
        if stripped:
            break
    return ""


def _render_module_index(repo_root: Path, commit_sha: str) -> str:
    key_paths = [
        "app/main.py",
        "app/orchestrator.py",
        "app/config.py",
        "app/startup.py",
        "app/routers/chat.py",
    ]

    modules: list[tuple[str, str, str, str]] = []
    for py_file in _iter_tracked_files(repo_root, suffix=".py"):
        module = _module_name_for_file(repo_root, py_file)
        if not module:
            continue
        rel_posix = _posix_relpath(py_file, repo_root)
        summary = _module_summary(py_file)
        source_url = f"{REPO_URL}/blob/main/{rel_posix}"
        modules.append((module, rel_posix, summary, source_url))

    modules.sort(key=lambda r: r[0])

    lines: list[str] = []
    lines.extend(_generated_header(commit_sha, "python scripts/build_agent_docs.py"))
    lines.append("# Module index (generated)")
    lines.append("")
    lines.append("Key files:")
    for rel in key_paths:
        if (repo_root / rel).exists():
            lines.append(f"- `{rel}`")
    lines.append("")
    lines.append("Modules:")
    lines.append("")
    lines.append("| Module | Path | Summary | Source |")
    lines.append("|---|---|---|---|")
    for module, rel_posix, summary, source_url in modules:
        safe_summary = summary.replace("|", "\\|")
        lines.append(f"| `{module}` | `{rel_posix}` | {safe_summary} | [link]({source_url}) |")
    lines.append("")
    return "\n".join(lines)


@dataclass(frozen=True)
class ConfigRef:
    key: str
    default: str | None
    path: str
    line: int
    kind: str


def _stable_id(prefix: str, seed: str) -> str:
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10].upper()
    return f"{prefix}-{digest}"


def _extract_config_refs_from_settings_classes(py_file: Path, repo_root: Path) -> list[ConfigRef]:
    refs: list[ConfigRef] = []
    try:
        src = py_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return refs
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return refs

    rel_posix = _posix_relpath(py_file, repo_root)

    def is_basesettings(base: ast.expr) -> bool:
        if isinstance(base, ast.Name):
            return base.id == "BaseSettings"
        if isinstance(base, ast.Attribute):
            return base.attr == "BaseSettings"
        return False

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(is_basesettings(b) for b in node.bases):
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                key = stmt.target.id
                default = None
                if stmt.value is not None and isinstance(stmt.value, ast.Constant):
                    default = repr(stmt.value.value)
                refs.append(
                    ConfigRef(
                        key=key,
                        default=default,
                        path=rel_posix,
                        line=getattr(stmt, "lineno", 1),
                        kind="BaseSettings field",
                    )
                )
            elif isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        default = None
                        if isinstance(stmt.value, ast.Constant):
                            default = repr(stmt.value.value)
                        refs.append(
                            ConfigRef(
                                key=target.id,
                                default=default,
                                path=rel_posix,
                                line=getattr(stmt, "lineno", 1),
                                kind="Class constant",
                            )
                        )
    return refs


def _extract_config_refs_from_env_usage(py_file: Path, repo_root: Path) -> list[ConfigRef]:
    refs: list[ConfigRef] = []
    try:
        src = py_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return refs

    rel_posix = _posix_relpath(py_file, repo_root)
    try:
        tree = ast.parse(src)
    except SyntaxError:
        tree = None

    if tree is None:
        return refs

    class Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            func = node.func
            call_name = None
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                call_name = f"{func.value.id}.{func.attr}"
            elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Attribute):
                if isinstance(func.value.value, ast.Name) and func.value.value.id == "os":
                    call_name = f"os.{func.value.attr}.{func.attr}"
            elif isinstance(func, ast.Name):
                call_name = func.id

            if call_name in {"os.getenv", "getenv", "os.environ.get", "environ.get"}:
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    key = node.args[0].value
                    default = None
                    if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                        default = repr(node.args[1].value)
                    refs.append(
                        ConfigRef(
                            key=key,
                            default=default,
                            path=rel_posix,
                            line=getattr(node, "lineno", 1),
                            kind=call_name,
                        )
                    )
            self.generic_visit(node)

        def visit_Subscript(self, node: ast.Subscript) -> None:
            if isinstance(node.value, ast.Attribute):
                if isinstance(node.value.value, ast.Name) and node.value.value.id == "os" and node.value.attr == "environ":
                    idx = node.slice
                    if isinstance(idx, ast.Constant) and isinstance(idx.value, str):
                        refs.append(
                            ConfigRef(
                                key=idx.value,
                                default=None,
                                path=rel_posix,
                                line=getattr(node, "lineno", 1),
                                kind="os.environ[...]",
                            )
                        )
            self.generic_visit(node)

    Visitor().visit(tree)
    return refs


def _render_config_reference(repo_root: Path, commit_sha: str) -> str:
    refs: list[ConfigRef] = []
    for py_file in _iter_tracked_files(repo_root, suffix=".py"):
        refs.extend(_extract_config_refs_from_settings_classes(py_file, repo_root))
        refs.extend(_extract_config_refs_from_env_usage(py_file, repo_root))

    by_key: dict[str, list[ConfigRef]] = {}
    for r in refs:
        by_key.setdefault(r.key, []).append(r)

    lines: list[str] = []
    lines.extend(_generated_header(commit_sha, "python scripts/build_agent_docs.py"))
    lines.append("# Config reference (generated)")
    lines.append("")
    lines.append("Best-effort discovery of config keys and environment variables.")
    lines.append("")

    for key in sorted(by_key.keys()):
        key_refs = sorted(by_key[key], key=lambda r: (r.path, r.line, r.kind, r.default or ""))
        cfg_id = _stable_id("CFG", key)
        defaults = sorted({r.default for r in key_refs if r.default is not None})
        lines.append(f"## {cfg_id}: `{key}`")
        lines.append("")
        if defaults:
            lines.append("- Defaults:")
            for d in defaults:
                lines.append(f"  - `{d}`")
        else:
            lines.append("- Defaults: (not detected)")
        lines.append("- References:")
        for r in key_refs:
            source_url = f"{REPO_URL}/blob/main/{r.path}#L{r.line}"
            lines.append(f"  - `{r.path}:{r.line}` ({r.kind}) — [link]({source_url})")
        lines.append("")
    return "\n".join(lines)


@dataclass(frozen=True)
class LogRef:
    level: str
    template: str
    path: str
    line: int
    qualname: str | None


LOG_METHODS = {
    "debug",
    "info",
    "warning",
    "error",
    "exception",
    "critical",
    "fatal",
    "log",
}


def _format_ast_string(node: ast.AST, source: str) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                parts.append("{...}")
            else:
                parts.append("{...}")
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        left = _format_ast_string(node.left, source)
        if left is not None:
            return left
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
        base = _format_ast_string(node.func.value, source)
        if base is not None:
            return base
    seg = ast.get_source_segment(source, node)
    if seg is not None and isinstance(seg, str):
        seg = seg.strip()
        if seg.startswith(("\"", "'")):
            return None
    return None


def _extract_logs(py_file: Path, repo_root: Path) -> list[LogRef]:
    try:
        source = py_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    rel_posix = _posix_relpath(py_file, repo_root)
    logs: list[LogRef] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            super().__init__()
            self.scope: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        def visit_Call(self, node: ast.Call) -> None:
            level = None
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in LOG_METHODS:
                if isinstance(func.value, ast.Name):
                    base = func.value.id
                    if base == "logging" or base.lower().endswith("logger"):
                        level = func.attr
                elif isinstance(func.value, ast.Attribute):
                    if func.value.attr.lower().endswith("logger"):
                        level = func.attr
            if level and node.args:
                template = _format_ast_string(node.args[0], source) or "<dynamic message>"
                qualname = ".".join(self.scope) if self.scope else None
                logs.append(
                    LogRef(
                        level=level,
                        template=template,
                        path=rel_posix,
                        line=getattr(node, "lineno", 1),
                        qualname=qualname,
                    )
                )
            self.generic_visit(node)

    Visitor().visit(tree)
    return logs


def _render_log_catalog(repo_root: Path, commit_sha: str) -> str:
    all_logs: list[LogRef] = []
    for py_file in _iter_tracked_files(repo_root, suffix=".py"):
        all_logs.extend(_extract_logs(py_file, repo_root))

    def log_sort_key(lr: LogRef) -> tuple[str, int, str, str]:
        return (lr.path, lr.line, lr.level, lr.template)

    all_logs = sorted(all_logs, key=log_sort_key)

    lines: list[str] = []
    lines.extend(_generated_header(commit_sha, "python scripts/build_agent_docs.py"))
    lines.append("# Log catalog (generated)")
    lines.append("")
    lines.append("Best-effort extraction of log message templates from Python logging calls.")
    lines.append("")

    for lr in all_logs:
        log_id = _stable_id("LOG", f"{lr.path}|{lr.template}")
        source_url = f"{REPO_URL}/blob/main/{lr.path}#L{lr.line}"
        lines.append(f"## {log_id}")
        lines.append("")
        lines.append(f"- Level: `{lr.level}`")
        lines.append(f"- Message: `{lr.template}`")
        lines.append(f"- Location: `{lr.path}:{lr.line}` — [link]({source_url})")
        if lr.qualname:
            lines.append(f"- Function: `{lr.qualname}`")
        lines.append("")
        lines.append("Meaning:")
        lines.append("- (fill in)")
        lines.append("")
        lines.append("Causes:")
        lines.append("- (fill in)")
        lines.append("")
        lines.append("Next steps:")
        lines.append("- (fill in)")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    repo_root = _repo_root()
    commit_sha = _commit_sha(repo_root)

    changed = []
    changed.append(_write_generated_markdown(repo_root / "docs/ai/REPO_TREE.md", _render_repo_tree(repo_root, commit_sha)))
    changed.append(
        _write_generated_markdown(repo_root / "docs/ai/MODULE_INDEX.md", _render_module_index(repo_root, commit_sha))
    )
    changed.append(
        _write_generated_markdown(repo_root / "docs/ai/CONFIG_REFERENCE.md", _render_config_reference(repo_root, commit_sha))
    )
    changed.append(
        _write_generated_markdown(repo_root / "docs/ai/LOG_CATALOG.md", _render_log_catalog(repo_root, commit_sha))
    )

    any_changed = any(changed)
    print("agent docs: updated" if any_changed else "agent docs: up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
