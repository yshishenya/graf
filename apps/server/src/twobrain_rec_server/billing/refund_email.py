from __future__ import annotations

import re
from email.utils import parseaddr
from urllib.parse import quote, unquote

_SUPPORT_EMAIL_RE = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,63}")
_SAFE_INVOICE_RE = re.compile(r"[A-Z0-9][A-Z0-9-]{2,79}")


def build_refund_mailto(*, support_email: str, safe_invoice_number: str) -> str:
    if any(char in support_email for char in "\r\n"):
        raise ValueError("support email is invalid")
    address = parseaddr(support_email)[1].strip()
    if not address or not _SUPPORT_EMAIL_RE.fullmatch(address):
        raise ValueError("support email is invalid")
    reference = safe_invoice_number.strip()
    decoded_reference = unquote(reference)
    if (
        not reference
        or any(char in decoded_reference for char in "\r\n")
        or not _SAFE_INVOICE_RE.fullmatch(reference)
    ):
        raise ValueError("invoice reference is invalid")
    if len(reference) > 80:
        raise ValueError("invoice reference is too long")
    subject = quote(f"Возврат по платежу {reference}")
    body = quote(
        f"Номер платежа: {reference}\n\n"
        "Опишите запрос. Не отправляйте данные карты, идентификаторы YooKassa, "
        "ссылки или содержимое встреч."
    )
    return f"mailto:{address}?subject={subject}&body={body}"
