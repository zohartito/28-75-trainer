from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from trainer2875.analysis import analyze_folder
from trainer2875.mission import DEFAULT_MISSION
from trainer2875.scoring import score_analysis


class DuplicateEvidenceTests(unittest.TestCase):
    def test_unavailable_hashes_are_not_duplicate_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "big_a.png").write_bytes(b"a" * 1001)
            (root / "big_b.png").write_bytes(b"b" * 1001)
            (root / "copy_a.jpg").write_bytes(b"same bytes")
            (root / "copy_b.jpg").write_bytes(b"same bytes")
            with patch("trainer2875.analysis.MAX_FILE_BYTES", 1000):
                analysis = analyze_folder(root)
            self.assertEqual(sum(photo.sha256 == "unavailable" for photo in analysis.photos), 2)
            card = score_analysis(analysis, DEFAULT_MISSION)
            self.assertEqual(card.duplicate_groups, (("copy_a.jpg", "copy_b.jpg"),))

            with patch("trainer2875.analysis.open_regular_file", side_effect=OSError("unreadable")):
                unreadable = score_analysis(analyze_folder(root), DEFAULT_MISSION)
            self.assertEqual(unreadable.duplicate_groups, ())
            self.assertFalse(any("remove accidental copies" in line for line in unreadable.observations))
