#!/usr/bin/env bash
set -euo pipefail

fail() {
  printf 'pyffmpegcore-action: %s\n' "$1" >&2
  exit 2
}

require_workspace_path() {
  local value="$1"
  local label="$2"
  local allow_glob="${3:-false}"
  local segment
  local -a path_segments
  local checked="$workspace"
  local wildcard=false
  [[ -n "$value" ]] || fail "$label must not be empty"
  [[ "$value" != /* ]] || fail "$label must be relative to GITHUB_WORKSPACE"
  [[ "$value" != *$'\n'* && "$value" != *$'\r'* ]] || fail "$label must be a single path"
  IFS='/' read -r -a path_segments <<< "$value"
  for segment in "${path_segments[@]}"; do
    [[ -n "$segment" && "$segment" != "." && "$segment" != ".." ]] \
      || fail "$label must stay inside GITHUB_WORKSPACE"
    if [[ "$segment" == *'*'* || "$segment" == *'?'* || "$segment" == *'['* ]]; then
      [[ "$allow_glob" == true ]] || fail "$label must not contain a glob"
      wildcard=true
    fi
    if [[ "$wildcard" == false ]]; then
      checked="$checked/$segment"
      [[ ! -L "$checked" ]] || fail "$label must not contain a symbolic link"
    fi
  done
  if [[ "$allow_glob" == true ]]; then
    [[ "$checked" != "$workspace" ]] || fail "$label needs a literal directory prefix"
    if [[ -e "$checked" ]] && [[ -n "$(find "$checked" -type l -print -quit)" ]]; then
      fail "$label must not include symbolic links"
    fi
  fi
}

workspace="$(cd -P -- "${GITHUB_WORKSPACE:?GITHUB_WORKSPACE is required}" && pwd)"
readonly workspace
readonly image="${PYFFMPEGCORE_ACTION_IMAGE:?PYFFMPEGCORE_ACTION_IMAGE is required}"
readonly pipeline="${PYFFMPEGCORE_ACTION_PIPELINE:?PYFFMPEGCORE_ACTION_PIPELINE is required}"
readonly receipt_dir="${PYFFMPEGCORE_ACTION_RECEIPT_DIR:-.pyffmpegcore/receipts}"
readonly state="${PYFFMPEGCORE_ACTION_STATE:-.pyffmpegcore/pipeline-state.json}"
readonly events="${PYFFMPEGCORE_ACTION_EVENTS:-.pyffmpegcore/pipeline-events.jsonl}"
readonly result="${PYFFMPEGCORE_ACTION_RESULT:-.pyffmpegcore/pipeline-result.json}"
readonly variables="${PYFFMPEGCORE_ACTION_VARIABLES:-}"
readonly resume="${PYFFMPEGCORE_ACTION_RESUME:-true}"
readonly force="${PYFFMPEGCORE_ACTION_FORCE:-true}"
readonly network="${PYFFMPEGCORE_ACTION_NETWORK:-none}"
readonly artifacts="${PYFFMPEGCORE_ACTION_ARTIFACTS:-}"

[[ "$image" =~ ^ghcr\.io/othmaneblial/pyffmpegcore@sha256:[0-9a-f]{64}$ ]] \
  || fail "container image must be the official GHCR image pinned by sha256 digest"
[[ "$resume" == "true" || "$resume" == "false" ]] || fail "resume must be true or false"
[[ "$force" == "true" || "$force" == "false" ]] || fail "force must be true or false"
[[ "$network" == "none" || "$network" == "bridge" ]] || fail "network must be none or bridge"
require_workspace_path "$pipeline" "pipeline"
require_workspace_path "$receipt_dir" "receipt-dir"
require_workspace_path "$state" "state"
require_workspace_path "$events" "events"
require_workspace_path "$result" "result"
[[ -f "$workspace/$pipeline" ]] || fail "pipeline does not exist: $pipeline"
while IFS= read -r artifact || [[ -n "$artifact" ]]; do
  [[ -z "$artifact" ]] && continue
  require_workspace_path "$artifact" "artifacts" true
done <<< "$artifacts"

[[ "${1:-}" == "--validate-only" ]] && exit 0
[[ $# == 0 ]] || fail "unknown action-script argument"
command -v docker >/dev/null 2>&1 || fail "docker is required on the runner"

mkdir -p \
  "$workspace/$receipt_dir" \
  "$(dirname "$workspace/$state")" \
  "$(dirname "$workspace/$events")" \
  "$(dirname "$workspace/$result")"

docker_arguments=(
  run
  --rm
  --user "$(id -u):$(id -g)"
  --network "$network"
  --volume "$workspace:/workspace"
  --workdir /workspace
)
pipeline_arguments=(
  pipeline run "$pipeline"
  --receipt-dir "$receipt_dir"
  --state "$state"
  --events "$events"
  --result-json
)

while IFS= read -r variable_name || [[ -n "$variable_name" ]]; do
  variable_name="${variable_name%$'\r'}"
  [[ -z "$variable_name" ]] && continue
  [[ "$variable_name" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] \
    || fail "invalid environment variable name: $variable_name"
  printenv "$variable_name" >/dev/null \
    || fail "declared environment variable is not set: $variable_name"
  docker_arguments+=(--env "$variable_name")
  pipeline_arguments+=(--var "$variable_name")
done <<< "$variables"

[[ "$resume" == "true" ]] && pipeline_arguments+=(--resume)
[[ "$force" == "true" ]] && pipeline_arguments+=(--force)

docker "${docker_arguments[@]}" "$image" "${pipeline_arguments[@]}" > "$workspace/$result"
