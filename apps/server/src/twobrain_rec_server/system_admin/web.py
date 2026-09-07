"""Console HTTP routes use only the separate system session cookie."""

import base64
import hmac
import json
import secrets
import time
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, SecretStr, model_validator
from sqlalchemy import text

from twobrain_rec_server.billing.catalog import CatalogNotApproved
from twobrain_rec_server.cabinet.web_routes.auth_email_flow import _normalize_email
from twobrain_rec_server.db.tenant_context import SystemDatabaseContext
from twobrain_rec_server.system_admin.auth import (
    PasswordQueueFull,
    create_recovery_codes,
    create_totp_seed,
    decrypt_totp,
    encrypt_totp,
    hash_password,
    hash_token,
    matching_totp_counter,
    verify_password,
)
from twobrain_rec_server.system_admin.permissions import ROLE_PERMISSIONS
from twobrain_rec_server.system_admin.schemas import CommitOperation, MeetingPreview

router = APIRouter(prefix="/api/system-admin/v1")
PREAUTH_COOKIE = "__Host-graf_system_preauth"
SESSION_COOKIE = "__Host-graf_system_session"


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: Annotated[str, Field(min_length=1, max_length=320)]
    password: SecretStr


class MfaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge: Annotated[str, Field(min_length=40, max_length=100)]
    code: Annotated[str | None, Field(pattern=r"^[0-9]{6}$")] = None
    recovery_code: SecretStr | None = None

    @model_validator(mode="after")
    def single_proof(self):
        if (self.code is None) == (self.recovery_code is None):
            raise ValueError("one second factor is required")
        return self


class EnrolmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge: Annotated[str, Field(min_length=40, max_length=100)]
    password: SecretStr | None = None



async def _sql(request: Request, query: str, **parameters):
    async with request.app.state.system_sessions() as session:
        result = await session.scalar(text(query), parameters)
        await session.commit()
        return result


async def current_admin(request: Request) -> tuple[dict, SystemDatabaseContext]:
    token = request.cookies.get(SESSION_COOKIE, "")
    if not 40 <= len(token) <= 100:
        raise HTTPException(401, "Требуется вход администратора")
    digest = hash_token(token)
    identity = await _sql(request, "select system_control.auth_session(:token)", token=digest)
    if identity is None:
        raise HTTPException(401, "Сессия завершена. Войдите снова")
    return identity, SystemDatabaseContext(
        admin_session_id=UUID(identity["session_id"]), actor_id=UUID(identity["principal_id"]),
        session_token_hash=digest, permission="users.read",
    )


@router.post("/auth/login")
async def login(request: Request, payload: LoginInput):
    email = _normalize_email(payload.email) or "invalid"
    network = request.client.host if request.client else "unknown"
    attempt = uuid4()
    for kind, value in (("global", "console"), ("network", network), ("account", email)):
        admitted = await _sql(request, "select system_control.auth_rate_limit(:bucket,:kind,:attempt)",
                              bucket=hash_token(value), kind=kind, attempt=attempt)
        if not admitted:
            raise HTTPException(429, "Слишком много попыток. Повторите через 15 минут",
                                headers={"Retry-After": "900"})
    candidate = await _sql(request, "select system_control.auth_lookup(:email)", email=email)
    encoded = candidate["password_hash"] if candidate else request.app.state.dummy_password_hash
    try:
        valid = await request.app.state.password_computations.run(
            verify_password, payload.password.get_secret_value(), encoded,
        )
    except PasswordQueueFull:
        raise HTTPException(429, "Сервис входа занят. Повторите позже",
                            headers={"Retry-After": "5"}) from None
    await _sql(request, "select system_control.auth_login_result(:email,:success,:attempt)",
               email=email, success=bool(valid and candidate), attempt=attempt)
    if not valid or candidate is None:
        raise HTTPException(401, "Неверные данные для входа")
    token = secrets.token_urlsafe(32)
    issued = await _sql(request, "select system_control.auth_issue_preauth(:actor,:version,:credential,:hash)",
                        actor=UUID(candidate["principal_id"]), version=candidate["auth_version"],
                        credential=candidate["credential_version"], hash=hash_token(token))
    if not issued:
        raise HTTPException(401, "Неверные данные для входа")
    response = JSONResponse({"challenge": token, "state": "mfa_required"})
    response.set_cookie(PREAUTH_COOKIE, token, secure=True, httponly=True,
                        samesite="strict", path="/", max_age=300)
    return response


@router.post("/auth/mfa")
async def mfa(request: Request, payload: MfaInput):
    if not hmac.compare_digest(request.cookies.get(PREAUTH_COOKIE, ""), payload.challenge):
        raise HTTPException(401, "Проверка входа завершена. Введите пароль снова")
    digest = hash_token(payload.challenge)
    attempt = uuid4()
    if not await _sql(request, "select system_control.auth_factor_attempt(:hash,:attempt)", hash=digest, attempt=attempt):
        raise HTTPException(429, "Слишком много попыток. Повторите через 15 минут", headers={"Retry-After":"900"})
    if payload.recovery_code is not None:
        token = secrets.token_urlsafe(32)
        recovered = await _sql(request, "select system_control.auth_recover(:hash,:code,:new)",
            hash=digest, code=hash_token(payload.recovery_code.get_secret_value()), new=hash_token(token))
        await _sql(request, "select system_control.auth_factor_attempt(:hash,:attempt,:success)",
                   hash=digest, attempt=attempt, success=bool(recovered))
        if not recovered:
            raise HTTPException(401, "Неверный или уже использованный код")
        response = JSONResponse({"state": "mfa_enrolment_required", "challenge": token})
        response.set_cookie(PREAUTH_COOKIE, token, secure=True, httponly=True,
                            samesite="strict", path="/", max_age=300)
        response.delete_cookie(SESSION_COOKIE, secure=True, httponly=True, samesite="strict", path="/")
        return response
    challenge = await _sql(request, "select system_control.auth_challenge(:hash)", hash=digest)
    if not challenge or challenge["kind"] != "preauth" or not challenge["seed"]:
        raise HTTPException(401, "Проверка входа завершена. Введите пароль снова")
    key = request.app.state.totp_keys.get(challenge["key_id"])
    if key is None:
        raise HTTPException(503, "Вход временно недоступен")
    seed = decrypt_totp(bytes.fromhex(challenge["seed"]), nonce=bytes.fromhex(challenge["nonce"]),
                        principal_id=UUID(challenge["principal_id"]), key=key)
    counter = matching_totp_counter(seed, payload.code, now=time.time(), last_counter=challenge["last_counter"])
    if counter is None:
        await _sql(request, "select system_control.auth_factor_attempt(:hash,:attempt,false)", hash=digest, attempt=attempt)
        raise HTTPException(401, "Неверный или уже использованный код")
    token = secrets.token_urlsafe(32)
    identity = await _sql(request, "select system_control.auth_finish_totp(:hash,:counter,:session)",
                         hash=digest, counter=counter, session=hash_token(token))
    await _sql(request, "select system_control.auth_factor_attempt(:hash,:attempt,:success)",
               hash=digest, attempt=attempt, success=bool(identity))
    if not identity:
        raise HTTPException(401, "Неверный или уже использованный код")
    response = JSONResponse({"state": "authenticated"})
    response.set_cookie(SESSION_COOKIE, token, secure=True, httponly=True,
                        samesite="strict", path="/", max_age=12 * 60 * 60)
    response.delete_cookie(PREAUTH_COOKIE, secure=True, httponly=True, samesite="strict", path="/")
    return response


@router.get("/me")
async def me(request: Request):
    identity, _ = await current_admin(request)
    return {**identity, "permissions": sorted(ROLE_PERMISSIONS.get(identity["role"], ())) }


@router.post("/auth/activity")
async def activity(request: Request):
    _, context = await current_admin(request)
    if not await _sql(request, "select system_control.auth_session_action(:hash,'activity')",
                      hash=context.session_token_hash):
        raise HTTPException(401, "Сессия завершена")
    return {"status": "ok"}


@router.post("/auth/logout")
async def logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE, "")
    if 40 <= len(token) <= 100:
        await _sql(request, "select system_control.auth_session_action(:hash,'logout')", hash=hash_token(token))
    response = JSONResponse({"status": "ok"})
    for cookie in (SESSION_COOKIE, PREAUTH_COOKIE):
        response.delete_cookie(cookie, secure=True, httponly=True, samesite="strict", path="/")
    return response


@router.post("/auth/enrolment/begin")
async def begin_enrolment(request: Request, payload: EnrolmentInput):
    digest = hash_token(payload.challenge)
    candidate = await _sql(request, "select system_control.auth_challenge(:hash)", hash=digest)
    if not candidate or candidate["kind"] not in ("invitation", "enrolment"):
        raise HTTPException(401, "Приглашение недействительно или срок истёк")
    principal = UUID(candidate["principal_id"])
    next_token = payload.challenge
    if candidate["seed"] and candidate["kind"] == "enrolment":
        key = request.app.state.totp_keys.get(candidate["key_id"])
        if key is None:
            raise HTTPException(503, "Вход временно недоступен")
        seed = base64.b32encode(decrypt_totp(bytes.fromhex(candidate["seed"]),
            nonce=bytes.fromhex(candidate["nonce"]), principal_id=principal, key=key)).decode()
    else:
        password = None
        if candidate["kind"] == "invitation":
            if payload.password is None or not 14 <= len(payload.password.get_secret_value()) <= 128:
                raise HTTPException(422, "Пароль должен содержать от 14 до 128 символов")
            try:
                password = await request.app.state.password_computations.run(
                    hash_password, payload.password.get_secret_value())
            except PasswordQueueFull:
                raise HTTPException(429, "Сервис входа занят", headers={"Retry-After": "5"}) from None
        seed = create_totp_seed()
        key_id = request.app.state.active_totp_key
        nonce, encrypted = encrypt_totp(seed, principal_id=principal, key=request.app.state.totp_keys[key_id])
        next_token = secrets.token_urlsafe(32)
        saved = await _sql(request,
            "select system_control.auth_begin_enrolment(:hash,:password,:seed,:nonce,:key,:new_hash)",
            hash=digest,password=password,seed=encrypted,nonce=nonce,key=key_id,new_hash=hash_token(next_token))
        if not saved:
            raise HTTPException(409, "Настройка изменилась. Откройте её заново")
    response = JSONResponse({"state": "mfa_enrolment_required", "seed": seed, "challenge": next_token})
    response.set_cookie(PREAUTH_COOKIE, next_token, secure=True, httponly=True,
                        samesite="strict", path="/", max_age=300)
    return response


@router.post("/auth/enrolment/confirm")
async def confirm_enrolment(request: Request, payload: MfaInput):
    if payload.code is None or not hmac.compare_digest(request.cookies.get(PREAUTH_COOKIE, ""), payload.challenge):
        raise HTTPException(401, "Настройка второго фактора недействительна")
    digest = hash_token(payload.challenge)
    candidate = await _sql(request, "select system_control.auth_challenge(:hash)", hash=digest)
    if not candidate or candidate["kind"] != "enrolment" or not candidate["seed"]:
        raise HTTPException(401, "Настройка второго фактора недействительна")
    key = request.app.state.totp_keys.get(candidate["key_id"])
    if key is None:
        raise HTTPException(503, "Вход временно недоступен")
    seed = decrypt_totp(bytes.fromhex(candidate["seed"]), nonce=bytes.fromhex(candidate["nonce"]),
                        principal_id=UUID(candidate["principal_id"]), key=key)
    counter = matching_totp_counter(seed, payload.code, now=time.time(), last_counter=-1)
    if counter is None:
        raise HTTPException(401, "Неверный код")
    codes, code_hashes = create_recovery_codes()
    token = secrets.token_urlsafe(32)
    identity = await _sql(request, "select system_control.auth_confirm_enrolment(:hash,:counter,:session,:codes)",
        hash=digest, counter=counter, session=hash_token(token), codes=code_hashes)
    if not identity:
        raise HTTPException(401, "Настройка второго фактора недействительна")
    response = JSONResponse({"state": "authenticated", "recovery_codes": codes})
    response.set_cookie(SESSION_COOKIE, token, secure=True, httponly=True,
                        samesite="strict", path="/", max_age=12 * 60 * 60)
    response.delete_cookie(PREAUTH_COOKIE, secure=True, httponly=True, samesite="strict", path="/")
    return response


ROLE_LABELS = {
    "superadmin": "Суперадминистратор", "system_admin": "Системный администратор",
    "support": "Поддержка", "billing_manager": "Менеджер биллинга", "analyst": "Аналитик", "auditor": "Аудитор",
}


class AdministratorUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Annotated[int, Field(strict=True, ge=1)]
    role: str
    status: str
    expires_at: AwareDatetime | None = None
    reason: Annotated[str, Field(min_length=1, max_length=1000)]


@router.get("/admins")
async def administrators(request: Request, after: UUID | None = None):
    from dataclasses import replace

    from twobrain_rec_server.db.tenant_context import apply_system_context

    _, context = await current_admin(request)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session, replace(context, permission="admins.manage"))
        result = await session.scalar(text("select system_control.list_administrators(:after)"), {"after": after})
    if result is None:
        raise HTTPException(403, "Недостаточно прав")
    return {"items": result}


@router.patch("/admins/{principal_id}")
async def update_administrator(request: Request, principal_id: UUID, payload: AdministratorUpdate):
    from dataclasses import replace

    from twobrain_rec_server.db.tenant_context import apply_system_context

    if not request.app.state.commands_enabled:
        raise HTTPException(503, "Изменения временно отключены оператором")
    if payload.role not in ROLE_LABELS or payload.status not in ("active", "invited", "recovery_pending", "blocked", "revoked"):
        raise HTTPException(422, "Неизвестная роль или состояние")
    expires = payload.expires_at
    _, context = await current_admin(request)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session, replace(context, permission="admins.manage"))
        result = await session.scalar(text("""select system_control.update_administrator
            (:id,:version,:role,:status,:expiry,:reason)"""),
            {"id": principal_id,"version": payload.version,"role": payload.role,"status": payload.status,
             "expiry": expires,"reason": payload.reason})
        await session.commit()
    if "error" in result:
        messages = {"last_superadmin": "Нельзя удалить последнее бессрочное назначение суперадминистратора",
                    "version_conflict": "Данные изменились. Обновите страницу и повторите изменение",
                    "access_denied": "Недостаточно прав или требуется повторный вход со вторым фактором",
                    "enrolment_required": "Администратор должен завершить настройку второго фактора"}
        raise HTTPException(409, messages.get(result["error"], "Проверьте поля формы"))
    return result


@router.get("/meetings")
async def meeting_list(request: Request, after: UUID | None = None):
    from twobrain_rec_server.system_admin.queries import meetings

    identity, context = await current_admin(request)
    if "meetings.metadata" not in ROLE_PERMISSIONS[identity["role"]]:
        raise HTTPException(403, "Недостаточно прав")
    return await meetings(request.app.state.system_sessions, context, after=after)


class StepUpInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Annotated[str, Field(pattern=r"^[0-9]{6}$")]


@router.post("/auth/step-up")
async def step_up(request: Request, payload: StepUpInput):
    _, context = await current_admin(request)
    digest, attempt = context.session_token_hash, uuid4()
    if not await _sql(request, "select system_control.auth_factor_attempt(:hash,:attempt)", hash=digest, attempt=attempt):
        raise HTTPException(429, "Слишком много попыток", headers={"Retry-After":"900"})
    candidate = await _sql(request, "select system_control.auth_second_factor(:hash)", hash=digest)
    if candidate is None:
        raise HTTPException(401, "Сессия завершена")
    key = request.app.state.totp_keys.get(candidate["key_id"])
    if key is None:
        raise HTTPException(503, "Вход временно недоступен")
    seed = decrypt_totp(bytes.fromhex(candidate["seed"]), nonce=bytes.fromhex(candidate["nonce"]),
                        principal_id=UUID(candidate["principal_id"]), key=key)
    counter = matching_totp_counter(seed, payload.code, now=time.time(), last_counter=candidate["last_counter"])
    updated = bool(counter is not None and await _sql(request,
        "select system_control.auth_step_up(:hash,:counter)", hash=digest, counter=counter))
    await _sql(request, "select system_control.auth_factor_attempt(:hash,:attempt,:success)",
               hash=digest, attempt=attempt, success=updated)
    if not updated:
        raise HTTPException(403, "Неверный или уже использованный код")
    return {"status":"ok"}


class AdministratorInvite(BaseModel):
    expires_at: AwareDatetime | None = None
    model_config = ConfigDict(extra="forbid")
    email: Annotated[str, Field(min_length=3,max_length=240)]
    role: str
    reason: Annotated[str, Field(min_length=1,max_length=1000)]


@router.post("/admins", status_code=201)
async def invite_administrator(request: Request, payload: AdministratorInvite):
    from dataclasses import replace

    from twobrain_rec_server.db.tenant_context import apply_system_context

    if not request.app.state.commands_enabled:
        raise HTTPException(503, "Изменения временно отключены оператором")
    identity, context = await current_admin(request)
    if identity["role"] != "superadmin":
        raise HTTPException(403, "Недостаточно прав")
    if request.app.state.mailer is None:
        raise HTTPException(503, "Оператор ещё не настроил отправку приглашений")
    email = _normalize_email(payload.email)
    if email is None or payload.role not in ROLE_LABELS:
        raise HTTPException(422, "Проверьте адрес и роль")
    token = secrets.token_urlsafe(32)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session, replace(context,permission="admins.manage"))
        principal = await session.scalar(text("""select system_control.invite_administrator
            (:email,:role,:expiry,:reason,:hash)"""),
            {"email":email,"role":payload.role,"expiry":payload.expires_at,"reason":payload.reason,"hash":hash_token(token)})
        await session.commit()
    if principal is None:
        raise HTTPException(409, "Администратор уже существует или требуется повторный вход со вторым фактором")
    delivery = await _deliver_link(request, email, token, reset=False)
    return {"id":str(principal),"status":"invited","delivery_state":delivery}


async def _deliver_link(request: Request, email: str, token: str, *, reset: bool) -> str:
    from twobrain_rec_server.auth.email_delivery import EmailLoginDeliveryError

    digest = hash_token(token)
    if not await _sql(request, "select system_control.auth_delivery(:hash,'sending')", hash=digest):
        return "unknown"
    state = "submitted"
    try:
        page = "reset" if reset else "activate"
        await request.app.state.mailer.send_system_admin_link(recipient_email=email,
            url=f"{request.app.state.public_origin}/system-admin/{page}#{token}", reset=reset)
    except EmailLoginDeliveryError as error:
        state = "unknown" if error.outcome_unknown else "failed"
    # A crash between send and this commit leaves durable 'sending', never a
    # false delivery confirmation. Explicit resend invalidates the old link.
    await _sql(request, "select system_control.auth_delivery(:hash,:state)", hash=digest, state=state)
    return state


class ResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: Annotated[str,Field(min_length=1,max_length=240)]


class ResetComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: Annotated[str,Field(min_length=40,max_length=100)]
    password: SecretStr


@router.post("/auth/password-reset/request")
async def request_password_reset(request: Request, payload: ResetRequest):
    if request.app.state.mailer is None:
        raise HTTPException(503, "Оператор ещё не настроил отправку писем")
    email = _normalize_email(payload.email) or "invalid"
    network = request.client.host if request.client else "unknown"
    for kind,value in (("global","console"),("network",network),("account",email)):
        if not await _sql(request,"select system_control.auth_rate_limit(:bucket,:kind)",bucket=hash_token(value),kind=kind):
            raise HTTPException(429,"Слишком много попыток",headers={"Retry-After":"900"})
    token = secrets.token_urlsafe(32)
    principal = await _sql(request,"select system_control.auth_request_reset(:email,:hash)",email=email,hash=hash_token(token))
    if principal is not None:
        # Same public answer for known/unknown accounts and provider failures.
        await _deliver_link(request, email, token, reset=True)
    return {"status":"accepted","message":"Если учётная запись доступна, на её адрес отправлена ссылка"}


@router.post("/auth/password-reset/complete")
async def complete_password_reset(request: Request, payload: ResetComplete):
    candidate = await _sql(request,"select system_control.auth_challenge(:hash)",hash=hash_token(payload.token))
    if candidate is None or candidate["kind"] != "reset":
        raise HTTPException(401,"Ссылка недействительна или срок истёк")
    if not 14 <= len(payload.password.get_secret_value()) <= 128:
        raise HTTPException(422,"Пароль должен содержать от 14 до 128 символов")
    try:
        encoded = await request.app.state.password_computations.run(hash_password,payload.password.get_secret_value())
    except PasswordQueueFull:
        raise HTTPException(429,"Сервис входа занят",headers={"Retry-After":"5"}) from None
    saved = await _sql(request,"select system_control.auth_complete_reset(:hash,:password)",hash=hash_token(payload.token),password=encoded)
    if not saved:
        raise HTTPException(401,"Ссылка недействительна или срок истёк")
    response = JSONResponse({"status":"ok","message":"Пароль изменён. Войдите с прежним вторым фактором"})
    response.delete_cookie(SESSION_COOKIE,secure=True,httponly=True,samesite="strict",path="/")
    response.delete_cookie(PREAUTH_COOKIE,secure=True,httponly=True,samesite="strict",path="/")
    return response


@router.get("/users")
async def user_list(request: Request, after: UUID | None = None, plan: str | None = None, status: str | None = None):
    from twobrain_rec_server.system_admin.queries import users

    identity, context = await current_admin(request)
    if "users.read" not in ROLE_PERMISSIONS[identity["role"]]:
        raise HTTPException(403,"Недостаточно прав")
    return await users(request.app.state.system_sessions,context,after=after,plan=plan,status=status)


@router.get("/users/{user_id}")
async def user_detail(request: Request, user_id: UUID):
    from dataclasses import replace

    from twobrain_rec_server.db.tenant_context import apply_system_context
    _, context = await current_admin(request)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session, replace(context, permission="users.read", target_type="user", target_id=user_id))
        result = await session.scalar(text("select system_control.get_user_detail(:id)"), {"id": user_id})
    if result is None:
        raise HTTPException(404, "Пользователь не найден или недоступен")
    return result


class SearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: Annotated[str,Field(min_length=3,max_length=240)]


@router.post("/search")
async def search(request: Request,payload: SearchInput):
    from twobrain_rec_server.system_admin.queries import users

    identity, context = await current_admin(request)
    if "users.read" not in ROLE_PERMISSIONS[identity["role"]]:
        raise HTTPException(403,"Недостаточно прав")
    email = _normalize_email(payload.email)
    if email is None:
        raise HTTPException(422,"Введите полный адрес")
    return await users(request.app.state.system_sessions,context,email=email)


class PlanCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{2,31}$")]
    display_name: Annotated[str, Field(min_length=1, max_length=80)]
    capabilities: dict
    display_terms: dict
    monthly_amount_minor: Annotated[int | None, Field(strict=True, gt=0)] = None
    annual_amount_minor: Annotated[int | None, Field(strict=True, gt=0)] = None
    reason: Annotated[str, Field(min_length=10, max_length=500)]


class PlanStateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: Literal["open", "closed", "archived"]
    reason: Annotated[str, Field(min_length=10, max_length=500)]


class PlanPublishInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version_id: UUID
    reason: Annotated[str, Field(min_length=10, max_length=500)]


class CampaignCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Annotated[str, Field(min_length=3, max_length=48)]
    campaign_version: Annotated[str, Field(min_length=1, max_length=64)]
    plan_code: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{2,31}$")]
    cycle: Literal["month", "year"] | None = None
    benefit_kind: Literal["discount", "gift"]
    discount_percent: Annotated[int | None, Field(strict=True, ge=1, le=99)] = None
    gift_days: Annotated[int | None, Field(strict=True, ge=1, le=365)] = None
    audience: Literal["all", "never_paid", "first_purchase", "selected", "former_paid"] = "all"
    target_user_id: UUID | None = None
    max_redemptions: Annotated[int, Field(strict=True, ge=1, le=1_000_000)] = 1
    budget_minor: Annotated[int | None, Field(strict=True, gt=0)] = None
    starts_at: AwareDatetime | None = None
    ends_at: AwareDatetime | None = None
    display_name: Annotated[str | None, Field(max_length=120)] = None
    reason: Annotated[str, Field(min_length=10, max_length=500)]


class CampaignStateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: Literal["active", "paused", "finished", "archived"]
    reason: Annotated[str, Field(min_length=10, max_length=500)]


class CampaignCodesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: UUID
    count: Annotated[int, Field(strict=True, ge=1, le=1000)]
    prefix: Annotated[str, Field(min_length=3, max_length=20)] = "GRAF"
    target_user_ids: list[UUID | None] | None = None
    reason: Annotated[str, Field(min_length=10, max_length=500)]


class SubscriptionAdjustmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["subscription.adjust", "subscription.adjustment.revoke"] = "subscription.adjust"
    adjustment_kind: Literal["plan_interval", "allow", "deny", "extra_quota", "exact_limit"] | None = None
    adjustment_id: UUID | None = None
    subject_user_id: UUID | None = None
    feature_key: str | None = Field(default=None, max_length=40)
    value: object | None = None
    unit: str | None = Field(default=None, max_length=16)
    plan_version_id: UUID | None = None
    plan_mode: Literal["append", "overlay"] | None = None
    starts_at: AwareDatetime | None = None
    ends_at: AwareDatetime | None = None
    timezone: str = "UTC"
    source_ref: Annotated[str, Field(pattern=r"^[A-Za-z0-9:_-]{1,160}$")]
    reason: Annotated[str, Field(min_length=10, max_length=500)]
    expected_version: Annotated[int, Field(strict=True, ge=1)]

    @model_validator(mode="after")
    def validate_shape(self):
        if self.kind == "subscription.adjust":
            if self.adjustment_kind is None or self.adjustment_id is not None or self.starts_at is None or self.ends_at is None:
                raise ValueError("для назначения нужны вид, срок и интервал")
            if self.ends_at <= self.starts_at:
                raise ValueError("окончание должно быть позже начала")
        elif self.adjustment_id is None or self.adjustment_kind is not None:
            raise ValueError("для отзыва нужно существующее назначение")
        return self


class SubscriptionOperationCommit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preview_id: UUID
    expected_preview_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


def _catalog_error(result: dict) -> None:
    error = result.get("error")
    if not error:
        return
    status = 403 if error == "access_denied" else 409 if error in {"already_exists", "promotion_exhausted", "campaign_unavailable"} else 422
    messages = {"access_denied":"Недостаточно прав", "already_exists":"Такая запись уже существует",
                "promotion_exhausted":"Лимит акции исчерпан", "campaign_unavailable":"Акция недоступна",
                "invalid_catalog":"Условия тарифа не прошли проверку", "invalid_campaign":"Условия акции не прошли проверку",
                "invalid_batch":"Партия кодов недействительна", "code_already_exists":"Коллизия кода, повторите выпуск",
                "not_found":"Запись не найдена", "invalid_state":"Недопустимое состояние"}
    raise HTTPException(status, messages.get(error, "Операция недоступна"))


@router.get("/billing/subscriptions")
async def billing_subscriptions(request: Request, after: UUID | None = None,
                               plan: str | None = None, state: str | None = None):
    from dataclasses import replace

    from twobrain_rec_server.db.tenant_context import apply_system_context
    _, context = await current_admin(request)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session, replace(context, permission="billing.read"))
        items = await session.scalar(text("select system_control.list_billing_subscriptions(:after,:plan,:state)"),
                                     {"after": after, "plan": plan, "state": state})
    if items is None:
        raise HTTPException(403, "Недостаточно прав")
    return {"items": items[:100], "next_cursor": str(items[99]["workspace_id"]) if len(items)>100 else None}


@router.get("/billing/invoices")
async def billing_invoices(request: Request, after: UUID | None = None,
                           workspace_id: UUID | None = None, status: str | None = None):
    from dataclasses import replace

    from twobrain_rec_server.db.tenant_context import apply_system_context
    _, context = await current_admin(request)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session, replace(context, permission="billing.read"))
        items = await session.scalar(text("select system_control.list_billing_invoices(:after,:workspace,:status)"),
                                     {"after": after, "workspace": workspace_id, "status": status})
    if items is None:
        raise HTTPException(403, "Недостаточно прав")
    return {"items": items[:100], "next_cursor": str(items[99]["id"]) if len(items)>100 else None}


@router.get("/billing/refunds")
async def billing_refunds(request: Request, after: UUID | None = None, workspace_id: UUID | None = None):
    from dataclasses import replace

    from twobrain_rec_server.db.tenant_context import apply_system_context
    _, context = await current_admin(request)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session, replace(context, permission="billing.read"))
        items = await session.scalar(text("select system_control.list_billing_refunds(:after,:workspace)"),
                                     {"after": after, "workspace": workspace_id})
    if items is None:
        raise HTTPException(403, "Недостаточно прав")
    return {"items": items[:100], "next_cursor": str(items[99]["id"]) if len(items)>100 else None}


@router.get("/subscriptions/{workspace_id}/adjustments")
async def subscription_adjustments(request: Request, workspace_id: UUID, after: UUID | None = None):
    from dataclasses import replace

    from twobrain_rec_server.db.tenant_context import apply_system_context
    _, context = await current_admin(request)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session, replace(context, permission="billing.read"))
        items = await session.scalar(text("select system_control.list_subscription_adjustments(:after,:workspace)"),
                                     {"after": after, "workspace": workspace_id})
    if items is None:
        raise HTTPException(403, "Недостаточно прав")
    return {"items": items[:100], "next_cursor": str(items[99]["id"]) if len(items)>100 else None}


def _subscription_command(payload: SubscriptionAdjustmentInput, workspace_id: UUID) -> dict:
    values = payload.model_dump(exclude={"kind", "reason", "expected_version"}, mode="json")
    values["workspace_id"] = str(workspace_id)
    return {"kind": payload.kind, "target_id": str(workspace_id), "expected_version": payload.expected_version,
            "reason": payload.reason.strip(), "parameters": values}


@router.post("/subscriptions/{workspace_id}/adjustments/preview")
async def subscription_adjustment_preview(request: Request, workspace_id: UUID, payload: SubscriptionAdjustmentInput):
    from dataclasses import replace

    from twobrain_rec_server.db.tenant_context import apply_system_context
    if not request.app.state.commands_enabled:
        raise HTTPException(503, "Изменения временно отключены оператором")
    _, context = await current_admin(request)
    command = _subscription_command(payload, workspace_id)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session, replace(context, permission="billing.manage", target_type="subscription", target_id=workspace_id))
        result = await session.scalar(text("select system_control.preview_subscription_operation(cast(:command as jsonb))"),
                                      {"command": json.dumps(command, default=str)})
        await session.commit()
    result = dict(result or {})
    error = result.get("error")
    if error:
        status = 403 if error == "access_denied" else 409 if error == "version_conflict" else 422
        raise HTTPException(status, {"invalid_command":"Проверьте параметры назначения", "invalid_target":"Пространство не найдено",
                                     "version_conflict":"Подписка изменилась. Обновите карточку", "access_denied":"Недостаточно прав"}.get(error, "Предпросмотр недоступен"))
    result["effects"] = ["Будет добавлено неизменяемое назначение доступа" if payload.kind == "subscription.adjust" else "Будет создана запись отзыва назначения",
                          "Тариф, квота и оплаченные события не изменяются"]
    result["warnings"] = ["После запуска действие попадёт в очередь системного исполнителя"]
    result["requires_step_up"] = True
    return result


@router.post("/subscriptions/{workspace_id}/adjustments", status_code=202)
async def subscription_adjustment_commit(request: Request, workspace_id: UUID, payload: SubscriptionOperationCommit):
    from dataclasses import replace

    from twobrain_rec_server.db.tenant_context import apply_system_context
    if not request.app.state.commands_enabled:
        raise HTTPException(503, "Изменения временно отключены оператором")
    try:
        key = UUID(request.headers.get("idempotency-key", ""))
    except ValueError:
        raise HTTPException(422, "Требуется Idempotency-Key в формате UUID") from None
    _, context = await current_admin(request)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session, replace(context, permission="billing.manage", target_type="subscription", target_id=workspace_id))
        result = await session.scalar(text("select system_control.commit_subscription_operation(:preview,:hash,:key)"),
                                      {"preview": payload.preview_id, "hash": payload.expected_preview_hash, "key": key})
        await session.commit()
    result = dict(result or {})
    error = result.get("error")
    if error:
        status = 403 if error in {"access_denied", "step_up_required"} else 409
        raise HTTPException(status, {"preview_expired":"Предпросмотр истёк", "step_up_required":"Подтвердите полномочия свежим кодом второго фактора",
                                     "version_conflict":"Подписка изменилась. Обновите карточку", "idempotency_conflict":"Ключ уже использован для другого действия",
                                     "preview_consumed":"Предпросмотр уже применён", "access_denied":"Недостаточно прав"}.get(error, "Действие недоступно"))
    return {**result, "status_url": f"/api/system-admin/v1/operations/{result['operation_id']}"}


@router.get("/plans")
async def plans(request: Request, after: UUID | None = None):
    from dataclasses import replace

    from twobrain_rec_server.db.tenant_context import apply_system_context
    _, context = await current_admin(request)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session, replace(context, permission="catalog.read"))
        items = await session.scalar(text("select system_control.list_catalog_plans(:after)"), {"after": after})
    if items is None:
        raise HTTPException(403, "Недостаточно прав")
    return {"items": items[:100], "next_cursor": str(items[99]["id"]) if len(items)>100 else None}


@router.post("/plans", status_code=201)
async def create_plan(request: Request, payload: PlanCreateInput):
    from dataclasses import replace

    from twobrain_rec_server.billing.admin_catalog import create_plan as create
    from twobrain_rec_server.db.tenant_context import apply_system_context
    from twobrain_rec_server.system_admin.audit import record_admin_mutation
    if not request.app.state.commands_enabled:
        raise HTTPException(503, "Изменения временно отключены оператором")
    _, context = await current_admin(request)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session, replace(context, permission="catalog.draft"))
        try:
            result = await create(session, payload.model_dump(exclude={"reason"}))
            if not result.get("error"):
                await record_admin_mutation(session, permission="catalog.draft", action="catalog.plan.create",
                                            target_type=None, target_id=None, reason=payload.reason)
            await session.commit()
        except (ValueError, CatalogNotApproved) as error:
            await session.rollback()
            raise HTTPException(422, "Условия тарифа не прошли проверку") from error
    _catalog_error(result)
    return result


@router.post("/plans/{plan_id}/publish")
async def publish_plan(request: Request, plan_id: UUID, payload: PlanPublishInput):
    from dataclasses import replace

    from twobrain_rec_server.billing.admin_catalog import publish_plan as publish
    from twobrain_rec_server.db.tenant_context import apply_system_context
    from twobrain_rec_server.system_admin.audit import record_admin_mutation
    if not request.app.state.commands_enabled:
        raise HTTPException(503, "Изменения временно отключены оператором")
    _, context = await current_admin(request)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session, replace(context, permission="catalog.publish", target_type="plan", target_id=plan_id))
        result = await publish(session, plan_id=plan_id, version_id=payload.version_id)
        if not result.get("error"):
            await record_admin_mutation(session, permission="catalog.publish", action="catalog.plan.publish",
                                        target_type="plan", target_id=plan_id, reason=payload.reason)
        await session.commit()
    _catalog_error(result)
    return result


@router.patch("/plans/{plan_id}/state")
async def plan_state(request: Request, plan_id: UUID, payload: PlanStateInput):
    from dataclasses import replace

    from twobrain_rec_server.billing.admin_catalog import set_plan_state
    from twobrain_rec_server.db.tenant_context import apply_system_context
    from twobrain_rec_server.system_admin.audit import record_admin_mutation
    if not request.app.state.commands_enabled:
        raise HTTPException(503, "Изменения временно отключены оператором")
    _, context = await current_admin(request)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session, replace(context, permission="catalog.publish", target_type="plan", target_id=plan_id))
        result = await set_plan_state(session, plan_id=plan_id, state=payload.state)
        if not result.get("error"):
            await record_admin_mutation(session, permission="catalog.publish", action="catalog.plan.state",
                                        target_type="plan", target_id=plan_id, reason=payload.reason)
        await session.commit()
    _catalog_error(result)
    return result


@router.get("/campaigns")
async def campaigns(request: Request, after: UUID | None = None):
    from dataclasses import replace

    from twobrain_rec_server.db.tenant_context import apply_system_context
    _, context = await current_admin(request)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session, replace(context, permission="promotions.read"))
        items = await session.scalar(text("select system_control.list_campaigns(:after)"), {"after": after})
    if items is None:
        raise HTTPException(403, "Недостаточно прав")
    return {"items": items[:100], "next_cursor": str(items[99]["id"]) if len(items)>100 else None}


async def _system_projection(request: Request, permission: str, statement: str, **parameters):
    """Run one bounded read through the isolated system context."""
    from dataclasses import replace

    from twobrain_rec_server.db.tenant_context import apply_system_context

    _, context = await current_admin(request)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session, replace(context, permission=permission))
        result = await session.scalar(text(statement), parameters)
        await session.commit()
    if result is None:
        raise HTTPException(403, "Недостаточно прав")
    return result


@router.get("/overview")
async def system_overview(request: Request):
    return await _system_projection(request, "operations.read", "select system_control.system_overview()")


@router.get("/operations")
async def system_operations(request: Request, after: UUID | None = None, state: str | None = None):
    items = await _system_projection(request, "operations.read",
                                     "select system_control.list_system_operations(:after,:state)",
                                     after=after, state=state)
    return {"items": items[:100], "next_cursor": str(items[99]["id"]) if len(items) > 100 else None}


@router.get("/incidents")
async def system_incidents(request: Request, after: UUID | None = None, status: str | None = None):
    items = await _system_projection(request, "support.read",
                                     "select system_control.list_support_incidents(:after,:status)",
                                     after=after, status=status)
    return {"items": items[:100], "next_cursor": str(items[99]["id"]) if len(items) > 100 else None}


@router.get("/devices")
async def system_devices(request: Request, after: UUID | None = None, status: str | None = None):
    items = await _system_projection(request, "devices.read",
                                     "select system_control.list_system_devices(:after,:status)",
                                     after=after, status=status)
    return {"items": items[:100], "next_cursor": str(items[99]["id"]) if len(items) > 100 else None}


@router.get("/dependencies")
async def system_dependencies(request: Request, after: UUID | None = None):
    items = await _system_projection(request, "operations.read",
                                     "select system_control.list_system_dependencies(:after)", after=after)
    return {"items": items[:100], "next_cursor": str(items[99]["id"]) if len(items) > 100 else None}


@router.get("/integrations")
async def system_integrations(request: Request, after: UUID | None = None):
    items = await _system_projection(request, "integrations.read",
                                     "select system_control.list_system_integrations(:after)", after=after)
    return {"items": items[:100], "next_cursor": str(items[99]["id"]) if len(items) > 100 else None}


@router.get("/metrics")
async def system_metrics(request: Request, start: AwareDatetime | None = None, end: AwareDatetime | None = None):
    result = await _system_projection(request, "analytics.read",
                                      "select system_control.list_system_metrics(:start,:end)",
                                      start=start, end=end)
    return result


@router.get("/storage")
async def system_storage(request: Request):
    return await _system_projection(request, "operations.read", "select system_control.system_storage_status()")


@router.get("/alerts")
async def system_alerts(request: Request):
    return await _system_projection(request, "operations.read", "select system_control.list_system_alerts()")


@router.get("/settings")
async def system_settings(request: Request):
    result = await _system_projection(request, "settings.read", "select system_control.system_settings()")
    return result


@router.patch("/settings/{key}")
async def update_system_setting(request: Request, key: str):
    # Runtime settings are injected into the isolated process and require a
    # controlled restart; never mutate process configuration from a browser.
    await _system_projection(request, "settings.manage", "select system_control.system_settings()")
    raise HTTPException(409, "Настройка изменяется через управляемую конфигурацию и перезапуск")


@router.post("/campaigns", status_code=201)
async def create_campaign_route(request: Request, payload: CampaignCreateInput):
    from dataclasses import replace

    from twobrain_rec_server.billing.promotion_admin import create_campaign
    from twobrain_rec_server.db.tenant_context import apply_system_context
    from twobrain_rec_server.system_admin.audit import record_admin_mutation
    if not request.app.state.commands_enabled:
        raise HTTPException(503, "Изменения временно отключены оператором")
    _, context = await current_admin(request)
    values = payload.model_dump(exclude={"reason"})
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session, replace(context, permission="promotions.draft"))
        try:
            result = await create_campaign(session, **values)
            if not result.get("error"):
                await record_admin_mutation(session, permission="promotions.draft", action="promotion.campaign.create",
                                            target_type=None, target_id=None, reason=payload.reason)
            await session.commit()
        except ValueError as error:
            await session.rollback()
            raise HTTPException(422, "Условия акции не прошли проверку") from error
    _catalog_error(result)
    return result


@router.patch("/campaigns/{campaign_id}/state")
async def campaign_state(request: Request, campaign_id: UUID, payload: CampaignStateInput):
    from dataclasses import replace

    from twobrain_rec_server.db.tenant_context import apply_system_context
    from twobrain_rec_server.system_admin.audit import record_admin_mutation
    if not request.app.state.commands_enabled:
        raise HTTPException(503, "Изменения временно отключены оператором")
    _, context = await current_admin(request)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session, replace(context, permission="promotions.publish", target_type="campaign", target_id=campaign_id))
        result = await session.scalar(text("select system_control.set_promotion_campaign_state(:id,:state)"),
                                      {"id": campaign_id, "state": payload.state})
        result = dict(result or {})
        if not result.get("error"):
            await record_admin_mutation(session, permission="promotions.publish", action="promotion.campaign.state",
                                        target_type="campaign", target_id=campaign_id, reason=payload.reason)
        await session.commit()
    _catalog_error(dict(result or {}))
    return result


@router.post("/campaigns/{campaign_id}/codes", status_code=201)
async def campaign_codes(request: Request, campaign_id: UUID, payload: CampaignCodesInput):
    from dataclasses import replace

    from twobrain_rec_server.billing.promotion_admin import issue_codes
    from twobrain_rec_server.db.tenant_context import apply_system_context
    from twobrain_rec_server.system_admin.audit import record_admin_mutation
    if not request.app.state.commands_enabled:
        raise HTTPException(503, "Изменения временно отключены оператором")
    _, context = await current_admin(request)
    # Code issuance is a sensitive catalog mutation. Keep its operator reason
    # in the same audited case stream used by the other campaign actions.
    from twobrain_rec_server.system_admin.audit import create_case_context
    await create_case_context(request.app.state.system_sessions,
                              replace(context, permission="promotions.read", target_type="campaign", target_id=campaign_id),
                              reason=payload.reason)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session, replace(context, permission="promotions.manage", target_type="campaign", target_id=campaign_id))
        try:
            result = await issue_codes(session, campaign_id=campaign_id, idempotency_key=str(payload.idempotency_key),
                                       count=payload.count, prefix=payload.prefix, target_user_ids=payload.target_user_ids)
            if not result.get("error"):
                await record_admin_mutation(session, permission="promotions.manage", action="promotion.codes.issue",
                                            target_type="campaign", target_id=campaign_id, reason=payload.reason)
            await session.commit()
        except ValueError as error:
            await session.rollback()
            raise HTTPException(422, "Партия кодов недействительна") from error
    _catalog_error(result)
    response = JSONResponse(result, status_code=200 if result.get("duplicate") else 201)
    response.headers["Cache-Control"] = "no-store"
    return response


class InvitationResend(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Annotated[int,Field(strict=True,ge=1)]
    reason: Annotated[str,Field(min_length=1,max_length=1000)]


@router.post("/admins/{principal_id}/resend-invitation")
async def resend_invitation(request: Request,principal_id: UUID,payload: InvitationResend):
    from dataclasses import replace

    from twobrain_rec_server.db.tenant_context import apply_system_context

    if not request.app.state.commands_enabled or request.app.state.mailer is None:
        raise HTTPException(503,"Отправка приглашений сейчас недоступна")
    _,context=await current_admin(request)
    token=secrets.token_urlsafe(32)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session,replace(context,permission="admins.manage"))
        result=await session.scalar(text("select system_control.resend_administrator_invitation(:id,:version,:reason,:hash)"),
            {"id":principal_id,"version":payload.version,"reason":payload.reason,"hash":hash_token(token)})
        await session.commit()
    if "error" in result:
        raise HTTPException(429 if result["error"]=="rate_limited" else 409,
            "Приглашение изменилось, срок роли истёк или достигнут предел повторной отправки")
    state = await _deliver_link(request, result["email"], token, reset=False)
    return {"id":str(principal_id),"version":result["version"],"delivery_state":state}


class GrantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    principal_id: UUID
    version: Annotated[int,Field(strict=True,ge=1)]
    permission: str
    target_type: str
    target_id: UUID
    expires_at: AwareDatetime
    reason: Annotated[str,Field(min_length=1,max_length=1000)]


@router.get("/admins/{principal_id}/grants")
async def administrator_grants(request: Request,principal_id: UUID):
    from dataclasses import replace

    from twobrain_rec_server.db.tenant_context import apply_system_context

    _,context=await current_admin(request)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session,replace(context,permission="admins.manage"))
        result=await session.scalar(text("select system_control.administrator_grants(:id)"),{"id":principal_id})
    if result is None:
        raise HTTPException(403,"Недостаточно прав")
    return {"items":result}


@router.post("/grants",status_code=201)
async def create_grant(request: Request,payload: GrantCreate):
    from dataclasses import replace

    from twobrain_rec_server.db.tenant_context import apply_system_context
    from twobrain_rec_server.system_admin.permissions import GRANT_TARGETS

    if not request.app.state.commands_enabled:
        raise HTTPException(503,"Изменения временно отключены оператором")
    if payload.permission not in GRANT_TARGETS or payload.target_type not in GRANT_TARGETS[payload.permission]:
        raise HTTPException(422,"Это разрешение нельзя выдать на выбранный тип объекта")
    _,context=await current_admin(request)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session,replace(context,permission="admins.manage"))
        result=await session.scalar(text("""select system_control.create_administrator_grant
            (:id,:version,:permission,:type,:target,:expiry,:reason)"""),
            {"id":payload.principal_id,"version":payload.version,"permission":payload.permission,
             "type":payload.target_type,"target":payload.target_id,"expiry":payload.expires_at,"reason":payload.reason})
        await session.commit()
    if "error" in result:
        raise HTTPException(409,"Проверьте роль, версию, объект и срок до 24 часов. Может требоваться свежий второй фактор")
    return result


@router.delete("/grants/{grant_id}")
async def revoke_grant(request: Request,grant_id: UUID,payload: InvitationResend):
    from dataclasses import replace

    from twobrain_rec_server.db.tenant_context import apply_system_context

    if not request.app.state.commands_enabled:
        raise HTTPException(503,"Изменения временно отключены оператором")
    _,context=await current_admin(request)
    async with request.app.state.system_sessions() as session:
        await apply_system_context(session,replace(context,permission="admins.manage"))
        result=await session.scalar(text("select system_control.revoke_administrator_grant(:id,:version,:reason)"),
            {"id":grant_id,"version":payload.version,"reason":payload.reason})
        await session.commit()
    if "error" in result:
        raise HTTPException(409,"Назначение изменилось или недостаточно полномочий")
    return result


class CaseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: Annotated[str, Field(min_length=1, max_length=1000)]


@router.post("/meetings/{meeting_id}/case", status_code=201)
async def open_meeting_case(request: Request, meeting_id: UUID, payload: CaseInput):
    from dataclasses import replace

    from twobrain_rec_server.system_admin.audit import create_case_context

    _, context = await current_admin(request)
    context = replace(context, permission="meetings.metadata", target_type="meeting", target_id=meeting_id)
    try:
        case_id = await create_case_context(request.app.state.system_sessions, context, reason=payload.reason)
    except (PermissionError, ValueError):
        raise HTTPException(403, "Недостаточно прав или не указана причина разбора") from None
    return {"case_context_id": case_id}


class ContentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_context_id: UUID
    result_id: UUID | None = None
    after: Annotated[int, Field(strict=True, ge=-1)] = -1
    search: Annotated[str | None, Field(max_length=200)] = None


@router.post("/meetings/{meeting_id}/content")
async def read_meeting_content(request: Request, meeting_id: UUID, payload: ContentInput):
    from dataclasses import replace

    from twobrain_rec_server.system_admin.queries import meeting_content

    _, context = await current_admin(request)
    context = replace(context, permission="content.read", target_type="meeting", target_id=meeting_id,
                      case_context_id=payload.case_context_id)
    try:
        return await meeting_content(request.app.state.system_sessions, context, after=payload.after,
                                     result_id=payload.result_id, search=payload.search)
    except PermissionError:
        raise HTTPException(403, "Нет доступа к содержимому или встреча удаляется") from None
    except ValueError as error:
        raise HTTPException(409, str(error)) from None


@router.post("/meetings/{meeting_id}/content/access")
async def check_meeting_content_access(request: Request, meeting_id: UUID, payload: ContentInput):
    from dataclasses import replace

    from twobrain_rec_server.system_admin.queries import check_content_access

    _, context = await current_admin(request)
    context = replace(context, permission="content.read", target_type="meeting", target_id=meeting_id,
                      case_context_id=payload.case_context_id)
    try:
        await check_content_access(request.app.state.system_sessions, context)
    except PermissionError:
        raise HTTPException(403, "Доступ к содержимому прекращён") from None
    return {"status": "ok"}


def _operation_response(result: dict) -> dict:
    messages = {
        "access_denied": "Недостаточно прав для этого действия",
        "step_up_required": "Подтвердите полномочия свежим кодом второго фактора",
        "preview_expired": "Срок предпросмотра истёк. Получите новый предпросмотр",
        "version_conflict": "Встреча изменилась. Обновите страницу и проверьте действие снова",
        "target_unavailable": "Встреча недоступна или уже удаляется",
        "idempotency_conflict": "Этот ключ уже использован для другого действия",
    }
    error = result.get("error")
    if error:
        raise HTTPException(403 if error == "access_denied" else 409,
                            messages.get(error, "Предпросмотр недействителен. Проверьте действие снова"))
    return result


@router.post("/previews")
async def operation_preview(request: Request, payload: MeetingPreview):
    from twobrain_rec_server.system_admin.operations import preview_operation

    _, context = await current_admin(request)
    if not request.app.state.commands_enabled:
        raise HTTPException(503, "Изменения временно выключены")
    result = _operation_response(await preview_operation(
        request.app.state.system_sessions, context, payload.domain_command(),
    ))
    deletion = payload.command == "meeting.delete"
    return {**result, "source_versions": [{"type": "meeting", "id": str(payload.targets[0].id),
            "version": result["expected_version"]}],
        "effects": ["Удаление встречи и данных, которыми управляет GRAF" if deletion
                    else "Новая попытка обработки сохранённого исходника; прежний результат остаётся доступен"],
        "warnings": (["Удаление необратимо. Скачанные копии и сохранённая диагностика не удаляются этим действием. "
                      "Состояния резервных и локальных копий будут указаны в отчёте удаления."] if deletion else
                     ["Запуск проверит доступность исходника и квоту. При невозможности обработки операция завершится отказом."]),
        "blocked_reasons": [], "requires_step_up": True}


@router.post("/operations", status_code=202)
async def operation_commit(request: Request, payload: CommitOperation):
    from twobrain_rec_server.system_admin.operations import commit_operation

    _, context = await current_admin(request)
    if not request.app.state.commands_enabled:
        raise HTTPException(503, "Изменения временно выключены")
    try:
        key = UUID(request.headers.get("idempotency-key", ""))
    except ValueError:
        raise HTTPException(422, "Требуется Idempotency-Key в формате UUID") from None
    result = _operation_response(await commit_operation(request.app.state.system_sessions, context,
        preview_id=payload.preview_id, expected_preview_hash=payload.expected_preview_hash, idempotency_key=key))
    return {**result, "status_url": f"/api/system-admin/v1/operations/{result['operation_id']}"}


@router.get("/operations/{operation_id}")
async def operation_status(request: Request, operation_id: UUID):
    from twobrain_rec_server.system_admin.operations import read_operation

    _, context = await current_admin(request)
    result = await read_operation(request.app.state.system_sessions, context, operation_id)
    if result is None:
        raise HTTPException(404, "Операция недоступна")
    return result


@router.get("/meetings/{meeting_id}")
async def meeting_overview(request: Request, meeting_id: UUID):
    from twobrain_rec_server.system_admin.queries import meeting_overview as query

    _, context = await current_admin(request)
    result = await query(request.app.state.system_sessions, context, meeting_id)
    if result is None:
        raise HTTPException(404, "Встреча недоступна")
    return result


@router.get("/meetings/{meeting_id}/processing")
async def meeting_processing(request: Request, meeting_id: UUID, before: UUID | None = None):
    from twobrain_rec_server.system_admin.queries import meeting_history

    _, context = await current_admin(request)
    try:
        return await meeting_history(request.app.state.system_sessions, context, meeting_id, before=before)
    except PermissionError:
        raise HTTPException(403, "История обработки недоступна") from None


@router.get("/meetings/{meeting_id}/revisions")
async def meeting_revision_list(request: Request, meeting_id: UUID, before: int | None = None):
    from twobrain_rec_server.system_admin.queries import meeting_revisions

    _, context = await current_admin(request)
    try:
        return await meeting_revisions(request.app.state.system_sessions, context, meeting_id, before=before)
    except PermissionError:
        raise HTTPException(403, "Версии записи недоступны") from None


class MediaTicketInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purpose: Annotated[str, Field(pattern=r"^(listen|download)$")]
    case_context_id: UUID
    revision_id: UUID | None = None


@router.post("/meetings/{meeting_id}/media-ticket")
async def media_ticket(request: Request, meeting_id: UUID, payload: MediaTicketInput):
    from dataclasses import replace

    from twobrain_rec_server.system_admin.media import issue_media_ticket

    _, context = await current_admin(request)
    if getattr(request.app.state, "media_storage", None) is None:
        raise HTTPException(503, "Доступ к записям временно недоступен")
    context = replace(context, permission="audio." + payload.purpose, target_type="meeting",
                      target_id=meeting_id, case_context_id=payload.case_context_id)
    try:
        return await issue_media_ticket(request.app.state.system_sessions, context, revision_id=payload.revision_id)
    except PermissionError:
        raise HTTPException(403, "Нет доступа к записи, исходник недоступен или достигнут предел запросов") from None


@router.get("/media/{token}")
async def media_stream(request: Request, token: str):
    from twobrain_rec_server.api.problems import ProblemDetail
    from twobrain_rec_server.system_admin.media import audio_response

    _, context = await current_admin(request)
    storage = getattr(request.app.state, "media_storage", None)
    if storage is None:
        raise HTTPException(503, "Доступ к записям временно недоступен")
    try:
        return await audio_response(request.app.state.system_sessions, context, token=token,
            cookies=request.cookies, storage=storage, range_header=request.headers.get("range"))
    except PermissionError:
        raise HTTPException(403, "Доступ к записи завершён. Запросите его снова") from None
    except ProblemDetail as error:
        raise HTTPException(error.status, "Запрошенная часть записи недоступна") from None
    except ValueError:
        raise HTTPException(503, "Запись временно недоступна в хранилище") from None


@router.post("/meetings/{meeting_id}/media/access")
async def media_access(request: Request, meeting_id: UUID, payload: MediaTicketInput):
    from dataclasses import replace

    from twobrain_rec_server.db.tenant_context import apply_system_context
    from twobrain_rec_server.system_admin.audit import authorize_access

    _, context = await current_admin(request)
    try:
        context = await authorize_access(request.app.state.system_sessions, replace(context,
            permission="audio."+payload.purpose, target_type="meeting", target_id=meeting_id,
            case_context_id=payload.case_context_id))
        async with request.app.state.system_sessions() as session:
            await apply_system_context(session, context)
            source = await session.scalar(text("select system_control.media_source(:id,:revision)"),
                                          {"id": meeting_id, "revision": payload.revision_id})
            if source is None:
                raise PermissionError
    except PermissionError:
        raise HTTPException(403, "Доступ к записи прекращён") from None
    return {"status": "ok"}
