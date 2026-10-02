# Modellkatalog und Mehrsprachigkeit

Stand: 2026-10-02. Freigegeben für Moonshine Voice **0.1.5** auf Linux amd64.

Deutsch/Small ist Standard. Eine Instanz lädt genau ein Modell und eine Sprache.

## Freigegebene Streaming-Modelle

| Modell-ID | Sprache | Architektur | Revision | Status | Artefaktgröße | Offizielle Quelle |
| --- | --- | --- | --- | --- | ---: | --- |
| medium-streaming-en | Englisch (en) | MEDIUM_STREAMING | quantized_26_08_21 | strukturell; kein realer Inferenztest | 269,141,623 Bytes | [Modellquelle](https://download.moonshine.ai/model/medium-streaming-en/quantized_26_08_21) |
| small-streaming-de | Deutsch (de) | SMALL_STREAMING | quantized_26_08_24 | Phase 7.5 real getestet | 121,800,823 Bytes | [Modellquelle](https://download.moonshine.ai/model/small-streaming-de/quantized_26_08_24) |
| small-streaming-en | Englisch (en) | SMALL_STREAMING | quantized_26_08_21 | strukturell; kein realer Inferenztest | 142,300,974 Bytes | [Modellquelle](https://download.moonshine.ai/model/small-streaming-en/quantized_26_08_21) |
| small-streaming-es | Spanisch (es) | SMALL_STREAMING | quantized_26_08_24 | strukturell; kein realer Inferenztest | 121,800,392 Bytes | [Modellquelle](https://download.moonshine.ai/model/small-streaming-es/quantized_26_08_24) |
| small-streaming-ja | Japanisch (ja) | SMALL_STREAMING | quantized_26_08_23 | strukturell; kein realer Inferenztest | 121,803,780 Bytes | [Modellquelle](https://download.moonshine.ai/model/small-streaming-ja/quantized_26_08_23) |
| tiny-streaming-ar | Arabisch (ar) | TINY_STREAMING | quantized_26_08_24 | strukturell; kein realer Inferenztest | 32,349,411 Bytes | [Modellquelle](https://download.moonshine.ai/model/tiny-streaming-ar/quantized_26_08_24) |
| tiny-streaming-de | Deutsch (de) | TINY_STREAMING | quantized_26_08_24 | strukturell; nicht in der aktuellen Version praktisch validiert | 32,317,004 Bytes | [Modellquelle](https://download.moonshine.ai/model/tiny-streaming-de/quantized_26_08_24) |
| tiny-streaming-en | Englisch (en) | TINY_STREAMING | quantized_26_08_21 | strukturell; kein realer Inferenztest | 45,233,659 Bytes | [Modellquelle](https://download.moonshine.ai/model/tiny-streaming-en/quantized_26_08_21) |
| tiny-streaming-es | Spanisch (es) | TINY_STREAMING | quantized_26_08_24 | strukturell; kein realer Inferenztest | 32,316,573 Bytes | [Modellquelle](https://download.moonshine.ai/model/tiny-streaming-es/quantized_26_08_24) |
| tiny-streaming-ja | Japanisch (ja) | TINY_STREAMING | quantized_26_08_23 | strukturell; kein realer Inferenztest | 32,319,961 Bytes | [Modellquelle](https://download.moonshine.ai/model/tiny-streaming-ja/quantized_26_08_23) |
| tiny-streaming-tl | Tagalog (tl) | TINY_STREAMING | quantized_26_08_24 | strukturell; kein realer Inferenztest | 32,309,481 Bytes | [Modellquelle](https://download.moonshine.ai/model/tiny-streaming-tl/quantized_26_08_24) |
| tiny-streaming-vi | Vietnamesisch (vi) | TINY_STREAMING | quantized_26_08_24 | strukturell; kein realer Inferenztest | 32,309,008 Bytes | [Modellquelle](https://download.moonshine.ai/model/tiny-streaming-vi/quantized_26_08_24) |
| tiny-streaming-zh | Chinesisch (zh) | TINY_STREAMING | quantized_26_08_24 | strukturell; kein realer Inferenztest | 32,290,152 Bytes | [Modellquelle](https://download.moonshine.ai/model/tiny-streaming-zh/quantized_26_08_24) |

## Beleg und zentrale Quelle

Die tatsächliche offizielle 0.1.5-Runtime liefert diese Einträge über
moonshine_get_stt_catalog_string und moonshine_get_stt_dependencies_string mit
model_arch als numerischem Wert des öffentlichen ModelArch-Enums. Die native
Abhängigkeitsantwort liefert pro Datei Namen, URL, Größe und CRC32C. Alle 13
Einträge wurden exakt abgeglichen; die Getter laden keine Modelle herunter.

Offizielle Version: [Moonshine v0.1.5](https://github.com/moonshine-ai/moonshine/releases/tag/v0.1.5).
Installationshash und Version: ./moonshine-stt-wyoming/config/dependency-manifest.json.
Die einzige verbindliche Modellquelle ist
./moonshine-stt-wyoming/src/moonshine_stt_wyoming/model-manifest.json.
Darin stehen für jedes Modell alle benötigten Dateien einschließlich Größe/CRC32C.
Der installierte Python-Adapter bildet TINY_STREAMING=2, SMALL_STREAMING=4 und
MEDIUM_STREAMING=5 ab; der unveränderte CPU-Backend-Code verwendet dieses Enum.

Strukturelle Unterstützung bedeutet: offizielle Runtime kennt Architektur und
Download-Manifest; Konfiguration, Downloader, Validator und Wyoming wurden mit
isolierten Testartefakten/Mock-Inferenz geprüft. Es ist kein Beweis für tatsächliche
Sprachqualität oder erfolgreiche native Modellinitialisierung der nicht geladenen Modelle.
Keine neuen Sprachmodelle oder Audiodaten wurden in Phase 7.5 heruntergeladen.

## Auswahl und manuelle Installation

Beide Werte müssen zusammenpassen:

    MOONSHINE_MODEL=small-streaming-en
    MOONSHINE_LANGUAGE=en

Der Sprachdefault bleibt de. Englisch nur im Modellfeld zu wählen ist deshalb
ein klarer Startfehler. Kein automatisches Erkennen, kein mehrsprachiges Routing.
Wyoming nennt nur die Sprache des tatsächlich ausgewählten Modells.

Unter /app/models/<Modell-ID>/ liegen die Dateien direkt, ohne Revisions-Unterordner:

    adapter.ort
    cross_kv.ort
    decoder_kv.ort
    encoder.ort
    frontend.model.ort
    frontend.weights.ort
    streaming_config.json
    tokenizer.bin

Jede registrierte Streaming-Variante benötigt derzeit diese acht Dateien, aber
jeweils ihre eigenen im Manifest hinterlegten Größen und CRC32C. Keine Artefakte
zwischen Modellen oder Revisionen vermischen. Die Download-URL einer Datei ist
die offizielle Basisadresse in der Tabelle plus /<Dateiname>. Optionales model.json
muss bei Vorhandensein Modell-ID, Revision und vollständige SHA256-Werte enthalten.
Manuelle Installationen benötigen diese eigenen Metadaten nicht. Eine CRC32C ist
eine Integritätsprüfung und keine Signatur; lokal erzeugte SHA256-Werte sind kein
unabhängiger Anbieterhash. Herkunft wird durch offizielle HTTPS-Quellen belegt.

Auto=1 lädt beim Start nur das ausgewählte fehlende Modell. Auto=0 lädt niemals.
Ein gültiges vorhandenes Modell wird unverändert verwendet. Unvollständige oder
beschädigte vorhandene Verzeichnisse werden abgewiesen, nicht überschrieben.
Modelle sind persistent außerhalb des Images; ein Image-Update behält sie.

## Nicht freigegebene Kandidaten

Die 0.1.5-Runtime führt zusätzlich Legacy-Tiny/Base-Modelle, darunter Koreanisch
(ko) und Ukrainisch (uk). Sie haben andere Artefaktlayouts als der hier getestete
Streaming-Adapter. Sie sind keine auswählbaren Modelle dieser Anwendung. Ihre
Aufnahme benötigt einen eigenen Backend-/Validierungsvertrag und reale Tests.
BASE_STREAMING ist zwar ein Enum-Wert, hat im nativen Katalog keinen veröffentlichten
Modelleintrag. Neue Modelle einer neueren Runtime werden nicht automatisch akzeptiert.

## Messgrenzen

Die N100-Empfehlung MOONSHINE_THREADS=1 ist für Deutsch/Small belegt.
Keine Leistungs- oder Qualitätsübertragung auf Englisch/Medium oder andere Sprachen.
Geeignete öffentliche oder eigens erstellte Testaufnahmen für diese Modelle bleiben offen.
