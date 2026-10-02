import asyncio
import json
import unittest

from moonshine_stt_wyoming.errors import ServiceError
from moonshine_stt_wyoming.transport import read_message


def reader_for(data):
    reader = asyncio.StreamReader(limit=8192)
    reader.feed_data(data)
    reader.feed_eof()
    return reader


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_json_and_pcm_framing(self):
        data = json.dumps({"rate": 16000, "width": 2, "channels": 1}).encode()
        header = json.dumps({"type": "audio-chunk", "data_length": len(data), "payload_length": 2}).encode()
        message = await read_message(reader_for(header + b"\n" + data + b"xx"))
        self.assertEqual(message.type, "audio-chunk")
        self.assertEqual(message.data["rate"], 16000)
        self.assertEqual(message.payload, b"xx")

    async def test_invalid_headers(self):
        values = [b"not-json\n", b"[]\n", b'{"type":"describe","payload_length":-1}\n',
                  b'{"type":"describe","data_length":true}\n',
                  b'{"type":"audio-chunk","payload_length":65537}\n',
                  b'{"type":"describe","data":[]}\n', b'{}\n', b'{"type":"describe"}',
                  b'{"type":"describe","data_length":8193}\n']
        for value in values:
            with self.subTest(value=value):
                with self.assertRaises(ServiceError):
                    await read_message(reader_for(value))

    async def test_large_header(self):
        with self.assertRaises(ServiceError):
            await read_message(reader_for(b"x" * 9000 + b"\n"))

    async def test_truncated_payload(self):
        with self.assertRaises(asyncio.IncompleteReadError):
            await read_message(reader_for(b'{"type":"audio-chunk","payload_length":4}\nxx'))

    async def test_eof(self):
        self.assertIsNone(await read_message(reader_for(b"")))
