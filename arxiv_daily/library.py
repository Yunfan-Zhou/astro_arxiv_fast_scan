"""Small portable favorites store; no vector database or service required."""
import argparse
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from .cli import write_atomic, json_text
from .report import safe_child


def save_favorite(root, identifier, note=""):
    latest = json.loads((root / "data/latest.json").read_text())
    batch = safe_child(root / "data", latest["batch_path"])
    papers = json.loads((batch / "papers.json").read_text())
    key = identifier.removeprefix("arXiv:")
    matches = [p for p in papers if p["arxiv_id"] == key]
    if not matches:
        raise ValueError("Paper not found in current batch; use its arXiv ID, not an ambiguous index")
    paper = max(matches, key=lambda p: p["version"])
    path = root / "library/favorites.json"
    items = json.loads(path.read_text()) if path.exists() else {}
    existing = items.get(key, {})
    items[key] = {"arxiv_id": key, "title": paper["title"], "url": paper["url"],
                  "version": paper["version"], "note": note or existing.get("note", ""),
                  "status": existing.get("status", "to_read"),
                  "saved_at": existing.get("saved_at", datetime.now(ZoneInfo("Asia/Shanghai")).isoformat())}
    write_atomic(path, json_text(items))
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Save a paper for future deep reading")
    parser.add_argument("arxiv_id")
    parser.add_argument("--note", default="")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(save_favorite(args.root, args.arxiv_id, args.note))
