"""Read-only public release checks; no Docker, remote or Git mutations."""
import json
import os
from pathlib import Path
import re
import tomllib
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def check():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert metadata["project"]["name"] == "moonshine-stt-wyoming"
    assert metadata["project"]["license"] == "Apache-2.0"
    version = metadata["project"]["version"]
    ref = os.environ.get("GITHUB_REF", "")
    if ref.startswith("refs/tags/v"):
        assert ref == "refs/tags/v" + version, "Tag must match package version"
    workflow = (ROOT / ".github/workflows/docker-publish.yml").read_text()
    actions = re.findall(r"uses:\s+([^\s@]+)@([^\s#]+)", workflow)
    assert actions and all(re.fullmatch(r"[a-f0-9]{40}", sha) for _, sha in actions)
    assert re.search(r"if:\s*>-\s+false\s*&&", workflow), "Phase 9A GHCR guard missing"
    assert "vars.RELEASE_PUBLISH_ENABLED == 'true'" in workflow
    assert "environment: ghcr-release" in workflow
    assert "github.event_name != 'pull_request'" in workflow
    assert "persist-credentials: false" in workflow
    assert "${{ secrets.GITHUB_TOKEN }}" in workflow
    assert "pull_request_target" not in workflow
    assert "IMAGE_NAME: ghcr.io/marco-taylor/moonshine-stt-wyoming" in workflow
    assert "type=ref,event=tag" in workflow and "flavor: latest=false" in workflow
    template = ET.parse(ROOT / "templates/moonshine-stt-wyoming.xml").getroot()
    assert template.findtext("Repository") == "ghcr.io/marco-taylor/moonshine-stt-wyoming:latest"
    assert template.findtext("License") == "Apache-2.0"
    assert template.findtext("Privileged") == "false"
    for tag in ("Registry", "Project", "Support", "ReadMe", "TemplateURL"):
        assert "marco-taylor/moonshine-stt-wyoming" in template.findtext(tag)
    assert not template.findtext("Icon"), "Do not invent an unvalidated icon URL"
    catalog = json.loads((ROOT / "src/moonshine_stt_wyoming/model-manifest.json").read_text())
    assert catalog["default_model"] == "small-streaming-de"
    assert len(catalog["models"]) == 13
    assert len({s["language"] for s in catalog["models"].values()}) == 8
    for filename in ("LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md"):
        assert (ROOT / filename).stat().st_size > 100
    docker = (ROOT / "Dockerfile").read_text()
    assert 'org.opencontainers.image.licenses="Apache-2.0"' in docker
    assert "COPY licenses /usr/share/licenses/" in docker
    assert "tiny-en/tokenizer.bin" in (ROOT / "build-support/prune_runtime.py").read_text()
    return {"passed": True, "version": version, "pinned_action_references": len(actions),
            "models": 13, "languages": 8, "publication_enabled_by_default": False}


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
