import csv
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from arxiv_daily.cli import save_batch
from arxiv_daily.core import normalize
from arxiv_daily.report import compose
from arxiv_daily.library import add_from_report, export_library, indices_from_text, list_papers, set_status


def paper(number, version=1, title="Paper"):
    return normalize({"arvixNo": f"2610.{number:05d}", "version": version, "title": title,
                      "author": "甲,乙", "subjects": "(astro-ph.GA)", "paperAbstract": "An abstract.",
                      "comments": "Two figures"}, "1")


def report(root, papers, date="2026-10-02"):
    save_batch(root / "data", date, "s", 2, ("1",), papers, {"New submissions": len(papers)})
    return compose(root)


class LibraryTests(unittest.TestCase):
    def test_old_report_numbers_survive_latest_batch_changes_and_both_lists(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old = report(root, [paper(1), paper(2)])
            new = report(root, [paper(3)])  # Same date, different selection/order.
            self.assertNotEqual(old, new)
            add_from_report(root, old, indices_from_text("001，002"), "deep-read", "精读原因")
            add_from_report(root, old, [1], "favorite", "收藏原因")
            records = list_papers(root)
            self.assertEqual([p["arxiv_id"] for p in records], ["2610.00001", "2610.00002"])
            self.assertTrue(records[0]["favorite"] and records[0]["deep_read"])
            self.assertEqual(records[0]["note"], "精读原因\n收藏原因")
            self.assertEqual(len(records[0]["sources"]), 1)
            self.assertEqual(records[0]["authors"], "甲,乙")
            self.assertEqual(records[0]["keywords_status"], "not_provided")
            self.assertEqual(len(list_papers(root, "deep-read", "unread")), 2)

    def test_revision_dedup_keeps_notes_saved_time_read_state_and_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = report(root, [paper(1)], "2026-10-01")
            add_from_report(root, first, [1], "deep-read", "remember")
            set_status(root, ["2610.00001"], "read")
            saved = list_papers(root)[0]["saved_at"]
            second = report(root, [paper(1, 2, "Updated")])
            add_from_report(root, second, [1], "deep-read", "remember")
            add_from_report(root, first, [1], "favorite")  # Older report cannot downgrade v2.
            record = list_papers(root)[0]
            self.assertEqual(record["version"], 2)
            self.assertEqual(record["title"], "Updated")
            self.assertEqual(record["status"], "read")
            self.assertEqual(record["note"], "remember")
            self.assertEqual(record["saved_at"], saved)
            self.assertEqual(len(record["sources"]), 2)
            self.assertEqual((record["first_seen"], record["last_seen"]), ("2026-10-01", "2026-10-02"))

    def test_out_of_range_and_edited_report_do_not_add_partial_selection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = report(root, [paper(1)])
            with self.assertRaises(ValueError):
                add_from_report(root, path, [1, 9])
            self.assertEqual(list_papers(root), [])
            path.write_text(path.read_text().replace("## 001 ·", "## 002 ·"))
            with self.assertRaisesRegex(ValueError, "numbers differ"):
                add_from_report(root, path, [2])
            self.assertEqual(list_papers(root), [])

    def test_csv_excel_text_encoding_and_no_formula_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = report(root, [paper(1, title='=HYPERLINK("untrusted")')])
            add_from_report(root, path, [1])
            csv_path = export_library(root)
            self.assertTrue(csv_path.read_bytes().startswith(b"\xef\xbb\xbf"))
            with csv_path.open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(rows[0]["作者"], "甲,乙")
            self.assertTrue(rows[0]["论文名称"].startswith("'="))
            self.assertEqual(rows[0]["来源关键词"], "")
            self.assertTrue(list_papers(root)[0]["title"].startswith("="))

    def test_simultaneous_additions_preserve_both_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = report(root, [paper(1), paper(2)])
            export_library(root)
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda i: add_from_report(root, path, [i]), [1, 2]))
            self.assertEqual(sum(r["new_records"] for r in results), 2)
            self.assertEqual(len(list_papers(root)), 2)
            with (root / "library/papers.csv").open(encoding="utf-8-sig", newline="") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 2)

    def test_legacy_favorites_migrate_once_without_losing_notes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "library").mkdir()
            old = {"2610.00001": {"title": "Old", "arxiv_id": "2610.00001", "version": 1,
                                   "note": "Old note", "saved_at": "2026-09-30", "status": "to_read"}}
            (root / "library/favorites.json").write_text(json.dumps(old))
            export_library(root)
            export_library(root)
            records = list_papers(root)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["note"], "Old note")
            self.assertEqual(records[0]["saved_at"], "2026-09-30")
            self.assertEqual(records[0]["status"], "unread")

    def test_status_update_is_atomic_for_unknown_id(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = report(root, [paper(1)])
            add_from_report(root, path, [1])
            with self.assertRaises(ValueError):
                set_status(root, ["2610.00001", "missing"], "read")
            self.assertEqual(list_papers(root)[0]["status"], "unread")


if __name__ == "__main__":
    unittest.main()
