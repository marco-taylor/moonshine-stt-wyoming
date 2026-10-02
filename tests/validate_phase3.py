"""Opt-in real-runtime validation; never provisions models or uses port 10300.

Requires pre-provisioned .validation/small-test-models and .validation/audio inputs.
All reports are created exclusively in .validation with unique names.
"""
import argparse
import asyncio
import ctypes
from dataclasses import replace
import errno
import importlib.metadata
import json
from pathlib import Path
import platform
import resource
import signal
import socket
import sys
import time
import uuid
import wave

from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioStart, AudioChunk, AudioStop
from wyoming.event import async_read_event, async_write_event
from wyoming.info import Describe, Info

from moonshine_stt_wyoming.backends.moonshine_cpu import MoonshineCPU
from moonshine_stt_wyoming.config import Config
from moonshine_stt_wyoming.errors import ServiceError
from moonshine_stt_wyoming.healthcheck import check
from moonshine_stt_wyoming.stt_service import STTService
from moonshine_stt_wyoming.wyoming_server import WyomingServer

ROOT = Path(__file__).resolve().parents[1]


def deny_network_for_current_process():
    """Linux amd64 seccomp, inherited by worker threads; no host policy change."""
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeError("Offline seccomp validation requires Linux x86_64")

    class Filter(ctypes.Structure):
        _fields_ = [("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte),
                    ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint32)]

    class Program(ctypes.Structure):
        _fields_ = [("len", ctypes.c_ushort), ("filter", ctypes.POINTER(Filter))]

    # Check AUDIT_ARCH_X86_64 before examining architecture-specific syscall IDs.
    rules = [Filter(0x20, 0, 0, 4), Filter(0x15, 1, 0, 0xC000003E),
             Filter(0x06, 0, 0, 0x80000000), Filter(0x20, 0, 0, 0)]
    for syscall in (41, 42, 53):  # socket, connect, socketpair
        rules += [Filter(0x15, 0, 1, syscall), Filter(0x06, 0, 0, 0x50000 | errno.EPERM)]
    rules.append(Filter(0x06, 0, 0, 0x7FFF0000))
    array = (Filter * len(rules))(*rules)
    program = Program(len(rules), array)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) or libc.prctl(22, 2, ctypes.byref(program), 0, 0):
        raise OSError(ctypes.get_errno(), "Could not install process-only seccomp filter")
    try:
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except PermissionError:
        return True
    raise AssertionError("Network denial probe unexpectedly succeeded")


def usage():
    value = resource.getrusage(resource.RUSAGE_SELF)
    return value.ru_utime + value.ru_stime


def rss_mib(field="VmRSS"):
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith(field + ":"):
            return int(line.split()[1]) / 1024
    return None


def audio_inputs():
    metadata = json.loads((ROOT / ".validation/audio/prepared-sources.json").read_text())
    for item in metadata:
        with wave.open(str(ROOT / ".validation/audio" / item["test_file"]), "rb") as wav:
            assert (wav.getframerate(), wav.getsampwidth(), wav.getnchannels()) == (16000, 2, 1)
            item["pcm"] = wav.readframes(wav.getnframes())
    return metadata


async def direct(service, item):
    lease = service.reserve()
    started, cpu = time.perf_counter(), usage()
    try:
        await lease.open()
        for offset in range(0, len(item["pcm"]), 6400):
            await lease.add_audio(item["pcm"][offset:offset + 6400])
        text = await lease.finish()
        elapsed = time.perf_counter() - started
    finally:
        await lease.close()
    cpu_seconds = usage() - cpu
    assert text, "Real inference returned empty text"
    return {"expected": item["expected"], "recognized": text,
            "audio_seconds": item["audio_seconds"], "inference_seconds": elapsed,
            "rtf": elapsed / item["audio_seconds"], "cpu_seconds": cpu_seconds,
            "cpu_percent_one_core": cpu_seconds / elapsed * 100,
            "rss_mib": rss_mib(),
            "peak_rss_mib": rss_mib("VmHWM"),
            "getrusage_peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024}


async def receive(reader):
    event = await asyncio.wait_for(async_read_event(reader), timeout=30)
    assert event is not None, "Unexpected EOF"
    return event


async def send(writer, eventable):
    await async_write_event(eventable.event(), writer)


async def wait_released(service):
    for _ in range(200):
        if not service.leases:
            return
        await asyncio.sleep(0.01)
    raise AssertionError("Stream admission not released")


async def local_wyoming(service, items):
    server = WyomingServer(service)
    clients = []
    results = {}
    try:
        # Port 0 asks the kernel for an ephemeral port; never use the default.
        ephemeral_range = Path("/proc/sys/net/ipv4/ip_local_port_range").read_text().split()
        assert int(ephemeral_range[0]) > 10300
        await server.start()
        port = server.server.sockets[0].getsockname()[1]
        assert port != 10300
        results["loopback_port"] = port

        async def connect():
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            clients.append(writer)
            return reader, writer

        reader, writer = await connect()
        await send(writer, Describe())
        event = await receive(reader)
        info = Info.from_event(event)
        assert info.asr[0].name == "moonshine-stt-wyoming"
        assert info.asr[0].models[0].languages == ["de"]
        assert await check(replace(service.config, port=port))
        results["describe_and_health"] = "passed"
        results["end_to_end"] = []
        for item in items:
            started, cpu = time.perf_counter(), usage()
            await send(writer, Transcribe(language="de", name=service.config.model))
            await send(writer, AudioStart(rate=16000, width=2, channels=1))
            for offset in range(0, len(item["pcm"]), 6400):
                await send(writer, AudioChunk(rate=16000, width=2, channels=1,
                                             audio=item["pcm"][offset:offset + 6400]))
            await send(writer, AudioStop())
            event = await receive(reader)
            assert event.type == "transcript", event.type
            transcript = Transcript.from_event(event)
            assert transcript.language == "de" and transcript.text
            elapsed = time.perf_counter() - started
            results["end_to_end"].append({"expected": item["expected"],
                "recognized": transcript.text, "audio_seconds": item["audio_seconds"],
                "roundtrip_seconds": elapsed, "rtf": elapsed / item["audio_seconds"],
                "cpu_seconds": usage() - cpu})
        writer.close()
        await writer.wait_closed()
        await wait_released(service)

        reader, writer = await connect()
        item = items[0]
        await send(writer, Transcribe(language="de"))
        await send(writer, AudioStart(rate=16000, width=2, channels=1))
        started = time.perf_counter()
        for offset in range(0, len(item["pcm"]), 6400):
            chunk = item["pcm"][offset:offset + 6400]
            await send(writer, AudioChunk(rate=16000, width=2, channels=1, audio=chunk))
            await asyncio.sleep(len(chunk) / 32000)
        stopped = time.perf_counter()
        await send(writer, AudioStop())
        transcript = Transcript.from_event(await receive(reader))
        assert transcript.text
        results["paced_stream"] = {"recognized": transcript.text,
            "audio_seconds": item["audio_seconds"],
            "wall_seconds": time.perf_counter() - started,
            "audio_stop_to_transcript_seconds": time.perf_counter() - stopped}
        writer.close()
        await writer.wait_closed()
        await wait_released(service)

        reader, writer = await connect()
        await send(writer, Transcribe(language="de"))
        await send(writer, AudioStart(rate=8000, width=2, channels=1))
        event = await receive(reader)
        assert event.type == "error" and event.data["code"] == "unsupported-audio-format"
        results["invalid_audio_format"] = "passed"
        writer.close()
        await writer.wait_closed()

        reader, writer = await connect()
        await send(writer, Transcribe(language="de"))
        await send(writer, AudioStart(rate=16000, width=2, channels=1))
        for _ in range(6):  # Test configuration has a five-second audio limit.
            await send(writer, AudioChunk(rate=16000, width=2, channels=1, audio=bytes(32000)))
        event = await receive(reader)
        assert event.type == "error" and event.data["code"] == "audio-too-long"
        results["max_audio_seconds"] = "passed"
        writer.close()
        await writer.wait_closed()
        await wait_released(service)

        reader1, writer1 = await connect()
        await send(writer1, Transcribe(language="de"))
        await send(writer1, AudioStart(rate=16000, width=2, channels=1))
        # describe on the same connection proves prior audio-start was processed.
        await send(writer1, Describe())
        assert (await receive(reader1)).type == "info"
        assert len(service.leases) == 1
        reader2, writer2 = await connect()
        await send(writer2, Transcribe(language="de"))
        await send(writer2, AudioStart(rate=16000, width=2, channels=1))
        event = await receive(reader2)
        assert event.type == "error" and event.data["code"] == "busy"
        results["concurrent_request_rejected"] = "passed"
        writer1.close()
        writer2.close()
        await writer1.wait_closed()
        await writer2.wait_closed()
        await wait_released(service)
        results["disconnect_releases_stream"] = "passed"

        reader, writer = await connect()
        await send(writer, Transcribe(language="de"))
        await send(writer, AudioStart(rate=16000, width=2, channels=1))
        await send(writer, Describe())
        await receive(reader)
        await server.close()
        assert not service.leases and not server.server.is_serving()
        results["shutdown_with_active_client"] = "passed"
    finally:
        for writer in clients:
            writer.close()
        await asyncio.gather(*(writer.wait_closed() for writer in clients), return_exceptions=True)
        await server.close()
    return results


async def validate_sigterm():
    # Inherits the project's HOME/TMPDIR/cache variables and no external cwd.
    process = await asyncio.create_subprocess_exec(sys.executable, "-B",
        str(ROOT / "tests/validate_shutdown.py"), stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE, cwd=ROOT)
    try:
        ready = await asyncio.wait_for(process.stdout.readline(), 20)
        assert ready.startswith(b"READY "), "Test process did not become ready"
        port = int(ready.split()[1])
        assert port != 10300
        process.send_signal(signal.SIGTERM)
        stdout, stderr = await asyncio.wait_for(process.communicate(), 20)
        assert process.returncode == 0 and b"STOPPED" in stdout
        return {"passed": True, "exit_code": process.returncode, "loopback_port": port}
    finally:
        if process.returncode is None:
            process.terminate()
            await asyncio.wait_for(process.wait(), 20)


async def validate(offline, threads=1):
    report = {"python": platform.python_version(), "offline": offline, "threads_mode": threads,
              "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}}
    if offline:
        report["network_syscalls_denied"] = deny_network_for_current_process()
    config = Config.from_env({"MOONSHINE_MODEL_DIR": str(ROOT / ".validation/small-test-models"),
                             "MOONSHINE_AUTO_DOWNLOAD": "0", "WYOMING_HOST": "127.0.0.1",
                             "MAX_AUDIO_SECONDS": "5", "MOONSHINE_THREADS": str(threads)})
    assert config.port == 10300 and config.max_concurrent_requests == 1
    missing = STTService(replace(config, model_dir=ROOT / ".validation/absent-model"), MoonshineCPU(threads=config.threads))
    try:
        try:
            await missing.initialize()
        except ServiceError as error:
            assert error.code == "model-missing"
            report["missing_model"] = {"code": error.code, "message": str(error), "passed": True}
        else:
            raise AssertionError("Missing model unexpectedly loaded")
    finally:
        await missing.close()
    assert not (ROOT / ".validation/absent-model").exists()
    service = STTService(replace(config, port=0), MoonshineCPU(threads=config.threads))
    assert service.backend.threads == config.threads
    items = audio_inputs()
    try:
        started = time.perf_counter()
        await service.initialize()
        report["process_thread_count_after_load"] = len(list(Path("/proc/self/task").iterdir()))
        report["model_load_seconds"] = time.perf_counter() - started
        assert service.ready and service.model_available
        report["model"] = {"id": config.model, "revision": "quantized_26_08_24", "language": "de"}
        report["direct"] = [await direct(service, item) for item in items]
        if not offline:
            report["wyoming"] = await local_wyoming(service, items)
    finally:
        await service.close()
    assert not service.backend.ready and service.closed and not service.leases
    report["backend_shutdown"] = "passed"
    if not offline:
        report["sigterm"] = await validate_sigterm()
    output = ROOT / ".validation" / ("results-" + ("offline-" if offline else "online-") + uuid.uuid4().hex + ".json")
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print("Report:", output.relative_to(ROOT.parent))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--threads", type=int, choices=(1, 4), default=1)
    args = parser.parse_args()
    # Create the loop's self-pipe before the process-only network filter is set.
    with asyncio.Runner() as runner:
        runner.run(validate(args.offline, args.threads))
