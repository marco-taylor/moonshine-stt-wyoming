"""Startup provisioning only; inference never downloads models."""
import logging

from .errors import ServiceError
from .models import validate_model

LOGGER = logging.getLogger("moonshine_stt_wyoming")


def ensure_model(config):
    try:
        directory = validate_model(config.model_dir, config.model)
    except ServiceError as error:
        if error.code != "model-missing":
            raise
        if not config.auto_download:
            raise ServiceError("model-missing", "Ausgewähltes Modell fehlt: " + config.model +
                "; MOONSHINE_AUTO_DOWNLOAD=0. Offizielle Dateien manuell installieren") from None
        from .model_download import download
        LOGGER.info("Ausgewähltes Modell fehlt; offizieller Download beim Start: %s", config.model)
        try:
            download(config)
        except ServiceError:
            raise
        except FileExistsError:
            # Another startup may have created the directory. Never overwrite it.
            return validate_model(config.model_dir, config.model)
        except Exception:
            raise ServiceError("model-download-failed", "Offizieller Modelldownload fehlgeschlagen; Netzwerk und Schreibzugriff prüfen. Unvollständige Dateien werden nicht überschrieben") from None
        return validate_model(config.model_dir, config.model)
    LOGGER.info("Vorhandenes Modell validiert; kein Download: %s", config.model)
    return directory
