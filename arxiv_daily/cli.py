from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .core import Client, NotReady, SourceError, SUBJECT, digest, reading_prompt, stable_collect
from .selection import DEFAULT_CATEGORIES, select_papers


def write_atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".tmp-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def save_batch(root, day, subject, level, sections, papers, counts, selection=None):
    identity = {"date": day, "subject_id": subject, "level": level, "sections": list(sections), "papers": papers}
    if selection is not None:
        identity["selection"] = selection
    batch_id = digest(identity)
    relative = Path(day) / batch_id[:16]
    folder = root / relative
    # Immutable batches; latest.json is the commit point for local readers.
    if not (folder / "batch.json").exists():
        tasks = []
        for paper in papers:
            key = digest({k: paper[k] for k in ("arxiv_id", "version", "title", "abstract", "authors_raw", "keywords_raw", "comments")})
            tasks.append({"task_id": f"{paper['arxiv_id'].replace('/', '_')}v{paper['version']}-{key[:12]}",
                          "arxiv_id": paper["arxiv_id"], "version": paper["version"],
                          "prompt": reading_prompt(paper)})
        write_atomic(folder / "papers.json", json_text(papers))
        write_atomic(folder / "tasks.jsonl", "".join(json.dumps(t, ensure_ascii=False) + "\n" for t in tasks))
        write_atomic(folder / "batch.json", json_text({
            "schema_version": 1, "batch_id": batch_id, "query_date": day,
            "date_basis": "Giiisp explicit startDate=endDate, getLatest=0; not arXiv submission timestamp",
            "subject_id": subject, "level": level, "sections": list(sections),
            "unique_papers": len(papers), "section_counts": counts,
            "selection": selection,
            "collected_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
            "source": "https://www.giiisp.com/#/arxiv?subjectId=" + subject,
            "validation": "site completion signal before/after plus two identical full passes",
        }))
    latest = {"schema_version": 1, "query_date": day, "batch_id": batch_id,
              "batch_path": relative.as_posix(), "unique_papers": len(papers),
              "status": "ready" if papers else ("no_matching_papers" if selection and selection["source_count"] else "no_papers_for_date"),
              "selection": selection}
    write_atomic(root / "latest.json", json_text(latest))
    return latest


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fetch Giiisp metadata and prepare Chinese reading tasks for dots")
    parser.add_argument("--date", help="Giiisp query date YYYY-MM-DD; default today in Asia/Shanghai")
    parser.add_argument("--output", type=Path, default=Path("data"))
    parser.add_argument("--subject", default=SUBJECT)
    parser.add_argument("--level", type=int, choices=(1, 2, 3), default=2)
    parser.add_argument("--sections", nargs="+", choices=("1", "2", "3"), default=["1", "2", "3"])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--categories", nargs="+", default=list(DEFAULT_CATEGORIES), help="Any primary/cross-listed category; default astro-ph.GA astro-ph.CO")
    group.add_argument("--all-subjects", action="store_true", help="Explicitly disable category filtering")
    args = parser.parse_args(argv)
    today = datetime.now(ZoneInfo("Asia/Shanghai"))
    day = args.date or today.date().isoformat()
    try:
        target = datetime.strptime(day, "%Y-%m-%d").date()
        if target > today.date():
            raise ValueError("Future dates are not supported")
        if target == today.date() and today.hour < 9:
            raise NotReady("Before 09:00 Asia/Shanghai; wait for today's source update")
        sections = tuple(dict.fromkeys(args.sections))
        papers, counts = stable_collect(Client(), day, subject=args.subject, level=args.level, sections=sections)
        selection = None
        if not args.all_subjects:
            papers, selection = select_papers(papers, args.categories)
            counts = {name: sum(name in p["sections"] for p in papers) for name in counts}
        result = save_batch(args.output, day, args.subject, args.level, sections, papers, counts, selection)
        print(json_text(result), end="")
        return 0
    except NotReady as exc:
        print(f"NOT_READY: {exc}. Previous output is unchanged; do not treat it as today's batch.", file=sys.stderr)
        return 3
    except (SourceError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
