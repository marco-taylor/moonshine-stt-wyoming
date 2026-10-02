# Third-party notices and distribution licenses

The project wrapper is Apache-2.0; upstream components retain their own terms.
The image retains all installed wheel license/NOTICE files and base-image notices.
No speech models are distributed inside the image or repository.

## Pinned Python runtime packages

| Package | Version | Official wheel license expression |
| --- | --- | --- |
| moonshine-voice | 0.1.5 | MIT |
| wyoming | 1.10.2 | MIT |
| numpy | 2.5.3 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| sounddevice | 0.5.6 | MIT |
| requests | 2.34.2 | Apache-2.0 |
| tqdm | 4.70.1 | MPL-2.0 AND MIT |
| filelock | 4.0.8 | MIT |
| platformdirs | 4.12.2 | MIT |
| google-crc32c | 1.9.0 | Apache-2.0 |
| cffi | 2.1.1 | MIT-0 |
| pycparser | 3.0 | BSD-3-Clause |
| charset-normalizer | 3.5.2 | MIT |
| idna | 3.20 | BSD-3-Clause |
| urllib3 | 2.8.0 | MIT |
| certifi | 2026.7.22 | MPL-2.0 |

The license expressions above were read from the actually installed, hash-pinned
official wheel metadata, not inferred from package names. Full texts are retained
in each distribution's .dist-info/licenses directory in /opt/runtime. The requests
NOTICE and nested NumPy bundled-library licenses are also retained. Build-only
setuptools/wheel/packaging remain in the build stage, outside the final application
runtime; the Python base image may contain its own pip/build-package components.

## Moonshine code, native libraries and models

The official v0.1.5 license states that all streaming STT models in every language
and size are MIT. All 13 registered models fall into that class. Non-English
legacy non-streaming models have different Community License terms and are not
supported by this service. Do not apply a blanket MIT claim to every upstream asset.
Full official text: licenses/upstream/moonshine-0.1.5-LICENSE.txt.

The native Moonshine library includes separately licensed third-party code.
The official v0.1.5 source/build definitions and notices identify Eigen (MPL-2.0,
MPL-only build subset), kaldi-native-fbank (Apache-2.0), kissfft (BSD-3-Clause),
nlohmann/json (MIT), utf8cpp (BSL-1.0), utf8proc (MIT plus Unicode data terms),
and ONNX Runtime (MIT plus its third-party notices). Doctest's MIT license is
included conservatively although its test code is not part of our server.
Corresponding full notices are under licenses/upstream/, with provenance and
SHA256 in licenses/sources.json.

The actual ORT version returned by OrtGetApiBase/GetVersionString from the
installed Moonshine libmoonshine.so is 1.23.2. Its official ThirdPartyNotices.txt
is included, rather than assuming the main Moonshine MIT notice covers ORT's
entire dependency tree. The native libraries and wheel code are unmodified.
Only unused demo WAVs, agent embeddings and the demo tiny-en tokenizer are omitted;
this is stated in NOTICE and the wheel RECORD is updated.

Corresponding upstream source for unmodified bundled components:
- https://github.com/moonshine-ai/moonshine/tree/v0.1.5/core/third-party
- https://github.com/microsoft/onnxruntime/tree/v1.23.2
- https://github.com/numpy/numpy/tree/v2.5.3
- https://github.com/certifi/python-certifi
- https://github.com/tqdm/tqdm

## Python and operating-system base

CPython 3.12.14 uses the PSF license and historical/third-party notices, not the
application's Apache license. The Debian Bookworm base contains components under
several licenses, including GPL/LGPL and permissive licenses. Their standard
/usr/share/doc copyright notices and CPython license are retained; no base-image
license cleanup is performed. Source and distribution terms remain those of
Python, Debian and the component maintainers.
- https://www.python.org/downloads/release/python-31214/
- https://docs.python.org/3.12/license.html
- https://www.debian.org/legal/licenses/
- https://sources.debian.org/

This inventory records evidence and preserves notices; it does not promise that
every future upstream release has the same terms. A publisher must review the
exact artifact, source-availability obligations, and any future dependency change
before publication. No distribution or publication was performed in Phase 8.
