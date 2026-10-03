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

Application/MSIX builds require the real pinned AEC3 backend; they now fail if
it is missing. An external cache can be selected with the MSBuild properties
`GrafAEC3Root` and `GrafAEC3BuildRoot`. Both must refer to the same clean pinned
checkout and its Meson Windows x64 build. `-VerifyBuildArtifacts` requires the
provenance written only after a successful build: pinned inputs, unchanged source
and header tree, architecture, configuration, recipe and hashes of libraries and
generated headers. Old caches without provenance must be rebuilt. The builder
compares unpacked Abseil with the pinned archive plus patch before compilation;
changed inputs during compilation invalidate the result. Linker errors still
reject missing dependencies.
ARM64 remains unsupported until its own source/build/hardware validation.

Run the build-gate regressions and the actual executable self-check on Windows:

```powershell
.\apps\windows\scripts\validate-aec3-build.ps1 `
  -SourceDirectory <pinned-source> -BuildDirectory <meson-build> `
  -MSBuild <MSBuild.exe> -Executable <built-or-installed-GrafWindowsApp.exe> `
  -ExpectedExecutableSha256 <independently-recorded-build-or-package-exe-sha256>
```

This checks missing/forged dependencies, unsupported architecture, wrong source
revision, stale/missing provenance, changed library bytes and the accepted real
dependency. The executable's `--verify-audio-backend` mode returns the distinctive
code **73** only after real AEC construction and
reverse-before-microphone processing; it does not open devices, record, write
user files or contact the network. A normal exit code 0 from an old executable,
a hash mismatch or a timeout/failure is not a pass. Without
`-Executable` that part is explicitly NOT_RUN. Repeat it on the installed
package and compare its executable hash with the MSIX payload. Neither this
check nor portable tests replaces real capture/AEC hardware acceptance.
