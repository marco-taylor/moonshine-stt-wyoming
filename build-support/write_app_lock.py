"""Build-stage only: include the locally built application in hash-enforced install."""
import hashlib
from pathlib import Path

wheels = list(Path("/opt/wheels").glob("moonshine_stt_wyoming-*.whl"))
if len(wheels) != 1:
    raise RuntimeError("Exactly one application wheel is required")
wheel = wheels[0]
Path("/opt/application.lock").write_text(
    str(wheel) + " --hash=sha256:" + hashlib.sha256(wheel.read_bytes()).hexdigest() + "\n"
)
