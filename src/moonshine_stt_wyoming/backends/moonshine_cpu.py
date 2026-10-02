from pathlib import Path
from importlib.metadata import version
import os

from .base import Backend, BackendStream
from ..audio import pcm_to_float
from ..errors import ServiceError
from ..models import model_spec


class MoonshineStream(BackendStream):
    def __init__(self, native):
        self.native = native
        try:
            native.start()
        except BaseException:
            native.close()
            self.native = None
            raise

    def add_audio(self, pcm: bytes) -> None:
        self.native.add_audio(pcm_to_float(pcm), 16000)

    def finish(self) -> str:
        result = self.native.stop()
        # The official wrapper can swallow final inference errors and return None.
        if result is None:
            raise ServiceError("inference-failed", "Moonshine konnte die Anfrage nicht abschließen")
        return " ".join(line.text.strip() for line in result.lines if line.text.strip())

    def close(self) -> None:
        if self.native is not None:
            native, self.native = self.native, None
            native.close()


class MoonshineCPU(Backend):
    def __init__(self, factory=None, architectures=None, threads=1):
        self._factory = factory
        self._architectures = architectures
        self._transcriber = None
        if threads not in (1, 4):
            raise ServiceError("unsupported-threads", "Runtime unterstützt 1 oder N100-Automatik (4)")
        self.threads = threads

    @property
    def ready(self) -> bool:
        return self._transcriber is not None

    def initialize(self, directory: Path, model: str) -> None:
        if self.ready:
            raise ServiceError("backend-state", "Backend ist bereits initialisiert")
        if self._factory is None:
            if version("moonshine-voice") != "0.1.5":
                raise ServiceError("runtime-version", "moonshine-voice 0.1.5 erforderlich")
            from moonshine_voice import Transcriber
            from moonshine_voice.moonshine_api import ModelArch
            self._factory = Transcriber
            self._architectures = ModelArch
        # The official native library exposes only a single-thread switch, not
        # a general ORT thread-count option. Mode 4 keeps automatic N100 pooling.
        os.environ["MOONSHINE_ORT_SINGLE_THREAD"] = "1" if self.threads == 1 else "0"
        arch = getattr(self._architectures, model_spec(model)["architecture"])
        self._transcriber = self._factory(
            model_path=str(directory), model_arch=arch, update_interval=0.5,
            options={"ort_providers": "CPU", "log_output_text": "false",
                     "log_api_calls": "false", "log_ort_run": "false",
                     "identify_speakers": "false", "return_audio_data": "false"},
        )

    def create_stream(self) -> BackendStream:
        if not self.ready:
            raise ServiceError("not-ready", "Backend ist nicht betriebsbereit")
        return MoonshineStream(self._transcriber.create_stream(update_interval=0.5))

    def close(self) -> None:
        if self._transcriber is not None:
            transcriber, self._transcriber = self._transcriber, None
            transcriber.close()
