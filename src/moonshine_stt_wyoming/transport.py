"""Bounded Wyoming framing with the official wyoming Event and writer."""
import asyncio
import json

from .audio import MAX_CHUNK_BYTES
from .errors import ServiceError
from .protocol import Message

MAX_JSON_BYTES = 8192


def _object(raw):
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError):
        raise ServiceError("invalid-event", "Ungültiges Wyoming-JSON") from None
    if not isinstance(value, dict):
        raise ServiceError("invalid-event", "Wyoming-Ereignis muss ein JSON-Objekt sein")
    return value


def _length(header, key, maximum):
    value = header.get(key, 0)
    if type(value) is not int or not 0 <= value <= maximum:
        raise ServiceError("event-too-large", "Ungültige oder zu große Wyoming-Ereignislänge")
    return value


async def read_message(reader: asyncio.StreamReader):
    try:
        line = await reader.readline()
    except ValueError:
        raise ServiceError("event-too-large", "Wyoming-Header ist zu groß") from None
    if not line:
        return None
    if len(line) > MAX_JSON_BYTES or not line.endswith(b"\n"):
        raise ServiceError("invalid-event", "Wyoming-Header ist unvollständig oder zu groß")
    header = _object(line)
    kind = header.get("type")
    if not isinstance(kind, str) or not kind or len(kind) > 128:
        raise ServiceError("invalid-event", "Wyoming-Ereignistyp fehlt oder ist ungültig")
    data = header.get("data", {})
    if not isinstance(data, dict):
        raise ServiceError("invalid-event", "Wyoming-Daten müssen ein JSON-Objekt sein")
    data_length = _length(header, "data_length", MAX_JSON_BYTES)
    payload_length = _length(header, "payload_length", MAX_CHUNK_BYTES)
    if payload_length and kind != "audio-chunk":
        raise ServiceError("invalid-event", "Binäre Nutzdaten sind nur für audio-chunk erlaubt")
    if data_length:
        data.update(_object(await reader.readexactly(data_length)))
    payload = await reader.readexactly(payload_length) if payload_length else None
    return Message(kind, data, payload)


async def write_message(writer, message: Message):
    from wyoming.event import Event, async_write_event
    await async_write_event(Event(type=message.type, data=message.data, payload=message.payload), writer)
