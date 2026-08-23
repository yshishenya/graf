# Windows build and evidence scripts

The first claim is x64 on Windows 10 22H2 (19045) and the separately recorded
supported Windows 11 build set. ARM64 is a gate, not an implied target.

Pinned setup dependencies:

- Windows App SDK `2.4.0`;
- WebView2 SDK `1.0.4129.50` with Evergreen Runtime at install/runtime;
- C++/WinRT `3.0.260818.1`;
- GrafAEC3 source identity from `Native/GrafAEC3/upstream.lock`.

All scripts must keep the same boundaries:

- synthetic audio contains only generated tones/noise and never real meetings;
- evidence contains metadata, bounded counters, durations, safe reason codes and
  redacted device identity only;
- raw audio, transcripts, cookies, tokens, signed URLs and local private paths
  stay outside git and committed evidence;
- callbacks remain bounded packet drains; file I/O, WebView calls and AEC3 stay
  on workers;
- no virtual audio driver, Stereo Mix dependency, kernel component, elevated
  service or direct MediaScribe/MinIO egress;
- every Windows claim names the host OS/build, architecture, exact SHA and
  skipped ARM64/hardware lanes.

`build-graf-aec3.ps1 -VerifyOnly` checks only the pinned checkout and upstream
license files. A successful verification is not a successful Windows build or
hardware/audio-quality gate.
