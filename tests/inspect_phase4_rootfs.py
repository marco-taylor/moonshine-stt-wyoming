"""Read a Docker-export tar stream without extracting or altering files."""
import json
import sys
import tarfile

files = []
with tarfile.open(fileobj=sys.stdin.buffer, mode="r|*") as archive:
    for member in archive:
        if member.isfile():
            files.append((member.name.lstrip("./"), member.size))

report = {
    "regular_file_bytes": sum(size for name, size in files),
    "runtime_bytes": sum(size for name, size in files if name.startswith("opt/runtime/")),
    "largest_files": sorted(files, key=lambda item: item[1], reverse=True)[:20],
    "model_artifacts": [name for name, size in files
                        if name.endswith((".ort", ".onnx", "/tokenizer.bin")) or name.startswith("app/models/")],
    "audio_assets": [name for name, size in files if name.endswith((".wav", ".flac", ".mp3"))],
    "development_artifacts": [name for name, size in files
                              if "/.venv/" in name or "/.cache/pip/" in name
                              or name.startswith(("app/tests/", "app/docs/"))],
    "compiler_or_git": [name for name, size in files
                        if name in ("usr/bin/gcc", "usr/bin/g++", "usr/bin/git")],
    "headers_bytes": sum(size for name, size in files
                         if name.startswith("usr/local/include/")
                         or name.startswith("opt/runtime/numpy/_core/include/")),
    "build_package_files": [name for name, size in files
                            if name.startswith(("opt/runtime/setuptools/", "opt/runtime/wheel/",
                                                "opt/runtime/packaging/"))],
}
assert not report["model_artifacts"]
assert not report["audio_assets"]
assert not report["development_artifacts"]
assert not report["compiler_or_git"]
assert not report["build_package_files"]
print(json.dumps(report, indent=2))
