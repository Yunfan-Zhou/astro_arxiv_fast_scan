import json
import tempfile
import unittest
from pathlib import Path

from arxiv_daily.core import collect, stable_collect, SourceError, NotReady, normalize, reading_prompt
from arxiv_daily.cli import save_batch
from arxiv_daily.assemble import assemble
from arxiv_daily.library import save_favorite


def row(identifier="2610.00001", version=1):
    return {"arvixNo": "arXiv:" + identifier, "version": version,
            "title": "A test paper", "author": "A. Author,B. Author",
            "paperAbstract": "We report a measurement of 2 ± 1 units.", "keyWord": ""}


class Fake:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def page(self, day, subject, level, section, number, size):
        self.calls.append((section, number))
        return {"code": 200, "total": 999, "rows": self.pages.get((section, number), [])}

    def status(self, subject):
        return {"empty": "2", "count": "2"}


class Tests(unittest.TestCase):
    def test_pagination_continues_after_short_page(self):
        client = Fake({("1", 1): [row()], ("1", 2): [row("2610.00002")]})
        papers, counts = collect(client, "2026-10-02", sections=("1",))
        self.assertEqual(len(papers), 2)
        self.assertEqual(client.calls, [("1", 1), ("1", 2), ("1", 3)])
        self.assertEqual(counts["New submissions"], 2)

    def test_repeated_page_fails_closed(self):
        client = Fake({("1", 1): [row()], ("1", 2): [row()]})
        with self.assertRaises(SourceError):
            collect(client, "2026-10-02", sections=("1",))

    def test_merge_crosslists_but_keep_versions(self):
        client = Fake({("1", 1): [row()], ("2", 1): [row()], ("3", 1): [row(version=2)]})
        papers, _ = collect(client, "2026-10-02")
        self.assertEqual(len(papers), 2)
        self.assertEqual(set(papers[0]["sections"]), {"New submissions", "Cross-lists"})
        self.assertEqual(papers[1]["version"], 2)

    def test_missing_abstract_and_invalid_id_rejected(self):
        for bad in ({**row(), "paperAbstract": ""}, {**row(), "arvixNo": "../../x"}):
            with self.assertRaises(SourceError):
                normalize(bad, "1")

    def test_keywords_not_fabricated(self):
        paper = normalize(row(), "1")
        self.assertEqual(paper["keywords_status"], "not_provided")
        self.assertEqual(paper["keywords_raw"], "")
        self.assertIn("摘要未说明", reading_prompt(paper))

    def test_conflicting_crosslist_fails(self):
        client = Fake({("1", 1): [row()], ("2", 1): [{**row(), "title": "changed"}]})
        with self.assertRaises(SourceError):
            collect(client, "2026-10-02")

    def test_unstable_source_fails(self):
        class Changing(Fake):
            def page(self, *args):
                result = super().page(*args)
                if len(self.calls) > 2 and result["rows"]:
                    result["rows"] = [{**row(), "title": "changed"}]
                return result
        with self.assertRaises(NotReady):
            stable_collect(Changing({("1", 1): [row()]}), "2026-10-02", sections=("1",))

    def test_output_idempotent_and_revision_tasks_change(self):
        papers = [normalize(row(), "1")]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = save_batch(root, "2026-10-02", "s", 2, ("1",), papers, {"New submissions": 1})
            files = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(first, save_batch(root, "2026-10-02", "s", 2, ("1",), papers, {"New submissions": 1}))
            self.assertEqual(files, {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()})
            old_task = json.loads((root / first["batch_path"] / "tasks.jsonl").read_text())["task_id"]
            papers[0]["abstract"] = "Updated result"
            second = save_batch(root, "2026-10-02", "s", 2, ("1",), papers, {"New submissions": 1})
            new_task = json.loads((root / second["batch_path"] / "tasks.jsonl").read_text())["task_id"]
            self.assertNotEqual(old_task, new_task)
            self.assertTrue((root / first["batch_path"] / "papers.json").exists())

    def test_empty_batch_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            result = save_batch(Path(temp), "2026-10-02", "s", 2, ("1",), [], {})
            self.assertEqual(result["status"], "no_papers_for_date")

    def test_page_cap_fails(self):
        with self.assertRaises(SourceError):
            collect(Fake({("1", 1): [row()]}), "2026-10-02", sections=("1",), max_pages=1)

    def test_report_unicode_jsonl_and_favorite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paper = normalize({**row(), "paperAbstract": "Unexpected Unicode separator \u0085 inside source."}, "1")
            save_batch(root / "data", "2026-10-02", "s", 2, ("1",), [paper], {})
            readings = root / "readings"
            readings.mkdir()
            item = {"index": 1, "arxiv_id": paper["arxiv_id"], "version": 1,
                    "title_zh": "测试", "problem": "问题", "method": "方法", "result": "结果",
                    "meaning": "意义", "limitation": ""}
            (readings / "read_1.json").write_text(json.dumps([item]))
            markdown, html = assemble(root, readings)
            self.assertIn("待阅读 0 篇", markdown.read_text())
            self.assertIn("Unexpected Unicode separator", html.read_text())
            saved = save_favorite(root, paper["arxiv_id"], "interesting")
            self.assertEqual(json.loads(saved.read_text())[paper["arxiv_id"]]["note"], "interesting")
            save_favorite(root, paper["arxiv_id"])
            self.assertEqual(len(json.loads(saved.read_text())), 1)

    def test_assembly_rejects_missing_readings(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            save_batch(root / "data", "2026-10-02", "s", 2, ("1",), [normalize(row(), "1")], {})
            with self.assertRaises(ValueError):
                assemble(root, root / "missing")


if __name__ == "__main__":
    unittest.main()
