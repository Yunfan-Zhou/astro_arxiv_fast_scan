import json
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.install_skill import install
from arxiv_daily.cli import save_batch
from arxiv_daily.core import normalize
from arxiv_daily.reading import READING_STYLE


class SkillInstallTests(unittest.TestCase):
    def test_delivery_cache_requires_current_reading_style(self):
        runner = Path(__file__).resolve().parents[1] / "skills/arxiv-daily-reader/scripts/run.py"
        spec = importlib.util.spec_from_file_location("reader_runner", runner)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / "report.md"
            report.write_text("exists")
            cached = {"batch_id": "same", "markdown": str(report), "html": str(report)}
            latest = {"batch_id": "same"}
            self.assertFalse(module.reusable(cached, latest))
            cached["reading_style"] = READING_STYLE
            self.assertTrue(module.reusable(cached, latest))
            self.assertFalse(module.reusable(cached, {"batch_id": "changed"}))

    def test_standalone_install_and_finish_outside_repository(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace = (root / "paper workspace").resolve()
            destination = install(root / "skills/arxiv-daily-reader", workspace)
            script = destination / "scripts/run.py"
            status = subprocess.check_output([sys.executable, str(script), "status"], cwd=root, text=True)
            self.assertEqual(Path(json.loads(status)["workspace"]), workspace)
            self.assertTrue((destination / "references/FIGURES.md").exists())
            self.assertTrue((destination / "scripts/arxiv_daily/reader.html").exists())
            paper = normalize({"arvixNo": "2610.00001", "version": 1, "title": "Title", "author": "Author",
                               "paperAbstract": "A measured result."}, "1")
            latest = save_batch(workspace / "data", "2026-10-02", "s", 2, ("1",), [paper], {})
            readings = workspace / "readings/2026-10-02" / latest["batch_id"][:16] / READING_STYLE
            readings.mkdir(parents=True)
            row = {"index": 1, "arxiv_id": "2610.00001", "version": 1, "title_zh": "标题",
                   "problem": "问题", "method": "方法", "result": "结果", "meaning": "意义", "limitation": ""}
            (readings / "read_001_001.json").write_text(json.dumps([row]))
            output = json.loads(subprocess.check_output([sys.executable, str(script), "finish"], cwd=root, text=True))
            self.assertTrue(Path(output["markdown"]).exists())
            self.assertIn("待阅读 0 篇", Path(output["markdown"]).read_text())
            self.assertEqual(json.loads((workspace / "reports/delivery.json").read_text())["batch_id"], latest["batch_id"])
            subprocess.check_call([sys.executable, str(script), "favorite", "2610.00001", "--note", "follow up"],
                                  cwd=root, stdout=subprocess.DEVNULL)
            self.assertEqual(json.loads((workspace / "library/favorites.json").read_text())["2610.00001"]["note"], "follow up")
            with self.assertRaises(FileExistsError):
                install(destination, workspace)


if __name__ == "__main__":
    unittest.main()
