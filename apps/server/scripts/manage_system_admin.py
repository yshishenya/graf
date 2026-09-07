#!/usr/bin/env python3
"""Operator-only bootstrap/recovery. Never imported by a public HTTP route."""

import argparse
import asyncio
import base64
import json
import os
import secrets
from pathlib import Path
from uuid import uuid4

from cryptography.exceptions import InvalidTag
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine

from twobrain_rec_server.cabinet.web_routes.auth_email_flow import _normalize_email
from twobrain_rec_server.system_admin.app import public_origin
from twobrain_rec_server.system_admin.auth import decrypt_totp, encrypt_totp, hash_token


async def issue_enrolment(*, database_url: str, action: str, email: str, reason: str) -> str:
    """The caller owns the operator credential; no system session is minted."""
    normalized = _normalize_email(email)
    if normalized is None or not reason.strip() or len(reason) > 1000:
        raise ValueError("Укажите действующий адрес и причину длиной до 1000 символов")
    if action not in ("init", "recover"):
        raise ValueError("Неизвестная операция")
    engine = create_async_engine(database_url, echo=False)
    token = secrets.token_urlsafe(32)
    try:
        async with engine.begin() as connection:
            locked = await connection.scalar(text("select id from system_control.governance_lock where id=1 for update"))
            if locked != 1:
                raise ValueError("Не выполнена миграция системной консоли")
            if action == "init":
                if await connection.scalar(text("select exists(select 1 from system_control.principals)")):
                    raise ValueError("Первый администратор уже создан; используйте восстановление")
                actor = uuid4()
                await connection.execute(text("""insert into system_control.principals
                    (id,normalized_email,status,auth_version) values(:id,:email,'invited',1)"""),
                    {"id": actor, "email": normalized})
                await connection.execute(text("""insert into system_control.role_assignments
                    (id,principal_id,role,starts_at,reason) values(:id,:actor,'superadmin',now(),:reason)"""),
                    {"id": uuid4(), "actor": actor, "reason": reason})
                await connection.execute(text("insert into system_control.credentials(principal_id) values(:id)"), {"id": actor})
                kind, version, credential = "invitation", 1, 1
            else:
                principal = (await connection.execute(text("""select id,status,auth_version,(password_hash is not null) as has_password
                    from system_control.principals where normalized_email=:email for update"""),
                    {"email": normalized})).mappings().one_or_none()
                if not principal or principal["status"] not in ("active", "recovery_pending", "invited"):
                    raise ValueError("Учётная запись недоступна для восстановления")
                actor = principal["id"]
                if not await connection.scalar(text("""select exists(select 1 from system_control.role_assignments
                    where principal_id=:id and revoked_at is null and starts_at<=now()
                      and (expires_at is null or expires_at>now()))"""), {"id": actor}):
                    raise ValueError("Нет действующего назначения роли")
                kind = "invitation" if not principal["has_password"] else "enrolment"
                target_status = "invited" if kind=="invitation" else "recovery_pending"
                version = await connection.scalar(text("""update system_control.principals
                    set auth_version=auth_version+1,status=:status where id=:id returning auth_version"""), {"id": actor, "status": target_status})
                credential = await connection.scalar(text("""update system_control.credentials
                    set credential_version=credential_version+1,recovery_code_hashes='{}'
                    where principal_id=:id returning credential_version"""), {"id": actor})
                await connection.execute(text("""update system_control.sessions set revoked_at=now()
                    where principal_id=:id and revoked_at is null"""), {"id": actor})
                await connection.execute(text("""update system_control.challenges set consumed_at=now()
                    where principal_id=:id and consumed_at is null"""), {"id": actor})
            await connection.execute(text("""insert into system_control.challenges
                (principal_id,kind,token_hash,issued_auth_version,credential_version,expires_at)
                values(:id,cast(:kind as varchar),:hash,:version,:credential,
                  now()+case when cast(:kind as varchar)='invitation' then interval '24 hours' else interval '5 minutes' end)"""),
                {"id": actor, "kind": kind, "hash": hash_token(token), "version": version, "credential": credential})
            await connection.execute(text("""insert into system_control.audit_events
                (id,principal_id,role,permission,action,target_type,target_id,result,reason)
                values(:event,:id,'operator','admins.manage',:action,'system',:id,'allowed',:reason)"""),
                {"event": uuid4(), "id": actor, "action": f"operator.{action}", "reason": reason})
        return token
    finally:
        await engine.dispose()


async def rotate_totp_keys(*, database_url: str, keys: dict[str,bytes], active: str) -> int:
    if active not in keys or any(len(key)!=32 for key in keys.values()):
        raise ValueError("Некорректный набор ключей MFA")
    engine=create_async_engine(database_url,echo=False)
    changed=0
    try:
        while True:
            async with engine.begin() as connection:
                rows=(await connection.execute(text("""select principal_id,principal_id as id,'credential' as kind
                    from system_control.credentials where encrypted_totp_seed is not null and key_id<>:key
                    union all select principal_id,id,'challenge' from system_control.challenges
                    where encrypted_totp_seed is not null and key_id<>:key limit 100"""),{"key":active})).mappings().all()
                if not rows:
                    break
                for item in sorted(rows,key=lambda row:str(row["principal_id"])):
                    await connection.execute(text("select id from system_control.principals where id=:id for update"),{"id":item["principal_id"]})
                    # Names come only from the two branches of the fixed query.
                    table,column=("credentials","principal_id") if item["kind"]=="credential" else ("challenges","id")
                    row=(await connection.execute(text(f"""select encrypted_totp_seed,nonce,key_id,credential_version
                        from system_control.{table} where {column}=:id for update"""),{"id":item["id"]})).mappings().one_or_none()
                    if row is None or row["encrypted_totp_seed"] is None or row["key_id"]==active:
                        continue
                    if row["key_id"] not in keys:
                        raise ValueError("Старый ключ MFA недоступен; ротация остановлена")
                    seed=decrypt_totp(row["encrypted_totp_seed"],nonce=row["nonce"],principal_id=item["principal_id"],key=keys[row["key_id"]])
                    nonce,cipher=encrypt_totp(base64.b32encode(seed).decode(),principal_id=item["principal_id"],key=keys[active])
                    result=await connection.execute(text(f"""update system_control.{table}
                        set encrypted_totp_seed=:seed,nonce=:nonce,key_id=:key
                        where {column}=:id and credential_version=:version"""),
                        {"seed":cipher,"nonce":nonce,"key":active,"id":item["id"],"version":row["credential_version"]})
                    changed+=result.rowcount
        return changed
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Первый суперадминистратор или восстановление MFA")
    parser.add_argument("action", choices=("init", "recover", "rotate-mfa-key"))
    args = parser.parse_args()
    if args.action == "rotate-mfa-key":
        try:
            url=Path(os.environ["SYSTEM_ADMIN_OPERATOR_DATABASE_URL_FILE"]).read_text().strip()
            keyring=json.loads(Path(os.environ["SYSTEM_ADMIN_TOTP_KEYS_FILE"]).read_text())
            keys={name:base64.b64decode(value,validate=True) for name,value in keyring["keys"].items()}
            changed=asyncio.run(rotate_totp_keys(database_url=url,keys=keys,active=keyring["active"]))
        except (ValueError,SQLAlchemyError,OSError,KeyError,InvalidTag):
            parser.exit(1,"Ротация не завершена. Проверьте ключи и операторскую конфигурацию.\n")
        print(f"Перешифровано записей: {changed}. Старые ключи сохраняйте до проверки восстановления резервных копий.")
        return
    email = input("Адрес администратора: ")
    reason = input("Причина (без содержимого встреч): ")
    try:
        origin = public_origin(os.environ["SYSTEM_ADMIN_PUBLIC_ORIGIN"])
        url = Path(os.environ["SYSTEM_ADMIN_OPERATOR_DATABASE_URL_FILE"]).read_text().strip()
        token = asyncio.run(issue_enrolment(database_url=url, action=args.action, email=email, reason=reason))
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    except (SQLAlchemyError, OSError, KeyError):
        parser.exit(1, "Не удалось выполнить операцию. Проверьте миграции и операторскую конфигурацию.\n")
    print("Одноразовая ссылка. Откройте её в закрытом браузере; не сохраняйте в журналах:")
    print(f"{origin}/system-admin/activate#{token}")


if __name__ == "__main__":
    main()
