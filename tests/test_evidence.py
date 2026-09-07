import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from build_evidence import build_evidence  # noqa: E402


class RecordedRunEvidenceTests(unittest.TestCase):
    def test_public_evidence_rebuilds_from_tracked_inputs(self):
        evidence = build_evidence(
            REPO_ROOT / "data" / "recorded-run.json",
            REPO_ROOT / "data" / "imports",
        )

        self.assertEqual(evidence["summary"]["input_files"], 5)
        self.assertEqual(evidence["summary"]["raw_records"], 161)
        self.assertEqual(evidence["summary"]["unique_papers"], 159)
        self.assertEqual(evidence["summary"]["links"]["reachable_total"], 156)
        self.assertEqual(sum(evidence["summary"]["relevance"].values()), 159)

        committed = json.loads(
            (REPO_ROOT / "web" / "public" / "run-summary.json").read_text(encoding="utf-8")
        )
        self.assertEqual(evidence, committed)


if __name__ == "__main__":
    unittest.main()
