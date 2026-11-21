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

Before a Windows artifact is distributed, copy the exact upstream license files
into this directory or attach their immutable source/evidence receipt to the
build output. Do not commit downloaded source archives, generated `.lib` files,
raw audio or private build paths.
