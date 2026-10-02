# Versionsentscheidung, geprüft am 01.10.2026

## Offizielle Quellen

- https://pypi.org/pypi/moonshine-voice/json — Version 0.1.5, Linux amd64-Wheel.
- https://pypi.org/pypi/wyoming/json — Version 1.10.2, keine notwendigen Runtime-Zusatzpakete.
- https://www.python.org/downloads/ — neueste Feature-Serie 3.14; 3.12.15 veröffentlicht.
- https://www.python.org/downloads/release/python-31214/ — gewählte Python-Version 3.12.14.
- https://hub.docker.com/_/python — offizielles Image, nur Registry-Manifeste abgefragt.
- https://github.com/moonshine-ai/moonshine/blob/main/language-bindings/python/pyproject.toml
- https://moonshine-voice.readthedocs.io/en/latest/models/available-models/
- https://github.com/moonshine-ai/moonshine/blob/main/core/moonshine-model-catalog.cpp
- https://github.com/moonshine-ai/moonshine/blob/main/core/moonshine-model-file-metadata.generated.cpp
- https://github.com/moonshine-ai/moonshine/blob/main/language-bindings/python/src/moonshine_voice/transcriber.py
- https://github.com/OHF-Voice/wyoming

## Auswahl

Python 3.12 entspricht der dokumentierten Moonshine-Anbindung. 3.12.15 ist neu,
sein Docker-Tag 3.12.15-slim-bookworm antwortete aber mit 404. 3.12.14-slim-bookworm
ist vorhanden. amd64-Manifest:
sha256:1aaa65a85fda306ffb8b910824d4e93bdce61e212c7e87168123ea3073b41a1a.
Bei der Docker-Registry-Prüfung wurden nur JSON-Metadaten abgefragt, keine Image-Layer
geladen. Python-Wheels wurden für die isolierte Phase-3-Umgebung bereitgestellt.

./moonshine-stt-wyoming/requirements.lock fixiert die 15 notwendigen Runtime-Pakete.
./moonshine-stt-wyoming/requirements-build.lock fixiert getrennt setuptools, wheel
und packaging. Alle Pins/Hashes bleiben unverändert, nur ihre Gruppen wurden getrennt.
./moonshine-stt-wyoming/config/dependency-manifest.json enthält Requires-Python, Requires-Dist
und die freigegebenen Artefakte sowie Runtime-/Build-Gruppen. Die Auflösung und
Installation wurden in der isolierten Python-3.12.14-Umgebung praktisch bestätigt;
offizielle Metadaten/Hashes erneut geprüft, pip check ohne Konflikte.
Die finale Docker-Stufe benötigt keine zusätzlichen apt-Pakete für diesen STT-Pfad:
MicTranscriber/sounddevice sind lazy und werden nicht importiert. Der frühere PortAudio-
Systempaketentwurf entfällt. Docker-Build und Systembibliotheken im Basisimage müssen
in Phase 4 praktisch geprüft werden.

Die offizielle Moonshine-Runtime hängt von sounddevice ab. Wir entfernen diese
Upstream-Abhängigkeit nicht künstlich; keine Host-Audiogeräte werden eingebunden und
kein Mikrofon-API wird verwendet. Keine PyTorch-/Transformers-/Trainings-Extras.
ORT ist Bestandteil der nativen offiziellen Runtime, kein separat gewähltes GPU-Paket.

## Deutsche Artefakte

Modell-IDs tiny-streaming-de und small-streaming-de, Revision quantized_26_08_24.
Die acht Dateien pro Modell werden aus offiziellen Dateimetadaten samt Größe und CRC32C
festgelegt. Die Paket- und Dokumentationskataloge unterscheiden sich im Beschreibungstext;
das veröffentlichte 0.1.5-Wheel wurde mit beiden Architekturen und genau diesen
Modellkomponenten erfolgreich initialisiert; Small und Tiny wurden praktisch transkribiert.
Ein unverifizierter main-Build wird nicht als Ersatz automatisch verwendet.

## Mehrsprachiger Katalog, 02.10.2026

Keine Runtime- oder Dependency-Aktualisierung in Phase 7.5.
Die tatsächlich installierte offizielle Runtime 0.1.5 liefert über ihre nativen Getter
13 Streaming-Modelle für acht Sprachen samt exakten URLs, Dateigrößen und CRC32C.
Dieser Katalog wurde ohne Modelldownload übernommen und vollständig gegen die API
geprüft. Deutsch/Small wurde erneut real getestet; Deutsch/Tiny nur in früheren Phasen.
Andere Sprachen sind strukturell unterstützt, noch nicht praktisch validiert.
Der vollständige Katalog steht in ./moonshine-stt-wyoming/docs/models.md.
Einzige Modellquelle: ./moonshine-stt-wyoming/src/moonshine_stt_wyoming/model-manifest.json.
Der unveränderte ältere Docker-Runtime-Stand wurde mit read-only Quellcode-Mount
für die neue Anwendung getestet; das umbenannte Docker-Image wurde nicht neu gebaut.
