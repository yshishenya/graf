# F243 research

## Native confirmations and navigation

Decision: one WKUIDelegate confirm entry with NSAlert, safe Cancel, trusted
main-frame origin/route guards, one pending completion cancelled on navigation,
teardown/process termination. Exact lifecycle wiring is researched before code.
Rationale: all JS callers share window.confirm; no delegate means Cancel by SDK.
Rejected: auto-approve, broad route prefixes or removing server security checks.
Only precise settings tails, UUID details and safe legal handoffs are added.

Research agent Euler verified actual callers and SDK: current coordinator can
own a pending alert tuple keyed by UUID; clear before endSheet/callback, ignore
late callbacks with different identity. NSAlert continuation is the explicit
second-button return code, not NSOpenPanel.OK. Host mainWindow is retained after
close, so observe its willClose notification while pending. Also cancel before
SwiftUI load and main-frame navigation, on current failure/response rejection,
didStartProvisionalNavigation, detach and WebContentProcessDidTerminate. Process
termination uses cancelPendingNavigation, not a nil navigation failure. Reuse
sameOrigin and routePolicy without external-provider continuation flags, reject
userinfo and non-cabinet documents. No generic dialog service is needed.

## Themes, overlays and focus

Decision: reuse scoped tokens and existing attributes/handlers. Explicit theme
wins; sidebar may independently remain dark. Bound overlay geometry to viewport
and remove hidden overflow. Rationale: observed six-theme matrix,375px tooltip
overflow and550px flipped submenu. Reject new dependency or per-page offsets.

## Language and copy

Decision: retain locale persistence per F140 FR-014; state UI currently Russian.
No claim of completed translation or removal of en-US. Calendar connection does
not enable recording; native per-app policy remains. Personal formats are scoped
to current workspace; roles/status labels change, machine codes do not.

## Retirement

Decision: retire audited20 exact dead CSS tokens and19 macros only after fresh
consumer search, preserving mixed-selector siblings. Replace demo privacy test
with production renderer coverage. All46 template files have production references.
Reject deletion of active/dynamic classes, F201 disabled entries or broad legacy.

## Reservation

F243 umbrella #6567 reserved by scripts/claim-feature.py. Git extension exact
branch override passed full branch as slug and failed before mutation; separate
valid slug allocation succeeded after adding feature label. No guard bypassed.
Bootstrap-source repair is outside this cabinet task.
