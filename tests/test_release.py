import unittest
from unittest.mock import patch
from pathlib import Path
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

    def assert_workflow_mutation_rejected(self, before, after):
        original_read_text = Path.read_text

        def changed_read_text(path, *args, **kwargs):
            text = original_read_text(path, *args, **kwargs)
            if path.name == "docker-publish.yml":
                self.assertIn(before, text)
                return text.replace(before, after)
            return text

        with patch.object(Path, "read_text", new=changed_read_text):
            with self.assertRaises(AssertionError):
                check()

    def test_repository_opt_in_cannot_be_removed(self):
        self.assert_workflow_mutation_rejected(
            "vars.RELEASE_PUBLISH_ENABLED == 'true' &&", "")

    def test_other_branch_cannot_replace_main(self):
        self.assert_workflow_mutation_rejected(
            "github.ref == 'refs/heads/main'", "github.ref == 'refs/heads/feature'")

    def test_pull_request_exclusion_cannot_be_removed(self):
        self.assert_workflow_mutation_rejected(
            "github.event_name != 'pull_request' &&", "")

    def test_protected_environment_cannot_be_replaced(self):
        self.assert_workflow_mutation_rejected(
            "environment: ghcr-release", "environment: unprotected")
