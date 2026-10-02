import unittest

import numpy as np

from validate_phase6 import audio_variant, normalized, percentile


class Phase6MetricTests(unittest.TestCase):
    def test_normalization_preserves_word_errors(self):
        self.assertEqual(normalized("Schoko-Bonbons!"), normalized("Schokobonbons."))
        self.assertNotEqual(normalized("Eurasien bezeichnet"), normalized("Eurasien betont"))

    def test_percentile_nearest_rank(self):
        self.assertEqual(percentile(list(range(1, 21)), .95), 19)
        self.assertEqual(percentile([2, 1], .5), 1)

    def test_clean_audio_unchanged(self):
        pcm = np.array([-32768, -1, 0, 1, 32767], dtype="<i2").tobytes()
        self.assertEqual(audio_variant(pcm, "clean"), pcm)

    def test_quiet_audio_is_half_amplitude(self):
        pcm = np.array([-1000, 0, 1000], dtype="<i2").tobytes()
        self.assertEqual(audio_variant(pcm, "quiet"), np.array([-500, 0, 500], dtype="<i2").tobytes())

    def test_noise_is_reproducible_twenty_db(self):
        original = np.full(16000, 1000, dtype="<i2")
        pcm = original.tobytes()
        noisy = audio_variant(pcm, "noise20db")
        self.assertEqual(noisy, audio_variant(pcm, "noise20db"))
        error = np.frombuffer(noisy, dtype="<i2").astype(float)-original
        self.assertAlmostEqual(float(np.sqrt(np.mean(error*error))), 100, delta=3)
