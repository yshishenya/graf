# Validation summary

Evidence is recorded during PR and release closeout. The local build must
report both `arm64` and `x86_64`, the staged package must contain one desktop
component, and focused Swift/public tests plus local CI must pass.

Production signing, notarization, stapling, and live public download evidence
remain explicit release gates and are not inferred from an ad-hoc local build.
