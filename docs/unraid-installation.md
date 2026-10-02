# Unraid-Installation und Bedienung

Status: lokaler, validierter Template-Entwurf. Noch keine Community-Applications-App,
kein veröffentlichtes GHCR-Image und kein automatischer Installer. Diese Anleitung
beschreibt die Einstellungen für eine Installation aus einem selbst gebauten Image
oder später aus einem veröffentlichten GHCR-Image.

## Vor der späteren Installation

1. Ein freigegebenes, versioniertes CPU-Image bereitstellen. Der lokale Entwurf
   ./moonshine-stt-wyoming/templates/moonshine-stt-wyoming.xml referenziert
   das geplante GHCR-Image ghcr.io/marco-taylor/moonshine-stt-wyoming:latest. Seine
   Registry-Verweis ist vorbereitet; GHCR ist noch nicht veröffentlicht.
   Ein eigenes Icon fehlt noch.
2. Den Modellbereich auf dauerhaftem Appdata-Speicher wählen, beispielsweise
   /mnt/user/appdata/moonshine-stt-wyoming/models. Dieser Vorschlag wurde
   durch die Template-Erstellung nicht angelegt.
3. Vor Containerstart Host-Port 10300 prüfen. Ist er belegt, den anderen Dienst
   unverändert lassen. Ein bereits funktionierender Wyoming-Dienst darf nicht durch die neue Instanz verdrängt werden.
   Eine spätere Migration braucht eine eigene Freigabe. Isolierte Tests verwenden
   einen freien Loopback-Hostport und intern weiterhin 10300.
4. Template-Installation über Unraids Docker-Verwaltung erst bewusst durchführen.
   Der aktuelle Entwurf wurde nicht nach /boot oder in die Docker-Verwaltung kopiert.

Unraid beschreibt Port-, Pfad- und Variablenfelder in seiner
[Container-Dokumentation](https://docs.unraid.net/unraid-os/using-unraid-to/run-docker-containers/managing-and-customizing-containers/).
Die lokale Prüfung bestätigt zusätzlich das Verhalten des tatsächlich installierten
Docker-Managers: neue Pfadzuordnungen werden bei einer echten Installation für
UID/GID 99:100 angelegt; der Parser-Test dieser Phase führt diese Aktion nicht aus.

## Empfohlene Einstellungen

| Feld | Wert |
| --- | --- |
| Netzwerk | bridge |
| Host-Port / Container-Port | 10300 / 10300 TCP |
| Persistenter Hostpfad | /mnt/user/appdata/moonshine-stt-wyoming/models |
| Modellpfad im Container | /app/models |
| MOONSHINE_MODEL | small-streaming-de |
| MOONSHINE_LANGUAGE | de |
| MOONSHINE_AUTO_DOWNLOAD | 1 |
| MOONSHINE_THREADS | 1 |
| WYOMING_PORT | 10300 |
| WYOMING_STT_CONCURRENT_REQUESTS | 1 |

Der Template-Entwurf verwendet --user=99:100, read-only Root-Dateisystem,
cap-drop ALL, no-new-privileges, ein begrenztes /tmp-Tmpfs und begrenzte Docker-Logs.
Keine GPU, keine Host-Geräte und kein privileged erforderlich. Das Image selbst
hat den Benutzer 65532:65532; der Unraid-Entwurf überschreibt ihn mit dem
praktisch getesteten Unraid-Benutzer. Es gibt keine PUID/PGID-Umgebungsvariablen und
keinen versteckten Startprozess, der Dateirechte verändert.

Unraid setzt die Server-Zeitzone bereits als TZ. Daher enthält das Template kein
doppeltes Zeitzonenfeld; die Zeitzone beeinflusst nicht die STT-Modellwahl.
Eine Oberfläche im Browser gibt es nicht: die Schnittstelle ist Wyoming TCP.

Das Modellverzeichnis muss für den tatsächlichen Containerbenutzer lesbar sein,
bei Auto-Download zusätzlich schreibbar. Bei einem selbst vorab angelegten Pfad
Eigentümer und Rechte gezielt prüfen lassen. Keine globalen Rechtekorrekturen,
kein pauschales chmod 777 und kein privilegierter Container als Fehlerlösung.

## Automatische Modellinstallation

Ein leeres /app/models ist beim ersten Start erlaubt: der Unterordner
/app/models/small-streaming-de existiert dann noch nicht. Mit Auto-Download=1
lädt der Dienst ausschließlich die acht Dateien von Small aus der offiziellen
Moonshine-Quelle, prüft Größen und CRC32C und speichert zusätzliche SHA256-Metadaten.
Danach wird das Modell geladen; erst dann wird Wyoming bereit.

Bei weiteren Starts werden vollständige vorhandene Dateien validiert und geladen,
ohne erneuten Download. Ein Image-Update behält Modelle bei, wenn Mount und
Modellmanifest kompatibel bleiben. Keine zweite Kopie im Home-/HF-/Platformdirs-Cache.

Ein bereits existierender, aber leerer oder unvollständiger Modell-Unterordner gilt
als Fehler. Er wird nicht still repariert. Nach unterbrochenem Download verbleiben
Teildateien sichtbar; eine gezielte Reparatur oder Entfernung braucht eine bewusste
Entscheidung. Andere Modelle und Daten werden nicht überschrieben.

## Small und Tiny auswählen

Small Streaming Deutsch ist der Standard und auf dem N100 mit einem Thread
empfohlen. Tiny Streaming Deutsch bleibt eine ausdrückliche Alternative:

    MOONSHINE_MODEL=tiny-streaming-de

Nur diese Auswahl erlaubt Tiny-Nutzung bzw. bei Auto-Download=1 einen fehlenden
Tiny-Download. Small und Tiny werden nicht gemeinsam vorsorglich bereitgestellt.
Ein vorhandenes Tiny ändert den Standard nicht. Bei Modellwechsel bleiben bereits
vorhandene Modelle erhalten; geladen wird nur das ausgewählte Modell.

Moonshine Voice 0.1.5 unterstützt öffentlich den Einzelthread-Schalter. Im Projekt
bedeutet MOONSHINE_THREADS=4 Runtime-Automatik, keinen garantierten harten Zähler.
Auf dem geprüften N100 war 1 deutlich schneller. Andere Threadwerte werden abgewiesen.

## Andere Sprache auswählen

Im Template Modell **und** Sprache gemeinsam wählen. Der Modellname endet mit dem
Sprachcode, beispielsweise small-streaming-en und en. Deutsch/Small bleibt Standard.
Die beiden Dropdowns sind statisch; Unraid koppelt sie nicht dynamisch. Die Anwendung
verweigert falsche Kombinationen vor einem Download. Der vollständige Katalog steht in
./moonshine-stt-wyoming/docs/models.md. Jede Instanz bedient genau eine Sprache.
Für weitere gleichzeitige Sprachen wären separate Instanzen mit getrennten freien Hostports
erforderlich. Keine automatischen Änderungen an bestehenden Diensten oder HA-Pipelines.
Andere Sprachen wurden noch nicht real bewertet; keine Übertragung der deutschen N100-Messwerte.

## Manuelle Installation und Offline-Betrieb

Kompatibel sind die registrierten offiziellen Streaming-Modelle mit der jeweils im
Katalog festgelegten Revision. Siehe ./moonshine-stt-wyoming/docs/models.md.
Deutsch/Small verwendet quantized_26_08_24 und die offizielle Basisadresse:

    https://download.moonshine.ai/model/small-streaming-de/quantized_26_08_24/

Je Dateiname die entsprechende Datei beziehen. Keine privaten Fremdrepositories
oder Modelle anderer Projekte kopieren. Erwartete Struktur:

    /app/models/
      small-streaming-de/
        adapter.ort
        cross_kv.ort
        decoder_kv.ort
        encoder.ort
        frontend.model.ort
        frontend.weights.ort
        streaming_config.json
        tokenizer.bin

Keine zusätzliche Revisions-Unterebene. model.json ist optional; die Anwendung
fordert keine Metadaten ihres eigenen Downloaders. Vorhandene zusätzliche Metadaten
müssen aber ebenfalls gültig sein. Symlinks auf Artefakte werden nicht akzeptiert.
Größen und CRC32C stehen in ./moonshine-stt-wyoming/src/moonshine_stt_wyoming/model-manifest.json.
Fremde Revisionen werden derzeit nicht geladen. Für Tiny analog dessen offiziellen
Modellpfad und Manifest verwenden; nichts ohne ausdrückliche Auswahl herunterladen.

Mit MOONSHINE_AUTO_DOWNLOAD=0 erfolgt niemals ein automatischer Download. Ein
vorhandenes kompatibles Modell funktioniert vollständig lokal; ein fehlendes Modell
führt vor Öffnen des Wyoming-Listeners zu einem verständlichen Startfehler.
Ein read-only Modell-Mount funktioniert mit vorhandenen Modellen auch bei Auto=1;
für einen später tatsächlich fehlenden Modellwechsel ist wieder ein beschreibbarer
Mount erforderlich. Das read-only Root-Dateisystem bleibt unabhängig davon aktiviert.

## Home Assistant

Für eine neue Installation: in Einstellungen → Geräte & Dienste die Integration Wyoming Protocol
hinzufügen, Unraid-LAN-IP und Port 10300 eingeben. Verwende die tatsächliche LAN-IP deines Unraid-Servers und den zugeordneten Hostport. Nicht die Docker-interne Bridge-IP oder 127.0.0.1 eintragen.
Die [offizielle Wyoming-Anleitung](https://www.home-assistant.io/integrations/wyoming/)
beschreibt die Integration über die Oberfläche.

Für Qualitätstests eine separate deutsche Assist-Testpipeline mit Moonshine als STT
verwenden, ohne bestehende Pipelines, bevorzugte Pipeline oder Satelliten-Zuordnungen
zu ersetzen. Tests auf den STT-Schritt begrenzen, damit keine Gerätebefehle entstehen.
Wyoming besitzt hier weder TLS noch Authentifizierung; nur im vertrauenswürdigen LAN,
keine Portweiterleitung ins Internet.

## Updates und Troubleshooting

Vor einem später freigegebenen Update Image-Version und Modellrevision notieren;
den persistenten Mount behalten. Keine Modelle löschen, keine Docker-Prune-Aktion
als Update-Schritt. Ein neues Modellmanifest kann bewusste Modellmigration erfordern;
kein pauschales Versprechen, dass jede zukünftige Revision alte Dateien akzeptiert.

| Symptom | Prüfen |
| --- | --- |
| Port bereits belegt | Anderen Dienst nicht stoppen. Freien Testport verwenden oder Migration gesondert planen. |
| Sprache passt nicht zum Modell | Beide Variablen anhand des Katalogs gemeinsam einstellen. |
| Modell fehlt bei Auto=0 | Ausgewähltes Modell manuell vollständig installieren oder Auto=1 bewusst aktivieren. |
| Modell unvollständig/CRC-Fehler | Richtige acht Dateien und Revision prüfen; keine automatische Überschreibung. |
| Permission denied | Rechte des eigenen Modellpfads für den tatsächlichen UID/GID prüfen; kein globales chmod/chown. |
| Download schlägt fehl | Internet/HTTPS-Zugriff und freien Speicher prüfen. Teilmodell nicht still weiterverwenden. |
| Container startet, noch nicht healthy | Ersten Download und Modellinitialisierung abwarten; Logs prüfen. |
| Zweite Anfrage erhält busy | N100 verarbeitet standardmäßig einen Stream. Auf Abschluss der ersten Anfrage warten. |
| Audio abgewiesen | 16000 Hz, Mono, PCM16; maximale Audiodauer standardmäßig 30 s. |
| Hohe Latenz | MOONSHINE_THREADS=1 und Hostlast prüfen; keine GPU nötig. |
| unhealthy ohne Neustart | Healthcheck allein löst keinen Docker-Neustart aus. Keine automatischen Eingriffe in andere Dienste. |

Transkripte sind standardmäßig nicht in Logs; Audiodaten werden niemals geloggt.
Bekannter nativer Tokenizer-Fallback-Hinweis bedeutet nicht automatisch einen
Startfehler; tatsächlichen Healthcheck und Inferenz prüfen.

## Weitere Dokumentation

- [Modellkatalog](models.md)
- [Architektur](architecture.md)
- [Release- und Veröffentlichungshinweise](release.md)
