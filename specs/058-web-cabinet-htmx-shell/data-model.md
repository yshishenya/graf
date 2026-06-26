# Data Model: Web Cabinet HTMX Shell

No database schema changes are planned. These are view and contract entities used by server templates, desktop route policy, tests, and validation evidence.

## Cabinet Shell

**Purpose**: Server-owned online workspace frame.

**Fields**:

- `surface_mode`: `standalone_browser` | `desktop_embedded` | `auth_recovery` | `unavailable`
- `navigation`: list of `CabinetNavigationItem`
- `active_route_kind`: route kind from the cabinet route contract
- `workspace_label`: metadata-safe display label
- `account_label`: metadata-safe display label
- `csrf_token`: present only for authenticated unsafe-action surfaces

**Rules**:

- Does not include native capture controls.
- Does not include raw transcript text in list/navigation context.
- Desktop embedded mode hides native-only routes and keeps WebView content inside online cabinet scope.

## Cabinet Navigation Item

**Purpose**: Reusable online cabinet menu item.

**Fields**:

- `id`: stable string key
- `label`: Russian UI text
- `icon`: Lucide-style icon key
- `href`: online cabinet route
- `active`: boolean
- `availability`: `available` | `disabled` | `hidden` | `unavailable`
- `badge_count`: optional safe count
- `unavailable_reason`: optional bounded copy

**Rules**:

- No local native route targets.
- Disabled/unavailable items must not imply that an action executed.
- Future sections use hidden or bounded unavailable states until implemented.

## Internal Atomic Component

**Purpose**: Product-owned reusable primitive control.

**Fields**:

- `name`: stable component name
- `variant`: semantic variant such as `primary`, `quiet`, `danger`, `chip`, `tab`
- `states`: supported states
- `accessible_name_required`: boolean
- `icon_allowed`: boolean
- `localization_required`: boolean

**States**:

- `normal`
- `hover`
- `focus`
- `disabled`
- `unavailable`
- `loading`
- `selected`
- `destructive`
- `error`
- `empty`
- `overflow_text`

**Rules**:

- Interactive targets must meet the 24 by 24 CSS pixel target gate unless equivalent spacing is validated.
- Component templates receive already-authorized view data only.
- Components must escape output by default.

## Composed Cabinet Section

**Purpose**: Reusable region built from atomic components.

**Fields**:

- `name`: stable section name
- `atoms`: referenced atomic components
- `surface_modes`: supported surface modes
- `allowed_state_sources`: view-model fields that may drive state
- `fragment_id`: optional HTMX fragment identifier

**Initial sections**:

- sidebar navigation
- workspace/account header
- meeting row
- selection toolbar
- playback controls
- detail side panel
- confirmation dialog
- status banner
- empty state
- unavailable state
- auth form

**Rules**:

- Sections do not query the database.
- Sections do not make access, tenant, lifecycle, deletion, or egress decisions.
- HTMX fragments must render the section body only, not a full page shell.

## Static Cabinet Style Layer

**Purpose**: Single cabinet styling source.

**Fields**:

- `tokens`: CSS custom properties for color, spacing, radius, typography, focus, state color
- `component_classes`: semantic classes used by Jinja components
- `responsive_rules`: browser desktop, mobile width, and desktop embedded WebView rules
- `accessibility_rules`: focus, target size, reduced motion

**Rules**:

- No Tailwind-generated CSS.
- No frontend build pipeline.
- No external fonts or CDN assets.

## Lucide-Style Icon

**Purpose**: Centralized inline SVG icon vocabulary.

**Fields**:

- `key`: icon key such as `trash`, `filter`, `sort`, `download`, `audio`
- `view_box`: fixed `0 0 24 24`
- `stroke_width`: fixed shared stroke width
- `aria_hidden`: true for decorative icons
- `accessible_label`: supplied by the parent control when the icon carries meaning

**Rules**:

- Pages do not embed ad hoc emoji, Unicode controls, or one-off SVG styles.
- New icons are added through the central helper/macro and covered by component tests.

## Progressive Cabinet Interaction

**Purpose**: Bounded enhanced interaction driven by server truth.

**Fields**:

- `interaction_id`: stable identifier
- `trigger`: link, form, or button
- `request_method`: `GET` or unsafe method
- `target_region`: fragment target
- `fallback_url`: full-page fallback
- `requires_csrf`: boolean
- `failure_copy`: bounded Russian copy

**Rules**:

- Browser-side state is ephemeral only.
- Server response decides row state, deletion state, auth state, and errors.
- Full-page and fragment responses remain distinguishable and set `Vary: HX-Request`.

## Anti-Forgery Guard

**Purpose**: Session-bound proof for unsafe browser/WebView actions.

**Fields**:

- `token`: opaque random value
- `session_id`: auth session binding
- `issued_at`: timestamp
- `expires_at`: timestamp
- `submitted_via`: hidden field or `X-CSRF-Token`

**Rules**:

- Required for unsafe cookie-authenticated cabinet actions.
- Failure returns bounded copy and no mutation.
- Tokens are never logged or committed in evidence.

## Desktop Route Policy Decision

**Purpose**: Native classification of WebView or external navigation.

**Fields**:

- `route_kind`: exact kind such as `meeting_list`, `meeting_detail`, `deletion_report`, `auth_login`, `auth_signup`, `safe_help`, `blocked_native`, `blocked_unknown`
- `decision`: `allow` | `block_with_message` | `open_externally`
- `reason`: stable safe reason
- `user_message`: bounded copy

**Rules**:

- Exact route kind matching replaces substring blocking.
- Native capture, permission, local diagnostics, local files, and upload-picker routes remain blocked.
- Login pages do not mark cabinet ready.

## Metadata-Safe Evidence

**Purpose**: Validation output that proves behavior without private content.

**Fields**:

- `scenario`: safe scenario key
- `route_kind`: route kind
- `surface_mode`: surface mode
- `viewport`: dimensions or named viewport
- `result`: pass/fail
- `safe_counts`: optional counts
- `failure_reason`: safe reason

**Rules**:

- No raw audio, transcript text, generated outcome text, signed URLs, object keys, credentials, private local paths, private meeting identifiers, or real account identifiers.
