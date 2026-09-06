"""RFC 6238 vectors and administrative credential boundaries."""

import asyncio
from uuid import uuid4

import pytest
from cryptography.exceptions import InvalidTag

from twobrain_rec_server.system_admin.auth import (
    PasswordComputations,
    PasswordQueueFull,
    create_recovery_codes,
    create_totp_seed,
    decrypt_totp,
    encrypt_totp,
    hash_password,
    matching_totp_counter,
    totp_code,
    verify_password,
)


@pytest.mark.parametrize("timestamp,expected", [
    (59, "94287082"), (1111111109, "07081804"), (1111111111, "14050471"),
    (1234567890, "89005924"), (2000000000, "69279037"), (20000000000, "65353130"),
])
def test_totp_rfc6238(timestamp, expected):
    assert totp_code(b"12345678901234567890", timestamp // 30, digits=8) == expected


def test_totp_window_replay_and_credential_binding():
    seed = b"12345678901234567890"
    code = totp_code(seed, 100)
    assert matching_totp_counter(seed, code, now=3001, last_counter=99) == 100
    assert matching_totp_counter(seed, code, now=3001, last_counter=100) is None
    assert matching_totp_counter(seed, code, now=3061, last_counter=99) is None
    key, principal = bytes(range(32)), uuid4()
    nonce, encrypted = encrypt_totp(create_totp_seed(), principal_id=principal, key=key)
    assert len(decrypt_totp(encrypted, nonce=nonce, principal_id=principal, key=key)) == 20
    with pytest.raises(InvalidTag):
        decrypt_totp(encrypted, nonce=nonce, principal_id=uuid4(), key=key)
    codes, hashes = create_recovery_codes()
    assert len(set(codes)) == len(set(hashes)) == 10
    assert not set(codes) & set(hashes)


def test_password_parameters_and_exact_unicode_password():
    password = " Synthetic пароль  "
    encoded = hash_password(password)
    assert encoded.startswith("scrypt$131072$8$1$")
    assert verify_password(password, encoded)
    assert not verify_password(password.strip(), encoded)
    assert not verify_password(password, encoded.replace("131072", "16384"))
    with pytest.raises(ValueError):
        hash_password("short")
    with pytest.raises(ValueError):
        hash_password("a" * 129)


@pytest.mark.asyncio
async def test_password_queue_is_bounded():
    import threading

    limiter = PasswordComputations()
    gate = threading.Event()
    tasks = [asyncio.create_task(limiter.run(gate.wait)) for _ in range(12)]
    await asyncio.sleep(0.02)
    try:
        with pytest.raises(PasswordQueueFull):
            await limiter.run(lambda: None)
        tasks[0].cancel()
        await asyncio.sleep(0.02)
        assert limiter._outstanding == 12  # still owns its memory slot
    finally:
        gate.set()
        await asyncio.gather(*tasks, return_exceptions=True)
    assert limiter._outstanding == 0
