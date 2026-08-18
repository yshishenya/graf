# Data model: Адаптивное стартовое состояние боковой панели

Persistent data is not introduced. The feature operates on one existing shell
state during one page lifetime.

| Entity | Fields | Rules |
|---|---|---|
| Cabinet shell | `desktop-embedded`, `is-rail-pinned`, `railReady` | One shell is initialized once; explicit `is-rail-pinned` means expanded. |
| Rail state | `expanded` / `collapsed` | Derived once from explicit state or the surface-specific min-width query; changed only by the existing toggle and existing close paths afterward. |
| Responsive default | surface, min-width, matches | Browser uses 981 px; embedded uses 1121 px; it is not stored. |

State transition:

```text
explicit is-rail-pinned
        │
        ├── present ──> expanded
        │
        └── absent ──> match surface breakpoint ──> expanded or collapsed
```

No database, API payload, cookie, localStorage key, analytics event or
cross-session identity is part of this model.
