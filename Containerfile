FROM python:3.12.14-slim-bookworm@sha256:0f5b26b9518d002b6173fd61daad821fa340635ebfec5bba471013f9ca114579

ARG FFMPEG_VERSION=7:5.1.9-0+deb12u1

LABEL org.opencontainers.image.title="PyFFmpegCore"
LABEL org.opencontainers.image.description="Safe, explainable FFmpeg task runner for terminal and CI workflows"
LABEL org.opencontainers.image.source="https://github.com/OthmaneBlial/pyffmpegcore"
LABEL org.opencontainers.image.documentation="https://othmaneblial.github.io/pyffmpegcore/"
LABEL org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        ca-certificates \
        "ffmpeg=${FFMPEG_VERSION}" \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --create-home --home-dir /home/pyffmpegcore pyffmpegcore \
    && mkdir -p /workspace \
    && chown pyffmpegcore:pyffmpegcore /workspace

COPY . /opt/pyffmpegcore
RUN python -m pip install /opt/pyffmpegcore \
    && pyffmpegcore --version \
    && ffmpeg -version | head -n 1

WORKDIR /workspace
USER 10001:10001

ENTRYPOINT ["pyffmpegcore"]
CMD ["--help"]
