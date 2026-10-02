from dataclasses import dataclass, field
import logging
import time

from .audio import AudioBudget, validate_format
from .errors import ServiceError
from .models import model_spec

LOGGER = logging.getLogger("moonshine_stt_wyoming")


@dataclass
class Message:
    type: str
    data: dict = field(default_factory=dict)
    payload: bytes | None = None


def service_info(service):
    config = service.config
    ready = service.ready
    return Message("info", {"asr": [{
        "name": "moonshine-stt-wyoming", "installed": ready,
        "description": "Local multilingual Moonshine CPU STT", "version": "0.1.0",
        "attribution": {"name": "Moonshine AI", "url": "https://github.com/moonshine-ai/moonshine"},
        "supports_transcript_streaming": False, "requires_external_vad": True,
        "models": [{"name": config.model, "installed": ready,
                    "languages": [model_spec(config.model)["language"]], "description": "Moonshine streaming STT",
                    "version": model_spec(config.model)["revision"],
                    "attribution": {"name": "Moonshine AI", "url": "https://github.com/moonshine-ai/moonshine"}}],
    }], "moonshine_status": {"backend_initialized": ready, "model_loaded": ready,
                              "model_available": service.model_available, "device": "cpu"}})


class ProtocolSession:
    def __init__(self, service):
        self.service = service
        self.state = "idle"
        self.lease = None
        self.budget = None
        self.deadline = None

    def require(self, state):
        if self.state != state:
            raise ServiceError("invalid-state", "Ungültige Reihenfolge der Wyoming-Ereignisse")

    async def handle(self, message: Message):
        if message.type == "describe":
            return service_info(self.service)
        if message.type == "transcribe":
            self.require("idle")
            if message.data.get("language") not in (None, model_spec(self.service.config.model)["language"]):
                raise ServiceError("unsupported-language", "Nur konfigurierte Sprache unterstützt")
            if message.data.get("name") not in (None, self.service.config.model):
                raise ServiceError("unsupported-model", "Nur geladenes Modell unterstützt")
            self.state = "armed"
        elif message.type == "audio-start":
            self.require("armed")
            validate_format(message.data)
            self.budget = AudioBudget(self.service.config.max_audio_seconds)
            self.deadline = time.monotonic() + self.service.config.max_audio_seconds + self.service.config.client_timeout_seconds
            self.lease = self.service.reserve()
            await self.lease.open()
            self.state = "audio"
        elif message.type == "audio-chunk":
            self.require("audio")
            validate_format(message.data)
            self.budget.accept(message.payload or b"")
            await self.lease.add_audio(message.payload)
        elif message.type == "audio-stop":
            self.require("audio")
            if self.budget.total_bytes == 0:
                raise ServiceError("empty-audio", "Keine Audiodaten empfangen")
            text = await self.lease.finish()
            await self.lease.close()
            self.lease = None
            self.state = "idle"
            self.deadline = None
            if self.service.config.log_transcripts:
                # JSON quoting prevents transcript-based log line injection.
                import json
                LOGGER.info("transcript=%s", json.dumps(text, ensure_ascii=True))
            return Message("transcript", {"text": text, "language": model_spec(self.service.config.model)["language"]})
        # Unknown events are ignored for forward compatibility, as Wyoming specifies.
        return None

    async def close(self):
        if self.lease is not None:
            try:
                await self.lease.close()
            finally:
                self.lease = None
        self.state = "closed"
