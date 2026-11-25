from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class BuildToolingTests(unittest.TestCase):
    def test_build_backend_is_pinned_and_hash_locked(self) -> None:
        project = (REPO_ROOT / "pyproject.toml").read_text()
        requirement = re.search(r'requires = \["([^"\n]+)"\]', project).group(1)
        self.assertRegex(requirement, r"^setuptools==[0-9]+\.[0-9]+\.[0-9]+$")
        lock = (REPO_ROOT / "requirements-build.txt").read_text()
        self.assertRegex(lock, re.escape(requirement) + r"\s+--hash=sha256:[a-f0-9]{64}(?:\s|$)")
