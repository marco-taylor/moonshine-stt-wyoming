# Moonshine STT Wyoming

<p align="center">
  <img src="icons/moonshine-stt.svg" alt="Moonshine STT Wyoming" width="160">
</p>

Lokale Spracherkennung für Home Assistant über Wyoming, mit der offiziellen
Moonshine Voice Runtime. CPU-only für **Linux amd64**, praktisch geprüft auf
Intel N100. Eine Instanz lädt genau ein Modell für genau eine Sprache.

**Standard: Deutsch mit `small-streaming-de`, ein Thread, Port 10300.**
Modelle liegen persistent außerhalb des Images. Tiny und weitere Sprachen werden
nur bei ausdrücklicher Auswahl verwendet, niemals zusätzlich installiert.

> Das GHCR-Image ist veröffentlicht und kann direkt verwendet werden.
> Eine Community-Applications-App ist noch **nicht verfügbar**.

Projekt: https://github.com/marco-taylor/moonshine-stt-wyoming
Image: `ghcr.io/marco-taylor/moonshine-stt-wyoming:latest`

## Installation mit dem veröffentlichten GHCR-Image

Für Linux amd64 kann das veröffentlichte CPU-Image direkt aus GHCR verwendet werden.
Zuerst prüfen, dass Host-Port 10300 frei ist und der Modellordner für den
Containerbenutzer les- und schreibbar ist:

```sh
mkdir -p models
docker pull ghcr.io/marco-taylor/moonshine-stt-wyoming:latest
docker run -d --name moonshine-stt-wyoming \
  --restart unless-stopped --read-only --cap-drop ALL \
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" \
  --tmpfs /tmp:rw,nosuid,size=16m \
  --mount "type=bind,src=$PWD/models,dst=/app/models" \
  --publish 10300:10300 \
  -e MOONSHINE_MODEL=small-streaming-de -e MOONSHINE_LANGUAGE=de \
  -e MOONSHINE_AUTO_DOWNLOAD=1 -e MOONSHINE_THREADS=1 \
  ghcr.io/marco-taylor/moonshine-stt-wyoming:latest
```

Das Beispiel nutzt die UID/GID des ausführenden Benutzers. Für einen Betrieb als
unprivilegierter Benutzer einen passend zugänglichen Modellordner verwenden.
Die Modellartefakte werden beim ersten Start außerhalb des Images gespeichert.
Wyoming nur im vertrauenswürdigen LAN bereitstellen. Bei belegtem Port einen freien
Hostport zuordnen, ohne einen bestehenden Dienst zu stoppen.

## Installation unter Unraid

Bis zur Veröffentlichung in Community Applications kann der offizielle XML-Entwurf
aus diesem Projekt für Unraid verwendet werden. Das benötigte GHCR-Image ist bereits
öffentlich verfügbar.

1. Bridge-Netzwerk verwenden und einen persistenten Hostordner wählen, zum Beispiel
   `/mnt/user/appdata/moonshine-stt-wyoming/models` → `/app/models`.
2. Host-Port **10300/TCP** prüfen. Wenn belegt, den vorhandenen Dienst nicht stoppen;
   für eine weitere Instanz einen anderen freien Hostport zu intern 10300 zuordnen.
3. Modell `small-streaming-de`, Sprache `de`, Auto-Download `1` und Threads `1` belassen.
4. Container starten und auf den gesunden Healthcheck warten. Beim ersten Start wird
   ausschließlich das fehlende ausgewählte Modell heruntergeladen und geprüft.
5. Home Assistant anschließend über die normale Wyoming-Integration anbinden.

Der Unraid-Entwurf verwendet Benutzer **99:100**, schreibgeschütztes Root-Dateisystem,
`no-new-privileges`, entfernte Linux-Capabilities und ein begrenztes `/tmp`-Tmpfs.
Kein privileged-Modus und keine GPU-/Host-Geräte erforderlich. Der Modellmount ist
für Downloads beschreibbar; mit vorhandenen Modellen kann er read-only sein.
Hostordner müssen für den tatsächlichen Containerbenutzer zugänglich sein. Die
Anwendung verändert keine vorhandenen Eigentümer oder Dateirechte.

Die [Installationsanleitung](docs/unraid-installation.md) beschreibt Felder und Fehlerfälle.
Das [Unraid-Template](templates/moonshine-stt-wyoming.xml) ist ein lokal geprüfter Entwurf.

## Home Assistant

Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen → Wyoming Protocol**
die LAN-IP des Unraid-Servers und Port **10300** eintragen. Nicht die Docker-Bridge-IP
oder 127.0.0.1 auf einem anderen Rechner verwenden.

Moonshine als STT in einer passenden Assist-Pipeline auswählen. Für erste Tests eine
separate Pipeline verwenden, vorhandene Pipelines und Satellitenzuordnungen behalten.
Die Pipeline-Sprache muss zur Modellsprache passen. [Offizielle Wyoming-Anleitung](https://www.home-assistant.io/integrations/wyoming/).

Wyoming verarbeitet 16-kHz-Mono-PCM16-Audio und liefert finale Transkripte.
Es gibt keine Mikrofonaufnahme im Container und keine eigene Weboberfläche.
Die Schnittstelle hat hier keine Authentifizierung oder TLS: nur im vertrauenswürdigen
LAN bereitstellen, keine öffentliche Portweiterleitung.

## Modelle und Sprachen

13 offizielle Streaming-Modelle für Arabisch, Deutsch, Englisch, Spanisch, Japanisch,
Tagalog, Vietnamesisch und Chinesisch sind im festen Katalog der Runtime 0.1.5 registriert.

**Von uns in der aktuellen Version praktisch validiert:** Deutsch / `small-streaming-de`.
**Strukturell unterstützt, noch nicht in dieser Version praktisch validiert:** alle
übrigen Modelle, einschließlich `tiny-streaming-de`. Es gibt keine gemessene Qualitäts- oder Performance-
Aussage für andere Sprachen. Der [vollständige Katalog](docs/models.md) nennt Modell-ID,
Sprache, Architektur, Revision, offizielle Quellen und Prüfstatus.

Modell und Sprache **gemeinsam** konfigurieren, beispielsweise:

```text
MOONSHINE_MODEL=small-streaming-en
MOONSHINE_LANGUAGE=en
```

Für optionales Tiny Deutsch:

```text
MOONSHINE_MODEL=tiny-streaming-de
MOONSHINE_LANGUAGE=de
```

Ein englisches Modell mit `MOONSHINE_LANGUAGE=de` verweigert den Start vor Download
oder Listener. Wyoming meldet ausschließlich die tatsächlich ausgewählte Modellsprache
und weist andere Anfragesprachen ab. Kein automatisches Erkennen, kein Routing und
keine gleichzeitige Vorladung mehrerer Modelle.

## Einstellungen

| Variable | Standard | Bedeutung |
| --- | --- | --- |
| MOONSHINE_MODEL | small-streaming-de | Genau ein Modell aus dem offiziellen Katalog |
| MOONSHINE_LANGUAGE | de | Muss zur Sprache des Modells passen |
| MOONSHINE_MODEL_DIR | /app/models | Persistenter absoluter Modellpfad |
| MOONSHINE_AUTO_DOWNLOAD | 1 | Fehlendes ausgewähltes Modell beim Start laden; 0 deaktiviert Downloads |
| MOONSHINE_THREADS | 1 | Empfohlener nativer Einzelthread-Modus; 4 bedeutet Runtime-Automatik |
| WYOMING_HOST | 0.0.0.0 | Bind-Adresse im Container |
| WYOMING_PORT | 10300 | Interner Wyoming-STT-Port |
| WYOMING_STT_CONCURRENT_REQUESTS | 1 | Zugelassene Streams, 1–8; native Aufrufe bleiben seriell |
| MAX_AUDIO_SECONDS | 30 | Maximal 300 s konfigurierbar |
| CLIENT_TIMEOUT_SECONDS | 60 | Zeitlimit pro eingehendem Ereignis |
| MAX_CONNECTIONS | 16 | Maximale offene Wyoming-Verbindungen |
| LOG_LEVEL | INFO | DEBUG, INFO, WARNING, ERROR oder CRITICAL |
| LOG_TRANSCRIPTS | false | Transkripte nur ausdrücklich protokollieren |
| STT_DEVICE | cpu | Ausschließlich CPU in diesem Image |

Unraid setzt die Zeitzone selbst. Es gibt keine funktionslosen PUID-/PGID-Variablen.
Andere Werte für MOONSHINE_THREADS als 1 oder 4 werden abgewiesen. 4 ist **kein harter
Thread-Zähler**, sondern deaktiviert den Einzelthread-Schalter der offiziellen Runtime.

## Automatischer Download und Persistenz

Beim Start wird genau das ausgewählte Modell geprüft:

- vollständig und gültig vorhanden → unverändert laden, kein erneuter Download;
- Modellordner fehlt und Auto-Download=1 → ausschließlich dieses Modell herunterladen;
- Modell fehlt und Auto-Download=0 → verständlicher Startfehler;
- Ordner vorhanden, aber unvollständig oder beschädigt → Fehler, keine stille Reparatur.

Eine normale Neuinstallation lädt ausschließlich Small Deutsch. Ein vorhandenes Tiny
ändert den Standard nicht. Es gibt keine Downloads während einer STT-Anfrage, keine
vorsorglichen weiteren Sprachmodelle und keine zweite identische Kopie im Home-/HF-Cache.

Modelle liegen direkt unter `/app/models/<Modell-ID>/`. Ein Image-Update behält sie,
solange der persistente Mount erhalten bleibt und die registrierte Revision kompatibel
bleibt. Der Download überschreibt keine vorhandenen Dateien. Nach einem unterbrochenen
Download bleibt das Teilmodell sichtbar; eine bewusste Reparatur ist erforderlich.

## Manuelle Installation und Offline-Betrieb

Die acht offiziellen Artefakte der **exakten Katalogrevision** direkt in den jeweiligen
Modellordner legen. Für Small Deutsch ist die Revision `quantized_26_08_24`:

```text
/app/models/small-streaming-de/
  adapter.ort
  cross_kv.ort
  decoder_kv.ort
  encoder.ort
  frontend.model.ort
  frontend.weights.ort
  streaming_config.json
  tokenizer.bin
```

Keine zusätzliche Revisions-Unterebene. Die [Modellübersicht](docs/models.md) verlinkt
für jedes Modell die offizielle Basisadresse. Dateigröße und CRC32C werden gegen den
zentralen Katalog geprüft. Eigene Downloader-Metadaten sind nicht notwendig; falls
`model.json` vorhanden ist, müssen Identität, Revision und SHA256-Liste ebenfalls stimmen.
Keine Artefakte verschiedener Modelle vermischen. Dateien als Symlinks werden abgewiesen.

`MOONSHINE_AUTO_DOWNLOAD=0` deaktiviert automatische Downloads vollständig. Mit einem
vorhandenen kompatiblen Modell funktioniert Initialisierung und Inferenz ohne Internet.
Das Image enthält weder Small noch Tiny noch andere Modelle oder Testaudio.

## Intel N100 und Performance

Für **Deutsch/Small** ist `MOONSHINE_THREADS=1` empfohlen und reproduzierbar schneller
als die Runtime-Automatik auf unserem N100. Öffentliche saubere deutsche Aufnahmen
wurden in den bisherigen Tests schneller als Echtzeit transkribiert. Das ersetzt keine
Qualitätsprüfung mit eigenen Mikrofonen, Geräuschen, Sprecherabständen und Raum-/Gerätenamen.
Diese Messungen gelten nicht automatisch für andere Modelle oder Sprachen.

## Updates und Fehlerbehebung

Bei Updates den persistenten Modellmount behalten. Für reproduzierbare Installationen
möglichst versionierte `v*`-Tags oder einen Digest verwenden, sobald entsprechende
Versionstags veröffentlicht sind; `latest` ist bereits verfügbar.
Kein Docker-Prune und keine Modelllöschung als regulärer Update-Schritt.

| Problem | Prüfen |
| --- | --- |
| Port belegt | Vorhandenen Dienst belassen; freien Hostport oder geplante Migration verwenden. |
| Sprache passt nicht | Modell und Sprache anhand des Katalogs gemeinsam einstellen. |
| Modell fehlt bei Auto=0 | Vollständiges Modell manuell installieren oder Auto=1 bewusst aktivieren. |
| Modell unvollständig/CRC-Fehler | Richtige Dateien und Revision prüfen; keine automatische Überschreibung. |
| Permission denied | Zugriff des Containerbenutzers auf den eigenen Modellordner prüfen. |
| Downloadfehler | Offiziellen HTTPS-Zugang, Speicherplatz und Schreibzugriff prüfen. |
| Noch nicht healthy | Download, Integritätsprüfung und Initialisierung abwarten; Logs lesen. |
| Zweite Anfrage erhält busy | Standardmäßig ein Stream; Abschluss der ersten Anfrage abwarten. |
| Audio abgewiesen | 16 kHz, mono, PCM16 und maximale Audiodauer prüfen. |
| Hohe Latenz auf N100 | Für Deutsch/Small Threads=1 und Hostlast prüfen. |

Der bekannte native Tokenizer-Fallback-Hinweis ist bei erfolgreichen Tests kein
Startfehler. Der Healthcheck prüft Modell-/Backend-Bereitschaft, nicht Erkennungsqualität
oder jeden möglichen nativen Hänger. Ein Healthcheck allein erzwingt keinen Neustart.
Audio wird nie protokolliert; Transkripte standardmäßig ebenfalls nicht.

## Lizenz und Reproduzierbarkeit

Eigenes Projekt: **Apache-2.0**, siehe [Projektlizenz](LICENSE) und [NOTICE](NOTICE).
Moonshine-Streaming-Modelle: MIT gemäß offizieller 0.1.5-Lizenz. Nicht unterstützte
Legacy-Modelle können andere Bedingungen haben. Upstream-Pakete und native Bibliotheken
behalten ihre jeweiligen Lizenzen; siehe [Drittanbieterhinweise](THIRD_PARTY_NOTICES.md).

Python 3.12.14, Moonshine Voice 0.1.5 und Wyoming 1.10.2 sind festgelegt. Basisimage
und Python-Abhängigkeiten sind mit Digest beziehungsweise Wheel-Hashes gepinnt.
Modelle, Testaudio, virtuelle Entwicklungsumgebungen und Caches gehören weder ins
Repository noch ins Runtime-Image. Architektur und lokale Prüfungen sind separat
unter [Architektur](docs/architecture.md) und [Release-Vorbereitung](docs/release.md) beschrieben.
