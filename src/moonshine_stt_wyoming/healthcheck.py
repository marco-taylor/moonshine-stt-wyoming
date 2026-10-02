import asyncio
import sys

from .config import Config
from .protocol import Message
from .transport import MAX_JSON_BYTES, read_message, write_message


def is_healthy(message, config):
    if message is None or message.type != "info":
        return False
    status = message.data.get("moonshine_status", {})
    if any(status.get(key) is not True for key in
           ("backend_initialized", "model_loaded", "model_available")):
        return False
    return any(model.get("name") == config.model and model.get("installed") is True
               and config.language in model.get("languages", [])
               for program in message.data.get("asr", [])
               for model in program.get("models", []))


async def check(config):
    host = {"0.0.0.0": "127.0.0.1", "::": "::1"}.get(config.host, config.host)
    reader, writer = await asyncio.open_connection(host, config.port, limit=MAX_JSON_BYTES)
    try:
        await write_message(writer, Message("describe"))
        return is_healthy(await read_message(reader), config)
    finally:
        writer.close()
        await writer.wait_closed()


async def timed_check(config):
    return await asyncio.wait_for(check(config), timeout=5)


def main():
    try:
        healthy = asyncio.run(timed_check(Config.from_env()))
    except Exception:
        healthy = False
    print("ready" if healthy else "not-ready")
    sys.exit(0 if healthy else 1)


if __name__ == "__main__":
    main()
