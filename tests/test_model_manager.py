from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

from moonshine_stt_wyoming.config import Config
from moonshine_stt_wyoming.errors import ServiceError
from moonshine_stt_wyoming.model_manager import ensure_model
from support import fixture_directory, model_fixture


class ModelManagerTests(unittest.TestCase):
    def config(self, root, auto=True):
        return Config(model_dir=root, auto_download=auto)

    def test_missing_small_auto_downloads_only_once(self):
        root = fixture_directory()
        fixture_root = fixture_directory()
        _, spec = model_fixture(fixture_root, "small-streaming-de")
        config = self.config(root)
        with patch("moonshine_stt_wyoming.models.model_spec", return_value=spec), \
             patch("moonshine_stt_wyoming.model_download.download",
                   side_effect=lambda _: model_fixture(root, "small-streaming-de")) as download:
            ensure_model(config)
            ensure_model(config)
            download.assert_called_once_with(config)

    def test_existing_tiny_does_not_replace_or_provision_default_small(self):
        root = fixture_directory()
        tiny, _ = model_fixture(root, "tiny-streaming-de")
        source = fixture_directory()
        _, small_spec = model_fixture(source, "small-streaming-de")
        config = self.config(root)
        with patch("moonshine_stt_wyoming.models.model_spec", return_value=small_spec), \
             patch("moonshine_stt_wyoming.model_download.download",
                   side_effect=lambda _: model_fixture(root, "small-streaming-de")) as download:
            self.assertEqual(ensure_model(config), root / "small-streaming-de")
            download.assert_called_once_with(config)
            self.assertEqual(config.model, "small-streaming-de")
        self.assertTrue(tiny.exists())

    def test_missing_tiny_is_downloaded_only_when_explicitly_selected(self):
        root = fixture_directory()
        source = fixture_directory()
        _, spec = model_fixture(source, "tiny-streaming-de")
        config = replace(self.config(root), model="tiny-streaming-de")
        with patch("moonshine_stt_wyoming.models.model_spec", return_value=spec), \
             patch("moonshine_stt_wyoming.model_download.download",
                   side_effect=lambda _: model_fixture(root, "tiny-streaming-de")) as download:
            self.assertEqual(ensure_model(config), root / "tiny-streaming-de")
            ensure_model(config)
            download.assert_called_once_with(config)
        self.assertFalse((root / "small-streaming-de").exists())

    def test_existing_valid_small_offline_never_downloads(self):
        root = fixture_directory()
        directory, spec = model_fixture(root, "small-streaming-de")
        with patch("moonshine_stt_wyoming.models.model_spec", return_value=spec), \
             patch("moonshine_stt_wyoming.model_download.download") as download:
            self.assertEqual(ensure_model(self.config(root, False)), directory)
            download.assert_not_called()

    def test_missing_offline_has_clear_error_and_no_writes(self):
        root = fixture_directory() / "not-created"
        with patch("moonshine_stt_wyoming.model_download.download") as download:
            with self.assertRaises(ServiceError) as error:
                ensure_model(self.config(root, False))
            self.assertEqual(error.exception.code, "model-missing")
            self.assertIn("MOONSHINE_AUTO_DOWNLOAD=0", str(error.exception))
            download.assert_not_called()
        self.assertFalse(root.exists())

    def test_manual_artifacts_without_private_metadata_are_accepted(self):
        source = fixture_directory()
        directory, spec = model_fixture(source, "small-streaming-de")
        root = fixture_directory()
        manual = root / "small-streaming-de"
        manual.mkdir()
        for name in spec["files"]:
            (manual / name).write_bytes((directory / name).read_bytes())
        with patch("moonshine_stt_wyoming.models.model_spec", return_value=spec), \
             patch("moonshine_stt_wyoming.model_download.download") as download:
            self.assertEqual(ensure_model(self.config(root)), manual)
            self.assertEqual(ensure_model(self.config(root, False)), manual)
            download.assert_not_called()
        self.assertFalse((manual / "model.json").exists())

    def test_partial_directory_never_overwritten_or_downloaded(self):
        root = fixture_directory()
        manual = root / "small-streaming-de"
        manual.mkdir()
        (manual / "encoder.ort").write_bytes(b"incomplete")
        with patch("moonshine_stt_wyoming.model_download.download") as download:
            with self.assertRaises(ServiceError) as error:
                ensure_model(self.config(root))
            self.assertEqual(error.exception.code, "invalid-model-files")
            download.assert_not_called()
        self.assertEqual((manual / "encoder.ort").read_bytes(), b"incomplete")

    def test_tiny_remains_selectable(self):
        root = fixture_directory()
        directory, spec = model_fixture(root, "tiny-streaming-de")
        config = replace(self.config(root, False), model="tiny-streaming-de")
        with patch("moonshine_stt_wyoming.models.model_spec", return_value=spec):
            self.assertEqual(ensure_model(config), directory)

    def test_download_failure_is_redacted(self):
        root = fixture_directory()
        with patch("moonshine_stt_wyoming.model_download.download",
                   side_effect=RuntimeError("private credential")):
            with self.assertRaises(ServiceError) as error:
                ensure_model(self.config(root))
            self.assertEqual(error.exception.code, "model-download-failed")
            self.assertNotIn("private credential", str(error.exception))
