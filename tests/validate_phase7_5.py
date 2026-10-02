"""Opt-in German regression client/offline check; never manages Docker resources."""
import argparse
import asyncio
import json
from pathlib import Path
import time
import wave
from unittest.mock import patch

from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioStart, AudioChunk, AudioStop
from wyoming.event import async_read_event, async_write_event
from wyoming.info import Describe, Info
from validate_phase4 import process_usage, negative_protocol


def recordings(directory):
    for sample in json.loads((directory / "prepared-sources.json").read_text()):
        with wave.open(str(directory / sample["test_file"]), "rb") as wav:
            assert (wav.getframerate(), wav.getsampwidth(), wav.getnchannels()) == (16000, 2, 1)
            pcm = wav.readframes(wav.getnframes())
        yield sample, pcm


async def client(args):
    assert args.port != 10300, "Only an isolated temporary test port is allowed"
    reader, writer = await asyncio.open_connection("127.0.0.1", args.port)
    report = {"port": args.port, "samples": []}
    try:
        await async_write_event(Describe().event(), writer)
        event = await asyncio.wait_for(async_read_event(reader), 15)
        info = Info.from_event(event)
        assert info.asr[0].name == "moonshine-stt-wyoming"
        assert info.asr[0].models[0].name == "small-streaming-de"
        assert info.asr[0].models[0].languages == ["de"]
        assert all(event.data["moonshine_status"][key] for key in
                   ("backend_initialized", "model_loaded", "model_available"))
        report["info"] = event.data
        for _ in range(3):
            for sample, pcm in recordings(args.audio):
                cpu_before, _ = process_usage(args.pid)
                started = time.perf_counter()
                await async_write_event(Transcribe(language="de").event(), writer)
                await async_write_event(AudioStart(rate=16000, width=2, channels=1).event(), writer)
                for offset in range(0, len(pcm), 6400):
                    await async_write_event(AudioChunk(rate=16000, width=2, channels=1,
                        audio=pcm[offset:offset+6400]).event(), writer)
                stopped = time.perf_counter()
                await async_write_event(AudioStop().event(), writer)
                event = await asyncio.wait_for(async_read_event(reader), 30)
                elapsed = time.perf_counter()-started
                assert event.type == "transcript" and event.data["language"] == "de"
                text = Transcript.from_event(event).text
                assert text
                cpu_after, memory = process_usage(args.pid)
                report["samples"].append({"expected": sample["expected"], "recognized": text,
                    "audio_seconds": sample["audio_seconds"], "roundtrip_seconds": elapsed,
                    "rtf": elapsed/sample["audio_seconds"],
                    "finalization_seconds": time.perf_counter()-stopped,
                    "cpu_seconds": cpu_after-cpu_before,
                    "cpu_percent_one_core": 100*(cpu_after-cpu_before)/elapsed, **memory})
    finally:
        writer.close()
        await writer.wait_closed()
    report["negative_protocol"] = await negative_protocol(args.port)
    reader, writer = await asyncio.open_connection("127.0.0.1", args.port)
    try:
        await async_write_event(Transcribe(language="en").event(), writer)
        event = await asyncio.wait_for(async_read_event(reader), 5)
        assert event.type == "error" and event.data["code"] == "unsupported-language"
        report["wrong_language"] = "passed"
    finally:
        writer.close()
        await writer.wait_closed()
    return report


async def offline(args):
    from moonshine_stt_wyoming.config import Config
    from moonshine_stt_wyoming.stt_service import STTService
    from moonshine_stt_wyoming.backends.moonshine_cpu import MoonshineCPU
    from moonshine_stt_wyoming.models import validate_model
    config = Config.from_env()
    assert config.model == "small-streaming-de" and config.threads == 1
    # Network-none container plus a fail-fast guard for our downloader.
    report = {"auto_download": config.auto_download, "samples": []}
    service = STTService(config, MoonshineCPU(threads=config.threads))
    try:
        with patch("moonshine_stt_wyoming.model_download.urlopen",
                   side_effect=AssertionError("Unexpected download")) as network:
            started = time.perf_counter()
            await service.initialize()
            report["validation_and_load_seconds"] = time.perf_counter()-started
            for sample, pcm in recordings(args.audio):
                started = time.perf_counter()
                lease = service.reserve()
                try:
                    await lease.open()
                    for offset in range(0, len(pcm), 6400):
                        await lease.add_audio(pcm[offset:offset+6400])
                    text = await lease.finish()
                    assert text
                finally:
                    await lease.close()
                elapsed = time.perf_counter()-started
                report["samples"].append({"expected": sample["expected"], "recognized": text,
                    "audio_seconds": sample["audio_seconds"], "inference_seconds": elapsed,
                    "rtf": elapsed/sample["audio_seconds"]})
            network.assert_not_called()
            report["download_calls"] = 0
    finally:
        await service.close()
    report["shutdown"] = "passed"
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("client", "offline"))
    parser.add_argument("--port", type=int)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with asyncio.Runner() as runner:
        report = runner.run(client(args) if args.mode == "client" else offline(args))
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        root = Path(__file__).resolve().parents[1]
        assert args.output.resolve().is_relative_to(root)
        with args.output.open("x", encoding="utf-8") as output:
            output.write(serialized)
    print(serialized)
