# 2brain Rec macOS Installer

This directory owns the interactive MVP installer package and recovery scripts.

## MVP Scope

- Interactive install.
- Interactive update with active-call deferral.
- Repair.
- Rollback.
- Uninstall.
- User-visible restart-required and manual-cleanup states.

Silent install, MDM, fleet deployment, and enterprise deployment are out of scope for this feature.

## Signing Policy

- Developer ID signing and notarization are required before private-alpha release candidates.
- Local certificates, private keys, app-specific passwords, API keys, notarization credentials, and generated signed artifacts must stay outside git.
- Build scripts may reference environment variables or local keychain identities by name, but must not embed secret values.

## Safety Rules

- Updates must not interrupt active capture or an active call.
- Uninstall must remove app-managed virtual audio artifacts where macOS permits.
- Uninstall must attempt to restore previous physical microphone and speaker choices where macOS permits.
- Partial cleanup must be reported truthfully with a manual remediation step.
