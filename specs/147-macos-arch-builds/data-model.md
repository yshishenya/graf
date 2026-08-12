# Release artifact model

```text
graf.pkg
└── graf-desktop-app.pkg
    └── Applications/GRAF.app
        └── Contents/MacOS/GRAF: arm64 + x86_64
```

Compatibility tuple: `(macOS >= 14.5, architecture ∈ {arm64, x86_64})`.
Unknown architectures and older macOS versions fail closed.
