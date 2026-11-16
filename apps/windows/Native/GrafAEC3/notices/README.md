# GrafAEC3 notices

Feature 200 uses the same pinned WebRTC Audio Processing AEC3 source identity as
the existing macOS native target. The source is not copied into the repository
by the setup slice; the build script accepts a verified checkout and checks its
revision before building.

- Version/tag: `2.1` / `v2.1`
- Revision: `846fe90a289f58b7c9303a635142aa2c7caa93e5`
- Canonical source: `https://gitlab.freedesktop.org/pulseaudio/webrtc-audio-processing.git`
- Public mirror used for revision verification: `https://github.com/okarlsen/webrtc-audio-processing.git`
- License family: BSD 3-Clause and the upstream bundled notices listed in
  `../upstream.lock`.

This directory carries the exact eight upstream files listed in
`../upstream.lock`, preserving their relative paths. `Abseil/LICENSE` is the
unaltered Apache 2.0 text from the pinned Abseil 20240722.0 source archive.
Keep these files byte-for-byte identical to their pinned sources.

`../../../Installer/GrafWindows.Package.wapproj` includes these texts under
`ThirdPartyNotices/GrafAEC3/` and `ThirdPartyNotices/Abseil/` in every MSIX.
It also includes the pinned Microsoft SDK license/notice texts from
`../../../Installer/ThirdPartyNotices/`. The packaging build fails if a required
notice file is missing. No build-time download or notice generator is used.

`../../../Installer/ThirdPartyNotices/SOURCES.json` records exact source URLs,
archive members where applicable, source archive SHA-256 and notice SHA-256.
When a dependency pin changes, update its exact texts and this inventory
together; validate the resulting MSIX entries and their hashes against it.
Source/build receipts do not replace delivering these full texts to recipients.
Adding the texts does not establish Microsoft redistribution rights, end-user
terms, framework-package contents, public signing or installed acceptance.

Do not commit downloaded source archives, generated `.lib` files, raw audio or
private build paths.
