import asyncio
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

from moonshine_stt_wyoming.__main__ import run
from moonshine_stt_wyoming.config import Config


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_server_cleanup_failure_still_closes_backend_and_signals(self):
        loop = asyncio.get_running_loop()
        service, server = AsyncMock(), AsyncMock()
        service.initialize.side_effect = ValueError("initialization failure")
        server.close.side_effect = ValueError("cleanup failure")
        with patch("moonshine_stt_wyoming.__main__.version", return_value="1.10.2"), \
             patch("moonshine_stt_wyoming.__main__.STTService", return_value=service), \
             patch("moonshine_stt_wyoming.__main__.WyomingServer", return_value=server), \
             patch.object(loop, "add_signal_handler"), \
             patch.object(loop, "remove_signal_handler") as remove:
            with self.assertRaises(ValueError):
                await run(Config(model_dir=Path("/not-used")))
            service.close.assert_awaited_once()
            self.assertEqual(remove.call_count, 2)
