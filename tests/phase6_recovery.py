"""Container-only crash-once fixture; never run this script on the host.

First start launches the real server, then exits PID 1 with 42 after 15 seconds.
A persistent test-only marker makes the next start exec the normal server.
This is not a production process manager and is never copied into the image.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

marker = Path("/recovery/crash-once.json")
command = [sys.executable, "-m", "moonshine_stt_wyoming"]
if not marker.parent.is_dir():
    raise SystemExit("Container-only fixture requires explicit /recovery test mount")
if marker.exists():
    os.execv(sys.executable, command)
with marker.open("x") as stream:
    json.dump({"intentional_first_exit": 42}, stream)
child = subprocess.Popen(command)
print("PHASE6 intentional crash in 15 seconds; next start uses normal server", flush=True)
time.sleep(15)
if child.poll() is not None:
    raise SystemExit("Server failed before intentional recovery test")
os._exit(42)
