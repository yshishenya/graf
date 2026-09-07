"""Audited system audio egress; no tenant-admin shortcut or public object URL."""

import asyncio
import secrets
import time
from dataclasses import replace
from types import SimpleNamespace
from uuid import UUID

from anyio import to_thread
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import text

from twobrain_rec_server.cabinet.egress import (
    _is_stored_review_m4a,
    _playback_response_for_range,
    _stream_storage_object,
)
from twobrain_rec_server.db.tenant_context import apply_system_context
from twobrain_rec_server.system_admin.audit import authorize_access
from twobrain_rec_server.system_admin.auth import hash_token


class SystemAudioResponse(StreamingResponse):
    async def __call__(self, scope, receive, send):
        slots = scope["app"].state.media_stream_slots
        try:
            async with asyncio.timeout(0.1):
                await slots.acquire()
        except TimeoutError:
            await JSONResponse({"error": "media_busy"}, status_code=429,
                headers={"Retry-After": "5", "Cache-Control": "no-store"})(scope, receive, send)
            return
        try:
            await super().__call__(scope, receive, send)
        finally:
            slots.release()


def _artifact(source: dict | None):
    if source is None:
        raise PermissionError("audio access unavailable")
    artifact = SimpleNamespace(**source["artifact"])
    if not _is_stored_review_m4a(artifact, job=SimpleNamespace(**source["job"])):
        raise PermissionError("canonical audio unavailable")
    return artifact


async def issue_media_ticket(sessions, context, *, revision_id: UUID | None = None) -> dict:
    context = await authorize_access(sessions, context)
    token = secrets.token_urlsafe(32)
    async with sessions() as session:
        await apply_system_context(session, context)
        result = await session.scalar(text("select system_control.create_media_ticket(:hash,:meeting,:revision)"),
            {"hash": hash_token(token), "meeting": context.target_id, "revision": revision_id})
        artifact = _artifact(result["source"] if result else None)
        await session.commit()
    return {"ticket": token, "expires_at": result["expires_at"], "revision_id": artifact.media_revision_id,
            "byte_length": artifact.byte_length, "duration_seconds": artifact.duration_seconds}


async def _source(sessions, context, digest, lease, new_lease=None):
    async with sessions() as session:
        await apply_system_context(session, context)
        source = await session.scalar(text("select system_control.media_ticket_source(:hash,:lease,:new)"),
            {"hash": digest, "lease": hash_token(lease) if lease else None,
             "new": hash_token(new_lease) if new_lease else None})
        artifact = _artifact(source)
        await session.commit()
    return artifact


async def audio_response(sessions, context, *, token: str, cookies, storage, range_header: str | None):
    if not 40 <= len(token) <= 100:
        raise PermissionError("invalid media ticket")
    digest = hash_token(token)
    async with sessions() as session:
        await apply_system_context(session, context)
        ticket = await session.scalar(text("select system_control.describe_media_ticket(:hash)"), {"hash": digest})
    if ticket is None:
        raise PermissionError("media ticket unavailable")
    cookie_name = "__Host-graf_system_media_" + UUID(ticket["id"]).hex
    old_lease = cookies.get(cookie_name)
    if old_lease is not None and not 40 <= len(old_lease) <= 100:
        raise PermissionError("invalid media lease")
    lease = old_lease or secrets.token_urlsafe(32)
    context = await authorize_access(sessions, replace(context, permission=ticket["permission"],
        target_type="meeting", target_id=UUID(ticket["meeting_id"]), case_context_id=UUID(ticket["case_context_id"])))
    artifact = await _source(sessions, context, digest, old_lease, lease if old_lease is None else None)
    try:
        async with asyncio.timeout(15):
            stat = await storage.stat_object_async(artifact.storage_object_key)
        if stat.size != artifact.byte_length:
            raise ValueError("audio size mismatch")
    except Exception:
        raise ValueError("Запись временно недоступна в хранилище") from None
    filename = f"graf-{ticket['meeting_id']}.m4a"
    status, headers, offset, length = _playback_response_for_range(artifact.byte_length, range_header, filename=filename)
    if ticket["permission"] == "audio.download":
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    async def chunks():
        body = None
        active_context = context
        audited_at = time.monotonic()
        transferred = 0
        try:
            body = await _stream_storage_object(storage, artifact.storage_object_key, offset=offset, length=length)
            while True:
                async with asyncio.timeout(15):
                    chunk = await to_thread.run_sync(lambda: next(body, None))
                if chunk is None:
                    if transferred != length:
                        raise RuntimeError("system media stream incomplete")
                    break
                if not isinstance(chunk, bytes) or transferred + len(chunk) > length:
                    raise RuntimeError("system media stream size mismatch")
                if time.monotonic() - audited_at >= 30:
                    active_context = await authorize_access(sessions, active_context)
                    audited_at = time.monotonic()
                # A fresh DB statement before every chunk rechecks session,
                # object grant, case, deletion and the pinned canonical source.
                await _source(sessions, active_context, digest, lease)
                transferred += len(chunk)
                yield chunk
        except Exception:
            # Never embed storage keys, driver parameters or token URLs in logs.
            raise RuntimeError("system media stream interrupted") from None
        finally:
            close = getattr(body, "close", None)
            if close:
                await to_thread.run_sync(close)

    response = SystemAudioResponse(chunks(), status_code=status, media_type="audio/mp4", headers=headers)
    if old_lease is None:
        response.set_cookie(cookie_name, lease, secure=True, httponly=True, samesite="strict", path="/", max_age=900)
    return response
