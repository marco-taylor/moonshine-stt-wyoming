import asyncio
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from moonshine_stt_wyoming.config import Config
from moonshine_stt_wyoming.wyoming_server import WyomingServer
from support import FakeBackend
from test_protocol import TestService
from test_transport import reader_for


class Writer:
    def __init__(self):
        self.closed = False
    def close(self):
        self.closed = True
    async def wait_closed(self):
        pass


class ServerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.backend = FakeBackend()
        self.service = TestService(Config.from_env({}), self.backend)
        self.service.loaded_path = Path("/test")
        self.server = WyomingServer(self.service)
        self.replies = []
        async def capture(writer, message):
            self.replies.append(message)
        self.patch = patch("moonshine_stt_wyoming.wyoming_server.write_message", capture)
        self.patch.start()

    async def asyncTearDown(self):
        await self.server.close()
        await self.service.close()
        self.patch.stop()

    async def test_protocol_error_returns_error_and_closes(self):
        writer = Writer()
        await self.server.serve(reader_for(b'{"type":"audio-stop"}\n'), writer)
        self.assertEqual(self.replies[0].type, "error")
        self.assertEqual(self.replies[0].data["code"], "invalid-state")
        self.assertTrue(writer.closed)

    async def test_disconnect_releases_stream(self):
        events = [{'type': 'transcribe'}, {'type': 'audio-start',
                  'data': {'rate': 16000, 'width': 2, 'channels': 1}}]
        data = b"".join(json.dumps(event).encode() + b"\n" for event in events)
        await self.server.serve(reader_for(data), Writer())
        self.assertEqual(len(self.service.leases), 0)
        self.assertTrue(self.backend.streams[0].closed)

    async def test_native_error_redacted(self):
        def fail():
            raise RuntimeError("TOKEN=never-print-this")
        self.backend.create_stream = fail
        events = [{'type': 'transcribe'}, {'type': 'audio-start',
                  'data': {'rate': 16000, 'width': 2, 'channels': 1}}]
        data = b"".join(json.dumps(event).encode() + b"\n" for event in events)
        with self.assertLogs("moonshine_stt_wyoming", level="ERROR") as logs:
            await self.server.serve(reader_for(data), Writer())
        self.assertNotIn("never-print-this", str(self.replies) + str(logs.output))
        self.assertEqual(len(self.service.leases), 0)

    async def test_connection_limit(self):
        self.server.connections = {i: Writer() for i in range(16)}
        writer = Writer()
        self.server.accept(reader_for(b""), writer)
        self.assertTrue(writer.closed)
        self.server.connections.clear()
