# Moonshine STT Wyoming

<img src="icons/moonshine-stt.png" alt="Moonshine STT Wyoming" width="160">

Lokale, CPU-basierte **Speech-to-Text-Erkennung für Home Assistant** über das
[Wyoming-Protokoll](https://www.home-assistant.io/integrations/wyoming/), basierend auf
der offiziellen Moonshine Voice Runtime.

Das Projekt ist für **Linux amd64** ausgelegt und wurde mit
**Deutsch / `small-streaming-de` auf einem Intel N100** praktisch getestet.

**Standardkonfiguration:** `small-streaming-de` · Deutsch · 1 Thread · TCP-Port `10300`

> Das Docker-Image ist öffentlich über GHCR verfügbar. Das Projekt wurde für
> Unraid Community Applications eingereicht; bis zur Aufnahme kann das enthaltene
> Unraid-Template verwendet werden.

**Docker-Image:** `ghcr.io/marco-taylor/moonshine-stt-wyoming:latest`

## Funktionen

- lokale Spracherkennung ohne externen STT-Dienst
- direkte Anbindung an Home Assistant über Wyoming
- CPU-only – keine GPU erforderlich
- für Intel N100 geeignet
- persistente Modelle außerhalb des Containers
- automatischer Download ausschließlich des ausgewählten fehlenden Modells
- 13 registrierte Streaming-Modelle für 8 Sprachen
- schreibgeschütztes Container-Root-Dateisystem im Unraid-Template
- keine Weboberfläche und keine Cloud-Anmeldung erforderlich

## Installation unter Unraid

Nach der Aufnahme in **Community Applications** kann die App direkt über den
Unraid-CA-Katalog installiert werden. Bis dahin steht das Template im Repository unter
[`templates/moonshine-stt-wyoming.xml`](templates/moonshine-stt-wyoming.xml) zur Verfügung.

Empfohlene Standardwerte:

| Einstellung | Wert |
| --- | --- |
| Wyoming Port | `10300/TCP` |
| Modell | `small-streaming-de` |
| Sprache | `de` |
| Auto Download | `1` |
| Threads | `1` |
| Modellordner | `/mnt/user/appdata/moonshine-stt-wyoming/models` |

Beim ersten Start wird das ausgewählte Modell heruntergeladen und anschließend im
persistenten Modellordner wiederverwendet. Vor der Installation prüfen, ob Host-Port
`10300` bereits von einem anderen Wyoming-Dienst verwendet wird. Einen vorhandenen
Dienst nicht stoppen; bei Bedarf einen anderen freien Host-Port verwenden.

Eine ausführlichere Beschreibung befindet sich in der
[Unraid-Installationsanleitung](docs/unraid-installation.md).

## Home Assistant verbinden

In Home Assistant:

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen**
2. **Wyoming Protocol** auswählen.
3. Die LAN-IP des Unraid-Servers eintragen.
4. Port **10300** eintragen.
5. Moonshine anschließend als STT-Dienst in der gewünschten Assist-Pipeline auswählen.

Die Sprache der Assist-Pipeline muss zur Sprache des ausgewählten Moonshine-Modells
passen. Für erste Versuche empfiehlt sich eine separate Assist-Pipeline, damit eine
bestehende Sprachkonfiguration unverändert bleibt.

## Modelle und Sprachen

Die Runtime enthält einen festen Katalog mit 13 Streaming-Modellen für:

**Arabisch · Deutsch · Englisch · Spanisch · Japanisch · Tagalog · Vietnamesisch · Chinesisch**

Für Deutsch ist die Standardkonfiguration:

```text
MOONSHINE_MODEL=small-streaming-de
MOONSHINE_LANGUAGE=de
```

Optional steht auch `tiny-streaming-de` zur Auswahl. In der aktuellen Projektversion
wurde **`small-streaming-de` praktisch getestet**. Die weiteren registrierten Modelle
sind strukturell unterstützt, wurden von diesem Projekt jedoch nicht in gleichem Umfang
praktisch validiert.

Der vollständige Katalog mit Modell-IDs und Quellen befindet sich unter
[Modelle und Sprachen](docs/models.md).

## Docker / GHCR

Das veröffentlichte Image kann auf Linux amd64 direkt aus GHCR gestartet werden:

```sh
mkdir -p models

docker pull ghcr.io/marco-taylor/moonshine-stt-wyoming:latest

docker run -d \
  --name moonshine-stt-wyoming \
  --restart unless-stopped \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --user "$(id -u):$(id -g)" \
  --tmpfs /tmp:rw,nosuid,size=16m \
  --mount "type=bind,src=$PWD/models,dst=/app/models" \
  --publish 10300:10300 \
  -e MOONSHINE_MODEL=small-streaming-de \
  -e MOONSHINE_LANGUAGE=de \
  -e MOONSHINE_AUTO_DOWNLOAD=1 \
  -e MOONSHINE_THREADS=1 \
  ghcr.io/marco-taylor/moonshine-stt-wyoming:latest
```

Der Modellordner muss für den verwendeten Containerbenutzer les- und bei aktiviertem
Auto-Download schreibbar sein.

## Konfiguration

| Variable | Standard | Beschreibung |
| --- | --- | --- |
| `MOONSHINE_MODEL` | `small-streaming-de` | Ausgewähltes Modell |
| `MOONSHINE_LANGUAGE` | `de` | Sprache des Modells |
| `MOONSHINE_MODEL_DIR` | `/app/models` | Persistenter Modellpfad |
| `MOONSHINE_AUTO_DOWNLOAD` | `1` | Fehlendes Modell automatisch laden |
| `MOONSHINE_THREADS` | `1` | Empfohlene Einstellung für Deutsch/Small auf N100 |
| `WYOMING_HOST` | `0.0.0.0` | Bind-Adresse |
| `WYOMING_PORT` | `10300` | Interner Wyoming-Port |
| `WYOMING_STT_CONCURRENT_REQUESTS` | `1` | Anzahl zugelassener STT-Streams |
| `MAX_AUDIO_SECONDS` | `30` | Maximale Audiodauer pro Anfrage |
| `LOG_LEVEL` | `INFO` | Log-Level |
| `LOG_TRANSCRIPTS` | `false` | Erkannte Texte protokollieren |
| `STT_DEVICE` | `cpu` | Gerät; dieses Image verwendet CPU |

Modell und Sprache müssen zusammenpassen. Es wird immer genau **ein ausgewähltes Modell**
geladen; es gibt keine automatische Spracherkennung oder gleichzeitige Vorladung
mehrerer Sprachmodelle.

## Modelle und Updates

Modelle werden unter `/app/models/<Modell-ID>/` gespeichert. Dadurch bleiben sie bei
Container- und Image-Updates erhalten, solange der persistente Mount beibehalten wird.

Bei aktiviertem Auto-Download gilt:

- vorhandenes vollständiges Modell → direkt wiederverwenden
- fehlendes Modell → ausgewähltes Modell herunterladen
- unvollständiges oder beschädigtes Modell → Startfehler statt stiller Überschreibung

Mit `MOONSHINE_AUTO_DOWNLOAD=0` sind automatische Modelldownloads deaktiviert.
Vollständig vorhandene kompatible Modelle können dadurch auch offline verwendet werden.

Details zur manuellen Modellinstallation stehen in der
[Modellübersicht](docs/models.md).

## Intel N100

Für **Deutsch / Small** ist `MOONSHINE_THREADS=1` die empfohlene Einstellung.
Diese Kombination wurde auf einem Intel N100 praktisch getestet und erreichte bei den
verwendeten sauberen deutschen Testaufnahmen eine Verarbeitung schneller als Echtzeit.

Die tatsächliche Erkennungsqualität und Latenz hängen unter anderem von Mikrofon,
Umgebungsgeräuschen, Sprecher und verwendeten Begriffen ab.

## Sicherheit

Das mitgelieferte Unraid-Template verwendet unter anderem:

- unprivilegierten Benutzer `99:100`
- schreibgeschütztes Root-Dateisystem
- `no-new-privileges`
- entfernte Linux-Capabilities
- begrenztes `/tmp`-Tmpfs
- keinen privileged-Modus
- keine GPU- oder Host-Geräte

Wyoming stellt hier **keine eigene Authentifizierung oder TLS-Verschlüsselung** bereit.
Den Dienst deshalb nur in einem vertrauenswürdigen LAN verwenden und Port 10300 nicht
öffentlich ins Internet weiterleiten.

## Fehlerbehebung

| Problem | Prüfen |
| --- | --- |
| Port 10300 belegt | Anderen freien Host-Port verwenden |
| Sprache passt nicht | Modell und Sprache gemeinsam konfigurieren |
| Modell fehlt | Auto-Download aktivieren oder Modell vollständig bereitstellen |
| Modell beschädigt/unvollständig | Modellordner und richtige Revision prüfen |
| Permission denied | Rechte des persistenten Modellordners prüfen |
| Download schlägt fehl | Internetzugang, Speicherplatz und Schreibrechte prüfen |
| Noch nicht bereit | Modelldownload und Initialisierung abwarten und Logs prüfen |
| Anfrage meldet busy | Laufende STT-Anfrage zuerst abschließen |
| Audio wird abgewiesen | 16 kHz, Mono, PCM16 und Audiodauer prüfen |
| Hohe N100-Latenz | Für Deutsch/Small `MOONSHINE_THREADS=1` verwenden |

## Dokumentation

Weitere technische Informationen:

- [Unraid-Installation](docs/unraid-installation.md)
- [Modelle und Sprachen](docs/models.md)
- [Architektur](docs/architecture.md)
- [Release und Updates](docs/release.md)
- [Versionen](docs/versions.md)

## Lizenz

Dieses Projekt steht unter der **Apache License 2.0**. Siehe [LICENSE](LICENSE) und
[NOTICE](NOTICE).

Moonshine, Wyoming sowie weitere verwendete Pakete und native Bibliotheken unterliegen
ihren jeweiligen Lizenzen. Die zugehörigen Hinweise befinden sich in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
