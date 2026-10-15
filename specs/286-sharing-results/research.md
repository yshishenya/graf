# Research — F286

Source SHA df9c8f4ee4b538cba6c42e1fad6007595e22774a. Production 02c79e147e736b00ee1443f6face957bc950b99d is an ancestor; newer base changes only approved F278 evidence.

- Decision: retain encrypted token plus saved allowlisted summary. Existing access.py:create_scoped_share_grant rotates on re-create; share_panel_state skips link grants; load_pinned_egress_outcome disallows superseded. Snapshot isolates sharing without weakening exports/global loaders.
- Decision: new batch ledger reuses existing Postal transport and DispatchIntent/Temporal. Existing _send_internal_share_notification runs after commit without durable recipient state; unknown acceptance cannot safely be retried. Existing InvitationDeliveryWorkflow establishes sending-before-network pattern.
- Decision: exact email confirmation through current auth. Existing browser magic bootstrap may authenticate original invited address from forwarded token; new summary invitations must never take that path. Old full_meeting package stays intact.
- Decision: new owner/workspace preferences + exact series_key, never billing/notification settings. CalendarParticipant PK churns; rules bind approved user IDs/address hashes. normalize internal domain guesses and attendeesOmitted omissions are insufficient for AUTO; check actual active workspace and verified identity, completeness, privacy and freshness.
- Decision: new pending batches do not grant access during scheduled delay. Commit network reservation after current cancellation/ACL check; unknown stays unknown. Worker recovery never equates X-2brain-Delivery-Key with provider exactly-once.
- Decision: reuse cabinet CSS and native dialog. References: official Krisp Share/Auto-share instructions and approved synthetic prototype; own assets only. Simple results remain user-confirmed «Итоги отправлены».
- Alternatives rejected: live mutable summary, bearer invitation sign-in, re-send all, auto external audience, new services, front-end timer, matching series by title. They violate stable document, identity or explicit control.
