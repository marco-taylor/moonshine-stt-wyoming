from pathlib import Path
from types import SimpleNamespace
import unittest
import os
from unittest.mock import Mock

from moonshine_stt_wyoming.backends.base import Backend, BackendStream
from moonshine_stt_wyoming.backends.moonshine_cpu import MoonshineCPU, MoonshineStream
from moonshine_stt_wyoming.errors import ServiceError


class BackendTests(unittest.TestCase):
    def test_abstract_contract(self):
        with self.assertRaises(TypeError):
            Backend()
        with self.assertRaises(TypeError):
            BackendStream()

    def test_official_cpu_arguments_and_cleanup(self):
        native = Mock()
        native_stream = native.create_stream.return_value
        native_stream.stop.return_value = SimpleNamespace(lines=[SimpleNamespace(text=" Licht "), SimpleNamespace(text="an")])
        factory = Mock(return_value=native)
        arch = SimpleNamespace(TINY_STREAMING=2, SMALL_STREAMING=4)
        backend = MoonshineCPU(factory, arch)
        self.assertFalse(backend.ready)
        backend.initialize(Path("/models/tiny-streaming-de"), "tiny-streaming-de")
        self.assertTrue(backend.ready)
        self.assertEqual(factory.call_args.kwargs["options"]["ort_providers"], "CPU")
        self.assertEqual(factory.call_args.kwargs["options"]["log_output_text"], "false")
        stream = backend.create_stream()
        stream.add_audio(b"\x00\x40")
        native_stream.add_audio.assert_called_once_with([0.5], 16000)
        self.assertEqual(stream.finish(), "Licht an")
        stream.close()
        stream.close()
        native_stream.close.assert_called_once()
        backend.close()
        backend.close()
        native.close.assert_called_once()
        self.assertFalse(backend.ready)

    def test_small_architecture(self):
        factory = Mock()
        backend = MoonshineCPU(factory, SimpleNamespace(SMALL_STREAMING=4))
        backend.initialize(Path("/models/small-streaming-de"), "small-streaming-de")
        self.assertEqual(factory.call_args.kwargs["model_arch"], 4)
        backend.close()

    def test_supported_native_single_thread_switch(self):
        factory = Mock()
        backend = MoonshineCPU(factory, SimpleNamespace(SMALL_STREAMING=4), threads=1)
        backend.initialize(Path("/app/models/small-streaming-de"), "small-streaming-de")
        self.assertEqual(os.environ["MOONSHINE_ORT_SINGLE_THREAD"], "1")
        backend.close()
        with self.assertRaises(ServiceError):
            MoonshineCPU(threads=2)

    def test_swallowed_runtime_failure(self):
        native = Mock()
        native.stop.return_value = None
        stream = MoonshineStream(native)
        with self.assertRaises(ServiceError):
            stream.finish()
        stream.close()

    def test_start_failure_closes_stream(self):
        native = Mock()
        native.start.side_effect = RuntimeError("private content")
        with self.assertRaises(RuntimeError):
            MoonshineStream(native)
        native.close.assert_called_once()
