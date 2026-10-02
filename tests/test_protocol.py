import asyncio
from dataclasses import replace
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

from moonshine_stt_wyoming.config import Config
from moonshine_stt_wyoming.errors import ServiceError
from moonshine_stt_wyoming.healthcheck import is_healthy
from moonshine_stt_wyoming.protocol import Message, ProtocolSession, service_info
from moonshine_stt_wyoming.stt_service import STTService
from support import FakeBackend

FORMAT = {"rate": 16000, "width": 2, "channels": 1}


class TestService(STTService):
    @property
    def model_available(self):
        return self.backend.ready


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.backend = FakeBackend()
        self.service = TestService(Config.from_env({}), self.backend)
        self.service.loaded_path = Path("/test-only")
        self.session = ProtocolSession(self.service)

    async def asyncTearDown(self):
        await self.session.close()
        await self.service.close()

    async def start_audio(self, session=None):
        session = session or self.session
        await session.handle(Message("transcribe", {"language": "de"}))
        await session.handle(Message("audio-start", FORMAT))

    async def test_describe_and_health(self):
        info = await self.session.handle(Message("describe"))
        self.assertTrue(is_healthy(info, self.service.config))
        self.assertEqual(info.data["asr"][0]["models"][0]["name"], "small-streaming-de")
        self.backend.loaded = False
        self.assertFalse(is_healthy(await self.session.handle(Message("describe")), self.service.config))

    async def test_complete_flow_and_reuse(self):
        for _ in range(2):
            await self.start_audio()
            await self.session.handle(Message("audio-chunk", FORMAT, b"\x00" * 320))
            reply = await self.session.handle(Message("audio-stop"))
            self.assertEqual(reply.type, "transcript")
            self.assertEqual(reply.data["language"], "de")
            self.assertIn("Büro", reply.data["text"])
            self.assertEqual(len(self.service.leases), 0)
            self.assertTrue(self.backend.streams[-1].closed)

    async def test_invalid_order(self):
        for event in ("audio-start", "audio-chunk", "audio-stop"):
            with self.assertRaises(ServiceError):
                await self.session.handle(Message(event, FORMAT, b"xx"))

    async def test_wrong_language_and_model(self):
        for data in ({"language": "en"}, {"name": "tiny-streaming-de"}):
            with self.assertRaises(ServiceError):
                await self.session.handle(Message("transcribe", data))

    async def test_busy_and_disconnect_release(self):
        await self.start_audio()
        second = ProtocolSession(self.service)
        try:
            await second.handle(Message("transcribe"))
            with self.assertRaises(ServiceError) as error:
                await second.handle(Message("audio-start", FORMAT))
            self.assertEqual(error.exception.code, "busy")
            await self.session.close()
            self.assertTrue(self.backend.streams[0].closed)
            self.assertEqual(len(self.service.leases), 0)
        finally:
            await second.close()

    async def test_audio_length_failure(self):
        self.service.config = replace(self.service.config, max_audio_seconds=0.01)
        await self.start_audio()
        with self.assertRaises(ServiceError):
            await self.session.handle(Message("audio-chunk", FORMAT, b"\x00" * 322))
        self.assertEqual(self.backend.streams[0].audio, [])

    async def test_format_change(self):
        await self.start_audio()
        with self.assertRaises(ServiceError):
            await self.session.handle(Message("audio-chunk", {**FORMAT, "rate": 8000}, b"xx"))

    async def test_empty_audio(self):
        await self.start_audio()
        with self.assertRaises(ServiceError):
            await self.session.handle(Message("audio-stop"))

    async def test_unknown_event(self):
        self.assertIsNone(await self.session.handle(Message("future-extension")))

    async def test_no_transcript_logging_by_default(self):
        await self.start_audio()
        await self.session.handle(Message("audio-chunk", FORMAT, b"xx"))
        with patch("moonshine_stt_wyoming.protocol.LOGGER.info") as log:
            await self.session.handle(Message("audio-stop"))
            log.assert_not_called()

    async def test_inference_off_event_loop(self):
        loop_thread = threading.get_ident()
        worker_thread = await self.service.call(threading.get_ident)
        self.assertNotEqual(loop_thread, worker_thread)

    async def test_cancelled_open_does_not_leak_or_release_early(self):
        started, gate = threading.Event(), threading.Event()
        original = self.backend.create_stream
        def blocked():
            started.set()
            gate.wait(3)
            return original()
        self.backend.create_stream = blocked
        await self.session.handle(Message("transcribe"))
        task = asyncio.create_task(self.session.handle(Message("audio-start", FORMAT)))
        try:
            for _ in range(100):
                if started.is_set():
                    break
                await asyncio.sleep(0.01)
            self.assertTrue(started.is_set())
            task.cancel()
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            self.assertEqual(len(self.service.leases), 1)
        finally:
            gate.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        await self.session.close()
        self.assertEqual(len(self.service.leases), 0)
        self.assertTrue(self.backend.streams[0].closed)
