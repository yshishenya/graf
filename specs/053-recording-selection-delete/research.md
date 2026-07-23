# Research: Recording Selection And Delete

## Decision: Reuse The Existing Deletion Lifecycle Endpoint

**Rationale**: `/api/v1/cabinet/meetings/{meeting_id}/deletion-requests` already validates access, requires bounded confirmation copy, writes audit/report rows, and blocks deleted meetings from active list queries. Calling it from the list UI preserves deletion truth with the smallest code change.

**Alternatives considered**:
- New batch deletion endpoint: deferred. The current list limit is small and no throughput need justifies a second API.
- Client-only hiding: rejected because it would fake deletion without lifecycle accounting.

## Decision: Keep Bulk Download Disabled

**Rationale**: The user wants a download icon for interaction parity but explicitly says download is later. A disabled button with Russian explanatory text avoids new egress/audit behavior.

**Alternatives considered**:
- Wire existing per-meeting downloads: rejected because bulk download UX, package policy, and audit semantics are a separate slice.

## Decision: Replace Row Future Actions With Direct Delete

**Rationale**: The existing row actions are placeholders for future star/tag/access/more. The requested production path needs only delete now, and unread/overflow menus are out of scope.

**Alternatives considered**:
- Add a KRISP-like three-dot menu: rejected by user request and unnecessary scope.

## Decision: Use Inline Browser JavaScript In Existing Shell

**Rationale**: `cabinet/web.py` already owns server-rendered HTML and embeds page scripts. A small script can manage selection, dialog state, and delete requests without new frontend packaging.

**Alternatives considered**:
- New frontend bundle: rejected because the current surface is server-rendered and no dependency is needed.

## Decision: Keep The Report Out Of The Normal Owner Flow

**Rationale**: The owner asked for a fast, direct delete of the selected recording. The current web response replaces the list outcome with a detailed lifecycle report link and a persistent status block even though the request has already removed server-controlled content and the row should no longer be actionable. Removing the status block and the accepted row fixes the confusing hand-off without weakening the existing lifecycle accounting.

**Alternatives considered**:
- Delete the lifecycle report endpoint: rejected because support and operators still need the truthful artifact, dependency, backup, and local-purge status.
- Hide the row only in the browser: rejected because the server must accept the deletion request and keep the existing audit/report records.
- Add a new batch deletion API: rejected because the current list limit is small and the existing per-meeting request already handles partial failure safely.
