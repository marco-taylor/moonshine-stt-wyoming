"""Registry/API compatibility checks; no model downloads or real inference."""
import io
import json
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

from moonshine_stt_wyoming.config import Config, validate_selection
from moonshine_stt_wyoming.errors import ConfigurationError, ServiceError
from moonshine_stt_wyoming.models import manifest, validate_model
from moonshine_stt_wyoming.model_manager import ensure_model
from moonshine_stt_wyoming.protocol import Message, ProtocolSession, service_info
from moonshine_stt_wyoming.stt_service import STTService
from support import FakeBackend, fixture_directory, model_fixture


class MultilanguageTests(unittest.TestCase):
    def test_every_registered_model_and_language_combination(self):
        models = manifest()["models"]
        languages = {s["language"] for s in models.values()}
        self.assertEqual(languages, {"ar", "de", "en", "es", "ja", "tl", "vi", "zh"})
        for name, spec in models.items():
            for language in languages:
                with self.subTest(model=name, language=language):
                    env = {"MOONSHINE_MODEL": name, "MOONSHINE_LANGUAGE": language}
                    if language == spec["language"]:
                        self.assertEqual(Config.from_env(env).model, name)
                    else:
                        with self.assertRaisesRegex(ConfigurationError, "passt nicht"):
                            Config.from_env(env)

    def test_unknown_model_and_language(self):
        for env in ({"MOONSHINE_MODEL": "invented"}, {"MOONSHINE_LANGUAGE": "xx"}):
            with self.assertRaisesRegex(ConfigurationError, "unbekannt"):
                Config.from_env(env)

    def test_unknown_configuration_values_are_not_echoed(self):
        for variable in ("MOONSHINE_MODEL", "MOONSHINE_LANGUAGE"):
            with self.assertRaises(ConfigurationError) as error:
                Config.from_env({variable: "private-test-value\nforged-log-line"})
            self.assertNotIn("private-test-value", str(error.exception))

    def test_every_model_selects_exact_native_architecture(self):
        from moonshine_voice.moonshine_api import ModelArch
        from moonshine_stt_wyoming.backends.moonshine_cpu import MoonshineCPU
        for name, spec in manifest()["models"].items():
            with self.subTest(model=name):
                factory = Mock()
                backend = MoonshineCPU(factory, ModelArch)
                try:
                    backend.initialize(Path("/not-loaded") / name, name)
                    self.assertEqual(factory.call_args.kwargs["model_arch"],
                                     getattr(ModelArch, spec["architecture"]))
                    self.assertEqual(factory.call_args.kwargs["model_path"], "/not-loaded/" + name)
                finally:
                    backend.close()

    def test_language_is_not_automatically_detected_from_model(self):
        with self.assertRaisesRegex(ConfigurationError, "erforderlich: en"):
            Config.from_env({"MOONSHINE_MODEL": "small-streaming-en"})

    def test_official_runtime_catalog_and_file_metadata_agree_exactly(self):
        from moonshine_voice.download import _stt_catalog, _stt_dependency_manifest
        from moonshine_voice.moonshine_api import ModelArch
        released = {}
        for language, entry in _stt_catalog().items():
            for item in entry["models"]:
                arch = ModelArch(item["model_arch"])
                if arch not in (ModelArch.TINY_STREAMING, ModelArch.SMALL_STREAMING,
                                ModelArch.MEDIUM_STREAMING):
                    continue
                groups = _stt_dependency_manifest(language, arch)["groups"]
                self.assertEqual(len(groups), 1)
                group = groups[0]
                self.assertEqual(group["base_url"], item["download_url"])
                name, revision = group["base_url"].split("/")[-2:]
                released[name] = {"language": language, "architecture": arch.name,
                    "revision": revision, "base_url": group["base_url"],
                    "files": {f["name"]: {"size": f["size"], "crc32c": f["checksum"]}
                              for f in group["files"]}}
                for f in group["files"]:
                    self.assertEqual(f["checksum_type"], "crc32c")
                    self.assertEqual(f["url"], group["base_url"] + "/" + f["name"])
        self.assertEqual(manifest()["models"], released)

    def test_all_models_selected_only_download_reuse_manual_and_corruption(self):
        for name, original in manifest()["models"].items():
            with self.subTest(model=name):
                source = fixture_directory()
                folder, spec = model_fixture(source, name)
                spec["base_url"] = original["base_url"]
                contents = {f: (folder / f).read_bytes() for f in spec["files"]}
                def response(request, **kwargs):
                    self.assertTrue(request.full_url.startswith(original["base_url"] + "/"))
                    result = io.BytesIO(contents[request.full_url.rsplit("/", 1)[1]])
                    result.geturl = Mock(return_value=request.full_url)
                    return result
                root = fixture_directory()
                config = Config.from_env({"MOONSHINE_MODEL": name,
                    "MOONSHINE_LANGUAGE": original["language"], "MOONSHINE_MODEL_DIR": str(root)})
                with patch("moonshine_stt_wyoming.models.model_spec", return_value=spec), \
                     patch("moonshine_stt_wyoming.model_download.model_spec", return_value=spec), \
                     patch("moonshine_stt_wyoming.model_download.urlopen", side_effect=response) as network:
                    missing = replace(config, model_dir=fixture_directory(), auto_download=False)
                    with self.assertRaises(ServiceError):
                        ensure_model(missing)
                    network.assert_not_called()
                    ensure_model(config)
                    self.assertEqual(network.call_count, len(spec["files"]))
                    self.assertEqual({p.name for p in root.iterdir()}, {name})
                    calls = network.call_count
                    ensure_model(config)
                    ensure_model(replace(config, auto_download=False))
                    self.assertEqual(network.call_count, calls)
                    manual_root = fixture_directory()
                    manual = manual_root / name
                    manual.mkdir()
                    for f, content in contents.items():
                        (manual / f).write_bytes(content)
                    self.assertEqual(ensure_model(replace(config, model_dir=manual_root)), manual)
                    self.assertFalse((manual / "model.json").exists())
                    (manual / "encoder.ort").write_bytes(b"damaged")
                    with self.assertRaises(ServiceError) as error:
                        ensure_model(replace(config, model_dir=manual_root))
                    self.assertEqual(error.exception.code, "invalid-model-files")
                    self.assertEqual((manual / "encoder.ort").read_bytes(), b"damaged")
                    self.assertEqual(network.call_count, calls)


class MultilanguageProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_info_transcript_and_language_requests_for_every_model(self):
        from wyoming.info import Info
        for name, spec in manifest()["models"].items():
            with self.subTest(model=name):
                config = Config.from_env({"MOONSHINE_MODEL": name,
                                          "MOONSHINE_LANGUAGE": spec["language"]})
                service = STTService(config, FakeBackend())
                service.loaded_path = Path("/test-only")
                session = ProtocolSession(service)
                try:
                    info = Info.from_event(__import__("wyoming.event", fromlist=["Event"]).Event(
                        type="info", data=service_info(service).data))
                    self.assertEqual(info.asr[0].name, "moonshine-stt-wyoming")
                    self.assertEqual(info.asr[0].models[0].languages, [spec["language"]])
                    wrong = "en" if spec["language"] != "en" else "de"
                    with self.assertRaises(ServiceError) as error:
                        await session.handle(Message("transcribe", {"language": wrong}))
                    self.assertEqual(error.exception.code, "unsupported-language")
                    await session.handle(Message("transcribe", {"language": spec["language"]}))
                    fmt = {"rate": 16000, "channels": 1, "width": 2}
                    await session.handle(Message("audio-start", fmt))
                    await session.handle(Message("audio-chunk", fmt, b"\x00\x00"))
                    reply = await session.handle(Message("audio-stop"))
                    self.assertEqual(reply.data["language"], spec["language"])
                finally:
                    await session.close()
                    await service.close()

    async def test_direct_config_cannot_bypass_startup_language_validation(self):
        service = STTService(Config(language="en"), FakeBackend())
        try:
            with patch("moonshine_stt_wyoming.stt_service.ensure_model") as ensure:
                with self.assertRaises(ConfigurationError):
                    await service.initialize()
                ensure.assert_not_called()
            # Info derives language from the model even for an invalid direct Config.
            self.assertEqual(service_info(service).data["asr"][0]["models"][0]["languages"], ["de"])
        finally:
            await service.close()
