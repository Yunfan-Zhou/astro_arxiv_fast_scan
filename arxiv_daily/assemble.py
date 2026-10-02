"""Validate all readings, assemble Markdown, and make an optional offline star UI."""
import argparse
import json
from pathlib import Path

from .cli import json_text, write_atomic
from .report import compose, safe_child


def assemble(root, readings):
    latest = json.loads((root / "data/latest.json").read_text())
    batch = safe_child(root / "data", latest["batch_path"])
    papers = json.loads((batch / "papers.json").read_text())
    tasks = [json.loads(s) for s in (batch / "tasks.jsonl").read_text().split("\n") if s]
    results = {}
    for file in sorted(readings.glob("read_*.json")):
        for item in json.loads(file.read_text()):
            number = item["index"]
            if not isinstance(number, int) or not 1 <= number <= len(papers) or number in results:
                raise ValueError(f"Invalid or duplicate reading index: {number}")
            paper = papers[number - 1]
            if (item["arxiv_id"], item["version"]) != (paper["arxiv_id"], paper["version"]):
                raise ValueError(f"Reading identity mismatch: {number}")
            for field in ("title_zh", "problem", "method", "result", "meaning", "limitation"):
                if not isinstance(item.get(field), str) or (field != "limitation" and not item[field].strip()):
                    raise ValueError(f"Invalid {field}: {number}")
            results[number] = item
    if len(results) != len(papers):
        raise ValueError(f"Incomplete readings: {len(results)}/{len(papers)}; refusing a complete report")
    for number, task in enumerate(tasks, 1):
        item = results[number]
        content = ["### " + item["title_zh"], "阅读范围：标题与摘要初读；本篇未核验图表。",
                   "- **问题：** " + item["problem"], "- **方法：** " + item["method"],
                   "- **结果：** " + item["result"], "- **意义：** " + item["meaning"]]
        if item["limitation"]:
            content.append("- **限制／来源质量：** " + item["limitation"])
        write_atomic(safe_child(root / "reports/papers", task["task_id"] + ".md"), "\n\n".join(content) + "\n")
    markdown = compose(root)
    entries = [{"index": i, **p, **results[i]} for i, p in enumerate(papers, 1)]
    payload = json.dumps({"date": latest["query_date"], "papers": entries, "markdown": markdown.read_text()}, ensure_ascii=False)
    # Source content cannot break out of the JSON script element.
    payload = payload.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    template = (Path(__file__).parent / "reader.html").read_text()
    html = markdown.with_name("reader.html")
    write_atomic(html, template.replace("__PAPER_DATA__", payload))
    return markdown, html


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--readings", type=Path, required=True)
    args = parser.parse_args()
    for output in assemble(args.root, args.readings):
        print(output)
