"""Local HTTPS console with disposable PostgreSQL and a non-delivering mailbox."""

import argparse
import asyncio
import base64
import ipaddress
import json
import os
import tempfile
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import asyncpg
import uvicorn
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from sqlalchemy.engine import make_url

from tests.fixtures.playback_normalization_ui_harness import create_harness
from twobrain_rec_server.system_admin.app import create_app
from twobrain_rec_server.system_admin.auth import encrypt_totp, hash_password


async def seed_admin(url):
    conn = await asyncpg.connect(url.replace("+asyncpg", ""))
    actor, role = uuid4(), uuid4()
    key = bytes(range(32))
    seed = base64.b32encode(b"12345678901234567890").decode()
    nonce, cipher = encrypt_totp(seed, principal_id=actor, key=key)
    try:
        assert await conn.fetchval("select count(*) from system_control.principals") == 0
        await conn.execute("alter role twobrain_rec_system login password 'synthetic-browser-only'")
        await conn.execute("""insert into system_control.principals(id,normalized_email,password_hash,status,auth_version)
            values($1,'browser@example.invalid',$2,'active',1)""", actor, hash_password("Synthetic browser password 254"))
        await conn.execute("""insert into system_control.role_assignments(id,principal_id,role,starts_at)
            values($1,$2,'superadmin',now())""", role, actor)
        await conn.execute("""insert into system_control.credentials(principal_id,encrypted_totp_seed,key_id,nonce)
            values($1,$2,'synthetic',$3)""", actor, cipher, nonce)
    finally:
        await conn.close()
    return key


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url-file", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8943)
    args = parser.parse_args()
    url = args.database_url_file.read_text().strip()
    parsed = make_url(url)
    if parsed.host not in ("localhost", "127.0.0.1", "::1") or not parsed.database.startswith("twobrain_rec_test_"):
        parser.error("a disposable loopback test database is required")
    origin = f"https://localhost:{args.port}"
    with tempfile.TemporaryDirectory(prefix="graf-system-admin-ui-") as directory:
        root = Path(directory)
        product_app, state = create_harness(runtime_directory=root, origin=origin, database_url=url)
        asyncio.run(product_app.state.db_engine.dispose())
        key = asyncio.run(seed_admin(url))
        db_file, key_file = root/"database", root/"keys"
        db_file.write_text(parsed.set(username="twobrain_rec_system",password="synthetic-browser-only").render_as_string(hide_password=False))
        key_file.write_text(json.dumps({"active":"synthetic","keys":{"synthetic":base64.b64encode(key).decode()}}))
        for name,value in {"ENABLED":"true","COMMANDS_ENABLED":"true","PUBLIC_ORIGIN":origin,
                           "DATABASE_URL_FILE":str(db_file),"TOTP_KEYS_FILE":str(key_file)}.items():
            os.environ[f"SYSTEM_ADMIN_{name}"] = value
        os.environ.pop("SYSTEM_ADMIN_POSTAL_API_URL", None)
        app = create_app()
        original_lifespan = app.router.lifespan_context

        class Mailbox:
            async def send_system_admin_link(self, **message):
                pass  # Synthetic sink: never contacts a mail provider.

        @asynccontextmanager
        async def lifespan(application):
            async with original_lifespan(application):
                application.state.mailer = Mailbox()
                application.state.media_storage = product_app.state.storage
                yield

        app.router.lifespan_context = lifespan
        private = rsa.generate_private_key(public_exponent=65537,key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,"localhost")])
        cert = x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(private.public_key()).serial_number(x509.random_serial_number()).not_valid_before(datetime.now(UTC)-timedelta(minutes=1)).not_valid_after(datetime.now(UTC)+timedelta(days=1)).add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost"),x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),critical=False).sign(private,hashes.SHA256())
        cert_file, private_file = root/"certificate", root/"private"
        cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        private_file.write_bytes(private.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
        for file in (db_file,key_file,private_file):
            file.chmod(0o600)
        print(json.dumps({"origin":origin,"meeting_id":str(state["available_id"])}),flush=True)
        uvicorn.run(app,host="127.0.0.1",port=args.port,ssl_certfile=str(cert_file),ssl_keyfile=str(private_file),access_log=False,log_level="warning")


if __name__ == "__main__":
    run()
