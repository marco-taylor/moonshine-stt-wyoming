import asyncio
from importlib.metadata import version
import logging
import signal

from .backends.moonshine_cpu import MoonshineCPU
from .config import Config
from .errors import ConfigurationError, ServiceError
from .logging_config import configure
from .stt_service import STTService
from .wyoming_server import WyomingServer


async def run(config):
    if version("wyoming") != "1.10.2":
        raise ServiceError("runtime-version", "wyoming 1.10.2 erforderlich")
    service = STTService(config, MoonshineCPU(threads=config.threads))
    server = WyomingServer(service)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    try:
        await service.initialize()
        await server.start()
        logging.info("Moonshine CPU bereit; Wyoming-Port %d", config.port)
        await stop.wait()
    finally:
        try:
            await server.close()
        finally:
            try:
                await service.close()
            finally:
                for sig in (signal.SIGTERM, signal.SIGINT):
                    loop.remove_signal_handler(sig)


def main():
    try:
        config = Config.from_env()
        configure(config.log_level)
        asyncio.run(run(config))
    except (ConfigurationError, ServiceError) as error:
        logging.error("%s", error)
        raise SystemExit(1) from None
    except Exception:
        logging.error("Start fehlgeschlagen; Runtime, Modell und Portbelegung prüfen")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
