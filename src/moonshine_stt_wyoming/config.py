from dataclasses import dataclass
import math
import ipaddress
import re
import os
from pathlib import Path
from collections.abc import Mapping

from .errors import ConfigurationError
from .models import manifest, model_spec

MODELS = tuple(manifest()["models"])


def validate_selection(model: str, language: str):
    catalog = manifest()["models"]
    if model not in catalog:
        raise ConfigurationError("MOONSHINE_MODEL: unbekanntes oder nicht freigegebenes Modell")
    if language not in {spec["language"] for spec in catalog.values()}:
        raise ConfigurationError("MOONSHINE_LANGUAGE: unbekannte oder nicht freigegebene Sprache")
    expected = model_spec(model)["language"]
    if language != expected:
        raise ConfigurationError(f"MOONSHINE_LANGUAGE={language} passt nicht zu MOONSHINE_MODEL={model}; erforderlich: {expected}")


def _integer(env, name, default, low, high):
    try:
        result = int(env.get(name, str(default)))
    except (ValueError, TypeError):
        raise ConfigurationError(f"{name}: Ganzzahl erforderlich") from None
    if not low <= result <= high:
        raise ConfigurationError(f"{name}: erlaubter Bereich {low} bis {high}")
    return result


def _boolean(env, name, default):
    value = env.get(name, str(default)).lower()
    if value not in ("true", "false"):
        raise ConfigurationError(f"{name}: true oder false erforderlich")
    return value == "true"


@dataclass(frozen=True)
class Config:
    language: str = "de"
    model: str = "small-streaming-de"
    device: str = "cpu"
    host: str = "0.0.0.0"
    port: int = 10300
    model_dir: Path = Path("/app/models")
    auto_download: bool = True
    max_concurrent_requests: int = 1
    max_audio_seconds: float = 30.0
    log_level: str = "INFO"
    log_transcripts: bool = False
    client_timeout_seconds: int = 60
    max_connections: int = 16
    threads: int = 1

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None):
        env = os.environ if env is None else env
        for retired in ("MODEL_DIR", "MODEL_DOWNLOAD_POLICY", "MAX_CONCURRENT_REQUESTS"):
            if retired in env:
                raise ConfigurationError("Veraltete Variable: " + retired +
                    "; MOONSHINE_MODEL_DIR, MOONSHINE_AUTO_DOWNLOAD und WYOMING_STT_CONCURRENT_REQUESTS verwenden")
        language = env.get("MOONSHINE_LANGUAGE", "de")
        model = env.get("MOONSHINE_MODEL", "small-streaming-de")
        validate_selection(model, language)
        device = env.get("STT_DEVICE", "cpu")
        if device != "cpu":
            raise ConfigurationError("STT_DEVICE: derzeit nur cpu unterstützt")
        auto = env.get("MOONSHINE_AUTO_DOWNLOAD", "1")
        if auto not in ("0", "1"):
            raise ConfigurationError("MOONSHINE_AUTO_DOWNLOAD: 0 oder 1 erforderlich")
        threads = _integer(env, "MOONSHINE_THREADS", 1, 1, 4)
        if threads not in (1, 4):
            raise ConfigurationError("MOONSHINE_THREADS: 1 (native Einzelthread-Ausführung) oder 4 (Runtime-Automatik auf N100) erforderlich")
        host = env.get("WYOMING_HOST", "0.0.0.0")
        if not host or any(c.isspace() for c in host) or any(c in host for c in "/@\\"):
            raise ConfigurationError("WYOMING_HOST: gültiger Hostname oder IP erforderlich")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            labels = host.rstrip(".").split(".")
            if len(host) > 253 or any(not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label) for label in labels):
                raise ConfigurationError("WYOMING_HOST: gültiger Hostname oder IP erforderlich")
        directory = env.get("MOONSHINE_MODEL_DIR", "/app/models")
        if not directory or "\x00" in directory:
            raise ConfigurationError("MOONSHINE_MODEL_DIR: gültiger absoluter Pfad erforderlich")
        model_dir = Path(directory)
        if not model_dir.is_absolute():
            raise ConfigurationError("MOONSHINE_MODEL_DIR: absoluter Pfad erforderlich")
        try:
            seconds = float(env.get("MAX_AUDIO_SECONDS", "30"))
        except (ValueError, TypeError):
            raise ConfigurationError("MAX_AUDIO_SECONDS: positive Zahl erforderlich") from None
        if not math.isfinite(seconds) or not 0 < seconds <= 300:
            raise ConfigurationError("MAX_AUDIO_SECONDS: größer 0 und höchstens 300 erforderlich")
        level = env.get("LOG_LEVEL", "INFO").upper()
        if level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            raise ConfigurationError("LOG_LEVEL: ungültige Protokollstufe")
        return cls(language, model, device, host,
                   _integer(env, "WYOMING_PORT", 10300, 1, 65535), model_dir,
                   auto == "1", _integer(env, "WYOMING_STT_CONCURRENT_REQUESTS", 1, 1, 8),
                   seconds, level, _boolean(env, "LOG_TRANSCRIPTS", False),
                   _integer(env, "CLIENT_TIMEOUT_SECONDS", 60, 1, 3600),
                   _integer(env, "MAX_CONNECTIONS", 16, 1, 128), threads)
