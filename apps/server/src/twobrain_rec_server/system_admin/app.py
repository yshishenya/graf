"""Standalone ASGI process. Never mounted inside the product application."""

import asyncio
import base64
import hmac
import json
import os
import re
import secrets
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

from cryptography.exceptions import InvalidTag
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import DBAPIError

from twobrain_rec_server.db.session import (
    create_system_admin_database,
    verify_system_admin_database_identity,
)
from twobrain_rec_server.system_admin.auth import PasswordComputations, hash_password
from twobrain_rec_server.system_admin.web import router

SESSION_COOKIE = "__Host-graf_system_session"
CSRF_COOKIE = "__Host-graf_system_csrf"
SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Pragma": "no-cache",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'; form-action 'self'",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


class PayloadTooLarge(HTTPException):
    def __init__(self):
        super().__init__(413, "Слишком большой запрос")


class BodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        size = 0

        async def bounded_receive():
            nonlocal size
            message = await receive()
            size += len(message.get("body", b""))
            if size > 65536:
                raise PayloadTooLarge
            return message

        await self.app(scope, bounded_receive, send)


def public_origin(value: str) -> str:
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path not in ("", "/")):
        raise ValueError("SYSTEM_ADMIN_PUBLIC_ORIGIN must be an HTTPS origin")
    return f"https://{parsed.netloc}".rstrip("/")


def create_app() -> FastAPI:
    enabled = os.getenv("SYSTEM_ADMIN_ENABLED", "false") == "true"
    origin = public_origin(os.environ["SYSTEM_ADMIN_PUBLIC_ORIGIN"]) if enabled else ""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if not enabled:
            yield
            return
        # This file is mounted only into this process. No fallback to the
        # ordinary application or maintenance credentials is permitted.
        database_url = Path(os.environ["SYSTEM_ADMIN_DATABASE_URL_FILE"]).read_text().strip()
        engine, sessions = create_system_admin_database(database_url=database_url)
        try:
            await verify_system_admin_database_identity(sessions)
            keyring = json.loads(Path(os.environ["SYSTEM_ADMIN_TOTP_KEYS_FILE"]).read_text())
            app.state.totp_keys = {key: base64.b64decode(value, validate=True)
                                   for key, value in keyring["keys"].items()}
            if keyring["active"] not in app.state.totp_keys or any(
                len(value) != 32 for value in app.state.totp_keys.values()
            ):
                raise ValueError("invalid system MFA key configuration")
            app.state.active_totp_key = keyring["active"]
            app.state.password_computations = PasswordComputations()
            app.state.dummy_password_hash = hash_password(secrets.token_urlsafe(32))
            app.state.system_sessions = sessions
            app.state.media_storage = None
            storage_file = os.getenv("SYSTEM_ADMIN_STORAGE_CONFIG_FILE")
            if storage_file:
                from types import SimpleNamespace

                from twobrain_rec_server.storage.minio_client import MinioStorage

                try:
                    storage_config = json.loads(Path(storage_file).read_text())
                    required = {"endpoint", "access_key", "secret_key", "bucket", "secure"}
                    if set(storage_config) != required or type(storage_config["secure"]) is not bool:
                        raise ValueError
                    if any(not isinstance(storage_config[key], str) or not storage_config[key]
                           for key in required - {"secure"}):
                        raise ValueError
                    app.state.media_storage = MinioStorage(SimpleNamespace(
                        minio_endpoint=storage_config["endpoint"], minio_access_key=storage_config["access_key"],
                        minio_secret_key=storage_config["secret_key"], minio_bucket=storage_config["bucket"],
                        minio_secure=storage_config["secure"],
                    ))
                except Exception:
                    raise ValueError("invalid system media storage configuration") from None
            app.state.mailer = None
            if os.getenv("SYSTEM_ADMIN_POSTAL_API_URL"):
                from twobrain_rec_server.auth.email_delivery import PostalEmailLoginClient

                app.state.mailer = PostalEmailLoginClient(
                    api_url=os.environ["SYSTEM_ADMIN_POSTAL_API_URL"],
                    api_key=Path(os.environ["SYSTEM_ADMIN_POSTAL_KEY_FILE"]).read_text().strip(),
                    from_address=os.environ["SYSTEM_ADMIN_FROM_ADDRESS"],
                )
            yield
        finally:
            await engine.dispose()

    app = FastAPI(title="Системная консоль GRAF", lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(BodyLimit)
    app.state.media_stream_slots = asyncio.Semaphore(4)
    app.state.public_origin = origin
    app.state.commands_enabled = os.getenv("SYSTEM_ADMIN_COMMANDS_ENABLED", "false") == "true"

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        if not enabled:
            response = JSONResponse({"error": "console_disabled"}, status_code=503)
        elif request.headers.get("host") != urlsplit(origin).netloc:
            response = JSONResponse({"error": "invalid_host"}, status_code=400)
        elif request.method not in ("GET", "HEAD", "POST", "PATCH", "DELETE"):
            response = JSONResponse({"error": "method_not_allowed"}, status_code=405)
        elif request.method not in ("GET", "HEAD") and (
            request.headers.get("origin") != origin
            or not request.cookies.get(CSRF_COOKIE)
            or not hmac.compare_digest(
                request.cookies.get(CSRF_COOKIE, ""), request.headers.get("x-csrf-token", "")
            )
        ):
            response = JSONResponse({"error": "csrf_failed"}, status_code=403)
        else:
            response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        return response

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "system-admin"}

    @app.get("/api/system-admin/v1/auth/csrf")
    async def csrf(request: Request):
        token = request.cookies.get(CSRF_COOKIE, "")
        if re.fullmatch(r"[A-Za-z0-9_-]{43}", token) is None:
            token = secrets.token_urlsafe(32)
        response = JSONResponse({"csrf_token": token})
        response.set_cookie(CSRF_COOKIE, token, secure=True, httponly=True,
                            samesite="strict", path="/", max_age=12 * 60 * 60)
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request: Request, error: Exception):
        return JSONResponse({"error": "invalid_input"}, status_code=422)

    @app.exception_handler(PayloadTooLarge)
    async def oversized(request: Request, error: Exception):
        return JSONResponse({"error": "payload_too_large"}, status_code=413)

    @app.exception_handler(DBAPIError)
    @app.exception_handler(InvalidTag)
    async def unavailable(request: Request, error: Exception):
        # Do not log SQL parameters containing password hashes or MFA envelopes.
        return JSONResponse({"error": "service_unavailable"}, status_code=503)

    asset_root = Path(__file__).parent
    app.mount("/system-admin/static", StaticFiles(directory=asset_root / "static"), name="system-admin-static")

    @app.get("/system-admin/login")
    @app.get("/system-admin/activate")
    @app.get("/system-admin/reset")
    async def login_page():
        return FileResponse(asset_root / "templates/system_admin/login.html", media_type="text/html")

    @app.get("/")
    async def root():
        return RedirectResponse("/system-admin", status_code=303)

    @app.get("/system-admin")
    async def console_page(request: Request, section: str = "home", after: UUID | None = None):
        from twobrain_rec_server.system_admin import queries
        from twobrain_rec_server.system_admin.permissions import ROLE_PERMISSIONS
        from twobrain_rec_server.system_admin.web import ROLE_LABELS, administrators, current_admin

        try:
            identity, context = await current_admin(request)
        except HTTPException as error:
            if error.status_code == 401:
                return RedirectResponse("/system-admin/login", status_code=303)
            raise
        permissions = ROLE_PERMISSIONS[identity["role"]]
        sections = {"home": (None, "Мой доступ"), "meetings": ("meetings.metadata", "Встречи"),
                    "users": ("users.read", "Пользователи"),
                    "subscriptions": ("billing.read", "Подписки"),
                    "payments": ("billing.read", "Платежи"),
                    "plans": ("catalog.read", "Тарифы"),
                    "campaigns": ("promotions.read", "Акции"),
                    "admins": ("admins.manage", "Администраторы"), "audit": ("audit.read", "Журнал действий"),
                    "operations": ("operations.read", "Операции"), "incidents": ("support.read", "Обращения"),
                    "devices": ("devices.read", "Устройства"), "integrations": ("integrations.read", "Интеграции"),
                    "metrics": ("analytics.read", "Статистика"), "alerts": ("operations.read", "Оповещения"),
                    "storage": ("operations.read", "Хранилище"), "dependencies": ("operations.read", "Зависимости"),
                    "settings": ("settings.read", "Настройки")}
        if section not in sections:
            raise HTTPException(404, "Раздел не найден")
        permission, title = sections[section]
        if permission and permission not in permissions:
            raise HTTPException(403, "Недостаточно прав")
        rows, columns, next_cursor = [], [], None
        if section == "home":
            if "operations.read" in permissions:
                overview = await queries.system_projection(request.app.state.system_sessions, context,
                    permission="operations.read", statement="select system_control.system_overview()")
                rows = [{"key": key, "value": value} for key, value in overview.items()]
                columns = [("key", "Показатель"), ("value", "Значение")]
        elif section == "meetings":
            result = await queries.meetings(request.app.state.system_sessions, context, after=after)
            rows, next_cursor = result["items"], result["next_cursor"]
            columns = [("id","Встреча"),("workspace_id","Пространство"),("created_by_user_id","Пользователь"),
                       ("status","Состояние"),("processing_status","Обработка"),("duration_seconds","Длительность, с"),
                       ("created_at","Создана"),("control_version","Версия")]
        elif section == "users":
            result = await queries.users(request.app.state.system_sessions,context,after=after)
            rows,next_cursor = result["items"],result["next_cursor"]
            columns = [("email","Адрес"),("display_name","Имя"),("status","Состояние"),
                       ("assigned_plan_code","Назначенный тариф"),("subscription_state","Подписка"),
                       ("paid_through","Доступ до")]
            if "billing.read" in permissions:
                for row in rows:
                    for name in ("paid_amount_minor_rub","refunded_amount_minor_rub"):
                        value=row[name]
                        row[name]=(f"{value//100:,}".replace(",", " ")+f",{value%100:02d} ₽") if value is not None else None
                columns += [("paid_amount_minor_rub","Оплачено, ₽"),("refunded_amount_minor_rub","Возвращено, ₽")]
        elif section == "subscriptions":
            from dataclasses import replace

            from sqlalchemy import text

            from twobrain_rec_server.db.tenant_context import apply_system_context
            async with request.app.state.system_sessions() as session:
                await apply_system_context(session, replace(context, permission="billing.read"))
                result = await session.scalar(text("select system_control.list_billing_subscriptions(:after,null,null)"), {"after": after})
            rows = result[:100] if result else []
            next_cursor = rows[-1].get("workspace_id") if result and len(result) > 100 else None
            columns = [("workspace_id","Пространство"),("billing_owner_id","Плательщик"),("state","Состояние"),
                       ("plan_code","Тариф"),("cycle","Период"),("paid_through","Доступ до"),
                       ("invoice_count","Счетов"),("paid_amount_minor_rub","Оплачено, ₽"),
                       ("refunded_amount_minor_rub","Возвращено, ₽"),("last_payment_at","Последняя оплата")]
        elif section == "payments":
            from dataclasses import replace

            from sqlalchemy import text

            from twobrain_rec_server.db.tenant_context import apply_system_context
            async with request.app.state.system_sessions() as session:
                await apply_system_context(session, replace(context, permission="billing.read"))
                result = await session.scalar(text("select system_control.list_billing_invoices(:after,null,null)"), {"after": after})
            rows = result[:100] if result else []
            next_cursor = rows[-1].get("id") if result and len(result) > 100 else None
            columns = [("safe_number","Счёт"),("workspace_id","Пространство"),("plan_code","Тариф"),
                       ("amount_minor","Сумма, коп."),("currency","Валюта"),("status","Состояние"),
                       ("created_at","Создан")]
        elif section == "plans":
            from dataclasses import replace

            from sqlalchemy import text

            from twobrain_rec_server.db.tenant_context import apply_system_context
            async with request.app.state.system_sessions() as session:
                await apply_system_context(session, replace(context, permission="catalog.read"))
                result = await session.scalar(text("select system_control.list_catalog_plans(:after)"), {"after": after})
            rows = result[:100] if result else []
            next_cursor = rows[-1].get("id") if result and len(result) > 100 else None
            columns = [("code","Код"),("display_name","Название"),("sales_state","Продажи"),
                       ("version_number","Версия"),("version_status","Состояние версии"),
                       ("enabled_for_checkout","Доступен в покупке"),("prices","Цены")]
        elif section == "campaigns":
            from dataclasses import replace

            from sqlalchemy import text

            from twobrain_rec_server.db.tenant_context import apply_system_context
            async with request.app.state.system_sessions() as session:
                await apply_system_context(session, replace(context, permission="promotions.read"))
                result = await session.scalar(text("select system_control.list_campaigns(:after)"), {"after": after})
            rows = result[:100] if result else []
            next_cursor = rows[-1].get("id") if result and len(result) > 100 else None
            columns = [("display_name","Название"),("plan_code","Тариф"),("cycle","Период"),
                       ("benefit_kind","Выгода"),("discount_percent","Скидка, %"),("gift_days","Дней"),
                       ("audience","Аудитория"),("status","Состояние"),("redeemed_count","Использовано"),
                       ("max_redemptions","Лимит"),("code_count","Кодов"),("starts_at","Начало"),("ends_at","Окончание")]
        elif section == "operations":
            result = await queries.system_projection(request.app.state.system_sessions, context,
                permission="operations.read", statement="select system_control.list_system_operations(:after,null)",
                parameters={"after": after})
            rows, next_cursor = result[:100], str(result[99]["id"]) if len(result) > 100 else None
            columns = [("id","Операция"),("kind","Команда"),("target_type","Тип объекта"),("target_id","Объект"),
                       ("state","Состояние"),("target_state","Состояние объекта"),("error_code","Код ошибки"),
                       ("created_at","Создана"),("updated_at","Обновлена")]
        elif section == "incidents":
            result = await queries.system_projection(request.app.state.system_sessions, context,
                permission="support.read", statement="select system_control.list_support_incidents(:after,null)",
                parameters={"after": after})
            rows, next_cursor = result[:100], str(result[99]["id"]) if len(result) > 100 else None
            columns = [("incident_number","Обращение"),("workspace_id","Пространство"),("device_id","Устройство"),
                       ("problem_code","Проблема"),("failure_category","Категория"),("status","Состояние"),
                       ("affected_count","Затронуто"),("last_received_at","Последнее событие"),
                       ("github_issue_number","GitHub"),("github_issue_state","Состояние GitHub")]
        elif section == "devices":
            result = await queries.system_projection(request.app.state.system_sessions, context,
                permission="devices.read", statement="select system_control.list_system_devices(:after,null)",
                parameters={"after": after})
            rows, next_cursor = result[:100], str(result[99]["id"]) if len(result) > 100 else None
            columns = [("id","Устройство"),("workspace_id","Пространство"),("user_id","Пользователь"),
                       ("platform","Платформа"),("client_version","Версия клиента"),("status","Состояние"),
                       ("registration_state","Регистрация"),("last_seen_at","Последний контакт")]
        elif section == "integrations":
            result = await queries.system_projection(request.app.state.system_sessions, context,
                permission="integrations.read", statement="select system_control.list_system_integrations(:after)",
                parameters={"after": after})
            rows, next_cursor = result[:100], str(result[99]["id"]) if len(result) > 100 else None
            columns = [("id","Интеграция"),("workspace_id","Пространство"),("provider_family","Поставщик"),
                       ("connection_state","Подключение"),("credential_state","Доступ"),("sync_state","Синхронизация"),
                       ("last_successful_sync_at","Последняя успешная синхронизация"),("last_safe_error_code","Код ошибки")]
        elif section == "dependencies":
            result = await queries.system_projection(request.app.state.system_sessions, context,
                permission="operations.read", statement="select system_control.list_system_dependencies(:after)",
                parameters={"after": after})
            rows, next_cursor = result[:100], str(result[99]["id"]) if len(result) > 100 else None
            columns = [("dependency","Зависимость"),("workspace_id","Пространство"),("meeting_id","Встреча"),
                       ("state","Состояние"),("last_verified_at","Проверено"),("updated_at","Обновлено")]
        elif section == "storage":
            storage = await queries.system_projection(request.app.state.system_sessions, context,
                permission="operations.read", statement="select system_control.system_storage_status()")
            rows = [{"key": key, "value": value} for key, value in storage.items()]
            columns = [("key", "Показатель"), ("value", "Значение")]
        elif section == "alerts":
            alerts = await queries.system_projection(request.app.state.system_sessions, context,
                permission="operations.read", statement="select system_control.list_system_alerts()")
            rows, next_cursor = alerts.get("items", []), None
            columns = [("code","Код"),("severity","Важность"),("title","Описание"),("detail","Деталь"),("observed_at","Наблюдалось")]
        elif section == "settings":
            settings = await queries.system_projection(request.app.state.system_sessions, context,
                permission="settings.read", statement="select system_control.system_settings()")
            rows, next_cursor = settings.get("items", []), None
            columns = [("key","Ключ"),("value","Значение"),("mutable","Изменяемо")]
        elif section == "metrics":
            metrics = await queries.system_projection(request.app.state.system_sessions, context,
                permission="analytics.read", statement="select system_control.list_system_metrics(null,null)")
            rows, next_cursor = metrics.get("items", []), None
            columns = [("metric_key","Метрика"),("label","Название"),("value","Значение"),("unit","Единица")]
        elif section == "admins":
            rows = (await administrators(request, after))["items"]
            next_cursor = rows[-1]["id"] if len(rows)==100 else None
            delivery_labels = {"not_attempted":"Не отправлялось", "sending":"Результат не подтверждён",
                "submitted":"Принято почтовым сервисом", "unknown":"Результат неизвестен", "failed":"Отправка отклонена"}
            for row in rows:
                invitation = row.get("invitation")
                row["delivery_state"] = delivery_labels.get(invitation["state"]) if invitation else None
            columns = [("normalized_email","Адрес"),("role","Роль"),("status","Состояние"),
                       ("expires_at","Действует до"),("delivery_state","Приглашение"),("version","Версия")]
        elif section == "audit":
            result = await queries.audit(request.app.state.system_sessions, context, after=after)
            rows, next_cursor = result["items"], result["next_cursor"]
            columns = [("occurred_at","Время"),("principal_id","Администратор"),("action","Действие"),
                       ("target_id","Объект"),("result","Результат"),("reason","Причина")]
        return Jinja2Templates(directory=asset_root / "templates").TemplateResponse(request=request,
            name="system_admin/console.html",context={"title":title,"section":section,"rows":rows,
              "columns":columns,"next_cursor":next_cursor,"permissions":permissions,"identity":identity,
              "role_label":ROLE_LABELS[identity["role"]],"role_labels":ROLE_LABELS,
              "status_labels":{"active":"Действует","invited":"Ожидает активации",
                "recovery_pending":"Восстановление второго фактора","blocked":"Заблокировано",
                "revoked":"Доступ отозван","closed":"Закрыто","ready":"Готово",
                "processed":"Обработано","processing":"Обрабатывается","uploaded":"Загружено",
                "ingested_pending_processing":"Запись принята","local_only":"Только на устройстве",
                "uploading":"Загрузка записи","not_submitted":"Обработка не запущена","starting":"Запуск обработки",
                "workflow_started":"Обработка запущена","submitting":"Отправка на обработку",
                "submitted":"Отправлено на обработку","polling":"Ожидание результата",
                "importing":"Сохранение результата","failed_terminal":"Ошибка обработки",
                "canceled":"Отменено","none":"Нет","trial":"Пробный период",
                "expired":"Срок истёк","past_due":"Просрочено","free":"Бесплатный",
                "queued":"В очереди","running":"Выполняется","awaiting_reconciliation":"Ожидает сверки",
                "succeeded":"Успешно","failed":"Ошибка","cancelled":"Отменено","resolved":"Решено",
                "unavailable":"Недоступно","paused":"Приостановлено"},
              "observed_at":datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")})

    app.include_router(router)
    return app
