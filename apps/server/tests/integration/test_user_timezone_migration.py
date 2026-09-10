"""The preference migration preserves choices and refuses lossy rollback."""
import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from twobrain_rec_server.config import get_settings


def test_user_timezone_migration_preserves_choices_and_guards_rollback(postgres_clean_database_url, monkeypatch):
    root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", postgres_clean_database_url)
    get_settings.cache_clear()
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "src/twobrain_rec_server/db/migrations"))
    command.upgrade(config, "0085_merge_summary_mediascribe")
    org, workspace, default, chosen, utc = [uuid4() for _ in range(5)]

    async def execute(sql, params=None):
        engine = create_async_engine(postgres_clean_database_url)
        try:
            async with engine.begin() as connection:
                result = await connection.execute(text(sql), params or {})
                return result.fetchall() if result.returns_rows else None
        finally:
            await engine.dispose()

    def query(sql, params=None):
        return asyncio.run(execute(sql, params))

    query("INSERT INTO organizations (id,slug,name) VALUES (:id,'timezone-test','Synthetic')", {"id": org})
    query("INSERT INTO workspaces (id,organization_id,slug,name) VALUES (:id,:org,'tz','Synthetic')",
          {"id": workspace, "org": org})
    for user_id, zone in ((default, "Europe/Moscow"), (chosen, "Europe/Moscow"), (utc, "UTC")):
        query("INSERT INTO user_identities (id,organization_id,external_subject,timezone) VALUES (:id,:org,:subject,:zone)",
              {"id": user_id, "org": org, "subject": str(user_id), "zone": zone})
    query("""INSERT INTO auth_audit_events (id,workspace_id,user_id,event_type,outcome,metadata_json)
             VALUES (:id,:workspace,:user,'account_preferences_updated','success','{"fields":["timezone"]}')""",
          {"id": uuid4(), "workspace": workspace, "user": chosen})
    query("""INSERT INTO auth_audit_events (id,workspace_id,user_id,event_type,outcome,metadata_json)
             VALUES (:id,:workspace,:user,'account_preferences_updated','failure','{"fields":["timezone"]}')""",
          {"id": uuid4(), "workspace": workspace, "user": default})
    command.upgrade(config, "0091_comment_reader_projection")
    rows = dict(query("SELECT id,timezone FROM user_identities"))
    assert rows == {default: None, chosen: "Europe/Moscow", utc: "UTC"}
    fresh = uuid4()
    query("INSERT INTO user_identities (id,organization_id,external_subject) VALUES (:id,:org,:subject)",
          {"id": fresh, "org": org, "subject": str(fresh)})
    assert query("SELECT timezone FROM user_identities WHERE id=:id", {"id": fresh})[0][0] is None
    query("UPDATE user_identities SET timezone='Asia/Kathmandu' WHERE id=:id", {"id": fresh})
    with pytest.raises(Exception, match="Cannot downgrade: account time zones exceed Moscow/UTC"):
        command.downgrade(config, "0085_merge_summary_mediascribe")
    assert query("SELECT timezone FROM user_identities WHERE id=:id", {"id": fresh})[0][0] == "Asia/Kathmandu"
    query("UPDATE user_identities SET timezone='UTC' WHERE id=:id", {"id": fresh})
    command.downgrade(config, "0085_merge_summary_mediascribe")
    assert query("SELECT timezone FROM user_identities WHERE id=:id", {"id": default})[0][0] == "Europe/Moscow"
    command.upgrade(config, "0091_comment_reader_projection")
    assert query("SELECT timezone FROM user_identities WHERE id=:id", {"id": chosen})[0][0] == "Europe/Moscow"
