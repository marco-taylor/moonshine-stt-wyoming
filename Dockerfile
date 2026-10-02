# Reproducible CPU runtime; model artifacts are provisioned only in the persistent mount.
FROM --platform=linux/amd64 python:3.12.14-slim-bookworm@sha256:1aaa65a85fda306ffb8b910824d4e93bdce61e212c7e87168123ea3073b41a1a AS build
ENV PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1 SOURCE_DATE_EPOCH=1790812800
WORKDIR /app
COPY requirements-build.lock requirements.lock pyproject.toml README.md LICENSE NOTICE /app/
COPY src /app/src
COPY build-support /app/build-support
RUN python -m pip install --no-cache-dir --only-binary=:all: --require-hashes -r requirements-build.lock \
    && python -m pip wheel --no-cache-dir --no-deps --no-build-isolation --wheel-dir /opt/wheels /app \
    && python /app/build-support/write_app_lock.py \
    && python -m pip install --no-cache-dir --only-binary=:all: --require-hashes --no-compile --target=/opt/runtime -r requirements.lock -r /opt/application.lock \
    && python /app/build-support/prune_runtime.py

FROM --platform=linux/amd64 python:3.12.14-slim-bookworm@sha256:1aaa65a85fda306ffb8b910824d4e93bdce61e212c7e87168123ea3073b41a1a
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/opt/runtime PATH=/opt/runtime/bin:$PATH HOME=/app \
    MOONSHINE_LANGUAGE=de MOONSHINE_MODEL=small-streaming-de STT_DEVICE=cpu \
    WYOMING_HOST=0.0.0.0 WYOMING_PORT=10300 MOONSHINE_MODEL_DIR=/app/models \
    MOONSHINE_AUTO_DOWNLOAD=1 MOONSHINE_THREADS=1 WYOMING_STT_CONCURRENT_REQUESTS=1 MAX_AUDIO_SECONDS=30 \
    LOG_LEVEL=INFO LOG_TRANSCRIPTS=false
LABEL org.opencontainers.image.title="moonshine-stt-wyoming" \
      org.opencontainers.image.source="https://github.com/marco-taylor/moonshine-stt-wyoming" \
      org.opencontainers.image.url="https://github.com/marco-taylor/moonshine-stt-wyoming" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.licenses="Apache-2.0"
WORKDIR /app
COPY LICENSE NOTICE THIRD_PARTY_NOTICES.md /usr/share/licenses/moonshine-stt-wyoming/
COPY licenses /usr/share/licenses/moonshine-stt-wyoming/upstream/
COPY --from=build /opt/runtime /opt/runtime
# No microphone source: upstream MicTranscriber/sounddevice imports are lazy.
RUN mkdir -p /app/models && chown 65532:65532 /app/models
USER 65532:65532
EXPOSE 10300/tcp
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ["python", "-m", "moonshine_stt_wyoming.healthcheck"]
ENTRYPOINT ["python", "-m", "moonshine_stt_wyoming"]
