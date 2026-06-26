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
