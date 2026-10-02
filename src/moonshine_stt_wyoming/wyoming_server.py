import asyncio
import logging
import time

from .errors import ServiceError
from .protocol import Message, ProtocolSession
from .transport import MAX_JSON_BYTES, read_message, write_message

LOGGER = logging.getLogger("moonshine_stt_wyoming")


class WyomingServer:
    def __init__(self, service):
        self.service = service
        self.server = None
        self.connections = {}
        self.closing = False

    async def start(self):
        config = self.service.config
        self.server = await asyncio.start_server(self.accept, config.host, config.port,
                                                 limit=MAX_JSON_BYTES)

    def accept(self, reader, writer):
        if self.closing or len(self.connections) >= self.service.config.max_connections:
            writer.close()
            return
        task = asyncio.create_task(self.serve(reader, writer))
        self.connections[task] = writer
        task.add_done_callback(self.completed)

    def completed(self, task):
        self.connections.pop(task, None)
        if not task.cancelled() and task.exception() is not None:
            LOGGER.error("Verbindungsbereinigung fehlgeschlagen")

    async def send(self, writer, message):
        await asyncio.wait_for(write_message(writer, message), timeout=5)

    async def serve(self, reader, writer):
        session = ProtocolSession(self.service)
        try:
            while not self.closing:
                timeout = self.service.config.client_timeout_seconds
                if session.deadline is not None:
                    timeout = min(timeout, session.deadline - time.monotonic())
                    if timeout <= 0:
                        raise asyncio.TimeoutError
                message = await asyncio.wait_for(read_message(reader), timeout=timeout)
                if message is None:
                    break
                reply = await session.handle(message)
                if reply is not None:
                    await self.send(writer, reply)
        except ServiceError as error:
            LOGGER.warning("Anfrage abgewiesen: %s", error.code)
            try:
                await self.send(writer, Message("error", {"code": error.code, "text": str(error)}))
            except (OSError, asyncio.TimeoutError):
                pass
        except asyncio.TimeoutError:
            try:
                await self.send(writer, Message("error", {"code": "timeout", "text": "Client-Zeitlimit überschritten"}))
            except (OSError, asyncio.TimeoutError):
                pass
        except (OSError, asyncio.IncompleteReadError):
            pass
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.error("Interner STT-Fehler")
            try:
                await self.send(writer, Message("error", {"code": "inference-failed", "text": "STT-Anfrage fehlgeschlagen"}))
            except (OSError, asyncio.TimeoutError):
                pass
        finally:
            cleanup = asyncio.create_task(session.close())
            while not cleanup.done():
                try:
                    await asyncio.shield(cleanup)
                except asyncio.CancelledError:
                    continue
                except Exception:
                    LOGGER.error("STT-Ressourcenbereinigung fehlgeschlagen")
                    break
            if cleanup.done() and not cleanup.cancelled():
                cleanup.exception()
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), timeout=5)
            except (OSError, asyncio.TimeoutError):
                pass

    async def close(self):
        self.closing = True
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()
        tasks = tuple(self.connections)
        for task in tasks:
            self.connections[task].close()
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
