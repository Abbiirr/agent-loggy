from __future__ import annotations

import subprocess
import sys
from pathlib import Path


GENERATED_PATHS = [
    Path("docs/ai/REPO_TREE.md"),
    Path("docs/ai/MODULE_INDEX.md"),
    Path("docs/ai/CONFIG_REFERENCE.md"),
    Path("docs/ai/LOG_CATALOG.md"),
    Path("docs/ai/AI_PACK.md"),
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


def main() -> int:
    repo_root = _repo_root()
    py = sys.executable

    subprocess.run([py, str(repo_root / "scripts/build_agent_docs.py")], cwd=repo_root, check=True)
    subprocess.run([py, str(repo_root / "scripts/export_ai_pack.py")], cwd=repo_root, check=True)

    diff_args = ["git", "diff", "--exit-code", "--", *[str(p.as_posix()) for p in GENERATED_PATHS]]
    result = subprocess.run(diff_args, cwd=repo_root)
    if result.returncode != 0:
        print("", file=sys.stderr)
        print("error: generated docs are stale; re-run:", file=sys.stderr)
        print("  python scripts/build_agent_docs.py", file=sys.stderr)
        print("  python scripts/export_ai_pack.py", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

