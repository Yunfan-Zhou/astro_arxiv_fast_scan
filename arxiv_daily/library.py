"""Persistent personal reading library with transactional updates and Excel-friendly CSV."""
import argparse
import csv
import json
import os
import re
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .cli import write_atomic, json_text
from .report import safe_child

COLUMNS = {
    "arxiv_id": "arXiv ID", "title": "论文名称", "title_zh": "中文标题", "authors": "作者",
    "url": "URL", "pdf_url": "PDF URL", "version": "版本", "subjects": "分类",
    "keywords": "来源关键词", "keywords_status": "关键词状态", "abstract": "摘要",
    "comments": "评论说明", "source_release_label": "来源日期原文",
    "first_seen": "首次收录日报日期", "last_seen": "最近收录日报日期",
    "saved_at": "首次加入时间", "updated_at": "最近更新时间", "favorite": "收藏",
    "deep_read": "精读列表", "status": "阅读状态", "note": "备注", "sources": "日报来源记录",
}
STATUSES = ("unread", "reading", "read")


def now():
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()


def database(root):
    folder = root / "library"
    folder.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(folder / "papers.sqlite3", timeout=30, isolation_level=None)
    conn.execute("CREATE TABLE IF NOT EXISTS papers (arxiv_id TEXT PRIMARY KEY, record TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    # Import the earlier JSON store once. Never replace a newer library record.
    conn.execute("BEGIN IMMEDIATE")
    try:
        if not conn.execute("SELECT 1 FROM settings WHERE key='legacy_imported'").fetchone():
            legacy = folder / "favorites.json"
            if legacy.exists():
                for identifier, old in json.loads(legacy.read_text()).items():
                    record = {**old, "arxiv_id": identifier, "favorite": True, "deep_read": False,
                              "status": "unread" if old.get("status", "to_read") == "to_read" else old["status"],
                              "saved_at": old.get("saved_at") or now(), "sources": old.get("sources", [])}
                    conn.execute("INSERT OR IGNORE INTO papers VALUES (?,?)", (identifier, json.dumps(record, ensure_ascii=False)))
            conn.execute("INSERT INTO settings VALUES ('legacy_imported','1')")
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        raise
    return conn


def _csv_cell(value):
    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False)
    elif isinstance(value, bool):
        value = "是" if value else "否"
    value = str(value)
    # Keep source strings as text when Excel opens the CSV, never formulas.
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r")) else value


def export_library(root, conn=None):
    """Export under the write lock so simultaneous tasks cannot publish stale snapshots."""
    if conn is None:
        with closing(database(root)) as opened:
            return export_library(root, opened)
    path = root / "library/papers.csv"
    conn.execute("BEGIN IMMEDIATE")
    temp = None
    try:
        fd, temp = tempfile.mkstemp(prefix=".papers-", suffix=".csv", dir=path.parent)
        favorites = {}
        with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(COLUMNS.values())
            for identifier, payload in conn.execute("SELECT arxiv_id, record FROM papers ORDER BY arxiv_id"):
                record = json.loads(payload)
                writer.writerow([_csv_cell(record.get(key, "")) for key in COLUMNS])
                if record.get("favorite"):
                    favorites[identifier] = record
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        write_atomic(root / "library/favorites.json", json_text(favorites))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if temp and os.path.exists(temp):
            os.unlink(temp)
    return path


def indices_from_text(text):
    tokens = re.split(r"[,，、\s]+", text.strip())
    if not tokens or any(not re.fullmatch(r"\d+", t) or int(t) < 1 for t in tokens):
        raise ValueError("Use positive report numbers, e.g. 001,002")
    return list(dict.fromkeys(int(t) for t in tokens))


def report_snapshot(root, report):
    report = report.expanduser().resolve()
    text = report.read_text(encoding="utf-8")
    match = re.search(r"^批次：`([0-9a-f]{64})`$", text, re.M)
    if not match:
        raise ValueError("Report has no batch identity; provide an original daily.md")
    batch_id = match[1]
    index = report.with_name("paper-index.json")
    if index.exists():
        snapshot = json.loads(index.read_text())
        if snapshot.get("batch_id") != batch_id:
            raise ValueError("Report/index batch mismatch")
    else:
        # Older reports can use the immutable source batch, never data/latest.json.
        data_roots = [root / "data"]
        # Old sample reports may live in their own workspace under work/.
        report_root = next((p.parent for p in report.parents if p.name == "reports"), None)
        if report_root is not None and (report_root / "data").resolve() != (root / "data").resolve():
            data_roots.append(report_root / "data")
        matches = [p for folder in data_roots for p in folder.glob(f"*/{batch_id[:16]}/batch.json")]
        matches = [p for p in matches if json.loads(p.read_text())["batch_id"] == batch_id]
        if len(matches) != 1:
            raise ValueError("Report snapshot unavailable; keep paper-index.json beside the Markdown")
        batch = matches[0].parent
        meta = json.loads((batch / "batch.json").read_text())
        papers = json.loads((batch / "papers.json").read_text())
        snapshot = {"batch_id": batch_id, "query_date": meta["query_date"],
                    "papers": [{"index": i, "paper": p} for i, p in enumerate(papers, 1)]}
    # Check displayed numbers against the snapshot, including old/edited reports.
    blocks = re.split(r"(?m)^## (\d+) ·[^\n]*\n", text)
    visible = {}
    for pos in range(1, len(blocks), 2):
        number = int(blocks[pos])
        link = re.search(r"arXiv：\[([^\]]+)v(\d+)\]\(", blocks[pos + 1])
        if not link or number in visible:
            raise ValueError("Ambiguous report numbering")
        visible[number] = (link[1], int(link[2]))
    expected = {r["index"]: (r["paper"]["arxiv_id"], r["paper"]["version"]) for r in snapshot["papers"]}
    if visible != expected or len(expected) != len(snapshot["papers"]):
        raise ValueError("Displayed report numbers differ from saved index; refusing to save the wrong paper")
    return snapshot


def _merge(conn, paper, source, kind, note):
    key = paper["arxiv_id"]
    found = conn.execute("SELECT record FROM papers WHERE arxiv_id=?", (key,)).fetchone()
    old = json.loads(found[0]) if found else {}
    record = dict(old)
    if not old or int(paper["version"]) >= int(old.get("version", 0)):
        record.update({"arxiv_id": key, "title": paper["title"], "authors": paper.get("authors_raw", ""),
                       "url": paper["url"], "pdf_url": paper.get("pdf_url") or paper["url"].replace("/abs/", "/pdf/"),
                       "version": paper["version"], "subjects": paper.get("subjects", ""),
                       "keywords": paper.get("keywords_raw", ""), "keywords_status": paper.get("keywords_status", "not_provided"),
                       "abstract": paper.get("abstract", ""), "comments": paper.get("comments", ""),
                       "source_release_label": paper.get("source_release_label", "")})
        record["title_zh"] = paper.get("title_zh") or old.get("title_zh", "")
    seen = source["report_date"]
    record.update({"first_seen": min(old.get("first_seen") or seen, seen),
                   "last_seen": max(old.get("last_seen") or seen, seen),
                   "saved_at": old.get("saved_at") or now(), "updated_at": now(),
                   "favorite": bool(old.get("favorite")) or kind == "favorite",
                   "deep_read": bool(old.get("deep_read")) or kind == "deep-read",
                   "status": old.get("status", "unread")})
    notes = old.get("note", "").split("\n") if old.get("note") else []
    if note and note not in notes:
        notes.append(note)
    record["note"] = "\n".join(notes)
    history = list(old.get("sources", []))
    if not any((s.get("batch_id"), s.get("index"), s.get("version")) == (source["batch_id"], source["index"], source["version"]) for s in history):
        history.append(source)
    record["sources"] = history
    conn.execute("INSERT INTO papers VALUES (?,?) ON CONFLICT(arxiv_id) DO UPDATE SET record=excluded.record",
                 (key, json.dumps(record, ensure_ascii=False)))
    return record, not bool(old)


def add_entries(root, entries, kind="favorite", note=""):
    if kind not in ("favorite", "deep-read"):
        raise ValueError("List must be favorite or deep-read")
    with closing(database(root)) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            records, added = [], 0
            for paper, source in entries:
                record, is_new = _merge(conn, paper, source, kind, note)
                records.append(record)
                added += int(is_new)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        csv_path = export_library(root, conn)
    return {"csv": str(csv_path.resolve()), "database": str((root / "library/papers.sqlite3").resolve()),
            "new_records": added, "existing_records": len(records) - added,
            "papers": [{"arxiv_id": r["arxiv_id"], "title": r["title"], "favorite": r["favorite"], "deep_read": r["deep_read"]} for r in records]}


def add_from_report(root, report, indices, kind="favorite", note=""):
    snapshot = report_snapshot(root, report)
    mapping = {r["index"]: r["paper"] for r in snapshot["papers"]}
    indices = list(dict.fromkeys(indices))
    if not indices or any(i not in mapping for i in indices):
        raise ValueError("Report number out of range; no papers saved")
    entries = [(mapping[i], {"batch_id": snapshot["batch_id"], "report_date": snapshot["query_date"],
                            "index": i, "version": mapping[i]["version"], "report_path": str(report.resolve())}) for i in indices]
    return add_entries(root, entries, kind, note)


def save_favorite(root, identifier, note=""):
    latest = json.loads((root / "data/latest.json").read_text())
    batch = safe_child(root / "data", latest["batch_path"])
    papers = json.loads((batch / "papers.json").read_text())
    key = identifier.removeprefix("arXiv:")
    matches = [(i, p) for i, p in enumerate(papers, 1) if p["arxiv_id"] == key]
    if not matches:
        raise ValueError("Paper not found in current batch; use its arXiv ID, or library add with an explicit report")
    index, paper = max(matches, key=lambda pair: pair[1]["version"])
    add_entries(root, [(paper, {"batch_id": latest["batch_id"], "report_date": latest["query_date"],
                              "index": index, "version": paper["version"], "report_path": ""})], note=note)
    return root / "library/favorites.json"


def list_papers(root, kind=None, status=None, limit=50):
    with closing(database(root)) as conn:
        rows = []
        for payload, in conn.execute("SELECT record FROM papers ORDER BY arxiv_id"):
            record = json.loads(payload)
            if kind and not record.get("deep_read" if kind == "deep-read" else "favorite"):
                continue
            if status and record.get("status") != status:
                continue
            rows.append(record)
            if len(rows) >= limit:
                break
        return rows


def set_status(root, identifiers, status, note=""):
    if status not in STATUSES:
        raise ValueError("Invalid reading status")
    with closing(database(root)) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            for key in identifiers:
                found = conn.execute("SELECT record FROM papers WHERE arxiv_id=?", (key,)).fetchone()
                if not found:
                    raise ValueError(f"Paper not in library: {key}")
                record = json.loads(found[0])
                record.update(status=status, updated_at=now())
                notes = record.get("note", "").split("\n") if record.get("note") else []
                if note and note not in notes:
                    notes.append(note)
                record["note"] = "\n".join(notes)
                conn.execute("UPDATE papers SET record=? WHERE arxiv_id=?", (json.dumps(record, ensure_ascii=False), key))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return export_library(root, conn)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Persistent favorites and deep-reading queue")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("export")
    add = sub.add_parser("add")
    add.add_argument("--report", type=Path, required=True)
    add.add_argument("--indices", required=True, help="Report numbers such as 001,002")
    add.add_argument("--list", dest="kind", choices=("favorite", "deep-read"), default="favorite")
    add.add_argument("--note", default="")
    show = sub.add_parser("list")
    show.add_argument("--list", dest="kind", choices=("favorite", "deep-read"))
    show.add_argument("--status", choices=STATUSES)
    show.add_argument("--limit", type=int, default=50)
    mark = sub.add_parser("mark")
    mark.add_argument("--ids", nargs="+", required=True)
    mark.add_argument("--status", choices=STATUSES, required=True)
    mark.add_argument("--note", default="", help="Append a note or a completed report path")
    args = parser.parse_args(argv)
    root = args.root.expanduser().resolve()
    if args.command in ("init", "export"):
        print(json_text({"csv": str(export_library(root)), "database": str(root / "library/papers.sqlite3")}))
    elif args.command == "add":
        print(json_text(add_from_report(root, args.report, indices_from_text(args.indices), args.kind, args.note)))
    elif args.command == "list":
        if args.limit < 1:
            parser.error("limit must be positive")
        print(json_text(list_papers(root, args.kind, args.status, args.limit)))
    else:
        print(set_status(root, args.ids, args.status, args.note))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
