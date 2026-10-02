import json
from pathlib import Path

from .errors import ServiceError
from .integrity import file_integrity

MANIFEST_PATH = Path(__file__).with_name("model-manifest.json")


def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def model_spec(name: str) -> dict:
    try:
        return manifest()["models"][name]
    except KeyError:
        raise ServiceError("invalid-model", "Modell ist nicht freigegeben") from None


def model_path(root: Path, name: str) -> Path:
    model_spec(name)  # Prevent user-controlled traversal.
    resolved = root.resolve()
    candidate = (resolved / name).resolve()
    if not candidate.is_relative_to(resolved):
        raise ServiceError("invalid-model-path", "Modellpfad liegt außerhalb des Modellverzeichnisses")
    return candidate


def validate_model(root: Path, name: str) -> Path:
    """Read-only check. Never imports the runtime or starts a download."""
    spec = model_spec(name)
    directory = model_path(root, name)
    if not directory.exists():
        raise ServiceError("model-missing", "Ausgewähltes Modell fehlt: " + name)
    try:
        metadata_file = directory / "model.json"
        hashes = None
        if metadata_file.exists() or metadata_file.is_symlink():
            if metadata_file.is_symlink() or metadata_file.stat().st_size > 8192:
                raise ValueError("metadata")
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            if not isinstance(metadata, dict):
                raise ValueError("metadata")
            if metadata.get("model") != name or metadata.get("revision") != spec["revision"]:
                raise ValueError("identity")
            hashes = metadata["sha256"]
            if not isinstance(hashes, dict) or set(hashes) != set(spec["files"]):
                raise ValueError("files")
        for filename in spec["files"]:
            file = directory / filename
            if file.is_symlink() or not file.is_file() or file.stat().st_size == 0:
                raise ValueError("missing")
            expected = spec["files"][filename]
            if file.stat().st_size != expected["size"]:
                raise ValueError("size")
            actual = file_integrity(file)
            if ((hashes is not None and actual["sha256"] != hashes[filename]) or actual["size"] != expected["size"]
                    or actual["crc32c"] != expected["crc32c"]):
                raise ValueError("checksum")
        config = json.loads((directory / "streaming_config.json").read_text(encoding="utf-8"))
        if not isinstance(config, dict) or not config:
            raise ValueError("config")
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        raise ServiceError("invalid-model-files", "Modell unvollständig oder beschädigt: " + name +
                           "; offizielle Dateien/Revision prüfen, vorhandene Daten werden nicht überschrieben") from None
    return directory
