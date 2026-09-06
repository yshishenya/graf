"""Full HTTP login with isolated PostgreSQL and synthetic MFA credentials."""

import base64
import json
import time
from uuid import uuid4

import asyncpg
import httpx
import pytest

from tests.integration import test_system_admin_security as security
from twobrain_rec_server.system_admin.app import create_app
from twobrain_rec_server.system_admin.auth import encrypt_totp, hash_password, hash_token, totp_code

system_database = security.system_database
pytestmark = pytest.mark.strict_rls


async def _seed(db):
    key = bytes(range(32))
    seed = b"12345678901234567890"
    password = "Synthetic password 254"
    nonce, cipher = encrypt_totp(base64.b32encode(seed).decode(), principal_id=db["actor"], key=key)
    await db["owner"].execute("update system_control.principals set password_hash=$1", hash_password(password))
    await db["owner"].execute("""insert into system_control.credentials
        (principal_id,encrypted_totp_seed,key_id,nonce) values($1,$2,'test',$3)""", db["actor"], cipher, nonce)
    return key, seed, password


@pytest.mark.asyncio
async def test_http_login_cookie_mfa_replay_and_logout(system_database, monkeypatch, tmp_path):
    db = system_database
    key, seed, password = await _seed(db)
    database = tmp_path / "database"
    database.write_text(db["url"])
    keys = tmp_path / "keys"
    keys.write_text(json.dumps({"active": "test", "keys": {"test": base64.b64encode(key).decode()}}))
    monkeypatch.setenv("SYSTEM_ADMIN_ENABLED", "true")
    monkeypatch.setenv("SYSTEM_ADMIN_PUBLIC_ORIGIN", "https://admin.example.invalid")
    monkeypatch.setenv("SYSTEM_ADMIN_DATABASE_URL_FILE", str(database))
    monkeypatch.setenv("SYSTEM_ADMIN_TOTP_KEYS_FILE", str(keys))
    app = create_app()
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://admin.example.invalid",
    ) as client:
        assert (await client.get("/api/system-admin/v1/me")).status_code == 401
        csrf = (await client.get("/api/system-admin/v1/auth/csrf")).json()["csrf_token"]
        client.headers.update({"origin": "https://admin.example.invalid", "x-csrf-token": csrf})
        login = await client.post("/api/system-admin/v1/auth/login", json={
            "email": "synthetic@example.invalid", "password": password,
        })
        assert login.status_code == 200, login.text
        assert (await client.get("/api/system-admin/v1/me")).status_code == 401
        payload = {"challenge": login.json()["challenge"], "code": totp_code(seed, int(time.time()//30))}
        response = await client.post("/api/system-admin/v1/auth/mfa", json=payload)
        assert response.status_code == 200, response.text
        assert "__Host-graf_system_session" in response.headers["set-cookie"]
        assert await db["owner"].fetchval("""select count(*) from system_control.sessions
            where token_hash=$1 and last_interaction_at=issued_at and mfa_at=issued_at
              and absolute_expires_at=issued_at+interval '12 hours'""",
            hash_token(client.cookies["__Host-graf_system_session"])) == 1
        assert (await client.get("/api/system-admin/v1/me")).json()["role"] == "system_admin"
        home = await client.get("/system-admin")
        assert home.status_code == 200
        assert "Мой доступ" in home.text
        meetings = await client.get("/system-admin?section=meetings")
        assert meetings.status_code == 200, meetings.text
        assert "Synthetic private title" not in meetings.text
        assert (await client.get("/api/system-admin/v1/meetings")).json()["items"]
        assert (await client.get("/system-admin?section=admins")).status_code == 403
        assert (await client.get("/api/system-admin/v1/admins")).status_code == 403
        assert (await client.post("/api/system-admin/v1/auth/mfa", json=payload)).status_code == 401
        assert (await client.post("/api/system-admin/v1/auth/logout")).status_code == 200
        assert (await client.get("/api/system-admin/v1/me")).status_code == 401


@pytest.mark.asyncio
async def test_auth_reset_version_and_counter_are_atomic(system_database):
    db = system_database
    await _seed(db)
    conn = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    try:
        digest = hash_token("synthetic challenge")
        assert await conn.fetchval("select system_control.auth_issue_preauth($1,1,1,$2)", db["actor"], digest)
        await db["owner"].execute("update system_control.principals set auth_version=2")
        assert await conn.fetchval("select system_control.auth_challenge($1)", digest) is None
        assert await conn.fetchval("select system_control.auth_finish_totp($1,$2,$3)",
                                   digest, int(time.time()//30), uuid4().hex*2) is None
        assert await db["owner"].fetchval("select count(*) from system_control.sessions") == 1
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.fetch("select * from system_control.credentials")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute("set role twobrain_rec_system_auth")
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_invitation_enrolment_and_recovery_never_grant_early_session(system_database):
    db = system_database
    key, seed, _ = await _seed(db)
    conn = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    try:
        invite = hash_token("synthetic invitation")
        await db["owner"].execute("update system_control.principals set status='invited'")
        await db["owner"].execute("""insert into system_control.challenges
            (principal_id,kind,token_hash,issued_auth_version,credential_version,expires_at)
            values($1,'invitation',$2,1,1,now()+interval '24 hours')""", db["actor"], invite)
        nonce, cipher = encrypt_totp(base64.b32encode(seed).decode(), principal_id=db["actor"], key=key)
        enrolment = hash_token("synthetic initial enrolment")
        assert await conn.fetchval("select system_control.auth_begin_enrolment($1,$2,$3,$4,'test',$5)",
                                   invite, hash_password("Synthetic new password"), cipher, nonce, enrolment)
        assert await conn.fetchval("select system_control.auth_challenge($1)", invite) is None
        # The seed is immutable throughout confirmation, including concurrent begin calls.
        assert not await conn.fetchval("select system_control.auth_begin_enrolment($1,null,$2,$3,'test',$4)",
                                       invite, cipher, nonce, hash_token("synthetic repeat"))
        challenge = json.loads(await conn.fetchval("select system_control.auth_challenge($1)", enrolment))
        assert challenge["kind"] == "enrolment"
        session_hash = hash_token("synthetic enrolled session")
        code_hashes = [hash_token(f"synthetic recovery {n}") for n in range(10)]
        result = await conn.fetchval("select system_control.auth_confirm_enrolment($1,$2,$3,$4)",
                                     enrolment, int(time.time()//30), session_hash, code_hashes)
        assert result is not None
        assert await db["owner"].fetchval("""select count(*) from system_control.sessions
            where token_hash=$1 and last_interaction_at=issued_at and mfa_at=issued_at
              and absolute_expires_at=issued_at+interval '12 hours'""", session_hash) == 1
        assert await conn.fetchval("select system_control.auth_session($1)", session_hash) is not None
        version = await db["owner"].fetchval("select auth_version from system_control.principals")
        credential = await db["owner"].fetchval("select credential_version from system_control.credentials")
        preauth = hash_token("synthetic recovery preauth")
        assert await conn.fetchval("select system_control.auth_issue_preauth($1,$2,$3,$4)",
                                   db["actor"], version, credential, preauth)
        recovery = hash_token("synthetic recovery challenge")
        assert await conn.fetchval("select system_control.auth_recover($1,$2,$3)", preauth, code_hashes[0], recovery)
        assert await conn.fetchval("select system_control.auth_session($1)", session_hash) is None
        assert not await conn.fetchval("select system_control.auth_recover($1,$2,$3)", preauth, code_hashes[0], recovery)
        assert await db["owner"].fetchval("select status from system_control.principals") == "recovery_pending"
        assert await db["owner"].fetchval("select count(*) from system_control.role_assignments") == 1
        ch = json.loads(await conn.fetchval("select system_control.auth_challenge($1)", recovery))
        assert ch["kind"] == "enrolment"
        assert ch["seed"] is None
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_password_reset_keeps_mfa_and_revokes_all_prior_proofs(system_database):
    db = system_database
    await _seed(db)
    conn = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    try:
        seed_before = await db["owner"].fetchval("select encrypted_totp_seed from system_control.credentials")
        token = hash_token("synthetic password reset")
        preauth = hash_token("synthetic pending preauth")
        assert await conn.fetchval("select system_control.auth_issue_preauth($1,1,1,$2)", db["actor"], preauth)
        assert await conn.fetchval("select system_control.auth_request_reset('synthetic@example.invalid',$1)", token)
        encoded = hash_password("Synthetic replacement password")
        assert await conn.fetchval("select system_control.auth_complete_reset($1,$2)", token, encoded)
        assert not await conn.fetchval("select system_control.auth_complete_reset($1,$2)", token, encoded)
        assert await db["owner"].fetchval("select encrypted_totp_seed from system_control.credentials") == seed_before
        assert await conn.fetchval("select system_control.auth_challenge($1)", preauth) is None
        assert await db["owner"].fetchval("select count(*) from system_control.sessions where revoked_at is null") == 0
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_auth_rate_limit_is_rolling_and_success_releases_only_own_attempt(system_database):
    db = system_database
    await _seed(db)
    conn = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    bucket = hash_token("synthetic@example.invalid")
    attempts = [uuid4() for _ in range(5)]
    try:
        for attempt in attempts:
            assert await conn.fetchval("select system_control.auth_rate_limit($1,'account',$2)", bucket, attempt)
        assert not await conn.fetchval("select system_control.auth_rate_limit($1,'account',$2)", bucket, uuid4())
        await conn.fetchval("select system_control.auth_login_result('synthetic@example.invalid',true,$1)", attempts[2])
        assert await conn.fetchval("select system_control.auth_rate_limit($1,'account',$2)", bucket, uuid4())
        assert not await conn.fetchval("select system_control.auth_rate_limit($1,'account',$2)", bucket, uuid4())
        await db["owner"].execute("update system_control.rate_limits set window_start=window_start-interval '16 minutes'")
        assert await conn.fetchval("select system_control.auth_rate_limit($1,'account',$2)", bucket, uuid4())
        assert await db["owner"].fetchval("select count(*) from system_control.rate_limits") == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_same_mfa_counter_cannot_finish_two_challenges(system_database):
    import asyncio

    db = system_database
    await _seed(db)
    hashes = [hash_token(f"synthetic parallel challenge {n}") for n in range(2)]
    for digest in hashes:
        await db["owner"].execute("""insert into system_control.challenges
            (principal_id,kind,token_hash,issued_auth_version,credential_version,expires_at)
            values($1,'preauth',$2,1,1,now()+interval '5 minutes')""", db["actor"],digest)

    async def finish(digest):
        conn = await asyncpg.connect(db["url"].replace("+asyncpg",""))
        try:
            return await conn.fetchval("select system_control.auth_finish_totp($1,$2,$3)",
                digest,int(time.time()//30),hash_token(str(uuid4())))
        finally:
            await conn.close()

    results = await asyncio.gather(*(finish(digest) for digest in hashes))
    assert sum(result is not None for result in results) == 1


@pytest.mark.asyncio
async def test_http_invitation_delivers_only_to_selected_admin_and_activates_with_mfa(system_database,monkeypatch,tmp_path):
    db = system_database
    key, _, _ = await _seed(db)
    await db["owner"].execute("update system_control.role_assignments set role='superadmin'")
    session_token = "synthetic-session-token-with-at-least-forty-characters"
    await db["owner"].execute("update system_control.sessions set token_hash=$1",hash_token(session_token))
    database = tmp_path / "database"
    database.write_text(db["url"])
    keys = tmp_path / "keys"
    keys.write_text(json.dumps({"active":"test","keys":{"test":base64.b64encode(key).decode()}}))
    for name,value in {"ENABLED":"true","COMMANDS_ENABLED":"true","PUBLIC_ORIGIN":"https://admin.example.invalid",
                       "DATABASE_URL_FILE":str(database),"TOTP_KEYS_FILE":str(keys)}.items():
        monkeypatch.setenv(f"SYSTEM_ADMIN_{name}",value)
    app = create_app()
    sent = []

    class Mailbox:
        async def send_system_admin_link(self,**message):
            sent.append(message)

    async with app.router.lifespan_context(app),httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),base_url="https://admin.example.invalid",
    ) as admin:
        app.state.mailer=Mailbox()
        admin.cookies.set("__Host-graf_system_session",session_token)
        csrf=(await admin.get("/api/system-admin/v1/auth/csrf")).json()["csrf_token"]
        admin.headers.update({"origin":"https://admin.example.invalid","x-csrf-token":csrf})
        response=await admin.post("/api/system-admin/v1/admins",json={
            "email":"new@example.invalid","role":"support","reason":"Synthetic invitation",
        })
        assert response.status_code==201,response.text
        assert response.json()["delivery_state"]=="submitted"
        assert await db["owner"].fetchval("select delivery_state from system_control.challenges where kind='invitation'")=="submitted"
        assert len(sent)==1
        assert sent[0]["recipient_email"]=="new@example.invalid"
        token=sent[0]["url"].split("#")[1]
        assert token not in response.text
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="https://admin.example.invalid") as invited:
            csrf=(await invited.get("/api/system-admin/v1/auth/csrf")).json()["csrf_token"]
            invited.headers.update({"origin":"https://admin.example.invalid","x-csrf-token":csrf})
            response=await invited.post("/api/system-admin/v1/auth/enrolment/begin",json={
                "challenge":token,"password":"Synthetic invited password",
            })
            assert response.status_code==200,response.text
            assert (await invited.get("/api/system-admin/v1/me")).status_code==401
            token=response.json()["challenge"]
            seed=base64.b32decode(response.json()["seed"])
            response=await invited.post("/api/system-admin/v1/auth/enrolment/confirm",json={
                "challenge":token,"code":totp_code(seed,int(time.time()//30)),
            })
            assert response.status_code==200,response.text
            assert len(response.json()["recovery_codes"])==10
            assert (await invited.get("/api/system-admin/v1/me")).json()["role"]=="support"
            assert (await invited.get("/api/system-admin/v1/admins")).status_code==403


@pytest.mark.asyncio
async def test_operator_recovery_and_key_rotation_keep_mfa_boundary(system_database):
    import importlib.util
    from pathlib import Path

    from sqlalchemy.engine import make_url

    from twobrain_rec_server.system_admin.auth import decrypt_totp

    db=system_database
    key,seed,_=await _seed(db)
    module_spec=importlib.util.spec_from_file_location("system_admin_operator",Path(__file__).resolve().parents[2]/"scripts/manage_system_admin.py")
    operator=importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(operator)
    owner_url=make_url(db["url"]).set(username="twobrain_rec",password="twobrain_rec").render_as_string(hide_password=False)
    new_key=bytes(reversed(range(32)))
    assert await operator.rotate_totp_keys(database_url=owner_url,keys={"test":key,"next":new_key},active="next")==1
    assert await operator.rotate_totp_keys(database_url=owner_url,keys={"test":key,"next":new_key},active="next")==0
    credential=await db["owner"].fetchrow("select * from system_control.credentials")
    assert decrypt_totp(credential["encrypted_totp_seed"],nonce=credential["nonce"],principal_id=db["actor"],key=new_key)==seed
    token=await operator.issue_enrolment(database_url=owner_url,action="recover",email="synthetic@example.invalid",reason="Synthetic operator recovery")
    assert await db["owner"].fetchval("select count(*) from system_control.sessions where revoked_at is null")==0
    challenge=await db["owner"].fetchrow("select kind,issued_auth_version from system_control.challenges where token_hash=$1",hash_token(token))
    assert challenge["kind"]=="enrolment"
    assert challenge["issued_auth_version"]==2
    assert await db["owner"].fetchval("select status from system_control.principals")=="recovery_pending"


@pytest.mark.asyncio
async def test_operator_init_is_once_only_and_never_creates_session(system_database):
    import importlib.util
    from pathlib import Path

    from sqlalchemy.engine import make_url

    db=system_database
    await db["owner"].execute("truncate system_control.principals cascade")
    module_spec=importlib.util.spec_from_file_location("system_admin_init_operator",Path(__file__).resolve().parents[2]/"scripts/manage_system_admin.py")
    operator=importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(operator)
    owner_url=make_url(db["url"]).set(username="twobrain_rec",password="twobrain_rec").render_as_string(hide_password=False)
    token=await operator.issue_enrolment(database_url=owner_url,action="init",email="first@example.invalid",reason="Synthetic initial setup")
    assert await db["owner"].fetchval("select status from system_control.principals")=="invited"
    assert await db["owner"].fetchval("select expires_at from system_control.role_assignments") is None
    assert await db["owner"].fetchval("select count(*) from system_control.sessions")==0
    assert await db["owner"].fetchval("select token_hash from system_control.challenges")==hash_token(token)
    with pytest.raises(ValueError,match="уже создан"):
        await operator.issue_enrolment(database_url=owner_url,action="init",email="second@example.invalid",reason="Synthetic duplicate")
    recovery=await operator.issue_enrolment(database_url=owner_url,action="recover",email="first@example.invalid",reason="Synthetic lost initial invitation")
    assert await db["owner"].fetchval("select kind from system_control.challenges where token_hash=$1",hash_token(recovery))=="invitation"
