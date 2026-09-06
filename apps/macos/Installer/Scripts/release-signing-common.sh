#!/usr/bin/env sh
# Shared public-trust and signer-selection helpers for GRAF Sparkle releases.
# This file deliberately handles public keys and metadata only. Private signing
# material is selected by the caller and is never printed by these helpers.

release_signing_fail() {
  echo "release-signing: $*" >&2
  return 1
}

release_signing_plist_value() {
  value=$(/usr/bin/plutil -extract "$1" raw -o - "$2" 2>/dev/null) || return 0
  printf '%s\n' "$value"
}

release_signing_require_safe_identifier() {
  value=$1
  label=$2
  case "$value" in
    ''|*[!A-Za-z0-9._-]*)
      release_signing_fail "$label is invalid"
      return 1
      ;;
  esac
}

release_signing_require_public_key() {
  public_key=$1
  [ -n "$public_key" ] || {
    release_signing_fail "public key is missing"
    return 1
  }
  if ! printf '%s' "$public_key" | /usr/bin/base64 -D >/dev/null 2>&1; then
    release_signing_fail "public key is not valid base64"
    return 1
  fi
  public_key_bytes=$(printf '%s' "$public_key" | /usr/bin/base64 -D 2>/dev/null | wc -c | tr -d ' ')
  [ "$public_key_bytes" = "32" ] || {
    release_signing_fail "public key is not a 32-byte Ed25519 value"
    return 1
  }
}

release_signing_key_id() {
  release_signing_require_public_key "$1" || return 1
  public_hash=$(printf '%s' "$1" | /usr/bin/base64 -D 2>/dev/null | /usr/bin/shasum -a 256 | awk '{print $1}')
  case "$public_hash" in
    [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]*) ;;
    *) release_signing_fail "could not calculate public key identifier"; return 1 ;;
  esac
  printf 'sha256:%s\n' "$public_hash"
}

release_signing_require_active_manifest() {
  manifest_path=$1
  [ -f "$manifest_path" ] || {
    release_signing_fail "public signing manifest is missing"
    return 1
  }

  manifest_schema=$(release_signing_plist_value schemaVersion "$manifest_path")
  manifest_status=$(release_signing_plist_value status "$manifest_path")
  manifest_generation=$(release_signing_plist_value trustGeneration "$manifest_path")
  manifest_key_id=$(release_signing_plist_value keyId "$manifest_path")
  manifest_public_key=$(release_signing_plist_value publicKey "$manifest_path")
  primary_kind=$(release_signing_plist_value channels.primary.kind "$manifest_path")
  primary_account=$(release_signing_plist_value channels.primary.account "$manifest_path")
  legacy_environment=$(release_signing_plist_value channels.primary.environment "$manifest_path")
  legacy_secret_name=$(release_signing_plist_value channels.primary.secretName "$manifest_path")
  legacy_recovery=$(release_signing_plist_value channels.recovery.kind "$manifest_path")

  [ "$manifest_schema" = "1" ] || {
    release_signing_fail "public signing manifest schema is unsupported"
    return 1
  }
  [ "$manifest_status" = "active" ] || {
    release_signing_fail "public signing manifest is not active"
    return 1
  }
  case "$manifest_generation" in
    ''|*[!0-9]*|0)
      release_signing_fail "public signing manifest trust generation is invalid"
      return 1
      ;;
  esac
  release_signing_require_public_key "$manifest_public_key" || return 1
  calculated_key_id=$(release_signing_key_id "$manifest_public_key") || return 1
  [ "$manifest_key_id" = "$calculated_key_id" ] || {
    release_signing_fail "public signing manifest key identifier does not match its public key"
    return 1
  }
  [ "$primary_kind" = "macos-keychain" ] || {
    release_signing_fail "public signing manifest primary channel is invalid"
    return 1
  }
  release_signing_require_safe_identifier "$primary_account" "public signing manifest Keychain account" || return 1
  [ -z "$legacy_environment$legacy_secret_name$legacy_recovery" ] || {
    release_signing_fail "public signing manifest contains legacy remote signing fields"
    return 1
  }

  RELEASE_SIGNING_MANIFEST_PATH=$manifest_path
  RELEASE_SIGNING_TRUST_GENERATION=$manifest_generation
  RELEASE_SIGNING_KEY_ID=$calculated_key_id
  RELEASE_SIGNING_PUBLIC_KEY=$manifest_public_key
  RELEASE_SIGNING_KEYCHAIN_ACCOUNT=$primary_account
  export RELEASE_SIGNING_MANIFEST_PATH RELEASE_SIGNING_TRUST_GENERATION RELEASE_SIGNING_KEY_ID
  export RELEASE_SIGNING_PUBLIC_KEY RELEASE_SIGNING_KEYCHAIN_ACCOUNT
}

release_signing_require_matching_public_key() {
  observed_public_key=$1
  expected_public_key=$2
  label=$3
  release_signing_require_public_key "$observed_public_key" || return 1
  [ "$observed_public_key" = "$expected_public_key" ] || {
    release_signing_fail "$label does not match the active public signing generation"
    return 1
  }
}

release_signing_require_recent_attestation_timestamp() {
  checked_at=$1
  printf '%s' "$checked_at" | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$' || {
    release_signing_fail "safe signing attestation timestamp is invalid"
    return 1
  }
  checked_epoch=$(LC_ALL=C /bin/date -j -u -f '%Y-%m-%dT%H:%M:%SZ' "$checked_at" '+%s' 2>/dev/null || true)
  current_epoch=$(/bin/date -u '+%s')
  case "$checked_epoch" in
    ''|*[!0-9]*)
      release_signing_fail "safe signing attestation timestamp is invalid"
      return 1
      ;;
  esac
  [ "$checked_epoch" -le "$current_epoch" ] || {
    release_signing_fail "safe signing attestation timestamp is in the future"
    return 1
  }
  [ $((current_epoch - checked_epoch)) -le 86400 ] || {
    release_signing_fail "safe signing attestation is older than 24 hours"
    return 1
  }
}

release_signing_require_keychain_attestation() {
  attestation_path=$1
  expected_release_ref=$2
  expected_commit=${3:-}
  [ -f "$attestation_path" ] || {
    release_signing_fail "safe Keychain attestation is missing"
    return 1
  }
  attestation_schema=$(release_signing_plist_value schemaVersion "$attestation_path")
  attestation_key_id=$(release_signing_plist_value keyId "$attestation_path")
  attestation_generation=$(release_signing_plist_value trustGeneration "$attestation_path")
  attestation_channel=$(release_signing_plist_value channel "$attestation_path")
  attestation_state=$(release_signing_plist_value state "$attestation_path")
  attestation_checked_at=$(release_signing_plist_value checkedAt "$attestation_path")
  attestation_release_ref=$(release_signing_plist_value releaseRef "$attestation_path")
  attestation_commit=$(release_signing_plist_value commit "$attestation_path")
  attestation_workflow=$(release_signing_plist_value workflow "$attestation_path")
  attestation_evidence_id=$(release_signing_plist_value evidenceId "$attestation_path")
  [ "$attestation_schema" = "1" ] || {
    release_signing_fail "safe Keychain attestation schema is unsupported"
    return 1
  }
  [ "$attestation_key_id" = "$RELEASE_SIGNING_KEY_ID" ] || {
    release_signing_fail "safe Keychain attestation key identifier does not match the active generation"
    return 1
  }
  [ "$attestation_generation" = "$RELEASE_SIGNING_TRUST_GENERATION" ] || {
    release_signing_fail "safe Keychain attestation trust generation does not match the active generation"
    return 1
  }
  [ "$attestation_channel" = "macos-keychain" ] || {
    release_signing_fail "safe Keychain attestation channel is invalid"
    return 1
  }
  [ "$attestation_state" = "ready" ] || {
    release_signing_fail "safe Keychain attestation state is not ready"
    return 1
  }
  release_signing_require_recent_attestation_timestamp "$attestation_checked_at" || return 1
  [ "$attestation_release_ref" = "$expected_release_ref" ] || {
    release_signing_fail "safe Keychain attestation does not bind the requested release"
    return 1
  }
  printf '%s' "$attestation_commit" | grep -Eq '^[0-9a-f]{40}$' || {
    release_signing_fail "safe Keychain attestation commit is invalid"
    return 1
  }
  if [ -n "$expected_commit" ] && [ "$attestation_commit" != "$expected_commit" ]; then
    release_signing_fail "safe Keychain attestation does not bind the requested commit"
    return 1
  fi
  case "$attestation_workflow" in
    verify-release-signing-custody-local|sign-graf-app-update-local) ;;
    *) release_signing_fail "safe Keychain attestation workflow is invalid"; return 1 ;;
  esac
  printf '%s' "$attestation_evidence_id" | grep -Eq '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' || {
    release_signing_fail "safe Keychain attestation evidence identifier is invalid"
    return 1
  }
}

release_signing_select_signer() {
  mode=${GRAF_RELEASE_SIGNING_MODE:-}
  legacy_file=${GRAF_SPARKLE_PRIVATE_KEY_FILE:-}
  legacy_account=${GRAF_SPARKLE_KEYCHAIN_ACCOUNT:-}
  [ -z "$legacy_file" ] || {
    release_signing_fail "legacy arbitrary private-file input is forbidden"
    return 1
  }
  [ -z "$legacy_account" ] || {
    release_signing_fail "legacy Keychain-account override is forbidden"
    return 1
  }

  case "$mode" in
    keychain)
      requested_account=${GRAF_RELEASE_SIGNING_KEYCHAIN_ACCOUNT:-$RELEASE_SIGNING_KEYCHAIN_ACCOUNT}
      [ "$requested_account" = "$RELEASE_SIGNING_KEYCHAIN_ACCOUNT" ] || {
        release_signing_fail "Keychain account does not match the active public signing generation"
        return 1
      }
      RELEASE_SIGNING_SIGNER_MODE=keychain
      RELEASE_SIGNING_SIGNER_ACCOUNT=$RELEASE_SIGNING_KEYCHAIN_ACCOUNT
      ;;
    *)
      release_signing_fail "GRAF_RELEASE_SIGNING_MODE must be keychain"
      return 1
      ;;
  esac
  export RELEASE_SIGNING_SIGNER_MODE RELEASE_SIGNING_SIGNER_ACCOUNT
}

release_signing_derive_signer_public_key() {
  generate_keys=$1
  derive_helper=$2
  case "$RELEASE_SIGNING_SIGNER_MODE" in
    keychain)
      "$generate_keys" --account "$RELEASE_SIGNING_SIGNER_ACCOUNT" -p | tr -d '\r\n'
      ;;
    *)
      release_signing_fail "signer mode was not selected"
      return 1
      ;;
  esac
}

release_signing_emit_safe_state() {
  state=$1
  printf 'key_id=%s\ntrust_generation=%s\noverall=%s\n' "$RELEASE_SIGNING_KEY_ID" "$RELEASE_SIGNING_TRUST_GENERATION" "$state"
}
