# Phase 9B: GHCR-Veröffentlichung vorbereiten, nicht ausführen

Datum: 2026-10-02. Lokale Vorbereitung abgeschlossen. Kein Push, kein Commit in Phase 9B, kein GHCR-Login/Build/Publish, keine Tags/Releases/Community-Applications-Einreichung. Keine Änderungen an Home Assistant, laufenden Docker-Diensten, bestehenden SSH-Zugängen oder globaler Git-Konfiguration.

## Grundlage und bereits öffentlich geprüfter CI-Lauf

Repository: https://github.com/marco-taylor/moonshine-stt-wyoming.
Veröffentlichter main: 78f047a4e49a215bc8f3057756546d6ba1c8fc78.
Lokaler HEAD und origin/main stimmen mit dem lesend abgefragten Remote-main überein.

Der [erste GitHub-Actions-Lauf](https://github.com/marco-taylor/moonshine-stt-wyoming/actions/runs/37004137736) für diesen Commit ist abgeschlossen und erfolgreich. validate bestand inklusive tatsächlichem CPU-Image-Build auf GitHubs Runner, Tests gegen die gepinnten Runtime-Pakete und Release-Prüfung. publish wurde skipped, mit null ausgeführten Schritten. Der frühere CI-Build dauerte etwa 19 s; in Phase 9B wurde kein neuer Workflow gestartet oder Build durchgeführt.

## Lokale Änderungen

1. ./moonshine-stt-wyoming/.github/workflows/docker-publish.yml: ausschließlich der Freigabekommentar präzisiert. Eine Freigabe zur Vorbereitung ist keine GHCR-Veröffentlichungsfreigabe. Die funktionale false-&&-Sperre bleibt unverändert.
2. ./moonshine-stt-wyoming/templates/moonshine-stt-wyoming.xml: veraltete Statusbeschreibung korrigiert. Quellcode ist auf GitHub veröffentlicht, GHCR-Image und CA-App noch nicht. Keine funktionale Container-/Default-/Sicherheitsänderung.
3. ./moonshine-stt-wyoming/docs/phase9b-ghcr-preparation.md: dieser neue Bericht.

Die Änderungen wurden sowohl im Arbeitsprojekt als auch im vorbereiteten eigenständigen Git-Kandidaten lokal gepflegt. Kein git add/Commit/Push dieser Phase. Der neue Bericht ist untracked; normales git diff --stat zeigt daher nur die beiden bereits getrackten Dateien. Lokale maschinenlesbare Nachweise verbleiben ausgeschlossen im Validierungsbereich.

## Workflow-Prüfung

| Bereich | Ergebnis |
|---|---|
| Trigger | push auf main und v*-Tags; pull_request; workflow_dispatch |
| Freigabesicherheit | Publish-Job beginnt mit false && und kann unter keinem Trigger laufen |
| Weitere Gates | Exaktes Repository, RELEASE_PUBLISH_ENABLED=true, keine Pull Requests, main/v*-Ref, ghcr-release Environment |
| Reihenfolge | publish benötigt erfolgreichen validate-Job |
| Runner | ubuntu-24.04, nur linux/amd64, kein GPU-/ARM-Versprechen |
| Build-Kontext | context: . nach Checkout; Dockerfile standardmäßig ./Dockerfile |
| Validierungsbuild | load:true, push:false, lokaler CI-Tag; kein GHCR-Login im validate-Job |
| Publish-Vorbereitung | Buildx plus build-push-action; aktuell vollständig gesperrt |
| Login | registry ghcr.io, github.actor, automatisch bereitgestelltes secrets.GITHUB_TOKEN |
| Image | ghcr.io/marco-taylor/moonshine-stt-wyoming |
| Actions | Fünf Actions-Versionen, acht Referenzen, vollständige 40-stellige Commit-SHA-Pins |
| Checkout | persist-credentials:false; kein SSH-Deploy-Key auf dem Runner erforderlich |
| Concurrency | release-${{ github.ref }}, keine Abbruchautomatik für laufende Veröffentlichungen |
| Versionsprüfung | v*-Ref muss mit pyproject-Version übereinstimmen; derzeit 0.1.0 |

Die Mindestberechtigungen entsprechen [GitHubs GHCR-Workflow-Dokumentation](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images) und [GITHUB_TOKEN-Authentifizierung](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token). Für diese Konfiguration genügt contents:read bei Validierung und zusätzlich packages:write ausschließlich im späteren Publish-Job. Kein contents:write, actions:write, id-token:write, attestations:write oder PAT erforderlich. Es gibt keine GitHub-Artifact-Attestation-/OIDC-Schritte; bei deren späterer Einführung wären die entsprechenden zusätzlichen Rechte separat zu prüfen. BuildKit-Provenance ist davon zu unterscheiden.

Die Publish-Berechtigung wird im YAML ausdrücklich vorbereitet, aber der übersprungene Job erzeugt keine Login-/Publish-Schritte. Der bereits erfolgreiche Validierungsjob mit contents:read belegt die Kompatibilität dieser Minimalberechtigung für dessen vorhandene Schritte.

## Geplante Tags

- ghcr.io/marco-taylor/moonshine-stt-wyoming:latest nur bei main; nicht automatisch bei Versions-Tags.
- ghcr.io/marco-taylor/moonshine-stt-wyoming:v0.1.0 als möglicher später ausdrücklich freigegebener Versions-Tag; allgemein der exakte v*-Tag.
- Kein zusätzliches v0/v0.1/semver-Alias, kein automatischer Git-Tag und kein GitHub Release.

flavor:latest=false verhindert implizites latest. Ein manuelles workflow_dispatch auf main würde nach späterer bewusster Aktivierung ebenfalls latest bauen. main/v*-Pushes können nach Entfernen der Sperre und Setzen der weiteren Gates automatisch veröffentlichen; dies ist jetzt NICHT aktiviert. Image-Versionen/Labels sind bei der tatsächlichen späteren Veröffentlichung nochmals gegen Paketversion und Ref zu prüfen: metadata-action kann OCI-Versionslabels aus dem Ref erzeugen und Dockerfile-Labels überschreiben. latest ist veränderlich; einen veröffentlichten Digest für reproduzierbare Installation festhalten.

## Cache und Reproduzierbarkeit

Kein cache-from/cache-to und kein persistenter Registry-/GitHub-Actions-Cache konfiguriert. Nur kurzlebiger BuildKit-Cache innerhalb des jeweiligen Runners; kein Download-/Modellcache in den Builds. Der gemessene erste Build (~19 s) rechtfertigt derzeit keine zusätzliche Cache-Komplexität oder Veröffentlichung von Zwischenstufen. validate und später publish bauen getrennt; Basisdigest, Wheel-Hashes und SOURCE_DATE_EPOCH bleiben festgelegt. Ein identischer OCI-Digest über zwei komplette Builds wurde nicht nachgewiesen.

Die [offizielle Docker-Cache-Dokumentation](https://docs.docker.com/build/ci/github-actions/cache/) beschreibt spätere Optionen. Cache allein ist keine Voraussetzung für GHCR. Bei späterem Bedarf nur geprüfte Buildschichten und sichere PR-/Branch-Scopes verwenden; keine Modelldaten oder Secrets über Caches transportieren.

## Dockerfile, Modelle und geplanter Image-Inhalt

Dockerfile und Runtime-COPY-/Prune-Regeln gegenüber veröffentlichtem main unverändert. Multi-Stage linux/amd64 mit Python 3.12.14-slim-bookworm und festem Basisdigest; Moonshine Voice 0.1.5 und Wyoming 1.10.2, hashgeprüfte Build-/Runtime-Lockdateien. Build-Werkzeuge bleiben im Builder. Eigene Anwendung plus tatsächlich deklarierte Runtime-Abhängigkeiten und Lizenzhinweise im finalen Image; kein PyTorch/Transformers.

COPY verwendet nur explizite Quellcode-/Lock-/Metadaten-/Lizenzpfade bzw. /opt/runtime aus dem Builder. Modelle oder Testaudio werden weder im Dockerfile heruntergeladen noch kopiert. .dockerignore schließt .git, .validation, .venv, Tests, Dokumentation, Templates, Modelle, Audio, Buildartefakte, Caches, Exportarchive und Authentifizierungsdateien aus. Offizielle Demo-Audios/Embedding-Artefakte und der ungenutzte Demo-Tokenizer aus dem Moonshine-Wheel werden im Builder entfernt, RECORD wird angepasst. Es gibt kein pauschales COPY . in das Runtime-Image.

Das in Phase 8 tatsächlich untersuchte lokale Image (220.868.273 Bytes, 210,64 MiB) bleibt vorhanden. Lesendes docker image inspect bestätigt Architektur, Defaults und Image-Benutzer. Sein vollständiger früherer Rootfs-Audit enthält null Modellartefakte, Audio-/Entwicklungsartefakte, Compiler/Git oder Build-Paketdateien. /opt/runtime damals 96.112.199 Bytes. Diese historische Image-Prüfung ist kein neuer Phase-9B-Build: das spätere GHCR-Artefakt muss nach freigegebenem Build nochmals tatsächlich untersucht werden. Seitdem geänderte README-/Repository-Dokumentation kann Wheel-Metadaten/Größe ändern, nicht die Modellverwaltung oder Runtime-COPY-Regeln.

## Verbindliche Defaults / sicherer Unraid-Betrieb

```env
MOONSHINE_MODEL=small-streaming-de
MOONSHINE_LANGUAGE=de
MOONSHINE_MODEL_DIR=/app/models
MOONSHINE_AUTO_DOWNLOAD=1
MOONSHINE_THREADS=1
WYOMING_PORT=10300
WYOMING_STT_CONCURRENT_REQUESTS=1
```

Zusätzlich WYOMING_HOST=0.0.0.0, STT_DEVICE=cpu, MAX_AUDIO_SECONDS=30, LOG_TRANSCRIPTS=false. Defaults stimmen in Anwendung, Konfigurationsbeispiel, Docker-ENV, zentralem Katalog und Unraid-Template überein.

Das Image selbst hat USER 65532:65532; das Unraid-Template setzt ausdrücklich --user=99:100. Damit ist UID/GID 99:100 eine getestete Unraid-Startoption, kein falsches Versprechen über den Dockerfile-Default. Bridge, --read-only, --cap-drop=ALL, --security-opt=no-new-privileges, begrenztes /tmp-Tmpfs, begrenzte Docker-Logs, kein privileged/GPU/Host-Gerät. Persistentes /app/models für die gewählte Modellverwaltung; Hostordner für 99:100 lesbar, bei Auto-Download schreibbar. Keine automatische Rechte-/Eigentümeränderung am Host. Interner und standardmäßiger Hostport 10300/TCP, vor tatsächlichem Start auf Belegung prüfen. Kein Container in dieser Phase gestartet oder verändert.

Nur das ausgewählte fehlende Modell wird beim Start heruntergeladen. Standardinstallation ausschließlich Small Deutsch. Vorhandene kompatible Dateien werden ohne Download verwendet; manuelle Installation der acht registrierten Artefakte ohne eigene Downloader-Metadaten bleibt erlaubt. Auto0 verhindert Downloads. Unvollständige/beschädigte Verzeichnisse werden abgewiesen und nicht überschrieben. Modelle bleiben außerhalb des Images unter /app/models; eine Instanz lädt genau ein Modell/eine passende Sprache.

## Modellkatalog / Prüfstatus

13 Streaming-Modelle für acht Sprachen. Zentrale Quelle bleibt ./moonshine-stt-wyoming/src/moonshine_stt_wyoming/model-manifest.json. Alle Modelle haben acht erforderliche Dateien, offizielle Quelle und Größen/CRC32C; Modell/Sprache wird zwingend gekoppelt. Tests vergleichen die registrierten Angaben mit der öffentlichen API der installierten Runtime.

| Modell | Sprache | Architektur | Revision | Eigener Prüfstatus |
|---|---|---|---|---|
| tiny-streaming-ar | ar | TINY_STREAMING | quantized_26_08_24 | strukturell unterstützt |
| small-streaming-es | es | SMALL_STREAMING | quantized_26_08_24 | strukturell unterstützt |
| tiny-streaming-es | es | TINY_STREAMING | quantized_26_08_24 | strukturell unterstützt |
| small-streaming-de | de | SMALL_STREAMING | quantized_26_08_24 | praktisch validiert |
| tiny-streaming-de | de | TINY_STREAMING | quantized_26_08_24 | strukturell unterstützt |
| medium-streaming-en | en | MEDIUM_STREAMING | quantized_26_08_21 | strukturell unterstützt |
| small-streaming-en | en | SMALL_STREAMING | quantized_26_08_21 | strukturell unterstützt |
| tiny-streaming-en | en | TINY_STREAMING | quantized_26_08_21 | strukturell unterstützt |
| small-streaming-ja | ja | SMALL_STREAMING | quantized_26_08_23 | strukturell unterstützt |
| tiny-streaming-ja | ja | TINY_STREAMING | quantized_26_08_23 | strukturell unterstützt |
| tiny-streaming-vi | vi | TINY_STREAMING | quantized_26_08_24 | strukturell unterstützt |
| tiny-streaming-zh | zh | TINY_STREAMING | quantized_26_08_24 | strukturell unterstützt |
| tiny-streaming-tl | tl | TINY_STREAMING | quantized_26_08_24 | strukturell unterstützt |

Deutsch/Small ist die praktisch validierte Standardkonfiguration. Alle weiteren Modelle einschließlich Tiny Deutsch sind nur strukturell unterstützt; in dieser Phase wurden keine Modelle/Audio heruntergeladen und keine neuen Inferenzmessungen durchgeführt. Deutsche N100-Messwerte nicht auf andere Modelle/Sprachen übertragen.

## Tests / Datenschutz

83 Unit-Tests bestanden, 0 fehlgeschlagen, 0 übersprungen. 30 statische Prüfungen bestanden. Release-Prüfung erfolgreich: Version 0.1.0, acht gepinnte Action-Referenzen, 13 Modelle/acht Sprachen, Publish deaktiviert. Realer PyYAML-Parser und Permissions-/Trigger-/Kontext-/Plattformprüfungen erfolgreich. Installierter Unraid-XML-Parser erfolgreich mit create_paths=false; erzeugter Docker-Befehl nicht ausgeführt. Syntax und Image-Defaults zusätzlich geprüft.

Erneute Prüfung des Kandidaten, aller aktuell getrackten/veröffentlichungsfähigen Dateien, der bestehenden Git-Historie und des neuen Berichts auf typische private Schlüssel, GitHub-/AWS-Token, JWT, lange Secret-Zuweisungen, private IP-Adressen, alte Projektnamen und unerwartete E-Mail-Adressen. Modelle/.validation/Testaudio/Archive/private Schlüssel nicht als Git-Dateien vorhanden. Absichtlich erhaltene E-Mail-Adressen in offiziellen ONNX-Runtime-ThirdPartyNotices sind rechtlich erforderliche Attributionen; Commit-Identitäten verwenden ausschließlich die gewählte GitHub-Noreply-Adresse. Keine privaten GitHub-/HA-Zugangsdaten in Bericht/Workflow. Der GITHUB_TOKEN-Ausdruck ist nur eine GitHub-Secret-Referenz, kein gespeicherter Tokenwert.

## Noch vor einer tatsächlichen GHCR-Veröffentlichung erforderlich

ghcr-release wurde inzwischen vom Benutzer manuell eingerichtet. Die erneute lesende GitHub-API-Prüfung bestätigt: Required reviewers mit marco-taylor, prevent_self_review=false, can_admins_bypass=false und Selected branches and tags mit genau Branch main und Tag-Muster v*. Keine Environment-Einstellungen durch den Agenten verändert. Laut Benutzer sind keine Environment-Secrets angelegt; der Workflow referenziert ausschließlich das automatisch bereitgestellte GITHUB_TOKEN. Kein PAT und kein zusätzliches Secret erforderlich.

Das konfigurierte Environment hält einen später tatsächlich aktivierten Publish-Job vor seinen Schritten bis zur Reviewer-Freigabe an. Da Self-Review erlaubt ist, kann marco-taylor eigene Läufe bewusst freigeben; Administrator-Bypass ist deaktiviert. Ein fehlendes Environment würde von GitHub möglicherweise automatisch ohne Schutzregeln angelegt: Die nun bestätigte Einrichtung ist deshalb eine bewusste Voraussetzung der späteren Veröffentlichung und vor Aktivierung erneut zu prüfen.

RELEASE_PUBLISH_ENABLED und weitere Actions-/Package-Einstellungen wurden nicht verändert. Bei späterer ausdrücklicher Veröffentlichungsfreigabe die Variable als Repository-Variable prüfen/einrichten; nicht allein auf eine erst im Job verfügbare Environment-Variable für die Job-if-Bedingung verlassen. Ihre aktuelle Einstellung ist wegen der unveränderten false-Sperre unerheblich.

Nur nach neuer ausdrücklicher Veröffentlichungsfreigabe: den jetzt eingerichteten Environment-Schutz nochmals bestätigen, Package-/Actions-Schreibzugriff sicherstellen, gewünschten ersten Ref/Tag ausdrücklich bestimmen, harte false-Sperre und die sie derzeit verlangenden Prüfungen gemeinsam gezielt anpassen und weitere Gates bewusst aktivieren. Ein Push dieser Aktivierung kann bereits Publish auslösen; deshalb kein Aktivierungs-Push ohne passende Veröffentlichungsfreigabe.

Laut [offizieller GHCR-Dokumentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry) unterstützt der repositoryeigene GITHUB_TOKEN die Veröffentlichung zugehöriger Pakete. Bereits vorhandene gleichnamige Pakete müssen dem Repository Zugriff gewähren. Neue Pakete sind zunächst privat: eine spätere öffentliche Package-Sichtbarkeit und anonymer Pull benötigen bewusste Einrichtung/Prüfung, kein Automatismus aus einem öffentlichen Git-Repository. Weder Package-ACL noch Sichtbarkeit wurde hier geändert.

Nach späterem erlaubtem Build tatsächlichen Digest/Größe/Plattform/Labels und Modellfreiheit des GHCR-Artefakts prüfen. Erst danach separat freigegebenen anonymen Pull/isolierten Containertest erwägen. Kein Icon fertiggestellt, keine CA-Veröffentlichung vorbereitet ausgeführt, keine Releases/Tags erstellt.

## Ergebnis

Workflow und Projekt sind für den nächsten ausdrücklich freizugebenden GHCR-Schritt lokal vorbereitet und geprüft. Alle Publish-Gates bleiben geschlossen. Lokale Änderungen nicht committet oder gepusht. Keine Veröffentlichung in Phase 9B. Auf ausdrückliche Freigabe warten.

## Abschließender lokaler Stand

88 veröffentlichungsfähige Dateien einschließlich dieses neuen Berichts und beide bestehenden Commits wurden geprüft; null Secret-/Datenschutzfunde. Git-Index unverändert, kein neuer Commit. Auf main gibt es zwei geänderte getrackte Dateien (Workflow-Kommentar und Template-Status) sowie diesen neuen untracked Bericht. HEAD/origin/main bleiben 78f047a4e49a215bc8f3057756546d6ba1c8fc78. Normales git diff --stat: zwei Dateien, vier Einfügungen, drei Löschungen; der untracked Bericht wird dort noch nicht mitgezählt.
