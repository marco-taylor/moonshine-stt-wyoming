import json
import io
import unittest
from unittest.mock import patch, Mock

from moonshine_stt_wyoming.errors import ServiceError
from moonshine_stt_wyoming.integrity import CRC32C
from moonshine_stt_wyoming.model_download import download
from moonshine_stt_wyoming.config import Config
from moonshine_stt_wyoming.models import manifest, validate_model
from support import fixture_directory, model_fixture


class ModelTests(unittest.TestCase):
    def test_explicit_download_identifies_project_and_checks_integrity(self):
        root = fixture_directory()
        fixture_root = fixture_directory()
        directory, spec = model_fixture(fixture_root)
        spec["base_url"] = "https://download.moonshine.ai/model/test/revision"
        contents = {name: (directory / name).read_bytes() for name in spec["files"]}

        def response(request, **kwargs):
            self.assertEqual(request.get_header("User-agent"), "moonshine-stt-wyoming/0.1.0")
            self.assertTrue(request.full_url.startswith(spec["base_url"] + "/"))
            result = io.BytesIO(contents[request.full_url.rsplit("/", 1)[1]])
            result.geturl = Mock(return_value=request.full_url)
            return result

        config = Config.from_env({"MOONSHINE_MODEL_DIR": str(root), "MOONSHINE_AUTO_DOWNLOAD": "1", "MOONSHINE_MODEL": "tiny-streaming-de"})
        with patch("moonshine_stt_wyoming.model_download.model_spec", return_value=spec), \
             patch("moonshine_stt_wyoming.models.model_spec", return_value=spec), \
             patch("moonshine_stt_wyoming.model_download.urlopen", side_effect=response) as network:
            download(config)
            self.assertEqual(network.call_count, len(spec["files"]))
            validate_model(root, "tiny-streaming-de")

    def test_official_models(self):
        models = manifest()["models"]
        self.assertTrue({"tiny-streaming-de", "small-streaming-de"}.issubset(models))
        self.assertEqual(models["tiny-streaming-de"]["architecture"], "TINY_STREAMING")
        self.assertEqual(models["small-streaming-de"]["architecture"], "SMALL_STREAMING")
        for spec in models.values():
            self.assertEqual(len(spec["files"]), 8)
            self.assertTrue(spec["revision"].startswith("quantized_"))

    def test_crc_known_vector(self):
        crc = CRC32C()
        crc.update(b"123456789")
        self.assertEqual(crc.digest().hex(), "e3069283")

    def test_valid_fixture(self):
        root = fixture_directory()
        directory, spec = model_fixture(root)
        with patch("moonshine_stt_wyoming.models.model_spec", return_value=spec):
            self.assertEqual(validate_model(root, "tiny-streaming-de"), directory)

    def test_missing_model(self):
        with self.assertRaises(ServiceError):
            validate_model(fixture_directory(), "tiny-streaming-de")

    def test_corrupt_model(self):
        root = fixture_directory()
        directory, spec = model_fixture(root)
        (directory / "encoder.ort").write_bytes(b"corruption")
        with patch("moonshine_stt_wyoming.models.model_spec", return_value=spec):
            with self.assertRaises(ServiceError):
                validate_model(root, "tiny-streaming-de")

    def test_wrong_revision(self):
        root = fixture_directory()
        directory, spec = model_fixture(root)
        metadata = json.loads((directory / "model.json").read_text())
        metadata["revision"] = "wrong"
        (directory / "model.json").write_text(json.dumps(metadata))
        with patch("moonshine_stt_wyoming.models.model_spec", return_value=spec):
            with self.assertRaises(ServiceError):
                validate_model(root, "tiny-streaming-de")

    def test_deeply_nested_optional_metadata_is_reported_as_invalid(self):
        root = fixture_directory()
        directory, spec = model_fixture(root)
        (directory / "model.json").write_text('[' * 1500 + '0' + ']' * 1500)
        with patch("moonshine_stt_wyoming.models.model_spec", return_value=spec):
            with self.assertRaises(ServiceError) as error:
                validate_model(root, "tiny-streaming-de")
            self.assertEqual(error.exception.code, "invalid-model-files")

    def test_upstream_crc_checked_even_if_local_sha_matches(self):
        root = fixture_directory()
        _, spec = model_fixture(root)
        spec["files"]["encoder.ort"]["crc32c"] = "AAAAAA=="
        with patch("moonshine_stt_wyoming.models.model_spec", return_value=spec):
            with self.assertRaises(ServiceError):
                validate_model(root, "tiny-streaming-de")

    def test_never_does_not_touch_network(self):
        with patch("moonshine_stt_wyoming.model_download.urlopen") as network:
            with self.assertRaises(ServiceError) as error:
                download(Config.from_env({"MOONSHINE_AUTO_DOWNLOAD": "0"}))
            self.assertEqual(error.exception.code, "download-disabled")
            network.assert_not_called()

    def test_existing_model_never_overwritten(self):
        root = fixture_directory()
        directory, _ = model_fixture(root)
        before = (directory / "encoder.ort").read_bytes()
        config = Config.from_env({"MOONSHINE_MODEL_DIR": str(root), "MOONSHINE_AUTO_DOWNLOAD": "1", "MOONSHINE_MODEL": "tiny-streaming-de"})
        with patch("moonshine_stt_wyoming.model_download.urlopen") as network:
            with self.assertRaises(ServiceError):
                download(config)
            network.assert_not_called()
        self.assertEqual((directory / "encoder.ort").read_bytes(), before)
