"""Бюджет обращений к базе для страницы списка встреч.

Предохранитель для SC-001 и SC-006 из ``specs/270-cabinet-query-efficiency/spec.md``.

Страница списка встреч раньше обращалась к базе пропорционально числу встреч
(около 30,5 обращения на встречу: 144 при пяти, 609 при двадцати). Проверка
считает фактические обращения и падает, если эта зависимость вернётся.

Проверка намеренно не измеряет время: она детерминированная и не зависит от
загрузки и скорости машины, поэтому не становится источником ложных падений.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import event

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
from twobrain_rec_server.db.models import Meeting

MEETINGS_PATH = "/api/v1/cabinet/meetings"

SMALL_MEETING_COUNT = 5
LARGE_MEETING_COUNT = 50

# Допустимый рост числа обращений при росте числа встреч с 5 до 50.
MAX_GROWTH_RATIO = 0.25

# Абсолютный потолок, чтобы «постоянный, но огромный» расход тоже был замечен.
MAX_LARGE_PAGE_QUERIES = 80


def _meeting(index: int, started_at: datetime) -> Meeting:
    return Meeting(
        workspace_id=WORKSPACE_ID,
        created_by_user_id=USER_ID,
        device_id=DEVICE_ID,
        local_recording_id=f"query-budget-{index:04d}",
        title=f"Synthetic Query Budget {index:04d}",
        title_source="app_context",
        title_updated_at=started_at,
        started_at=started_at,
        ended_at=started_at + timedelta(minutes=30),
        duration_seconds=1800,
        status="draft",
        processing_status="not_submitted",
    )


def _seed_meetings(client, *, start: int, stop: int, base: datetime) -> None:
    async def seed() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add_all(
                [_meeting(index, base + timedelta(minutes=index)) for index in range(start, stop)]
            )
            await db.commit()

    client.portal.call(seed)


def _count_page_queries(client) -> int:
    engine = client.app_state["engine"]
    counter = {"value": 0}

    def _on_before_cursor_execute(_conn, _cursor, _statement, _parameters, _context, _many) -> None:
        counter["value"] += 1

    event.listen(engine.sync_engine, "before_cursor_execute", _on_before_cursor_execute)
    try:
        response = client.get(MEETINGS_PATH, headers=auth_headers())
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", _on_before_cursor_execute)

    assert response.status_code == 200, response.text
    return counter["value"]


def test_meeting_list_query_count_does_not_grow_with_meeting_count(client) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)

    _seed_meetings(client, start=0, stop=SMALL_MEETING_COUNT, base=base)
    small_page_queries = _count_page_queries(client)

    _seed_meetings(client, start=SMALL_MEETING_COUNT, stop=LARGE_MEETING_COUNT, base=base)
    large_page_queries = _count_page_queries(client)

    growth_ratio = (large_page_queries - small_page_queries) / small_page_queries

    assert growth_ratio <= MAX_GROWTH_RATIO, (
        "страница списка встреч снова обращается к базе пропорционально числу встреч: "
        f"{SMALL_MEETING_COUNT} встреч — {small_page_queries} обращений, "
        f"{LARGE_MEETING_COUNT} встреч — {large_page_queries} обращений "
        f"(рост {growth_ratio:.0%} при допустимых {MAX_GROWTH_RATIO:.0%}); "
        "проверьте цикл по встречам в list_cabinet_meetings"
    )
    assert large_page_queries <= MAX_LARGE_PAGE_QUERIES, (
        "страница списка встреч расходует слишком много обращений к базе: "
        f"{large_page_queries} при потолке {MAX_LARGE_PAGE_QUERIES}"
    )
