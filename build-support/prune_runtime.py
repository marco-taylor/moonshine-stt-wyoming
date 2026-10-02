"""Build-stage only: omit upstream demo audio and optional agent embeddings.

No STT code, native library, license or dependency is removed. Update RECORD so
the installed distribution describes the specialized runtime accurately.
"""
import csv
from pathlib import Path

root = Path("/opt/runtime")
assets = root / "moonshine_voice/assets"
names = ("beckett.wav", "clone-test.wav", "endgame_nagg_nell.wav", "error.wav",
         "success.wav", "two_cities.wav", "cached_embeddings.tsv", "tiny-en/tokenizer.bin")
removed = {"moonshine_voice/assets/" + name for name in names}
total = 0
for name in names:
    file = assets / name
    total += file.stat().st_size
    file.unlink()
record = root / "moonshine_voice-0.1.5.dist-info/RECORD"
with record.open(newline="") as stream:
    rows = [row for row in csv.reader(stream) if row[0] not in removed]
with record.open("w", newline="") as stream:
    csv.writer(stream).writerows(rows)
print(f"Omitted {len(names)} upstream demo assets: {total} bytes")
