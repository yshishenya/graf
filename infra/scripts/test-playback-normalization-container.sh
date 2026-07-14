#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

run_id="${PPID}-$$"
image_tag="graf-playback-normalization-capability:${run_id}"
container_name="graf-playback-normalization-capability-${run_id}"
run_label="graf.playback-normalization.capability=${run_id}"

cleanup() {
  docker rm --force "$container_name" >/dev/null 2>&1 || true
  docker image rm --force "$image_tag" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

docker build \
  --target media-runtime \
  --tag "$image_tag" \
  --file infra/server/Dockerfile \
  .

docker run --rm --interactive \
  --name "$container_name" \
  --label "$run_label" \
  --network none \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --pids-limit 128 \
  --memory 1g \
  --cpus 1 \
  --tmpfs /var/lib/twobrain-rec/playback-normalization:rw,noexec,nosuid,nodev,size=512m,mode=0700,uid=100,gid=101 \
  --entrypoint python \
  "$image_tag" \
  /app/scripts/verify_playback_normalization_runtime.py

cleanup
trap - EXIT INT TERM

container_residue_count="$(docker ps --all --quiet --filter "label=$run_label" | wc -l | tr -d ' ')"
image_residue_count="$(docker image ls --quiet "$image_tag" | wc -l | tr -d ' ')"
if [[ "$container_residue_count" != "0" || "$image_residue_count" != "0" ]]; then
  printf 'playback_normalization_container_result=fail\n' >&2
  printf 'container_residue_count=%s\n' "$container_residue_count" >&2
  printf 'image_residue_count=%s\n' "$image_residue_count" >&2
  exit 1
fi

printf 'playback_normalization_container_result=pass\n'
printf 'container_residue_count=0\n'
printf 'image_residue_count=0\n'
