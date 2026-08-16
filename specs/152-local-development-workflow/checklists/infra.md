# Infrastructure Checklist

- [X] Separate Compose and distinct ports.
- [X] Health → migration → seed → bucket → API order.
- [X] Processing, outcomes, billing and analytics off by default.
- [X] Disposable local `.app` stays under `.build/local` and does not install or
  modify the public installer artifact.
- [X] Quickstart and validation commands documented.
