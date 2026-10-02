"""Real offline/reuse/manual model cases; never downloads additional models."""
import asyncio
from dataclasses import replace
import json
from pathlib import Path
import uuid
from unittest.mock import patch

from moonshine_stt_wyoming.backends.moonshine_cpu import MoonshineCPU
from moonshine_stt_wyoming.config import Config
from moonshine_stt_wyoming.errors import ServiceError
from moonshine_stt_wyoming.models import model_spec
from moonshine_stt_wyoming.stt_service import STTService

ROOT = Path(__file__).resolve().parents[1]


async def loaded(config):
    service = STTService(config, MoonshineCPU(threads=config.threads))
    try:
        await service.initialize()
        assert service.ready and service.model_available
    finally:
        await service.close()
    assert not service.backend.ready and service.closed


async def validate():
    config = Config.from_env({"MOONSHINE_MODEL_DIR": str(ROOT / ".validation/small-test-models")})
    report = {}
    provisioning = json.loads((ROOT / ".validation/small-provisioning.json").read_text())
    assert provisioning["model"] == config.model and provisioning["download_calls"] == 8
    report["A_missing_auto_download"] = {"passed": True, "initial_download_calls": 8,
        "source_report": "./moonshine-stt-wyoming/.validation/small-provisioning.json"}
    source = config.model_dir / config.model
    manual_root = ROOT / ".validation/manual-small-models"
    manual = manual_root / config.model
    if not manual.exists():
        manual.mkdir(parents=True)
        # A true independent manual install: only the eight upstream artifacts,
        # no proprietary downloader metadata, no symlinks or cache redirection.
        for name in model_spec(config.model)["files"]:
            with (manual / name).open("xb") as output:
                output.write((source / name).read_bytes())
    assert not (manual / "model.json").exists()
    invalid_root = ROOT / ".validation/invalid-small-models"
    invalid = invalid_root / config.model
    if not invalid.exists():
        invalid.mkdir(parents=True)
        (invalid / "encoder.ort").write_bytes(b"deliberately incomplete test data")
    missing_root = ROOT / ".validation/offline-small-absent"
    assert not missing_root.exists()
    with patch("moonshine_stt_wyoming.model_download.urlopen",
               side_effect=AssertionError("Unexpected model network request")) as network:
        await loaded(config)
        report["B_existing_auto_enabled"] = {"passed": True, "download_calls": network.call_count}
        await loaded(replace(config, auto_download=False))
        report["C_existing_auto_disabled"] = {"passed": True, "download_calls": network.call_count}
        try:
            await loaded(replace(config, model_dir=missing_root, auto_download=False))
        except ServiceError as error:
            assert error.code == "model-missing"
            report["D_missing_offline"] = {"passed": True, "code": error.code, "message": str(error)}
        else:
            raise AssertionError("Missing offline model accepted")
        assert not missing_root.exists()
        for auto in (True, False):
            await loaded(replace(config, model_dir=manual_root, auto_download=auto))
        report["E_manual_small_without_metadata"] = {"passed": True, "download_calls": network.call_count,
            "files": len(list(manual.iterdir())), "metadata_generated": (manual / "model.json").exists()}
        await loaded(replace(config, model="tiny-streaming-de", model_dir=ROOT / ".validation/test-models",
                             auto_download=False))
        report["F_tiny_selected"] = {"passed": True, "download_calls": network.call_count}
        try:
            await loaded(replace(config, model_dir=invalid_root))
        except ServiceError as error:
            assert error.code == "invalid-model-files"
            report["G_incomplete_manual"] = {"passed": True, "code": error.code, "message": str(error)}
        else:
            raise AssertionError("Incomplete model accepted")
        assert (invalid / "encoder.ort").read_bytes() == b"deliberately incomplete test data"
        network.assert_not_called()
    report["all_reuse_manual_offline_cases_network_requests"] = 0
    output = ROOT / ".validation" / ("small-model-management-" + uuid.uuid4().hex + ".json")
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("Report:", output.relative_to(ROOT.parent))


if __name__ == "__main__":
    asyncio.run(validate())
