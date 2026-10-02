"""Assemble one Markdown daily report from dots' per-paper readings."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path

from .cli import write_atomic


def title_text(title):
    """Render common inline title math without requiring MathJax."""
    title = title.replace("$", "").replace(r"\,", " ").replace(r"\sim", "≈")
    return re.sub(r"\\(?:mathcal|mathrm|text)\{([^{}]*)\}", r"\1", title)


def safe_child(root, relative):
    child = (root / relative).resolve()
    if not child.is_relative_to(root.resolve()):
        raise ValueError("Path escapes repository")
    return child


def compose(root, absolute_images=False):
    latest = json.loads((root / "data/latest.json").read_text())
    batch = safe_child(root / "data", latest["batch_path"])
    papers = json.loads((batch / "papers.json").read_text())
    tasks = [json.loads(line) for line in (batch / "tasks.jsonl").read_text().split("\n") if line]
    if len(papers) != len(tasks):
        raise ValueError("Task count differs from paper count")
    day = latest["query_date"]
    output = root / "reports" / day / "daily.md"
    body = []
    completed = 0
    pending = []
    for number, (paper, task) in enumerate(zip(papers, tasks), 1):
        if (paper["arxiv_id"], paper["version"]) != (task["arxiv_id"], task["version"]):
            raise ValueError("Paper/task identity mismatch")
        task_id = task["task_id"]
        summary = safe_child(root / "reports/papers", task_id + ".md")
        body.extend([f"## {number:03d} · {title_text(paper['title'])}", f"arXiv：[{paper['arxiv_id']}v{paper['version']}]({paper['url']})",
                     "作者：" + paper["authors_raw"], "列表：" + ", ".join(paper["sections"]),
                     "来源关键词：" + (paper["keywords_raw"] or "来源未提供")])
        body.append(f"- [ ] 收藏 `{paper['arxiv_id']}`（可编辑勾选，或告诉 dots：收藏第 {number} 篇）")
        if summary.exists() and summary.read_text().strip():
            completed += 1
            body.append(summary.read_text().strip())
        else:
            pending.append(task_id)
            body.extend(["**待 dots 阅读；以下为原始摘要，不是已生成的总结。**", paper["abstract"]])
        assets = safe_child(root / "reports/assets", task_id)
        manifest = assets / "manifest.json"
        accepted = 0
        if manifest.exists():
            for figure in json.loads(manifest.read_text())["figures"]:
                if not figure.get("visually_verified") or not figure.get("verification_note"):
                    continue
                image = safe_child(assets, figure["image"])
                if hashlib.sha256(image.read_bytes()).hexdigest() != figure["image_sha256"]:
                    raise ValueError("Figure changed since visual verification")
                path = str(image) if absolute_images else os.path.relpath(image, output.parent)
                body.append(f"![{figure['name']}：{figure['selection_reason']}](<{path}>)")
                body.append(f"原 PDF 第 {figure['page']} 页；核验：{figure['verification_note']}")
                accepted += 1
        if not accepted:
            body.append("图表状态：无已验收图表附件；是否查看原图以正文说明为准。")
    header = [f"# {day} arXiv 天体物理论文日报", f"批次：`{latest['batch_id']}`",
              f"论文 {len(papers)} 篇；已有阅读文档 {completed} 篇；待阅读 {len(pending)} 篇。",
              "说明：标题与摘要初读；仅对明确标注的关键图表补充核验，不声称全文精读。"]
    if not papers:
        header.append("网站该查询日期没有论文。")
    write_atomic(output, "\n\n".join(header + body) + "\n")
    write_atomic(output.parent / "pending.json", json.dumps(pending, ensure_ascii=False, indent=2) + "\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--absolute-images", action="store_true", help="For Codex local Markdown preview")
    args = parser.parse_args()
    print(compose(args.root, args.absolute_images))
