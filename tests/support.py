import json
from pathlib import Path
import tempfile

from moonshine_stt_wyoming.backends.base import Backend, BackendStream
from moonshine_stt_wyoming.integrity import file_integrity

PROJECT = Path(__file__).resolve().parents[1]


def fixture_directory():
    # Keep all test writes inside the project; no automatic file deletion.
    base = PROJECT / ".test-tmp"
    base.mkdir(exist_ok=True)
    return Path(tempfile.mkdtemp(dir=base))


def model_fixture(root, name="tiny-streaming-de"):
    directory = root / name
    directory.mkdir()
    content = {"encoder.ort": b"test model", "streaming_config.json": b'{"test": true}'}
    hashes, files = {}, {}
    for filename, data in content.items():
        file = directory / filename
        file.write_bytes(data)
        info = file_integrity(file)
        hashes[filename] = info["sha256"]
        files[filename] = {"size": info["size"], "crc32c": info["crc32c"]}
    (directory / "model.json").write_text(json.dumps({"model": name,
        "revision": "test", "sha256": hashes}), encoding="utf-8")
    return directory, {"revision": "test", "files": files}


class FakeStream(BackendStream):
    def __init__(self):
        self.audio = []
        self.closed = False

    def add_audio(self, pcm):
        self.audio.append(pcm)

    def finish(self):
        return "Licht im Büro einschalten"

    def close(self):
        self.closed = True


class FakeBackend(Backend):
    def __init__(self):
        self.loaded = True
        self.streams = []

    @property
    def ready(self):
        return self.loaded

    def initialize(self, directory, model):
        self.loaded = True

    def create_stream(self):
        stream = FakeStream()
        self.streams.append(stream)
        return stream

    def close(self):
        self.loaded = False
