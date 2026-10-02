import struct
import unittest
from moonshine_stt_wyoming.audio import AudioBudget, pcm_to_float, validate_format
from moonshine_stt_wyoming.errors import ServiceError

FORMAT = {"rate": 16000, "width": 2, "channels": 1}


class AudioTests(unittest.TestCase):
    def test_format(self):
        validate_format(FORMAT)
        for key, value in (("rate", 48000), ("width", 4), ("channels", 2), ("channels", True), ("rate", "16000")):
            with self.subTest(key=key, value=value):
                with self.assertRaises(ServiceError):
                    validate_format({**FORMAT, key: value})
        with self.assertRaises(ServiceError):
            validate_format({})

    def test_pcm_signed_little_endian(self):
        values = pcm_to_float(struct.pack("<hhhh", -32768, 0, 16384, 32767))
        self.assertEqual(values[:3], [-1.0, 0.0, 0.5])
        self.assertLess(values[3], 1)

    def test_budget_exact_boundary(self):
        budget = AudioBudget(0.01)
        budget.accept(b"\x00" * 320)
        with self.assertRaises(ServiceError) as error:
            budget.accept(b"\x00\x00")
        self.assertEqual(error.exception.code, "audio-too-long")
        self.assertEqual(budget.total_bytes, 320)

    def test_invalid_chunk(self):
        for chunk in (b"", b"x", b"x" * 65538):
            with self.assertRaises(ServiceError):
                AudioBudget(30).accept(chunk)
