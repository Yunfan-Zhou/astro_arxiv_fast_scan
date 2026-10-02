import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from arxiv_daily.cli import main, save_batch
from arxiv_daily.core import normalize
from arxiv_daily.report import figure_evidence, compose
from arxiv_daily.selection import select_papers


def paper(number, subjects):
    return normalize({"arvixNo": f"2610.{number:05d}", "title": "Title", "author": "Author",
                      "paperAbstract": "Abstract", "subjects": subjects}, "1")


class SelectionFigureTests(unittest.TestCase):
    def test_any_category_crosslists_and_exact_match(self):
        papers = [paper(1, "(astro-ph.GA); (astro-ph.CO)"), paper(2, "(hep-ph); (astro-ph.CO)"),
                  paper(3, "(astro-ph.IM)"), paper(4, "(astro-ph.GAX)")]
        selected, info = select_papers(papers)
        self.assertEqual([p["arxiv_id"] for p in selected], ["2610.00001", "2610.00002"])
        self.assertEqual(info["excluded_count"], 2)
        with self.assertRaises(ValueError):
            select_papers([paper(5, "")])

    def test_fetch_filters_by_default_and_all_subjects_is_explicit(self):
        papers = [paper(1, "(astro-ph.GA)"), paper(2, "(astro-ph.IM)")]
        with tempfile.TemporaryDirectory() as temp, patch("arxiv_daily.cli.stable_collect", return_value=(papers, {"New submissions": 2})), patch("builtins.print"):
            root = Path(temp)
            args = ["--date", "2026-01-02", "--output", str(root)]
            self.assertEqual(main(args), 0)
            latest = json.loads((root / "latest.json").read_text())
            self.assertEqual(latest["unique_papers"], 1)
            self.assertEqual(latest["selection"]["source_count"], 2)
            self.assertEqual(main(args + ["--all-subjects"]), 0)
            all_latest = json.loads((root / "latest.json").read_text())
            self.assertEqual(all_latest["unique_papers"], 2)
            self.assertNotEqual(latest["batch_id"], all_latest["batch_id"])

    def test_empty_filter_is_not_empty_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            selected, info = select_papers([paper(1, "astro-ph.IM")])
            latest = save_batch(root / "data", "2026-01-02", "s", 2, ("1",), selected, {}, info)
            self.assertEqual(latest["status"], "no_matching_papers")
            self.assertIn("没有符合分类筛选", compose(root).read_text())

    def test_figures_need_visual_acceptance_explanation_and_unchanged_image(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "Missing figure review"):
                figure_evidence(root, "paper", required=True)
            assets = root / "reports/assets/paper"
            assets.mkdir(parents=True)
            (assets / "review.json").write_text(json.dumps({"task_id": "paper", "status": "reviewed", "reason": "Core result"}))
            (assets / "f.png").write_bytes(b"test image bytes")
            f = {"image": "f.png", "image_sha256": hashlib.sha256(b"test image bytes").hexdigest(),
                 "visually_verified": True, "verification_note": "All panels visible"}
            manifest = assets / "manifest.json"
            manifest.write_text(json.dumps({"figures": [f]}))
            with self.assertRaisesRegex(ValueError, "missing visual analysis"):
                figure_evidence(root, "paper", required=True)
            f["analysis"] = "Axes, comparison and uncertainty explained."
            manifest.write_text(json.dumps({"figures": [f]}))
            self.assertEqual(len(figure_evidence(root, "paper", required=True)["figures"]), 1)
            f["visually_verified"] = False
            manifest.write_text(json.dumps({"figures": [f]}))
            with self.assertRaises(ValueError):
                figure_evidence(root, "paper", required=True)
            f["visually_verified"] = True
            manifest.write_text(json.dumps({"figures": [f]}))
            (assets / "f.png").write_bytes(b"modified")
            with self.assertRaisesRegex(ValueError, "changed since"):
                figure_evidence(root, "paper", required=True)


if __name__ == "__main__":
    unittest.main()
