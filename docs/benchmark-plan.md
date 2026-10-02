# Benchmarkplan für Phase 3 und spätere Phasen

Phase 3 hat zwei öffentliche deutsche CC0-Aufnahmen mit Small und zuvor Tiny Streaming
auf dem N100 geprüft, einschließlich realem Wyoming und Offline-Betrieb.
Aktuelle Ergebnisse: ./moonshine-stt-wyoming/docs/phase3-small-validation.md.
Die folgenden Punkte beschreiben weitere Messungen; HA und Langzeitqualität bleiben offen.

## Reihenfolge

1. Standardbibliotheks-Unit-Tests und AST-Syntaxprüfung mit vorhandenem/freigegebenem Python ausführen.
2. Festgelegte Paketauflösung, Moonshine-Import und CPU-Modellinitialisierung nachweisen.
3. Deutsche Tiny-Streaming-Referenztranskription; danach Small Streaming vergleichen.
4. Wyoming-Protokolltest mit echten Events, aber zunächst ohne HA-Konfigurationsänderungen.
5. Erst nach Freigabe Container und separate HA-Testpipeline prüfen.

## Aufnahmen

Mit Zustimmung ein reproduzierbares deutsches Korpus verwenden: kurze Befehle,
Gerätenamen, Raumbezeichnungen, Zahlen, Komposita und Negationen. Stille,
Hintergrundgeräusche, entfernte Mikrofone und mehrere Sprecher separat auswerten.
Referenztexte manuell prüfen. PCM 16000 Hz, Mono, 16 Bit.
Keine Aufnahmen oder vollständigen Transkripte automatisch in Logs ablegen.

## Messgrößen

- WER/CER gegen Referenztext und korrekte Erkennung von Gerätenamen.
- Echtzeitfaktor: gesamte Inferenzrechenzeit / Audiodauer.
- Zeit von letztem Sprachsample zu audio-stop: separat, HA/VAD-abhängig.
- Zeit von audio-stop zu finalem transcript: Median, p95 und Maximum.
- Ende-zu-Ende-Assist-Latenz separat von STT und TTS.
- Modellladezeit, Peak-RSS, CPU-Last und Leerlaufverbrauch.
- Busy-Verhalten, Verbindungsabbruch und SIGTERM während Inferenz.
- Gesundheit vor Modellladung, bei fehlenden Dateien und nach Ladefehlern.

## N100-Profile

Alle regulären Funktions-, Wyoming-, Offline-, Persistenz-, Performance- und
Home-Assistant-Vorbereitungstests für Phase 4 verwenden Small. Tiny bleibt ein optionaler
Vergleich ausschließlich bei ausdrücklichem Bedarf; dafür nicht automatisch provisionieren.
Small zunächst mit einem Sprecher messen. Zunächst ohne konkurrierende
Inferenz, danach mit der üblichen Kikiri-/Ollama-Nutzung. Keine bestehenden Dienste
für Benchmarks ohne konkrete Freigabe stoppen oder rekonfigurieren.
WYOMING_STT_CONCURRENT_REQUESTS=1 bleibt Ausgangspunkt. CPU-/Threadparameter nicht anhand
von OMP_NUM_THREADS allein als wirksam annehmen; native Runtime prüfen.

## Abnahmevorschlag

Echtzeitfaktor unter 1 mit Reserve; p95-Finalisierung möglichst unter 1 Sekunde bei
kurzen Sprachbefehlen. Diese Zahlen sind Ziele, keine Leistungszusagen.
Small bleibt das Standard- und Abnahmemodell; Threadparameter anhand Genauigkeit und
Konkurrenzlast prüfen.
Keine Ressourcenlecks nach wiederholten Anfragen oder Abbrüchen.

## Spätere Beschleunigung

Intel-iGPU/OpenVINO, AMD-iGPU und NVIDIA jeweils gegen dieselbe CPU-Baseline testen.
Modellgraph-Kompatibilität, Decoder-State, Genauigkeit, Energiebedarf und Übergabe-
Overhead messen. Nur belegte Vorteile rechtfertigen einen zusätzlichen Backend.
NPU ist eine getrennte Untersuchung; CPU-Kompatibilität muss bestehen bleiben.
