"""Assemble one Markdown daily report from dots' per-paper readings."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path

from .cli import write_atomic
from .reading import READING_STYLE


def table_cell(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "&#124;").replace("\n", " ").replace("\r", " ")


def original_abstract(abstract):
    # Keep source math verbatim without requiring MathJax; embedded fences stay data.
    fence = "`" * max(3, 1 + max((len(s) for s in re.findall(r"`+", abstract)), default=0))
    return f"### 原始摘要\n\n{fence}text\n{abstract}\n{fence}"


def title_text(title):
    """Render common inline title math without requiring MathJax."""
    title = title.replace("$", "").replace(r"\,", " ").replace(r"\sim", "≈")
    return re.sub(r"\\(?:mathcal|mathrm|text)\{([^{}]*)\}", r"\1", title)


def safe_child(root, relative):
    child = (root / relative).resolve()
    if not child.is_relative_to(root.resolve()):
        raise ValueError("Path escapes repository")
    return child


def figure_evidence(root, task_id, required=False):
    assets = safe_child(root / "reports/assets", task_id)
    review_path = assets / "review.json"
    if not review_path.exists():
        if required:
            raise ValueError(f"Missing figure review: {task_id}; read key figures or record a concrete failure")
        return {"status": "pending", "reason": "尚未检查关键图表", "figures": []}
    review = json.loads(review_path.read_text())
    if review.get("task_id") != task_id or review.get("status") not in ("reviewed", "unavailable", "no_relevant_figures") or not isinstance(review.get("reason"), str) or not review["reason"].strip():
        raise ValueError(f"Invalid figure review: {task_id}")
    figures = []
    if review["status"] == "reviewed":
        manifest = json.loads((assets / "manifest.json").read_text())
        if not 1 <= len(manifest["figures"]) <= 2:
            raise ValueError("Expected 1–2 key figures per paper")
        for figure in manifest["figures"]:
            if figure.get("visually_verified") is not True or not figure.get("verification_note") or not isinstance(figure.get("analysis"), str) or not figure["analysis"].strip():
                raise ValueError(f"Unverified image or missing visual analysis: {task_id}")
            image = safe_child(assets, figure["image"])
            if hashlib.sha256(image.read_bytes()).hexdigest() != figure["image_sha256"]:
                raise ValueError("Figure changed since visual verification")
            figures.append({**figure, "path": str(image)})
    return {"status": review["status"], "reason": review["reason"], "figures": figures}


def compose(root, absolute_images=False):
    latest = json.loads((root / "data/latest.json").read_text())
    batch = safe_child(root / "data", latest["batch_path"])
    papers = json.loads((batch / "papers.json").read_text())
    tasks = [json.loads(line) for line in (batch / "tasks.jsonl").read_text().split("\n") if line]
    if len(papers) != len(tasks):
        raise ValueError("Task count differs from paper count")
    day = latest["query_date"]
    # Keep a stable path per batch: same-day refiltering must not renumber an open report.
    output = root / "reports" / day / latest["batch_id"][:16] / "daily.md"
    body = []
    index_papers = []
    completed = 0
    pending = []
    figure_counts = {"reviewed": 0, "unavailable": 0, "no_relevant_figures": 0, "pending": 0}
    for number, (paper, task) in enumerate(zip(papers, tasks), 1):
        if (paper["arxiv_id"], paper["version"]) != (task["arxiv_id"], task["version"]):
            raise ValueError("Paper/task identity mismatch")
        task_id = task["task_id"]
        summary = safe_child(root / "reports/papers" / READING_STYLE, task_id + ".md")
        index_paper = dict(paper)
        if summary.exists():
            first_line = summary.read_text().split("\n", 1)[0]
            if first_line.startswith("### "):
                index_paper["title_zh"] = first_line[4:]
        index_papers.append({"index": number, "paper": index_paper})
        metadata = [("标题", title_text(paper["title"])), ("作者", paper["authors_raw"]),
                    ("网站查询日期", day), ("分类", paper.get("subjects", "来源未提供")), ("列表", ", ".join(paper["sections"])),
                    ("来源关键词", paper["keywords_raw"] or "来源未提供"),
                    ("评论/说明", paper.get("comments") or "来源未提供")]
        table = "| 项目 | 内容 |\n|---|---|\n" + "\n".join(f"| {key} | {table_cell(value)} |" for key, value in metadata)
        body.extend([f"## {number:03d} · {title_text(paper['title'])}", f"arXiv：[{paper['arxiv_id']}v{paper['version']}]({paper['url']})", table])
        body.append(f"- [ ] 收藏 `{paper['arxiv_id']}`（可编辑勾选，或告诉 dots：收藏第 {number} 篇）")
        if summary.exists() and summary.read_text().strip():
            completed += 1
            body.append(summary.read_text().strip())
        else:
            pending.append(task_id)
            body.append("**待 dots 阅读；以下为原始摘要，不是已生成的总结。**")
        evidence = figure_evidence(root, task_id)
        figure_counts[evidence["status"]] += 1
        body.append("### 关键图表解读")
        body.append("图表状态：" + {"reviewed": "已实际读图", "unavailable": "获取或读取失败", "no_relevant_figures": "检查后无合适图表", "pending": "待检查"}[evidence["status"]] + "。" + evidence["reason"])
        for figure in evidence["figures"]:
            path = figure["path"] if absolute_images else os.path.relpath(figure["path"], output.parent)
            body.extend([f"#### {figure['name']} · PDF 第 {figure['page']} 页",
                         f"![{figure['name']}：{figure['selection_reason']}](<{path}>)", figure["analysis"],
                         f"图像核验：{figure['verification_note']}"])
        body.extend([original_abstract(paper["abstract"]), "---"])
    header = [f"# {day} arXiv 天体物理论文日报", f"批次：`{latest['batch_id']}`",
              f"论文 {len(papers)} 篇；已有阅读文档 {completed} 篇；待阅读 {len(pending)} 篇。",
              f"图表覆盖：已读 {figure_counts['reviewed']} 篇；获取/读取失败 {figure_counts['unavailable']} 篇；无合适图表 {figure_counts['no_relevant_figures']} 篇；待检查 {figure_counts['pending']} 篇。",
              "说明：摘要详解与关键图表阅读；实际读图覆盖及例外见上，不声称全文精读。"]
    header.append("收藏/待精读：告诉 dots“把本日报的 001、002 加入收藏或精读列表”。请保留同目录 paper-index.json，编号只对应本报告。")
    if not papers:
        header.append("该日期没有符合分类筛选的论文。" if (latest.get("selection") or {}).get("source_count") else "网站该查询日期没有论文。")
    if latest.get("selection"):
        selection = latest["selection"]
        header.append(f"筛选：{' / '.join(selection['categories'])}，主分类或交叉分类命中任一即保留；源列表 {selection['source_count']} 篇 → 保留 {selection['selected_count']} 篇。")
    write_atomic(output, "\n\n".join(header + body) + "\n")
    write_atomic(output.with_name("paper-index.json"), json.dumps({"schema_version": 1,
                 "batch_id": latest["batch_id"], "query_date": day, "papers": index_papers}, ensure_ascii=False, indent=2) + "\n")
    write_atomic(output.parent / "pending.json", json.dumps(pending, ensure_ascii=False, indent=2) + "\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--absolute-images", action="store_true", help="For Codex local Markdown preview")
    args = parser.parse_args()
    print(compose(args.root, args.absolute_images))
