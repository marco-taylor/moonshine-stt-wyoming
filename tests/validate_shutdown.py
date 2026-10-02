"""Isolated child process used only by Phase 3 validation."""
import asyncio
from dataclasses import replace
from pathlib import Path

from moonshine_stt_wyoming.__main__ import run
from moonshine_stt_wyoming.config import Config
from moonshine_stt_wyoming.wyoming_server import WyomingServer

ROOT = Path(__file__).resolve().parents[1]
original_start = WyomingServer.start


async def start_and_report(self):
    await original_start(self)
    port = self.server.sockets[0].getsockname()[1]
    assert port != 10300
    print("READY", port, flush=True)


if __name__ == "__main__":
    assert int(Path("/proc/sys/net/ipv4/ip_local_port_range").read_text().split()[0]) > 10300
    WyomingServer.start = start_and_report
    config = Config.from_env({"MOONSHINE_MODEL_DIR": str(ROOT / ".validation/small-test-models"),
                             "MOONSHINE_AUTO_DOWNLOAD": "0", "WYOMING_HOST": "127.0.0.1"})
    asyncio.run(run(replace(config, port=0)))
    print("STOPPED", flush=True)
