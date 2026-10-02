import importlib.util
from pathlib import Path
import unittest

from moonshine_stt_wyoming.config import Config
from moonshine_stt_wyoming.protocol import Message, service_info
from moonshine_stt_wyoming.transport import read_message, write_message
from support import FakeBackend
from test_protocol import TestService
from test_transport import reader_for


class BufferWriter:
    def __init__(self):
        self.data = bytearray()
    def writelines(self, lines):
        for line in lines:
            self.data.extend(line)
    def write(self, data):
        self.data.extend(data)
    async def drain(self):
        pass


@unittest.skipUnless(importlib.util.find_spec("wyoming"), "Optional: official wyoming package not installed")
class OfficialWyomingTests(unittest.IsolatedAsyncioTestCase):
    async def test_official_writer_and_bounded_reader_roundtrip(self):
        writer = BufferWriter()
        await write_message(writer, Message("transcript", {"text": "Büro", "language": "de"}))
        result = await read_message(reader_for(bytes(writer.data)))
        self.assertEqual(result.data["text"], "Büro")
        self.assertEqual(result.type, "transcript")

    async def test_info_parses_with_official_dataclasses(self):
        from wyoming.event import Event
        from wyoming.info import Info
        service = TestService(Config.from_env({}), FakeBackend())
        service.loaded_path = Path("/test")
        try:
            message = service_info(service)
            info = Info.from_event(Event(type=message.type, data=message.data))
            self.assertEqual(info.asr[0].models[0].languages, ["de"])
            self.assertTrue(info.asr[0].models[0].installed)
        finally:
            await service.close()
