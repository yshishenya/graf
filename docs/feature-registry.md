# Feature Number Registry

Date: 2026-06-17

This file is the single project-owned place for feature number reservations,
prepared backlog ranges, and active Spec Kit number decisions. Update it before
starting any new Spec Kit feature when the intended number is not already
represented here.

## Allocation Rule

Before creating a new feature spec or branch, verify the next number against:

- current `specs/` directories;
- local branches;
- remote branches after `git fetch --all --prune`;
- feature numbers mentioned in committed docs and backlog files;
- historical spec paths in `git log --all --name-only -- specs`.

Do not rely only on the highest visible directory in `specs/`. A number may be
reserved by a branch, backlog, historical draft, or another worktree even when
the spec directory is not present in the current checkout.

If a number is reserved here but not yet implemented, do not reuse it unless the
user explicitly retires or renumbers that reservation.

## Current Registry

| Number(s) | Status | Source / Notes |
|---|---|---|
| `001`-`008`, `010`-`022`, `025`-`036` | Active or accepted specs | Present as `specs/<number>-...` in the current Spec Kit line. |
| `009` | Superseded / do not reuse casually | Old meeting-mute draft superseded by `022-meeting-mute-truth`. |
| `023`-`024` | Historical draft numbers | Historical spec paths exist in git history. Reuse only after explicit owner decision and registry update. |
| `037` | Reserved backlog | `microphone-sample-graph-foundation`: app-owned mic sample graph before cleanup/AEC work. |
| `038` | Reserved backlog | `apple-voice-processing-spike`: Apple Voice Processing / VoiceProcessingIO evaluation. |
| `039` | Reserved backlog | `webrtc-aec3-speakerphone-spike`: WebRTC AEC3 speakerphone cleanup spike. |
| `040` | Reserved backlog | `speakerphone-recording-fallback-decision`: truthful fallback decision if clean built-in speakerphone capture is not proven. |
| `041` | Reserved backlog | `recording-permission-readiness-onboarding`: Mic and Screen/System Audio readiness before recording. |
| `042` | Claimed branch | `042-recording-sync-transcription-loop`: recording upload, offline sync, transcription, and transcript display loop. |

## Useful Checks

```sh
git fetch --all --prune
find specs -maxdepth 1 -mindepth 1 -type d -print | sort
git branch -a --format='%(refname:short)' | sort
git log --all --name-only --pretty=format: -- specs | rg '^specs/[0-9]{3}-' | sort -u
rg -n '0[0-9]{2}-|feature [0-9]{3}|Feature [0-9]{3}' docs specs AGENTS.md
```

When these checks disagree, stop and reconcile the registry before creating the
new feature.
