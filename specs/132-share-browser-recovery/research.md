# Research: browser invitation error responses

## Decision 1: Keep state semantics and change only the browser presentation

- **Decision**: Treat a consumed, expired, revoked, malformed or
  recipient-mismatched invitation as the existing safe domain failure. Change
  only the response shown to a browser request.
- **Rationale**: Production metadata shows a successful first magic-link POST
  followed by a second POST returning 404. The continuation is intentionally
  one-time; making it reusable would weaken replay protection.
- **Alternatives considered**:
  - Reuse the continuation after the first success — rejected because it would
    turn an exchange credential into a replayable credential.
  - Return a new invitation from the error path — rejected because it changes
    authorization and delivery semantics.

## Decision 2: Reuse the cabinet shell and a dedicated safe unavailable state

- **Decision**: Render a short invitation-unavailable page through the existing
  server-rendered cabinet shell and private/no-store response conventions.
- **Rationale**: The existing invitation page already has safe unavailable copy,
  and the cabinet shell supplies the product navigation and security headers.
  A dedicated state avoids exposing meeting metadata through an error handler.
- **Alternatives considered**:
  - Return a generic plain HTML string from the problem handler — rejected as
    inconsistent with the cabinet UI and accessibility conventions.
  - Redirect to a meeting or summary URL — rejected because the error path has
    no proof that the caller may view that meeting.

## Decision 3: Keep JSON for explicit API callers

- **Decision**: Requests that explicitly ask for JSON retain the current
  `application/problem+json` response, status and fields. Browser invitation
  paths with HTML, missing or generic `Accept` receive HTML for the human flow.
- **Rationale**: The user-facing defect is the JSON file in a browser; changing
  API consumers would be an unrelated contract break. Invitation browser paths
  are not public machine APIs, so generic browser navigation can safely prefer
  the human response there.
- **Alternatives considered**:
  - Make every ProblemDetail response HTML — rejected because API clients and
    operational tooling rely on the existing JSON contract.
  - Require every browser to send `Accept: text/html` — rejected because email
    clients, link previews and some embedded browsers send `*/*` or omit it.

## Decision 4: Preserve metadata-only diagnostics

- **Decision**: Keep the existing redacted request-path logging and do not add
  invitation tokens, continuation values, recipient addresses or meeting
  content to the HTML response or evidence.
- **Rationale**: The production diagnosis was possible from route/status and
  timing alone; the same evidence is sufficient for regression and operations.
