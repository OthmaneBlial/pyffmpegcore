FROM python:3.12-slim-trixie@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9

ARG FFMPEG_VERSION=7:7.1.5-0+deb13u1

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
    && apt-get upgrade --yes \
    && apt-get install --yes --no-install-recommends \
        ca-certificates \
        "ffmpeg=${FFMPEG_VERSION}" \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --create-home --home-dir /home/pyffmpegcore pyffmpegcore \
    && mkdir -p /workspace \
    && chown pyffmpegcore:pyffmpegcore /workspace

COPY . /opt/pyffmpegcore
RUN python -m pip install --only-binary=:all: --require-hashes -r /opt/pyffmpegcore/container-requirements.txt \
    && python -m pip install --no-index --no-deps --no-build-isolation /opt/pyffmpegcore \
    && rm -rf /opt/pyffmpegcore \
    && python -m pip uninstall --yes packaging setuptools wheel pip \
    && pyffmpegcore --version \
    && ffmpeg -version | head -n 1

WORKDIR /workspace
USER 10001:10001

ENTRYPOINT ["pyffmpegcore"]
CMD ["--help"]
