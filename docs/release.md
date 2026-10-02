# Release preparation and publication gates

Source repository: marco-taylor/moonshine-stt-wyoming.
Planned image: ghcr.io/marco-taylor/moonshine-stt-wyoming.
Version: 0.1.0. Source-only publication; no GHCR image, GitHub Release or CA submission.

The workflow under .github/workflows/docker-publish.yml follows Kikiri's main/v*
tags and GITHUB_TOKEN authentication. Actions are pinned to official release commit
SHAs. Pull requests and default runs only validate/build locally on the runner.
Phase 9A hard-disables the publish job with false &&. Only after separate GHCR
approval may this guard be removed. The remaining gate then requires
repository variable RELEASE_PUBLISH_ENABLED to be
exactly true, the repository name matches, and the ref is main or a v* tag.
It uses the ghcr-release environment, which should have required reviewers and branch
restrictions configured only after separate publication approval. No personal access
token is needed or stored. packages:write is limited to the publish job.

latest is produced only from main; tag pushes retain the exact v* version tag.
A tag must match the application version. Configure package visibility and test
anonymous pulls after the first separately approved GHCR publication.

Local checks: tests/run.py, tests/static-checks.mjs and tests/release_checks.py.
The installed-Unraid PHP parser test is local only and is not run on GitHub runners.
Runtime tests in CI use the pinned built image without model downloads. YAML syntax can be checked locally with the development-only PyYAML pin in
requirements-dev.lock and tests/validate_workflow.py; it is not a runtime dependency.
Real audio
and release-container checks are documented locally, outside the public candidate.

## Public source inventory

Site-specific historical phase reports, config/phase5-* and all .validation,
model/audio/cache/venv/benchmark artifacts are excluded from Git. Historical files
remain local, unmodified except normal project documentation updates. The public
candidate is checked without deleting these records. Do not force-add ignored data.

## Unraid / Community Applications

The template has planned image, registry, project, support, README and TemplateURL
links, Apache-2.0, AI/HomeAutomation categories and the validated CPU defaults.
GitHub source links become available with source publication; GHCR and CA remain
unpublished. No template was installed.
An original icon is still required before CA submission. Concept: simple microphone
and waveform, no borrowed Moonshine/HA logos or foreign graphics. No image was copied
or generated and the Icon field remains empty, rather than pointing at a missing file.

Review all upstream notices and source-availability obligations for the exact image
before distribution. LICENSE/NOTICE and full supplemental native-library notices are
retained in /usr/share/licenses/moonshine-stt-wyoming; official wheel notices and
base-image copyright files remain available as well.

GHCR publication, GitHub Releases and Community Applications submission remain
separately gated. The source-publication approval does not permit enabling the
GHCR publication job.
