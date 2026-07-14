#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

run_id="${PPID}-$$"
image_tag="graf-playback-normalization-performance:${run_id}"
container_name="graf-playback-normalization-performance-${run_id}"
volume_name="graf-playback-normalization-performance-${run_id}"
run_label="graf.playback-normalization.performance=${run_id}"

cleanup() {
  docker rm --force "$container_name" >/dev/null 2>&1 || true
  docker volume rm --force "$volume_name" >/dev/null 2>&1 || true
  docker image rm --force "$image_tag" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

docker build \
  --target media-runtime \
  --tag "$image_tag" \
  --file infra/server/Dockerfile \
  .

docker volume create \
  --label "$run_label" \
  "$volume_name" >/dev/null

docker run --rm \
  --network none \
  --read-only \
  --cap-drop ALL \
  --cap-add CHOWN \
  --security-opt no-new-privileges:true \
  --user 0:0 \
  --mount "type=volume,source=$volume_name,target=/work" \
  --entrypoint /bin/chown \
  "$image_tag" \
  100:101 /work

docker run --rm \
  --network none \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --user twobrain \
  --mount "type=volume,source=$volume_name,target=/work" \
  --entrypoint /bin/chmod \
  "$image_tag" \
  0700 /work

docker run --rm \
  --network none \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --pids-limit 128 \
  --memory 1g \
  --memory-swap 1g \
  --cpus 1 \
  --user twobrain \
  --mount "type=volume,source=$volume_name,target=/work" \
  --entrypoint /usr/bin/ffmpeg \
  "$image_tag" \
  -hide_banner -loglevel error -nostdin -y \
  -f lavfi -i "anoisesrc=color=pink:amplitude=0.02:sample_rate=44100:seed=99099" \
  -t 14399 -ac 1 -ar 44100 -c:a pcm_s32le -f wav /work/source-a.wav

docker run --rm \
  --network none \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --pids-limit 128 \
  --memory 1g \
  --memory-swap 1g \
  --cpus 1 \
  --user twobrain \
  --mount "type=volume,source=$volume_name,target=/work" \
  --entrypoint /bin/cp \
  "$image_tag" \
  /work/source-a.wav /work/source-b.wav

docker run \
  --name "$container_name" \
  --label "$run_label" \
  --network none \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --pids-limit 128 \
  --memory 1g \
  --memory-swap 1g \
  --cpus 1 \
  --user twobrain \
  --env TWOBRAIN_PLAYBACK_NORMALIZATION_WORK_BUDGET_BYTES=6442450944 \
  --env TWOBRAIN_PLAYBACK_NORMALIZATION_ACTIVITY_TIMEOUT_SECONDS=21600 \
  --mount "type=volume,source=$volume_name,target=/var/lib/twobrain-rec/playback-normalization" \
  --entrypoint python \
  "$image_tag" \
  /app/scripts/benchmark_playback_normalization.py

container_oom_killed="$(docker inspect --format '{{.State.OOMKilled}}' "$container_name")"
container_exit_code="$(docker inspect --format '{{.State.ExitCode}}' "$container_name")"
if [[ "$container_oom_killed" != "false" || "$container_exit_code" != "0" ]]; then
  printf 'playback_normalization_performance_container=fail\n' >&2
  printf 'container_oom_killed=%s\n' "$container_oom_killed" >&2
  printf 'container_exit_code=%s\n' "$container_exit_code" >&2
  exit 1
fi

cleanup
trap - EXIT INT TERM

container_residue_count="$(docker ps --all --quiet --filter "label=$run_label" | wc -l | tr -d ' ')"
volume_residue_count="$(docker volume ls --quiet --filter "label=$run_label" | wc -l | tr -d ' ')"
image_residue_count="$(docker image ls --quiet "$image_tag" | wc -l | tr -d ' ')"
if [[ "$container_residue_count" != "0" || "$volume_residue_count" != "0" || "$image_residue_count" != "0" ]]; then
  printf 'playback_normalization_performance_cleanup=fail\n' >&2
  printf 'container_residue_count=%s\n' "$container_residue_count" >&2
  printf 'volume_residue_count=%s\n' "$volume_residue_count" >&2
  printf 'image_residue_count=%s\n' "$image_residue_count" >&2
  exit 1
fi

printf 'playback_normalization_performance_cleanup=pass\n'
printf 'container_residue_count=0\n'
printf 'volume_residue_count=0\n'
printf 'image_residue_count=0\n'
