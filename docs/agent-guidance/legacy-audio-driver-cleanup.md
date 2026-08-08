# Existing Legacy Audio Component Cleanup

Repository retirement does not remove a proof component that was previously
installed on a developer Mac. This procedure is intentionally manual and is
never called by build, test, package, app launch, or uninstall validation.

## Safety Boundary

- Finish and close every recording, call, and audio-sensitive app first.
- Preserve `/Applications/GRAF.app`, GRAF application-support data, recording
  packages, permissions, and unrelated audio components.
- Act only on the exact known bundle paths below.
- If a similar but non-exact name appears, stop and investigate it separately.
- Do not recursively alter the parent HAL directory and do not clear attributes
  from unrelated bundles.

Known proof bundle paths and identifiers:

```text
/Library/Audio/Plug-Ins/HAL/GrafProof.driver -> pro.2brain.graf.proof.driver
/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver -> pro.2brain.rec.proof.driver
/Library/Audio/Plug-Ins/HAL/.graf-driver-staged/GrafProof.driver -> pro.2brain.graf.proof.driver
```

## Read-Only Inspection

```sh
inspect_bundle() {
  path=$1
  expected_identifier=$2

  if [ ! -e "$path" ]; then
    printf 'absent: %s\n' "$path"
    return
  fi
  if [ -L "$path" ] || [ -L "$(dirname "$path")" ]; then
    printf 'reject symlinked path: %s\n' "$path"
    return
  fi

  actual_identifier=$(
    /usr/bin/plutil -extract CFBundleIdentifier raw -o - \
      "$path/Contents/Info.plist" 2>/dev/null || true
  )
  ls -ld "$path"
  if [ "$actual_identifier" = "$expected_identifier" ]; then
    printf 'verified: %s (%s)\n' "$path" "$actual_identifier"
  else
    printf 'identifier mismatch: %s (expected %s, found %s)\n' \
      "$path" "$expected_identifier" "${actual_identifier:-missing}"
  fi
}

while IFS='|' read -r path expected_identifier
do
  inspect_bundle "$path" "$expected_identifier"
done <<'EOF'
/Library/Audio/Plug-Ins/HAL/GrafProof.driver|pro.2brain.graf.proof.driver
/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver|pro.2brain.rec.proof.driver
/Library/Audio/Plug-Ins/HAL/.graf-driver-staged/GrafProof.driver|pro.2brain.graf.proof.driver
EOF
```

Interpretation:

- **All absent**: no cleanup action is required.
- **Exact known path and identifier verified**: proceed only with explicit
  operator approval.
- **Symlink, identifier mismatch, lookalike, or additional bundle present**: do
  not remove it through this procedure.

## Deliberate Exact-Component Removal

Only after the safety checks and explicit approval:

```sh
remove_verified_bundle() {
  path=$1
  expected_identifier=$2

  [ -e "$path" ] || return
  if [ -L "$path" ] || [ -L "$(dirname "$path")" ]; then
    printf 'refusing symlinked path: %s\n' "$path" >&2
    return 1
  fi
  actual_identifier=$(
    /usr/bin/plutil -extract CFBundleIdentifier raw -o - \
      "$path/Contents/Info.plist" 2>/dev/null || true
  )
  if [ "$actual_identifier" != "$expected_identifier" ]; then
    printf 'refusing identifier mismatch: %s\n' "$path" >&2
    return 1
  fi
  sudo rm -rf -- "$path"
}

remove_verified_bundle \
  "/Library/Audio/Plug-Ins/HAL/GrafProof.driver" \
  "pro.2brain.graf.proof.driver"
remove_verified_bundle \
  "/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver" \
  "pro.2brain.rec.proof.driver"
remove_verified_bundle \
  "/Library/Audio/Plug-Ins/HAL/.graf-driver-staged/GrafProof.driver" \
  "pro.2brain.graf.proof.driver"
sudo killall coreaudiod
```

The final command asks macOS to reload audio components and can interrupt active
audio. It must never run during normal validation or an active recording/call.

Repeat the read-only inspection afterward. If an exact path remains, report the
failure; do not broaden the deletion target.
