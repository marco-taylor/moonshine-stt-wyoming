# Phase 9A: GitHub-Quellcodeveröffentlichung

Status: lokale Prüfungen erfolgreich; Veröffentlichung noch ausstehend. Das Zielrepository ist über den authentifizierten GitHub-Zugang nicht auffindbar (404). Die vorhandenen Connector-Werkzeuge unterstützen keine Repository-Erstellung. Eine lokale GitHub-CLI ist nicht installiert. Die bestehende SSH-Anmeldung ist nachweislich ein Deploy-Key ausschließlich für Kikiri; sie wird weder geändert noch für Moonshine umgewidmet. Für den normalen Git-Push fehlt damit zusätzlich ein eigener schreibberechtigter Zugang zum neuen Moonshine-Repository. Der Benutzer wurde um ein leeres öffentliches Zielrepository gebeten; keine Zugangsdaten angefordert oder ausgegeben.

## Ziel und Grenzen

Projekt moonshine-stt-wyoming, Python-Paket moonshine_stt_wyoming, Version 0.1.0.
Ziel: https://github.com/marco-taylor/moonshine-stt-wyoming, Hauptbranch main.
Nur GitHub-Quellcode freigegeben. GHCR, GitHub Release, Veröffentlichungstags und Community Applications gesperrt. Kein anderer Dienst oder Repository verändert.

## Änderungen

- ./moonshine-stt-wyoming/.gitignore und ./moonshine-stt-wyoming/.dockerignore: Export-/Archivdateien und weitere lokale Authentifizierungsdateien zusätzlich ausgeschlossen.
- ./moonshine-stt-wyoming/.github/workflows/docker-publish.yml: GHCR-Publish explizit mit false && gesperrt. Selbst eine schon vorhandene RELEASE_PUBLISH_ENABLED-Variable kann keinen Push erlauben. main/PR löst höchstens Validierung mit push:false aus. GHCR-Job kann erst nach Phase-9B-Freigabe geändert werden.
- ./moonshine-stt-wyoming/tests/release_checks.py und ./moonshine-stt-wyoming/tests/validate_workflow.py prüfen die ausdrückliche Sperre.
- ./moonshine-stt-wyoming/README.md: öffentlicher Zweck, Docker-Build/Installation aus Quellcode; GHCR/CA ausdrücklich noch nicht verfügbar, interne Entwicklungsformulierungen entfernt.
- ./moonshine-stt-wyoming/docs/release.md: Status/Gates für reine Quellcodeveröffentlichung aktualisiert.
- ./moonshine-stt-wyoming/docs/unraid-installation.md: ortsspezifische Formulierungen und Links auf nicht veröffentlichte historische Berichte entfernt.
- ./moonshine-stt-wyoming/docs/phase9a-github-publication.md: dieser Bericht.

## Sicherheit, Datenschutz und Größe

Erster Kandidat: 86 Dateien, 650.848 Bytes vor Phase-9A-Anpassungen. Größte Datei: offizielle ONNX-Runtime-ThirdPartyNotices, 326.866 Bytes. Keine unerwartet großen Dateien; keine Datei über 1 MiB. Der Bericht ergänzt eine Datei; endgültige Größe und Liste werden vor Commit nochmals überprüft.

Prüfung sämtlicher Kandidat-Dateien und Git-Index auf private Schlüssel, GitHub-/AWS-Tokenmuster, JWT, lange Passwort-/Tokenzuweisungen, private IP-Adressen und alte Projekt-/Paketnamen: keine Treffer. E-Mail-Adressen ausschließlich in offiziellen, bewusst erhaltenen Copyright-/Lizenzattributionen. GitHub-Noreply-Adresse ist die ausdrücklich gewählte öffentliche Commit-Identität, keine private Adresse. Keine Home-Assistant-Konfiguration gelesen.

.gitignore und .dockerignore schließen .validation, .venv, Modelle/Modelldateien, Testaudio, Caches, temporäre Daten, Benchmarkdaten, Buildartefakte und typische private Schlüssel-/Secretdateien aus. Historische ortsspezifische Entwicklungsberichte bleiben lokal und sind nicht Teil des Kandidaten. Docker-Kontext schließt zudem Tests/Dokumentation/Templates aus, sofern nicht für Runtime erforderlich. Lizenzhinweise bleiben bewusst erhalten. Keine Modelldateien, .validation oder Testaudiodateien im Git-Index.

## Release-Dateien / Tests

README, LICENSE/NOTICE/THIRD_PARTY_NOTICES, Dockerfile, pyproject, zentraler Modellkatalog, Workflow, Template und Dokumentation geprüft. Apache-2.0 für eigene Anwendung; MIT für registrierte Streaming-Modelle und Moonshine Voice/Wyoming, vollständige native Hinweise erhalten. 13 Streaming-Modelle für acht Sprachen bleiben registriert. Ausschließlich Deutsch/Small praktisch validiert; andere Modelle/Sprachen nur strukturell unterstützt. Defaults Small/de, Threads1, Auto1, /app/models, Wyoming10300, Concurrent1 unverändert.

83 Unit-Tests bestanden, 0 fehlgeschlagen, 0 übersprungen. 30 statische Prüfungen bestanden. Sowohl Projekt als auch unabhängiger Kandidat geprüft. Workflow real mit PyYAML 6.0.3 geparst, ausdrückliche GHCR-Sperre validiert. Kein STT-Benchmark, Modelldownload, Docker-Build oder neuer lokaler Container in Phase 9A.

## Git-Identität / Commit / Remote

Identität: marco-taylor mit der bereits im Kikiri-Projekt verwendeten GitHub-Noreply-Adresse, die zum bestätigten GitHub-Konto gehört. Identität nur für den neuen Repository-Kandidaten verwenden; keine globale Git-Konfiguration oder Kikiri-Konfiguration ändern. Branch main, normaler Commit und Push, kein Force-Push/History-Rewrite. Commit-ID und tatsächlicher Push-Status folgen nach Repository-Bereitstellung.

## Öffentliche Nachprüfung / GHCR

Noch ausstehend: öffentliches Repository, Darstellung der README, Remote-Dateibaum/Commitvergleich und Workflow-Status. Noch kein GitHub-Push durchgeführt und kein GHCR-Image in Phase 9A veröffentlicht. GHCR-Job dauerhaft false bis gesonderter Freigabe. Keine GitHub Releases/Tags/Assets/CA-Einreichung.

## Vorgesehene veröffentlichte Dateien

Vollständige geplante Liste; endgültig mit Git-Index/Remote abzugleichen:

```text
./moonshine-stt-wyoming/.dockerignore
./moonshine-stt-wyoming/.github/workflows/docker-publish.yml
./moonshine-stt-wyoming/.gitignore
./moonshine-stt-wyoming/.python-version
./moonshine-stt-wyoming/Dockerfile
./moonshine-stt-wyoming/LICENSE
./moonshine-stt-wyoming/NOTICE
./moonshine-stt-wyoming/README.md
./moonshine-stt-wyoming/THIRD_PARTY_NOTICES.md
./moonshine-stt-wyoming/build-support/prune_runtime.py
./moonshine-stt-wyoming/build-support/write_app_lock.py
./moonshine-stt-wyoming/config/defaults.env
./moonshine-stt-wyoming/config/dependency-manifest.json
./moonshine-stt-wyoming/config/model-manifest.json
./moonshine-stt-wyoming/docs/architecture.md
./moonshine-stt-wyoming/docs/benchmark-plan.md
./moonshine-stt-wyoming/docs/models.md
./moonshine-stt-wyoming/docs/phase9a-github-publication.md
./moonshine-stt-wyoming/docs/release.md
./moonshine-stt-wyoming/docs/unraid-installation.md
./moonshine-stt-wyoming/docs/versions.md
./moonshine-stt-wyoming/licenses/sources.json
./moonshine-stt-wyoming/licenses/upstream/Eigen-COPYING.MPL2
./moonshine-stt-wyoming/licenses/upstream/doctest-LICENSE.txt
./moonshine-stt-wyoming/licenses/upstream/kaldi-native-fbank-LICENSE.txt
./moonshine-stt-wyoming/licenses/upstream/kissfft-BSD-3-Clause.txt
./moonshine-stt-wyoming/licenses/upstream/kissfft-COPYING.txt
./moonshine-stt-wyoming/licenses/upstream/moonshine-0.1.5-LICENSE.txt
./moonshine-stt-wyoming/licenses/upstream/nlohmann-LICENSE.MIT
./moonshine-stt-wyoming/licenses/upstream/onnxruntime-1.23.2-ThirdPartyNotices.txt
./moonshine-stt-wyoming/licenses/upstream/onnxruntime-LICENSE.txt
./moonshine-stt-wyoming/licenses/upstream/utf8cpp-LICENSE.txt
./moonshine-stt-wyoming/licenses/upstream/utf8proc-LICENSE.md
./moonshine-stt-wyoming/pyproject.toml
./moonshine-stt-wyoming/requirements-build.lock
./moonshine-stt-wyoming/requirements-dev.lock
./moonshine-stt-wyoming/requirements.lock
./moonshine-stt-wyoming/src/moonshine_stt_wyoming/__init__.py
./moonshine-stt-wyoming/src/moonshine_stt_wyoming/__main__.py
./moonshine-stt-wyoming/src/moonshine_stt_wyoming/audio.py
./moonshine-stt-wyoming/src/moonshine_stt_wyoming/backends/__init__.py
./moonshine-stt-wyoming/src/moonshine_stt_wyoming/backends/base.py
./moonshine-stt-wyoming/src/moonshine_stt_wyoming/backends/moonshine_cpu.py
./moonshine-stt-wyoming/src/moonshine_stt_wyoming/config.py
./moonshine-stt-wyoming/src/moonshine_stt_wyoming/errors.py
./moonshine-stt-wyoming/src/moonshine_stt_wyoming/healthcheck.py
./moonshine-stt-wyoming/src/moonshine_stt_wyoming/integrity.py
./moonshine-stt-wyoming/src/moonshine_stt_wyoming/logging_config.py
./moonshine-stt-wyoming/src/moonshine_stt_wyoming/model-manifest.json
./moonshine-stt-wyoming/src/moonshine_stt_wyoming/model_download.py
./moonshine-stt-wyoming/src/moonshine_stt_wyoming/model_manager.py
./moonshine-stt-wyoming/src/moonshine_stt_wyoming/models.py
./moonshine-stt-wyoming/src/moonshine_stt_wyoming/protocol.py
./moonshine-stt-wyoming/src/moonshine_stt_wyoming/stt_service.py
./moonshine-stt-wyoming/src/moonshine_stt_wyoming/transport.py
./moonshine-stt-wyoming/src/moonshine_stt_wyoming/wyoming_server.py
./moonshine-stt-wyoming/templates/moonshine-stt-wyoming.xml
./moonshine-stt-wyoming/tests/inspect_phase4_rootfs.py
./moonshine-stt-wyoming/tests/phase6_recovery.py
./moonshine-stt-wyoming/tests/release_checks.py
./moonshine-stt-wyoming/tests/run.py
./moonshine-stt-wyoming/tests/static-checks.mjs
./moonshine-stt-wyoming/tests/support.py
./moonshine-stt-wyoming/tests/test_audio.py
./moonshine-stt-wyoming/tests/test_backend.py
./moonshine-stt-wyoming/tests/test_config.py
./moonshine-stt-wyoming/tests/test_lifecycle.py
./moonshine-stt-wyoming/tests/test_model_manager.py
./moonshine-stt-wyoming/tests/test_models.py
./moonshine-stt-wyoming/tests/test_multilanguage.py
./moonshine-stt-wyoming/tests/test_official_wyoming.py
./moonshine-stt-wyoming/tests/test_phase6_metrics.py
./moonshine-stt-wyoming/tests/test_protocol.py
./moonshine-stt-wyoming/tests/test_release.py
./moonshine-stt-wyoming/tests/test_runtime_api.py
./moonshine-stt-wyoming/tests/test_server.py
./moonshine-stt-wyoming/tests/test_transport.py
./moonshine-stt-wyoming/tests/test_unraid_template.py
./moonshine-stt-wyoming/tests/validate_model_management.py
./moonshine-stt-wyoming/tests/validate_phase3.py
./moonshine-stt-wyoming/tests/validate_phase4.py
./moonshine-stt-wyoming/tests/validate_phase6.py
./moonshine-stt-wyoming/tests/validate_phase7.py
./moonshine-stt-wyoming/tests/validate_phase7_5.py
./moonshine-stt-wyoming/tests/validate_shutdown.py
./moonshine-stt-wyoming/tests/validate_unraid_template.php
./moonshine-stt-wyoming/tests/validate_workflow.py
```

## Offene Punkte für Phase 9B

Erst GitHub-Veröffentlichung und öffentliche Nachprüfung abschließen. Danach neue ausdrückliche Freigabe für GHCR einholen; erst dann die harte Publish-Sperre gezielt entfernen, Schutz/Gates konfigurieren und Image-Veröffentlichung/Pull prüfen. Finales eigenes Icon und CA-Veröffentlichung bleiben separate Aufgaben/Freigaben.
