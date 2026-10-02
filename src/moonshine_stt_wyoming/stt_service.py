import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from .backends.base import Backend
from .config import Config, validate_selection
from .errors import ServiceError
from .models import model_spec
from .model_manager import ensure_model


class Lease:
    """Owns admission and native stream even if opening is cancelled."""
    def __init__(self, service):
        self.service = service
        self.stream = None
        self.closed = False

    async def open(self):
        def create():
            self.stream = self.service.backend.create_stream()
        await self.service.call(create)

    async def add_audio(self, pcm):
        await self.service.call(self.stream.add_audio, pcm)

    async def finish(self):
        return await self.service.call(self.stream.finish)

    async def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            if self.stream is not None:
                await self.service.call(self.stream.close)
        finally:
            self.service.leases.discard(self)


class STTService:
    def __init__(self, config: Config, backend: Backend):
        self.config = config
        self.backend = backend
        # One thread gives native calls affinity and prevents concurrent model calls.
        # Multiple admitted streams may interleave, but never race native inference.
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="moonshine")
        self.leases = set()
        self.loaded_path = None
        self.closing = False
        self.closed = False

    async def call(self, function, *args):
        future = asyncio.get_running_loop().run_in_executor(self.executor, partial(function, *args))
        try:
            return await asyncio.shield(future)
        except asyncio.CancelledError:
            # Cancelling an asyncio future cannot stop native code. Drain it before
            # stream/model cleanup or admission release, including repeated cancellation.
            while not future.done():
                try:
                    await asyncio.shield(future)
                except asyncio.CancelledError:
                    continue
                except Exception:
                    break
            if future.done() and not future.cancelled():
                future.exception()  # Consume failures without logging runtime content.
            raise

    async def initialize(self):
        validate_selection(self.config.model, self.config.language)
        self.loaded_path = await self.call(ensure_model, self.config)
        await self.call(self.backend.initialize, self.loaded_path, self.config.model)

    @property
    def model_available(self):
        if self.loaded_path is None:
            return False
        try:
            spec = model_spec(self.config.model)
            return all((self.loaded_path / name).is_file()
                       and (self.loaded_path / name).stat().st_size == expected["size"]
                       for name, expected in spec["files"].items())
        except OSError:
            return False

    @property
    def ready(self):
        return not self.closing and self.loaded_path is not None and self.backend.ready

    def reserve(self):
        # Runs synchronously on one event loop: no await between check and reserve.
        if not self.ready:
            raise ServiceError("not-ready", "STT-Backend ist nicht betriebsbereit")
        if len(self.leases) >= self.config.max_concurrent_requests:
            raise ServiceError("busy", "STT-Dienst verarbeitet bereits die maximale Anzahl Anfragen")
        lease = Lease(self)
        self.leases.add(lease)
        return lease

    async def close(self):
        if self.closed:
            return
        self.closing = True
        failed = False
        try:
            for lease in tuple(self.leases):
                try:
                    await lease.close()
                except Exception:
                    failed = True
            try:
                await self.call(self.backend.close)
            except Exception:
                failed = True
        finally:
            self.executor.shutdown(wait=True)
            self.closed = True
        if failed:
            raise ServiceError("cleanup-failed", "STT-Ressourcen konnten nicht vollständig freigegeben werden")
