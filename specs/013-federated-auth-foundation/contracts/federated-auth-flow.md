# Contract: Federated Authentication Flow

## Purpose

This document defines auth provider flow and device/session outcomes for feature 013.

## Actors

- anonymous workspace participant
- authenticated workspace participant
- workspace admin

## Endpoints

### 1) `GET /api/v1/auth/providers`

**Purpose**: Return enabled providers for a workspace and RU policy flags.

**Inputs**:
- `workspace_id` path or query
- request identity context optional (for admin/owner visibility where policy includes hidden internals)

**Success response**:
- enabled provider list: subset of `Yandex`, `VK`, `Telegram` (plus adapter-enabled families if admin enabled).
- deterministic consent copy and version for the workspace.

### 2) `POST /api/v1/auth/providers/{provider}/start`

**Purpose**: Start OAuth/ID auth and return redirect URL.

**Inputs**:
- provider (`yandex`, `vk`, `telegram`, optionally future configured adapter)
- workspace_id
- return_context (e.g., mobile/web callback route hint)
- optional existing session id for re-link flows

**Success response**:
- redirect URL safe to open in browser.

**Failure cases**:
- disabled provider: HTTP 403 with deterministic code.
- workspace policy disallows provider: HTTP 403.
- callback infrastructure unavailable: HTTP 503.

### 3) `GET /api/v1/auth/callback/{provider}`

**Purpose**: Receive provider callback and validate state/nonce.

**Inputs**:
- provider-specific query/fragment parameters
- state nonce
- optional error fields

**Success behavior**:
- issue or return active `AuthSession` (server-issued)
- create/resolve `InternalUser` and `ExternalIdentity` if safe
- emit audit event `provider_callback_success`

**Failure behavior**:
- state mismatch / replay: HTTP 400 `callback_state_invalid` and audit event `provider_callback_failed`
- denied by provider: HTTP 403 `callback_denied`
- provider outage: HTTP 503 `provider_unavailable`

### 4) `POST /api/v1/auth/link`

**Purpose**: Link a second provider identity to current active user.

**Inputs**:
- active authenticated session
- provider + external subject from callback or candidate match data

**Success behavior**:
- if safe verified match exists, state transitions to `confirmed`
- emit audit event `provider_link_confirmed`

**Failure behavior**:
- unresolved conflict: `provider_link_conflict`
- mismatch/unverified claim: `provider_link_rejected`

### 5) `POST /api/v1/auth/devices/register`

**Purpose**: Register current desktop client as trusted device.

**Inputs**:
- active authenticated session
- device public id, platform, client version, optional hardware hint

**Success behavior**:
- create `RegisteredDevice` + `AuthSessionDeviceBinding` and return device status.

### 6) `POST /api/v1/auth/devices/{device_id}/revoke`

**Purpose**: Revoke device trust immediately.

**Inputs**:
- authenticated user or workspace admin
- target device id

**Success behavior**:
- mark device/session binding revoked and deny future upload/session access.

### 7) `GET /api/v1/auth/me`

**Purpose**: Return current auth session + linked providers + policy summary.

**Inputs**:
- active internal auth session context

**Success behavior**:
- returns active providers, device state, and policy summary.

## Failure Taxonomy (required user-visible codes)

- `provider_disabled`
- `provider_missing`
- `callback_state_invalid`
- `callback_state_reused`
- `callback_denied`
- `provider_unavailable`
- `link_conflict`
- `link_requires_confirmation`
- `link_rejected`
- `device_revoked`
- `device_quarantined`
- `device_untrusted`
- `session_expired`
- `session_reused_from_other_workspace`

## Security Invariants

- No raw provider secret/token is returned in API responses.
- No provider secret/token is logged in request logs.
- State and callback values are single-use and short-lived.
- Revoked devices are denied before API action execution.
