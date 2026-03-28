#!/usr/bin/env bash

set -euo pipefail

PACKAGE_SPEC="${PYFFMPEGCORE_PACKAGE_SPEC:-pyffmpegcore}"
INSTALL_METHOD="auto"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SKIP_DOCTOR=0

usage() {
  cat <<'EOF'
Install PyFFmpegCore as a terminal command on Linux or macOS.

Usage:
  ./install.sh [options]

Options:
  --method auto|pipx|pip   Choose the install method. Defaults to auto.
  --spec VALUE             Package spec to install. Defaults to pyffmpegcore.
  --python VALUE           Python executable to use for pip installs.
  --skip-doctor            Skip the final pyffmpegcore doctor check.
  --help                   Show this help text.

Environment overrides:
  PYFFMPEGCORE_PACKAGE_SPEC
  PYTHON_BIN

Examples:
  ./install.sh
  ./install.sh --method pipx
  PYFFMPEGCORE_PACKAGE_SPEC=. ./install.sh --method pip
EOF
}

log() {
  printf '%s\n' "$1"
}

warn() {
  printf 'Warning: %s\n' "$1" >&2
}

die() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

run_pipx_install() {
  if ! command_exists pipx; then
    die "pipx is not installed. Re-run with --method pip or install pipx first."
  fi

  log "Installing ${PACKAGE_SPEC} with pipx"
  pipx install --force "$PACKAGE_SPEC"
}

run_pip_install() {
  if ! command_exists "$PYTHON_BIN"; then
    die "Python executable not found: ${PYTHON_BIN}"
  fi

  log "Installing ${PACKAGE_SPEC} with ${PYTHON_BIN} -m pip --user"
  "$PYTHON_BIN" -m pip install --user --upgrade "$PACKAGE_SPEC"
}

verify_install() {
  if command_exists pyffmpegcore; then
    pyffmpegcore --version
    if [[ "$SKIP_DOCTOR" -eq 0 ]]; then
      pyffmpegcore doctor || true
    fi
    return 0
  fi

  warn "pyffmpegcore is not on PATH yet."
  warn "Try opening a new shell or add your user Python bin directory to PATH."
  if command_exists "$PYTHON_BIN"; then
    "$PYTHON_BIN" -m pyffmpegcore --version || true
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --method)
      [[ $# -ge 2 ]] || die "--method requires a value"
      INSTALL_METHOD="$2"
      shift 2
      ;;
    --spec)
      [[ $# -ge 2 ]] || die "--spec requires a value"
      PACKAGE_SPEC="$2"
      shift 2
      ;;
    --python)
      [[ $# -ge 2 ]] || die "--python requires a value"
      PYTHON_BIN="$2"
      shift 2
      ;;
    --skip-doctor)
      SKIP_DOCTOR=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      die "Unknown option: $1"
      ;;
  esac
done

case "$(uname -s)" in
  Linux|Darwin)
    ;;
  *)
    die "install.sh is for Linux and macOS. On Windows use install.ps1 instead."
    ;;
esac

case "$INSTALL_METHOD" in
  auto)
    if command_exists pipx; then
      INSTALL_METHOD="pipx"
    else
      INSTALL_METHOD="pip"
    fi
    ;;
  pipx|pip)
    ;;
  *)
    die "Unsupported --method value: ${INSTALL_METHOD}"
    ;;
esac

if [[ "$INSTALL_METHOD" == "pipx" ]]; then
  run_pipx_install
else
  run_pip_install
fi

verify_install
