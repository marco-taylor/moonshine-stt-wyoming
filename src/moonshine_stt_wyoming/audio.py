import struct

from .errors import ServiceError

RATE = 16000
WIDTH = 2
CHANNELS = 1
BYTES_PER_SECOND = RATE * WIDTH * CHANNELS
MAX_CHUNK_BYTES = 65536


def validate_format(data: dict) -> None:
    for key, expected in (("rate", RATE), ("width", WIDTH), ("channels", CHANNELS)):
        value = data.get(key)
        if type(value) is not int or value != expected:
            raise ServiceError("unsupported-audio-format", "Audio muss 16000 Hz, Mono und 16-Bit-PCM verwenden")


class AudioBudget:
    def __init__(self, max_seconds: float):
        self.max_bytes = int(max_seconds * RATE) * WIDTH
        self.total_bytes = 0

    def accept(self, data: bytes) -> None:
        if not data or len(data) % WIDTH or len(data) > MAX_CHUNK_BYTES:
            raise ServiceError("invalid-audio", "PCM-Chunk ist leer, unvollständig oder zu groß")
        if self.total_bytes + len(data) > self.max_bytes:
            raise ServiceError("audio-too-long", "Maximale Audiolänge überschritten")
        self.total_bytes += len(data)


def pcm_to_float(data: bytes) -> list[float]:
    # Explicit little-endian signed PCM; no numpy or microphone access needed here.
    return [sample[0] / 32768.0 for sample in struct.iter_unpack("<h", data)]
