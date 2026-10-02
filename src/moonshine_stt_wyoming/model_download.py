"""Provisioning at startup or via CLI; never during transcription requests."""
import base64
import hashlib
import json
import logging
import ssl
from urllib.request import Request, urlopen

from .config import Config
from .errors import ConfigurationError, ServiceError
from .models import model_path, model_spec, validate_model
from .integrity import CRC32C


def download(config: Config):
    if not config.auto_download:
        raise ServiceError("download-disabled", "Download deaktiviert: MOONSHINE_AUTO_DOWNLOAD=0")
    spec = model_spec(config.model)
    destination = model_path(config.model_dir, config.model)
    if destination.exists():
        raise ServiceError("model-exists", "Modellverzeichnis existiert bereits; vorhandene Dateien werden nicht überschrieben")
    config.model_dir.mkdir(parents=True, exist_ok=True)
    destination.mkdir()
    hashes = {}
    for name, expected in spec["files"].items():
        digest = hashlib.sha256()
        crc = CRC32C()
        size = 0
        url = spec["base_url"] + "/" + name
        request = Request(url, headers={"User-Agent": "moonshine-stt-wyoming/0.1.0"})
        with urlopen(request, timeout=60, context=ssl.create_default_context()) as response:
            if not response.geturl().startswith(spec["base_url"] + "/"):
                raise ServiceError("download-redirect", "Unerwartete Download-Weiterleitung")
            with (destination / name).open("xb") as output:
                while block := response.read(65536):
                    size += len(block)
                    if size > expected["size"]:
                        raise ServiceError("download-size", "Modelldownload überschreitet erwartete Größe")
                    output.write(block)
                    digest.update(block)
                    crc.update(block)
        if size != expected["size"] or base64.b64encode(crc.digest()).decode() != expected["crc32c"]:
            raise ServiceError("download-integrity", "Modelldownload besteht die offizielle Integritätsprüfung nicht")
        hashes[name] = digest.hexdigest()
    metadata = {"model": config.model, "revision": spec["revision"], "sha256": hashes}
    with (destination / "model.json").open("x", encoding="utf-8") as output:
        json.dump(metadata, output, indent=2)
        output.write("\n")
    validate_model(config.model_dir, config.model)


def main():
    try:
        download(Config.from_env())
    except (ConfigurationError, ServiceError) as error:
        logging.error("%s", error)
        raise SystemExit(1) from None
    except Exception:
        logging.error("Modelldownload fehlgeschlagen; Details werden zum Schutz von Zugangsdaten nicht ausgegeben")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
