"""Stable entry point for both repository and standalone skill installs."""
from __future__ import annotations

import argparse
import json
import runpy
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
REPOSITORY = SKILL.parent.parent
if not (Path(__file__).parent / "arxiv_daily").is_dir():
    sys.path.insert(0, str(REPOSITORY))

from arxiv_daily.cli import main as fetch, write_atomic, json_text
from arxiv_daily.prepare import prepare
from arxiv_daily.assemble import assemble
from arxiv_daily.library import save_favorite
from arxiv_daily.library import main as library_main
from arxiv_daily.reading import READING_STYLE, FIGURE_POLICY
from arxiv_daily.report import safe_child, figure_evidence


def paths(workspace):
    latest = json.loads((workspace / "data/latest.json").read_text(encoding="utf-8"))
    readings = workspace / "readings" / latest["query_date"] / latest["batch_id"][:16] / READING_STYLE
    return latest, readings


def reusable(cached, latest):
    return (cached.get("batch_id") == latest["batch_id"]
            and cached.get("reading_style") == READING_STYLE
            and cached.get("figure_policy") == FIGURE_POLICY
            and all(Path(cached.get(k, "")).is_file() for k in ("markdown", "html")))


def figure_queue(workspace, latest):
    batch = safe_child(workspace / "data", latest["batch_path"])
    papers = json.loads((batch / "papers.json").read_text())
    tasks = [json.loads(s) for s in (batch / "tasks.jsonl").read_text().split("\n") if s]
    queue = []
    for paper, task in zip(papers, tasks):
        evidence = figure_evidence(workspace, task["task_id"])
        if evidence["status"] == "pending":
            queue.append({"task_id": task["task_id"], "arxiv_id": paper["arxiv_id"], "version": paper["version"],
                          "pdf_url": paper.get("pdf_url") or paper["url"].replace("/abs/", "/pdf/"),
                          "assets_directory": str(workspace / "reports/assets" / task["task_id"])})
    return queue


def main():
    parser = argparse.ArgumentParser(description="Start a daily scan, finish the Markdown report, or save a favorite")
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("command", choices=("status", "start", "finish", "favorite", "library", "figures", "report"))
    args, rest = parser.parse_known_args()
    config_file = SKILL / "local.json"
    config = json.loads(config_file.read_text()) if config_file.exists() else {}
    workspace = (args.workspace or Path(config.get("workspace", str(Path.cwd() / "astro_arxiv_fast_scan_output")))).expanduser().resolve()
    if args.command == "status":
        print(json_text({"skill": str(SKILL), "workspace": str(workspace), "python": sys.executable,
                         "library_csv": str(workspace / "library/papers.csv"),
                         "has_data": (workspace / "data/latest.json").exists()}))
        return 0
    if args.command == "start":
        result = fetch(rest + ["--output", str(workspace / "data")])
        if result:
            return result
        latest, readings = paths(workspace)
        delivery = workspace / "reports/delivery.json"
        if delivery.exists():
            cached = json.loads(delivery.read_text())
            if reusable(cached, latest) and not figure_queue(workspace, latest):
                print(json_text({"status": "already_read", **cached}))
                return 0
        files = prepare(workspace)
        queue = figure_queue(workspace, latest)
        queue_path = workspace / "work" / latest["batch_id"][:16] / "figure-queue.json"
        write_atomic(queue_path, json_text(queue))
        readings.mkdir(parents=True, exist_ok=True)
        print(json_text({"status": "needs_reading", "batch_id": latest["batch_id"],
                         "reading_style": READING_STYLE,
                         "figure_policy": FIGURE_POLICY, "figure_queue": str(queue_path), "figures_pending": len(queue),
                         "query_date": latest["query_date"], "paper_count": latest["unique_papers"],
                         "batch_files": [str(workspace / f) for f in files], "readings_directory": str(readings)}))
        return 0
    if args.command == "finish":
        latest, readings = paths(workspace)
        markdown, html = assemble(workspace, readings, require_figures=True)
        delivery = {"batch_id": latest["batch_id"], "query_date": latest["query_date"], "reading_style": READING_STYLE,
                    "figure_policy": FIGURE_POLICY,
                    "paper_count": latest["unique_papers"], "markdown": str(markdown), "html": str(html)}
        write_atomic(workspace / "reports/delivery.json", json_text(delivery))
        print(json_text(delivery))
        return 0
    if args.command == "favorite":
        sub = argparse.ArgumentParser()
        sub.add_argument("arxiv_id")
        sub.add_argument("--note", default="")
        favorite = sub.parse_args(rest)
        print(save_favorite(workspace, favorite.arxiv_id, favorite.note))
        return 0
    if args.command == "library":
        return library_main(["--root", str(workspace), *rest])
    if args.command == "figures":
        sys.argv = ["arxiv_daily.figures", *rest]
        runpy.run_module("arxiv_daily.figures", run_name="__main__")
        return 0
    if args.command == "report":
        sys.argv = ["arxiv_daily.report", *rest, "--root", str(workspace)]
        runpy.run_module("arxiv_daily.report", run_name="__main__")
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
