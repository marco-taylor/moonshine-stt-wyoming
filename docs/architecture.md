# Architektur

## Komponenten

1. ./moonshine-stt-wyoming/src/moonshine_stt_wyoming/config.py validiert Umgebungsvariablen.
2. ./moonshine-stt-wyoming/src/moonshine_stt_wyoming/model_manager.py prüft lokale Dateien und provisioniert ein fehlendes Modell beim Start.
   ./moonshine-stt-wyoming/src/moonshine_stt_wyoming/models.py validiert ausschließlich lesend.
3. ./moonshine-stt-wyoming/src/moonshine_stt_wyoming/backends/base.py definiert Backend und BackendStream.
4. ./moonshine-stt-wyoming/src/moonshine_stt_wyoming/backends/moonshine_cpu.py bindet die offizielle Runtime an.
5. ./moonshine-stt-wyoming/src/moonshine_stt_wyoming/stt_service.py besitzt Worker und Stream-Zulassung.
6. ./moonshine-stt-wyoming/src/moonshine_stt_wyoming/protocol.py implementiert den Anfragezustand.
7. ./moonshine-stt-wyoming/src/moonshine_stt_wyoming/transport.py begrenzt Wyoming-Framing und verwendet
   den offiziellen wyoming.Event/async_write_event für Antworten.
8. ./moonshine-stt-wyoming/src/moonshine_stt_wyoming/wyoming_server.py betreibt asyncio TCP und Verbindungen.

## Zustandsautomat

idle → transcribe → armed → audio-start → audio → audio-chunk* → audio-stop → idle.
Nach audio-stop wird ein finales transcript mit text und language gesendet.
Auf derselben Verbindung sind weitere Anfragen möglich. describe ist jederzeit erlaubt.
Ungültige Reihenfolgen, Formate, Sprache, Modell, Länge oder Überlast erzeugen error;
der Netzwerkadapter schließt anschließend die Verbindung. Unbekannte Ereignisse werden
entsprechend der Wyoming-Kompatibilitätsregel ignoriert.

Home Assistant sendet 16-kHz-Mono-16-Bit-PCM. Das Protokoll bietet in dieser Version
keine Teiltranskript-Ausgabe an; die Moonshine-Inferenz selbst verarbeitet trotzdem
inkrementell Audio. requires_external_vad=true, da audio-stop das Anfrageende steuert.
Mehrere Moonshine-Segmentzeilen werden beim Abschluss vollständig zusammengefügt.

## Nebenläufigkeit und Lebensdauer

Ein ThreadPoolExecutor mit genau einem Worker besitzt alle nativen Runtime-Aufrufe,
einschließlich Initialisierung und Schließen. Dies vermeidet parallele Zugriffe auf
modellinterne Zustände und erhält Thread-Affinität. Eine Lease reserviert synchron im
Eventloop einen Anfrageplatz, bevor irgendein nativer Aufruf gestartet wird.
WYOMING_STT_CONCURRENT_REQUESTS=1 ist Standard. Höhere Werte erlauben interleavende Streams,
keine parallelen nativen Inferenzaufrufe. Keine unbegrenzte STT-Auftragswarteschlange.

Ein abgebrochener asyncio-Aufruf stoppt native Inferenz nicht. Der Service shieldet
und drainiert deshalb den tatsächlichen Future, bevor er Streamressourcen freigibt.
Die Lease besitzt den erzeugten Stream auch bei Abbruch während create_stream.
Server-Shutdown stoppt zuerst Annahme, dann Verbindungen und deren Bereinigung,
anschließend Streams und Modell und zuletzt den Executor.

Wichtige Grenze: Ein dauerhaft hängender nativer Aufruf kann nicht sicher durch einen
Thread-Timeout abgebrochen werden. Für garantierte harte Inferenzzeitlimits wäre ein
späterer Prozess-Worker erforderlich. Der erste Runtime-Test muss normales Shutdown-
und Fehlerverhalten bestätigen. Phase 3 hat normalen SIGTERM, TCP-Abbruch und Shutdown
mit aktivem Stream bestätigt; ein dauerhaft hängender nativer Aufruf bleibt ungeprüft.

## Grenzen und Healthcheck

Maximal 16 TCP-Verbindungen, standardmäßig 1 STT-Stream, maximal 30 Audiosekunden.
PCM-Budget basiert auf Samples, nicht Wanduhrzeit. Zusätzlich ist die aktive Anfrage
auf MAX_AUDIO_SECONDS + CLIENT_TIMEOUT_SECONDS Wanduhrsekunden begrenzt, soweit kein
nativer Aufruf dauerhaft hängt. Reads und Writes haben Zeitlimits; große Längenangaben
werden vor Payload-Allokation abgewiesen. Backpressure entsteht durch sequenzielles
Ingest; pro Anfrage wird höchstens ein Chunk an den Worker übergeben.

Healthcheck nutzt describe/info und die Erweiterung moonshine_status. Er überprüft
native Initialisierung, Modellladung und aktuelle Dateiverfügbarkeit, ohne Inferenz.
SHA256, offizielle CRC32C und Revision werden beim Start geprüft, nicht bei jedem Probe.
Ein Modellmount sollte im Serverbetrieb read-only sein und nicht im laufenden Betrieb wechseln.

## Offline und Modellverwaltung

Small Deutsch ist Standard, Tiny eine Alternative. MOONSHINE_AUTO_DOWNLOAD=1 erlaubt
nur beim Start die Provisionierung eines nicht vorhandenen ausgewählten Modellordners.
Gültige vorhandene Modelle werden direkt geladen. Ein bestehender ungültiger Ordner wird
abgewiesen, niemals überschrieben. MOONSHINE_AUTO_DOWNLOAD=0 deaktiviert Startdownloads.
Modellprüfung und Download laufen im Worker vor Öffnen des Wyoming-Listeners.
Das Backend verwendet ausschließlich den lokalen Transcriber-Konstruktor, keine
automatischen Sprachkatalog- oder Cache-Downloads. Während Anfragen wird nicht provisioniert.
Revision und offizielle Größe/CRC32C definieren gültige manuelle Artefakte. Downloader-
SHA256-Metadaten sind optional; falls vorhanden, müssen sie zusätzlich stimmen.
Der Server schreibt keine Metadaten in manuelle Installationen. Es entsteht keine zweite
Cachekopie. /app/models bleibt der einzige persistente Produktions-Modellbereich.

MOONSHINE_THREADS=1 aktiviert den nativen Einzelthread-Schalter der offiziellen Runtime;
4 lässt den Schalter ausgeschaltet und nutzt automatische Pools auf dem N100. Ein
beliebiger harter Thread-Zähler ist in 0.1.5 nicht verfügbar; andere Werte werden abgewiesen.
Der Python-Worker ist davon unabhängig stets ein einzelner Thread.

## Backend-Erweiterungen

Neue Backends implementieren initialize, ready, create_stream, close; ihre Streams
implementieren add_audio, finish, close. Änderungen an Wyoming sind nicht nötig.
Die Datenübergabe bleibt signed little-endian PCM. Spätere Parallelisierung benötigt
zusätzlich einen überprüften Worker-/Thread-Sicherheitsvertrag.
CPU bleibt Standard und eigenständig nutzbar. GPU-Runtimes gehören in getrennte Images.

## Sicherheit

Keine Secrets als Konfiguration benötigt. Keine Payload-/Audio-Logs. Transkripte sind
Opt-in und JSON-escaped. Fehlertexte enthalten keine Clientwerte oder nativen Exceptions.
Begrenzte Protokollgrößen, keine Modellnamen als frei wählbare Pfade, keine Host-Mikrofone.
Phase 3 beobachtete eine native Tokenizer-Fallback-Meldung auf stderr trotz deaktivierter
Text-/API-Logs. Sie enthält keine Audiodaten oder Transkripte; die Optionen unterdrücken
also nicht alle nativen Diagnosen. Details: ./moonshine-stt-wyoming/docs/phase3-validation.md.
Wyoming enthält keine Authentifizierung; Netzwerkfreigabe ist eine spätere Betriebsentscheidung.

## Mehrsprachigkeit ab Phase 7.5

Ein Modell und eine Sprache pro Instanz. Alle Identitäten, Sprachen, Architekturen,
Revisionen und Größen/CRC32C stammen ausschließlich aus
./moonshine-stt-wyoming/src/moonshine_stt_wyoming/model-manifest.json.
./moonshine-stt-wyoming/config/model-manifest.json ist nur ein Pfadverweis.
Der Katalog wurde aus den nativen Metadaten-APIs der tatsächlich installierten
Moonshine Voice 0.1.5 ausgelesen und in einem Runtime-Vertragstest vollständig verglichen.
Config.from_env und zusätzlich STTService.initialize validieren Modell/Sprache vor
Provisionierung. Info, Anfragesprache und Transcript verwenden die Manifestsprache.
Wyoming und der CPU-Backend-Code benötigen keine sprachspezifischen Pfade.
Das derzeitige Streaming-Dateilayout enthält acht Artefakte je registriertem Modell.
Legacy-Tiny/Base und BASE_STREAMING sind nicht freigegeben. Keine Laufzeit-Katalogupdates.
Details und praktische Grenzen: ./moonshine-stt-wyoming/docs/models.md.
