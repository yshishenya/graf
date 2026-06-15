# Design Tokens

## Color Roles

The palette is intentionally not one-note. Neutral graphite/white carries the
workspace; green, cobalt, amber, and red are semantic accents.

| Role | Light | Dark | Use |
|---|---|---|---|
| App background | #F6F7F9 | #0F1115 | Window/page background |
| Surface primary | #FFFFFF | #171A20 | Main panes and modals |
| Surface secondary | #EEF1F4 | #20242C | Sidebars, list headers, subtle strips |
| Surface raised | #FFFFFF | #1E232B | Menus, popovers, tray |
| Border subtle | #DDE3EA | #303742 | Dividers and input borders |
| Border focus | #2F6BFF | #8EA8FF | Keyboard focus ring |
| Text primary | #111820 | #F4F6F8 | Primary copy |
| Text secondary | #596575 | #A8B1BD | Metadata and helper copy |
| Text muted | #7B8794 | #858F9C | Low-emphasis timestamps |
| Success | #12845A | #38D18E | Ready, saved, complete |
| Info | #2557D6 | #7896FF | Upload, processing, links |
| Warning | #B66B00 | #F4B04F | Stale, degraded, attention |
| Danger | #C42A36 | #FF6B76 | Active recording, destructive action |
| Recording fill | #E93645 | #FF5B69 | Active capture indicator only |
| Local source | #6A4CC2 | #B7A3FF | Local-only/this Mac source accent |

## Typography

Use San Francisco on native macOS surfaces and Inter or system sans on web. Do
not scale type with viewport width.

| Token | Size | Weight | Line height | Use |
|---|---:|---:|---:|---|
| Display | 28px | 650 | 34px | Prototype cover only |
| Page title | 22px | 650 | 28px | Web cabinet page title |
| Section title | 16px | 650 | 22px | Panels and screen regions |
| Row title | 14px | 600 | 20px | Meeting rows, queue rows |
| Body | 14px | 400 | 20px | Normal cabinet text |
| Body compact | 13px | 400 | 18px | Desktop shell metadata |
| Label | 12px | 600 | 16px | Chips, tabs, field labels |
| Caption | 12px | 400 | 16px | Helper text, timestamps |
| Mono timestamp | 12px | 500 | 16px | Transcript/playback times |

Letter spacing is `0` across all tokens.

## Spacing

| Token | Value | Use |
|---|---:|---|
| space-1 | 4px | Icon/text gap, dense dividers |
| space-2 | 8px | Chips, button internal gaps |
| space-3 | 12px | Row internals |
| space-4 | 16px | Panel padding, modal rows |
| space-5 | 20px | Desktop outer gutters |
| space-6 | 24px | Web page gutters |
| space-8 | 32px | Major web section gaps |

## Radius And Borders

| Token | Value | Use |
|---|---:|---|
| radius-1 | 4px | Inputs, chips, compact buttons |
| radius-2 | 6px | Badges, menu items |
| radius-3 | 8px | Cards, panels, modals maximum |
| border-1 | 1px | Default divider/border |
| focus-ring | 2px | Keyboard focus outline |

No component may exceed 8px radius unless it is inherited from native macOS
controls.

## Density And Layout

| Surface | Width/height contract | Notes |
|---|---|---|
| Desktop main window | 960-1120px wide, 680-760px high target | Works down to 820px width without overlap |
| Desktop sidebar | 192-220px | Contains Recorder, Library, Uploads, Settings handoff |
| Desktop status rail | 64-88px high | Must not collapse during recording |
| Web cabinet content | 1120-1280px max width | Dense list/review layout, not marketing hero |
| Web sidebar | 220-248px | Persistent nav on desktop web |
| Review transcript column | 52-60% width | Notes/AI/action side panel uses remaining width |
| Icon button | 32px default; 40px for primary capture | Tooltip required unless adjacent label exists |
| Primary button | 40px high | Compact labels only |
| Secondary button | 32-36px high | Used for filters and row actions |
| Chip | 28-32px high | Clear state visible |

## Elevation

- Base surfaces use borders, not heavy shadows.
- Popovers use `0 10px 30px rgba(15, 17, 21, 0.14)` in light mode and a
  subtle border in dark mode.
- No glow effects, gradient blobs, bokeh, decorative orbs, or nested card
  shadows.
