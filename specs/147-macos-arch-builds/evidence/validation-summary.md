# Validation summary

Evidence is recorded during PR and release closeout. The local build reported
both `arm64` and `x86_64`, the staged package contained one desktop component,
and focused Swift/public tests plus local CI passed.

Production signing, notarization, stapling, and live public download evidence
are all closed for `v2026.08.12.3`. The live receipt on 2026-08-13 returned
HTTP 200 for `/download` and `downloads/graf.pkg`; the downloaded 6 136 432-byte
asset matched SHA-256
`6c6cb57affebd65430c8b49a4636506638950e6ecb9fc4c88b638b6067342c5c`.

The remaining limitation is hardware smoke on a separate supported Intel Mac;
the release contract and universal Mach-O slice validation do not replace that
manual test.
