"""Development-only YAML parser/schema checks; no Actions execution or publication."""
import json
from pathlib import Path

import yaml

root = Path(__file__).resolve().parents[1]
workflow = yaml.load((root / ".github/workflows/docker-publish.yml").read_text(),
                     Loader=yaml.BaseLoader)
assert set(workflow["on"]) == {"push", "pull_request", "workflow_dispatch"}
assert workflow["permissions"] == {"contents": "read"}
assert workflow["jobs"]["publish"]["permissions"] == {"contents": "read", "packages": "write"}
assert workflow["jobs"]["publish"]["environment"] == "ghcr-release"
expected_condition = (
    "github.repository == 'marco-taylor/moonshine-stt-wyoming' && "
    "vars.RELEASE_PUBLISH_ENABLED == 'true' && "
    "github.event_name != 'pull_request' && "
    "(github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/v'))"
)
assert " ".join(workflow["jobs"]["publish"]["if"].split()) == expected_condition
assert "RELEASE_PUBLISH_ENABLED" in workflow["jobs"]["publish"]["if"]
assert "github.event_name != 'pull_request'" in workflow["jobs"]["publish"]["if"]
builds = [s for s in workflow["jobs"]["validate"]["steps"]
          if s.get("uses", "").startswith("docker/build-push-action@")]
assert len(builds) == 1 and builds[0]["with"]["push"] == "false"
assert builds[0]["with"]["platforms"] == "linux/amd64"
print(json.dumps({"passed": True, "parser": "PyYAML " + yaml.__version__,
                  "publish_requires_repository_opt_in": True,
                  "publish_requires_environment_review": True}, indent=2))
