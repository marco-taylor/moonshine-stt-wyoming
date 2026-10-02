"""Isolated Wyoming soak/quality benchmark. No Docker mutations or HA calls."""
import argparse
import asyncio
import json
import math
from pathlib import Path
import re
import statistics
import sys
import time
import wave

import numpy as np
from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioStart, AudioChunk, AudioStop
from wyoming.event import async_read_event, async_write_event
from wyoming.info import Describe, Info

from validate_phase4 import process_usage


def normalized(text):
    return "".join(re.findall(r"\w+", text.lower(), flags=re.UNICODE))


def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def load_audio(directory):
    result = json.loads((directory / "prepared-sources.json").read_text())
    for item in result:
        with wave.open(str(directory / item["test_file"]), "rb") as wav:
            assert (wav.getframerate(), wav.getsampwidth(), wav.getnchannels()) == (16000, 2, 1)
            item["pcm"] = wav.readframes(wav.getnframes())
    return result


def audio_variant(pcm, variant):
    samples = np.frombuffer(pcm, dtype="<i2").astype(np.float64)
    if variant == "quiet":
        samples *= 0.5
    elif variant == "noise20db":
        rms = np.sqrt(np.mean(samples * samples))
        samples += np.random.default_rng(6001).normal(0, rms / 10, len(samples))
    elif variant != "clean":
        raise ValueError(variant)
    return np.clip(np.rint(samples), -32768, 32767).astype("<i2").tobytes()


async def benchmark(args):
    items = load_audio(args.audio)
    samples = []
    reader, writer = await asyncio.open_connection(args.host, args.port)
    async def send(value):
        await async_write_event(value.event(), writer)
    async def receive():
        event = await asyncio.wait_for(async_read_event(reader), 45)
        assert event is not None
        return event
    report = {"host": args.host, "port": args.port, "threads": args.threads,
              "requests": args.requests, "pause_seconds": args.pause,
              "idle_seconds": args.idle, "samples": samples}
    started_all = time.perf_counter()
    try:
        await send(Describe())
        info = Info.from_event(await receive())
        assert info.asr[0].models[0].name == "small-streaming-de"
        for index in range(args.requests):
            item = items[index % len(items)]
            variant = ("clean", "quiet", "noise20db")[(index // len(items)) % 3] if args.quality else "clean"
            paced = args.paced_every > 0 and (index + 1) % args.paced_every == 0
            pcm = audio_variant(item["pcm"], variant)
            cpu0, _ = process_usage(args.pid)
            started = time.perf_counter()
            await send(Transcribe(language="de", name="small-streaming-de"))
            await send(AudioStart(rate=16000, width=2, channels=1))
            for offset in range(0, len(pcm), 6400):
                chunk = pcm[offset:offset+6400]
                await send(AudioChunk(rate=16000, width=2, channels=1, audio=chunk))
                if paced:
                    await asyncio.sleep(len(chunk)/32000)
            stopped = time.perf_counter()
            await send(AudioStop())
            event = await receive()
            assert event.type == "transcript", (index, event.type, event.data)
            text = Transcript.from_event(event).text
            elapsed = time.perf_counter()-started
            cpu1, memory = process_usage(args.pid)
            samples.append({"index": index, "expected": item["expected"], "recognized": text,
                "normalized_exact_match": normalized(text) == normalized(item["expected"]),
                "variant": variant, "paced": paced, "audio_seconds": item["audio_seconds"],
                "roundtrip_seconds": elapsed, "rtf": elapsed/item["audio_seconds"],
                "finalization_seconds": time.perf_counter()-stopped,
                "cpu_seconds": cpu1-cpu0, "cpu_percent_one_core": (cpu1-cpu0)/elapsed*100,
                **memory})
            if (index+1) % 10 == 0:
                print(f"Completed {index+1}/{args.requests}; RSS {memory['VmRSS']:.2f} MiB", file=sys.stderr, flush=True)
            if args.pause:
                await asyncio.sleep(args.pause)
        report["idle_memory"] = []
        idle_started = time.perf_counter()
        while time.perf_counter()-idle_started < args.idle:
            await asyncio.sleep(min(10, args.idle-(time.perf_counter()-idle_started)))
            _, memory = process_usage(args.pid)
            report["idle_memory"].append(memory)
    finally:
        writer.close()
        await writer.wait_closed()
    unpaced = [x for x in samples if not x["paced"]]
    report["total_wall_seconds"] = time.perf_counter()-started_all
    report["summary"] = {"successful_transcripts": len(samples),
        "normalized_exact_matches": sum(x["normalized_exact_match"] for x in samples),
        "unpaced_rtf_median": statistics.median(x["rtf"] for x in unpaced) if unpaced else None,
        "unpaced_rtf_p95": percentile([x["rtf"] for x in unpaced], .95) if unpaced else None,
        "finalization_median_seconds": statistics.median(x["finalization_seconds"] for x in samples),
        "finalization_p95_seconds": percentile([x["finalization_seconds"] for x in samples], .95),
        "rss_first_warm_median_mib": statistics.median(x["VmRSS"] for x in samples[6:16] or samples),
        "rss_last_median_mib": statistics.median(x["VmRSS"] for x in samples[-10:]),
        "rss_max_mib": max(x["VmRSS"] for x in samples)}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=11300)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--threads", type=int, choices=(1, 4), required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--requests", type=int, default=12)
    parser.add_argument("--pause", type=float, default=0)
    parser.add_argument("--idle", type=float, default=0)
    parser.add_argument("--paced-every", type=int, default=0)
    parser.add_argument("--quality", action="store_true")
    args = parser.parse_args()
    assert args.requests >= 2 and args.pause >= 0 and args.idle >= 0
    asyncio.run(benchmark(args))
