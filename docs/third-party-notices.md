# Third-Party Notices

## Lucide Icons

The cabinet UI uses SVG path data from Lucide Icons, including:
`volume-2`, `video`, `file-text`, `upload`, `bookmark`, `list-filter`,
`arrow-up-down`, `check`, `download`, `minus`, and `trash-2`.

Lucide Icons is licensed under the ISC License, with some icons derived from
Feather under the MIT License. See:

- https://github.com/lucide-icons/lucide
- https://github.com/lucide-icons/lucide/blob/main/LICENSE

## Sparkle

The macOS app embeds Sparkle `2.9.4` for authenticated application updates.
Sparkle is distributed under the MIT License and includes separately attributed
open-source components. Every packaged `GRAF.app` includes the complete pinned
upstream license and attribution text at
`Contents/Resources/Sparkle-LICENSE.txt`.

- https://github.com/sparkle-project/Sparkle
- https://github.com/sparkle-project/Sparkle/blob/2.9.4/LICENSE

## WebRTC AEC3

The macOS recording path statically links the AudioProcessing Module from
`webrtc-audio-processing` `v2.1` (WebRTC M131), pinned to commit
`846fe90a289f58b7c9303a635142aa2c7caa93e5`. The build also statically includes
the pinned Abseil fallback and bundled DSP components from the same source tree.

Every packaged `GRAF.app` includes the exact consolidated licenses,
attributions, and WebRTC patent grant at
`Contents/Resources/AEC3-THIRD-PARTY-NOTICES.txt`. The source inventory and
artifact hash are locked in `apps/macos/Native/GrafAEC3/upstream.lock`.

- https://gitlab.freedesktop.org/pulseaudio/webrtc-audio-processing/-/tree/v2.1
- https://webrtc.googlesource.com/src/+/refs/branch-heads/6613/LICENSE
- https://github.com/abseil/abseil-cpp/releases/tag/20240722.0
