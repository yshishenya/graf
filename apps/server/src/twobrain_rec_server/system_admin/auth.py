"""Administrative credentials; no product tokens or sessions are accepted."""

import asyncio
import base64
import hashlib
import hmac
import secrets
import struct
from functools import partial
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SCRYPT_N = 2**17
SCRYPT_R = 8
SCRYPT_P = 1


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    if not 14 <= len(password) <= 128:
        raise ValueError("password must contain 14 to 128 characters")
    salt = salt or secrets.token_bytes(16)
    value = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=SCRYPT_N,
                           r=SCRYPT_R, p=SCRYPT_P, maxmem=256 * 1024 * 1024, dklen=32)
    return f"scrypt$131072$8$1${salt.hex()}${value.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$")
        if (algorithm, n, r, p) != ("scrypt", "131072", "8", "1"):
            return False
        if len(salt) != 32 or len(expected) != 64:
            return False
        actual = hash_password(password, salt=bytes.fromhex(salt)).rsplit("$", 1)[1]
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError, AttributeError):
        return False


class PasswordComputations:
    """Bound scrypt memory to two calls, with at most ten waiting requests."""

    def __init__(self) -> None:
        self._semaphore = asyncio.Semaphore(2)
        self._outstanding = 0

    async def run(self, function, *args):
        if self._outstanding >= 12:
            raise PasswordQueueFull
        self._outstanding += 1
        try:
            await self._semaphore.acquire()
        except BaseException:
            self._outstanding -= 1
            raise
        task = asyncio.create_task(asyncio.to_thread(partial(function, *args)))

        def completed(task):
            # A cancelled HTTP request must retain its slot until the thread
            # finishes; repeated cancellation cannot exceed the memory limit.
            self._semaphore.release()
            self._outstanding -= 1
            if not task.cancelled():
                task.exception()

        task.add_done_callback(completed)
        return await asyncio.shield(task)



class PasswordQueueFull(Exception):
    pass


def totp_code(seed: bytes, counter: int, *, digits: int = 6) -> str:
    digest = hmac.new(seed, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = (int.from_bytes(digest[offset:offset + 4], "big") & 0x7FFFFFFF) % (10**digits)
    return str(number).zfill(digits)


def matching_totp_counter(seed: bytes, code: str, *, now: float, last_counter: int) -> int | None:
    if len(code) != 6 or not code.isascii() or not code.isdigit():
        return None
    current = int(now // 30)
    for counter in (current, current - 1, current + 1):
        if counter >= 0 and counter > last_counter and hmac.compare_digest(totp_code(seed, counter), code):
            return counter
    return None


def create_totp_seed() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii")


def encrypt_totp(seed: str, *, principal_id: UUID, key: bytes) -> tuple[bytes, bytes]:
    nonce = secrets.token_bytes(12)
    return nonce, AESGCM(key).encrypt(nonce, seed.encode("ascii"), principal_id.bytes)


def decrypt_totp(ciphertext: bytes, *, nonce: bytes, principal_id: UUID, key: bytes) -> bytes:
    return base64.b32decode(AESGCM(key).decrypt(nonce, ciphertext, principal_id.bytes))


def create_recovery_codes() -> tuple[list[str], list[str]]:
    codes = [secrets.token_urlsafe(24) for _ in range(10)]
    return codes, [hash_token(code) for code in codes]
