"""Install a self-contained skill without publishing local papers or credentials."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]


def install(destination, workspace):
    destination = destination.expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Destination already exists; refusing to overwrite: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".arxiv-skill-", dir=destination.parent))
    try:
        shutil.copytree(REPOSITORY / "skills/arxiv-daily-reader", stage, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "local.json"))
        shutil.copytree(REPOSITORY / "arxiv_daily", stage / "scripts/arxiv_daily",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (stage / "local.json").write_text(json.dumps({
            "workspace": str(workspace.expanduser().resolve()),
            "repository": "https://github.com/Yunfan-Zhou/astro_arxiv_fast_scan",
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        stage.rename(destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Install the arxiv-daily-reader skill and bundled runtime")
    parser.add_argument("--destination", type=Path,
                        default=Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills/arxiv-daily-reader")
    parser.add_argument("--workspace", type=Path, default=Path.home() / "astro_arxiv_fast_scan_output")
    args = parser.parse_args()
    try:
        print(install(args.destination, args.workspace))
    except FileExistsError as exc:
        parser.exit(1, str(exc) + "\n")
