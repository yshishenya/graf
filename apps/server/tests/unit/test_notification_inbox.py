from datetime import UTC, datetime
from uuid import uuid4

import pytest

from twobrain_rec_server.db.models.notifications import ServerNotification
from twobrain_rec_server.notifications.inbox import (
    acknowledge_revision,
    apply_event,
    decode_cursor,
    encode_cursor,
)


def test_retry_and_view_do_not_resolve_or_rearm_incident():
    row = ServerNotification(kind='processing_failed', revision=2, read_revision=2, requires_action=True)
    apply_event(row, kind='processing_failed', source_revision='retry', now=datetime.now(UTC))
    assert row.revision == 2 and row.requires_action
    apply_event(row, kind='result_ready', source_revision='accepted', now=datetime.now(UTC))
    assert not row.requires_action and row.resolved_at
    apply_event(row, kind='processing_failed', source_revision='new-incident', now=datetime.now(UTC))
    assert row.revision == 4 and row.requires_action
    acknowledge_revision(row, 2)
    assert row.read_revision == 2
    with pytest.raises(ValueError):
        acknowledge_revision(row, 5)
    with pytest.raises(ValueError):
        apply_event(row, kind='local_upload', source_revision='x', now=datetime.now(UTC))


def test_cursor_is_bound_to_auth_scope_filter_and_expiry():
    now = datetime.now(UTC)
    marker = (now, uuid4())
    cursor = encode_cursor(marker, binding='owner:session:scope:history', secret='test-key', now=now)
    assert decode_cursor(cursor, binding='owner:session:scope:history', secret='test-key', now=now) == marker
    for binding in ['other:session:scope:history', 'owner:session:scope:important']:
        with pytest.raises(ValueError):
            decode_cursor(cursor, binding=binding, secret='test-key', now=now)
    with pytest.raises(ValueError):
        decode_cursor(cursor+'x', binding='owner:session:scope:history', secret='test-key', now=now)
