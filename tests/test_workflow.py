from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pipeline
from parser import Paper, init_db, insert_paper, parse_file


REPO_ROOT = Path(__file__).resolve().parents[1]


class ParserEvidenceTests(unittest.TestCase):
    def test_recorded_imports_resolve_to_expected_counts(self):
        papers = []
        for path in sorted((REPO_ROOT / "data" / "imports").iterdir()):
            if path.is_file():
                papers.extend(parse_file(path))

        self.assertEqual(len(papers), 161)
        self.assertEqual(len({paper.dedup_key for paper in papers}), 159)

    def test_second_insert_is_deduplicated(self):
        conn = sqlite3.connect(":memory:")
        conn.execute(
            """
            CREATE TABLE papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dedup_key TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                authors TEXT, year TEXT, source TEXT, search_keyword TEXT,
                abstract TEXT, keywords TEXT, journal TEXT, volume TEXT,
                issue TEXT, pages TEXT, doi TEXT, link TEXT, language TEXT,
                pub_type TEXT, advisor TEXT, university TEXT, degree TEXT
            )
            """
        )
        paper = Paper("A stable title", "", "2026", "WOS", "test")
        self.assertTrue(insert_paper(conn, paper))
        self.assertFalse(insert_paper(conn, paper))
        conn.close()


class ReliabilityTests(unittest.TestCase):
    def test_email_brief_prioritizes_actions_instead_of_dumping_all_records(self):
        papers = []
        for relevance, count in (("high", 4), ("medium", 6), ("low", 2)):
            for index in range(count):
                papers.append(
                    {
                        "title": f"{relevance}-{index}",
                        "source": "CNKI",
                        "year": "2026",
                        "journal": "",
                        "language": "zh",
                        "relevance": relevance,
                        "analysis": f"判定理由: {relevance}-{index}",
                        "link": f"https://example.com/{relevance}/{index}",
                    }
                )

        brief = pipeline.step_format_brief(papers)

        self.assertIn("优先阅读全文 4 篇", brief)
        self.assertIn("其他高相关（1 篇）", brief)
        self.assertIn("浏览摘要（6 篇，邮件展示前 5 篇）", brief)
        self.assertIn("背景参考（2 篇）已归档", brief)
        self.assertNotIn("low-0", brief)
        self.assertIn("完整运行记录", brief)

    def test_incomplete_analysis_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Incomplete AI response"):
            pipeline._validate_analysis_results(
                [{"id": 1, "relevance": "unanalyzed", "analysis": ""}],
                expected_count=1,
            )

    def test_failed_delivery_keeps_paper_unpushed(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            conn = init_db(str(db_path))
            paper = Paper("Retry-safe title", "", "2026", "CNKI", "test")
            insert_paper(conn, paper)
            paper_id = conn.execute("SELECT id FROM papers").fetchone()[0]
            conn.close()

            analyzed = [
                {
                    "id": paper_id,
                    "title": paper.title,
                    "source": "CNKI",
                    "year": "2026",
                    "journal": "",
                    "language": "zh",
                    "relevance": "high",
                    "analysis": "判定理由: test",
                }
            ]

            with (
                patch("pipeline.step_collect", return_value=0),
                patch("pipeline.step_analyze", return_value=analyzed),
                patch("pipeline.step_format_brief", return_value="brief"),
                patch("pipeline.step_send_email", return_value=False),
            ):
                success = pipeline.run_pipeline(
                    import_dir=Path(tmp),
                    db_path=db_path,
                )

            self.assertFalse(success)
            conn = sqlite3.connect(db_path)
            pushed = conn.execute("SELECT pushed FROM papers WHERE id = ?", (paper_id,)).fetchone()[0]
            conn.close()
            self.assertEqual(pushed, 0)

    def test_dry_run_does_not_mark_pushed(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            conn = init_db(str(db_path))
            paper = Paper("Dry-run title", "", "2026", "CNKI", "test")
            insert_paper(conn, paper)
            paper_id = conn.execute("SELECT id FROM papers").fetchone()[0]
            conn.close()

            analyzed = [
                {
                    "id": paper_id,
                    "title": paper.title,
                    "source": "CNKI",
                    "year": "2026",
                    "journal": "",
                    "language": "zh",
                    "relevance": "medium",
                    "analysis": "判定理由: test",
                }
            ]

            with (
                patch("pipeline.step_collect", return_value=0),
                patch("pipeline.step_analyze", return_value=analyzed),
                patch("pipeline.step_format_brief", return_value="brief"),
            ):
                success = pipeline.run_pipeline(
                    import_dir=Path(tmp),
                    db_path=db_path,
                    dry_run=True,
                )

            self.assertTrue(success)
            conn = sqlite3.connect(db_path)
            pushed = conn.execute("SELECT pushed FROM papers WHERE id = ?", (paper_id,)).fetchone()[0]
            conn.close()
            self.assertEqual(pushed, 0)


if __name__ == "__main__":
    unittest.main()
