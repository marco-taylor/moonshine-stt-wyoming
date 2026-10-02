"""CRC32C fallback for installation-free tests and upstream model verification."""
import base64
import hashlib
from functools import lru_cache


@lru_cache(maxsize=1)
def _table():
    result = []
    for value in range(256):
        for _ in range(8):
            value = (value >> 1) ^ (0x82F63B78 if value & 1 else 0)
        result.append(value)
    return tuple(result)


class CRC32C:
    def __init__(self):
        self.value = 0xFFFFFFFF
        self.native = None
        try:
            from google_crc32c import Checksum
            self.native = Checksum()
        except ImportError:
            pass

    def update(self, data):
        if self.native is not None:
            self.native.update(data)
            return
        table = _table()
        value = self.value
        for byte in data:
            value = table[(value ^ byte) & 255] ^ (value >> 8)
        self.value = value

    def digest(self):
        if self.native is not None:
            return self.native.digest()
        return (self.value ^ 0xFFFFFFFF).to_bytes(4, "big")


def file_integrity(file):
    digest, crc, size = hashlib.sha256(), CRC32C(), 0
    with file.open("rb") as handle:
        while block := handle.read(65536):
            digest.update(block)
            crc.update(block)
            size += len(block)
    return {"size": size, "sha256": digest.hexdigest(),
            "crc32c": base64.b64encode(crc.digest()).decode("ascii")}
