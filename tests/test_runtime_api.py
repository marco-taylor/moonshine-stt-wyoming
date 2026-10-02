"""API contract checks, without loading models or invoking download helpers."""
import importlib.util
import importlib.metadata
import inspect
import unittest


@unittest.skipUnless(importlib.util.find_spec("moonshine_voice"), "Official runtime not installed")
class RuntimeAPITests(unittest.TestCase):
    def test_official_cpu_constructor_contract(self):
        from moonshine_voice import Transcriber
        from moonshine_voice.moonshine_api import ModelArch
        self.assertEqual(importlib.metadata.version("moonshine-voice"), "0.1.5")
        inspect.signature(Transcriber).bind(model_path="/not-loaded", model_arch=ModelArch.TINY_STREAMING,
                                          update_interval=0.5, options={"ort_providers": "CPU"})
        self.assertEqual(ModelArch.TINY_STREAMING.value, 2)
        self.assertEqual(ModelArch.SMALL_STREAMING.value, 4)

    def test_official_stream_contract(self):
        from moonshine_voice import Transcriber
        from moonshine_voice.transcriber import Stream
        inspect.signature(Transcriber.create_stream).bind(None, update_interval=0.5)
        inspect.signature(Stream.add_audio).bind(None, [0.0], 16000)
        for name in ("start", "stop", "close"):
            inspect.signature(getattr(Stream, name)).bind(None)

