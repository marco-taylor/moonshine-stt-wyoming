from abc import ABC, abstractmethod
from pathlib import Path


class BackendStream(ABC):
    @abstractmethod
    def add_audio(self, pcm: bytes) -> None:
        """Blocking PCM ingestion; called only by the service worker."""

    @abstractmethod
    def finish(self) -> str:
        """Flush and return the complete utterance, including all segment lines."""

    @abstractmethod
    def close(self) -> None:
        """Release stream resources; safe after failure and repeated calls."""


class Backend(ABC):
    @abstractmethod
    def initialize(self, directory: Path, model: str) -> None:
        """Load a local model, without network or download helpers."""

    @property
    @abstractmethod
    def ready(self) -> bool:
        """True only while the model is loaded and usable."""

    @abstractmethod
    def create_stream(self) -> BackendStream:
        pass

    @abstractmethod
    def close(self) -> None:
        pass
