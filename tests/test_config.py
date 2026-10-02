import unittest
from moonshine_stt_wyoming.config import Config
from moonshine_stt_wyoming.errors import ConfigurationError


class ConfigTests(unittest.TestCase):
    def test_defaults(self):
        config = Config.from_env({})
        self.assertEqual(config.port, 10300)
        self.assertEqual(config.host, "0.0.0.0")
        self.assertEqual(config.model, "small-streaming-de")
        self.assertEqual(config.language, "de")
        self.assertEqual(config.device, "cpu")
        self.assertEqual(config.auto_download, True)
        self.assertEqual(config.max_concurrent_requests, 1)
        self.assertEqual(config.max_audio_seconds, 30)
        self.assertFalse(config.log_transcripts)
        self.assertEqual(str(config.model_dir), "/app/models")
        self.assertEqual(config.threads, 1)

    def test_offline_and_single_thread(self):
        config = Config.from_env({"MOONSHINE_AUTO_DOWNLOAD": "0", "MOONSHINE_THREADS": "1"})
        self.assertFalse(config.auto_download)
        self.assertEqual(config.threads, 1)

    def test_retired_variable_names_fail_instead_of_ignoring_them(self):
        for name in ("MODEL_DIR", "MODEL_DOWNLOAD_POLICY", "MAX_CONCURRENT_REQUESTS"):
            with self.assertRaises(ConfigurationError):
                Config.from_env({name: "never-print-this-value"})

    def test_small_and_overrides(self):
        config = Config.from_env({"MOONSHINE_MODEL": "tiny-streaming-de", "WYOMING_PORT": "12000",
                                  "MOONSHINE_MODEL_DIR": "/custom/models", "LOG_TRANSCRIPTS": "true"})
        self.assertEqual(config.model, "tiny-streaming-de")
        self.assertEqual(config.port, 12000)
        self.assertTrue(config.log_transcripts)

    def test_invalid_config(self):
        cases = {"MOONSHINE_LANGUAGE": ["en", ""], "MOONSHINE_MODEL": ["../secret", "tiny"],
                 "STT_DEVICE": ["cuda", "auto"], "MOONSHINE_AUTO_DOWNLOAD": ["always", "auto", "true", "2"], "MOONSHINE_THREADS": ["0", "2", "3", "65"],
                 "WYOMING_PORT": ["0", "65536", "token-secret"], "MOONSHINE_MODEL_DIR": ["", "relative"],
                 "WYOMING_STT_CONCURRENT_REQUESTS": ["0", "9"], "MAX_AUDIO_SECONDS": ["0", "nan", "inf", "301"],
                 "LOG_TRANSCRIPTS": ["1", "yes"], "LOG_LEVEL": ["unknown"],
                 "WYOMING_HOST": ["", "host/token-secret"], "MAX_CONNECTIONS": ["0"],
                 "CLIENT_TIMEOUT_SECONDS": ["0"]}
        for key, values in cases.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    with self.assertRaises(ConfigurationError) as error:
                        Config.from_env({key: value})
                    self.assertNotIn("token-secret", str(error.exception))
