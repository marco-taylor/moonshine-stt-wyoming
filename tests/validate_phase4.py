"""Opt-in client and offline image checks; never manages Docker resources."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import time
import wave

from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioStart, AudioChunk, AudioStop
from wyoming.event import async_read_event, async_write_event
from wyoming.info import Describe, Info


def process_usage(pid):
    fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    cpu = (int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK")
    status = Path(f"/proc/{pid}/status").read_text().splitlines()
    memory = {line.split(":")[0]: int(line.split()[1]) / 1024
              for line in status if line.startswith(("VmRSS:", "VmHWM:"))}
    return cpu, memory


async def client(args):
    results = {"host_port": args.port, "model": "small-streaming-de", "samples": []}
    reader, writer = await asyncio.open_connection(args.host, args.port)
    async def send(value):
        await async_write_event(value.event(), writer)
    async def receive():
        event = await asyncio.wait_for(async_read_event(reader), 30)
        assert event is not None
        return event
    try:
        await send(Describe())
        info = Info.from_event(await receive())
        assert info.asr[0].models[0].name == "small-streaming-de"
        results["describe"] = "passed"
        metadata = json.loads((args.audio / "prepared-sources.json").read_text())
        for sample in metadata:
            with wave.open(str(args.audio / sample["test_file"]), "rb") as wav:
                assert (wav.getframerate(), wav.getsampwidth(), wav.getnchannels()) == (16000, 2, 1)
                pcm = wav.readframes(wav.getnframes())
            cpu_before, _ = process_usage(args.pid)
            started = time.perf_counter()
            await send(Transcribe(language="de", name="small-streaming-de"))
            await send(AudioStart(rate=16000, width=2, channels=1))
            for offset in range(0, len(pcm), 6400):
                await send(AudioChunk(rate=16000, width=2, channels=1, audio=pcm[offset:offset+6400]))
            await send(AudioStop())
            event = await receive()
            assert event.type == "transcript", event.type
            text = Transcript.from_event(event).text
            elapsed = time.perf_counter() - started
            cpu_after, memory = process_usage(args.pid)
            assert text
            results["samples"].append({"expected": sample["expected"], "recognized": text,
                "audio_seconds": sample["audio_seconds"], "roundtrip_seconds": elapsed,
                "rtf": elapsed/sample["audio_seconds"], "cpu_seconds": cpu_after-cpu_before,
                "cpu_percent_one_core": (cpu_after-cpu_before)/elapsed*100, **memory})
    finally:
        writer.close()
        await writer.wait_closed()
    if not args.skip_negative:
        results["negative_protocol"] = await negative_protocol(args.port, args.host)
    print(json.dumps(results, ensure_ascii=False, indent=2))


async def negative_protocol(port, host="127.0.0.1"):
    writers = []
    async def connect():
        reader, writer = await asyncio.open_connection(host, port)
        writers.append(writer)
        return reader, writer
    async def send(writer, value):
        await async_write_event(value.event(), writer)
    async def receive(reader):
        event = await asyncio.wait_for(async_read_event(reader), 10)
        assert event is not None
        return event
    results = {}
    try:
        reader, writer = await connect()
        await send(writer, Transcribe(language="de"))
        await send(writer, AudioStart(rate=8000, width=2, channels=1))
        event = await receive(reader)
        assert event.type == "error" and event.data["code"] == "unsupported-audio-format"
        results["invalid_format"] = "passed"
        writer.close()
        await writer.wait_closed()

        reader, writer = await connect()
        await send(writer, Transcribe(language="de"))
        await send(writer, AudioStart(rate=16000, width=2, channels=1))
        for _ in range(31):
            await send(writer, AudioChunk(rate=16000, width=2, channels=1, audio=bytes(32000)))
        event = await receive(reader)
        assert event.type == "error" and event.data["code"] == "audio-too-long"
        results["audio_limit"] = "passed"
        writer.close()
        await writer.wait_closed()

        first_reader, first_writer = await connect()
        await send(first_writer, Transcribe(language="de"))
        await send(first_writer, AudioStart(rate=16000, width=2, channels=1))
        await send(first_writer, Describe())
        assert (await receive(first_reader)).type == "info"
        reader, writer = await connect()
        await send(writer, Transcribe(language="de"))
        await send(writer, AudioStart(rate=16000, width=2, channels=1))
        event = await receive(reader)
        assert event.type == "error" and event.data["code"] == "busy"
        results["concurrent_request"] = "passed"
        first_writer.close()
        await first_writer.wait_closed()
        # A subsequent request proves disconnect eventually releases the lease.
        for _ in range(30):
            await asyncio.sleep(0.1)
            reader, writer = await connect()
            await send(writer, Transcribe(language="de"))
            await send(writer, AudioStart(rate=16000, width=2, channels=1))
            await send(writer, AudioStop())
            event = await receive(reader)
            if event.type == "error" and event.data["code"] == "empty-audio":
                results["disconnect_releases_lease"] = "passed"
                break
            assert event.type == "error" and event.data["code"] == "busy"
            writer.close()
            await writer.wait_closed()
        else:
            raise AssertionError("Disconnect did not release lease")
    finally:
        for writer in writers:
            writer.close()
        await asyncio.gather(*(writer.wait_closed() for writer in writers), return_exceptions=True)
    return results


async def offline(args):
    import sys
    import validate_phase3 as helpers
    from moonshine_stt_wyoming.config import Config
    from moonshine_stt_wyoming.stt_service import STTService
    from moonshine_stt_wyoming.backends.moonshine_cpu import MoonshineCPU
    report = {"network_syscalls_denied": helpers.deny_network_for_current_process()}
    config = Config.from_env()
    assert config.threads == 1 and (not config.auto_download or args.allow_auto_download)
    service = STTService(config, MoonshineCPU(threads=config.threads))
    try:
        started = time.perf_counter()
        await service.initialize()
        report["model_load_seconds"] = time.perf_counter()-started
        helpers.ROOT = args.audio.parent.parent
        report["direct"] = [await helpers.direct(service, x) for x in helpers.audio_inputs()]
    finally:
        await service.close()
    report["sounddevice_imported"] = "sounddevice" in sys.modules
    sizes=[]
    for root in (Path("/opt/runtime"), Path("/usr/local")):
        for f in root.rglob("*"):
            if f.is_file() and not f.is_symlink():
                sizes.append((f.stat().st_size, str(f)))
    report["largest_image_files"] = sorted(sizes, reverse=True)[:15]
    report["runtime_bytes"] = sum(size for size, name in sizes if name.startswith("/opt/runtime/"))
    report["forbidden_image_artifacts"] = [name for size, name in sizes
        if name.endswith((".ort", ".wav")) or
        (name.startswith("/opt/runtime/") and name.endswith(".whl")) or
        "/.venv/" in name or "/.cache/" in name]
    assert not report["forbidden_image_artifacts"]
    assert not Path("/usr/bin/gcc").exists() and not Path("/usr/bin/git").exists()
    report["shutdown"] = "passed"
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("client", "offline"))
    parser.add_argument("--port", type=int, default=10300)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--skip-negative", action="store_true",
                        help="Run only describe and real STT; omit deliberate error/admission tests")
    parser.add_argument("--allow-auto-download", action="store_true",
                        help="Offline check with AUTO_DOWNLOAD=1; network syscalls remain denied")
    parser.add_argument("--pid", type=int)
    parser.add_argument("--audio", type=Path, required=True)
    args = parser.parse_args()
    with asyncio.Runner() as runner:
        runner.run(client(args) if args.mode == "client" else offline(args))
