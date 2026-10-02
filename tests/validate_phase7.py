"""Opt-in extended Wyoming benchmark; no container or Home Assistant mutations."""
import argparse
import asyncio
import json
from pathlib import Path
import statistics
import time

from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioStart, AudioChunk, AudioStop
from wyoming.event import async_read_event, async_write_event
from wyoming.info import Describe, Info

from validate_phase4 import process_usage
from validate_phase6 import audio_variant, load_audio, normalized, percentile


def summarize(samples):
    unpaced = [s for s in samples if not s["paced"]]
    paced = [s for s in samples if s["paced"]]
    return {
        "transcripts": len(samples),
        "normalized_exact_matches": sum(s["normalized_exact_match"] for s in samples),
        "unpaced_rtf_median": statistics.median(s["rtf"] for s in unpaced) if unpaced else None,
        "unpaced_rtf_p95": percentile([s["rtf"] for s in unpaced], .95) if unpaced else None,
        "paced_finalization_median": statistics.median(s["finalization_seconds"] for s in paced) if paced else None,
        "paced_finalization_p95": percentile([s["finalization_seconds"] for s in paced], .95) if paced else None,
        "unpaced_cpu_mean_percent_one_core": statistics.mean(s["cpu_percent_one_core"] for s in unpaced) if unpaced else None,
        "warm_first_rss_median_mib": statistics.median(s["VmRSS"] for s in samples[10:30] or samples),
        "last_rss_median_mib": statistics.median(s["VmRSS"] for s in samples[-20:]),
        "maximum_rss_mib": max(s["VmRSS"] for s in samples),
    }


async def benchmark(args):
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if not output.is_relative_to(root / ".validation") or args.port == 10300:
        raise ValueError("Only project .validation output and a separate test port are allowed")
    items = load_audio(args.audio)
    report = {"port": args.port, "threads": 1, "samples": [], "connections": 0,
              "pause_seconds": args.pause, "idle_seconds": args.idle}
    reader = writer = None
    started_all = time.perf_counter()

    async def receive():
        event = await asyncio.wait_for(async_read_event(reader), 45)
        assert event is not None
        return event

    async def send(value):
        await async_write_event(value.event(), writer)

    try:
        with output.open("x", encoding="utf-8") as checkpoint:
            for index in range(args.requests):
                if index % args.reconnect_every == 0:
                    if writer is not None:
                        writer.close()
                        await writer.wait_closed()
                    reader, writer = await asyncio.open_connection("127.0.0.1", args.port)
                    report["connections"] += 1
                    await send(Describe())
                    info = Info.from_event(await receive())
                    assert info.asr[0].models[0].name == "small-streaming-de"
                item = items[index % len(items)]
                variant = ("clean", "quiet", "noise20db")[(index // len(items)) % 3]
                # Both recordings receive real-time pacing, rather than always the even slot.
                paced = index % 20 == (index // 20) % len(items)
                pcm = audio_variant(item["pcm"], variant)
                cpu0, _ = process_usage(args.pid)
                started = time.perf_counter()
                await send(Transcribe(language="de", name="small-streaming-de"))
                await send(AudioStart(rate=16000, width=2, channels=1))
                for offset in range(0, len(pcm), 6400):
                    chunk = pcm[offset:offset + 6400]
                    await send(AudioChunk(rate=16000, width=2, channels=1, audio=chunk))
                    if paced:
                        await asyncio.sleep(len(chunk) / 32000)
                stopped = time.perf_counter()
                await send(AudioStop())
                event = await receive()
                finished = time.perf_counter()
                assert event.type == "transcript", (index, event.type, event.data)
                text = Transcript.from_event(event).text
                cpu1, memory = process_usage(args.pid)
                elapsed = finished - started
                sample = {"index": index, "expected": item["expected"], "recognized": text,
                    "normalized_exact_match": normalized(text) == normalized(item["expected"]),
                    "variant": variant, "paced": paced, "audio_seconds": item["audio_seconds"],
                    "roundtrip_seconds": elapsed, "rtf": elapsed / item["audio_seconds"],
                    "finalization_seconds": finished - stopped,
                    "cpu_percent_one_core": (cpu1 - cpu0) / elapsed * 100, **memory}
                report["samples"].append(sample)
                checkpoint.write(json.dumps(sample, ensure_ascii=False) + "\n")
                checkpoint.flush()
                if (index + 1) % 10 == 0:
                    print(f"Completed {index + 1}/{args.requests}; RSS {memory['VmRSS']:.3f} MiB", flush=True)
                await asyncio.sleep(args.pause)
            report["idle_memory"] = []
            idle_start = time.perf_counter()
            while time.perf_counter() - idle_start < args.idle:
                await asyncio.sleep(min(10, max(0, args.idle - (time.perf_counter() - idle_start))))
                _, memory = process_usage(args.pid)
                report["idle_memory"].append(memory)
    finally:
        if writer is not None:
            writer.close()
            await writer.wait_closed()
    report["total_wall_seconds"] = time.perf_counter() - started_all
    report["summary"] = summarize(report["samples"])
    with output.with_suffix(".json").open("x", encoding="utf-8") as result:
        json.dump(report, result, ensure_ascii=False, indent=2)
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=11300)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--requests", type=int, default=600)
    parser.add_argument("--pause", type=float, default=2)
    parser.add_argument("--idle", type=float, default=120)
    parser.add_argument("--reconnect-every", type=int, default=5)
    args = parser.parse_args()
    if args.requests < 2 or args.pause < 0 or args.idle < 0 or args.reconnect_every < 1:
        parser.error("Invalid benchmark limits")
    asyncio.run(benchmark(args))
