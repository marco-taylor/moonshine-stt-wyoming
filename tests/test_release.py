import unittest
from unittest.mock import patch
from release_checks import check


class ReleaseTests(unittest.TestCase):
    def test_release_metadata_and_gates(self):
        self.assertTrue(check()["passed"])

    def test_matching_tag(self):
        with patch.dict("os.environ", {"GITHUB_REF": "refs/tags/v0.1.0"}):
            self.assertTrue(check()["passed"])

    def test_mismatched_version_tag_fails(self):
        with patch.dict("os.environ", {"GITHUB_REF": "refs/tags/v9.9.9"}):
            with self.assertRaisesRegex(AssertionError, "Tag must match"):
                check()
