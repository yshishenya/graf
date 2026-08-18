# Data Model: Выравнивание нижнего playback

No persistent data model.

| Field | Owner | Constraint |
|---|---|---|
| `railState` | cabinet shell class | compact or expanded |
| `inlineStart` | CSS custom property | equals active rail width |
| `playbackState` | existing audio/player DOM | unchanged by this slice |
