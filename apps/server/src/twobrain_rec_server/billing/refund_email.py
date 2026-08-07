from __future__ import annotations

from email.utils import parseaddr
from urllib.parse import quote, unquote


def build_refund_mailto(*, support_email: str, safe_invoice_number: str) -> str:
    if any(char in support_email for char in "\r\n"):
        raise ValueError("support email is invalid")
    address = parseaddr(support_email)[1].strip()
    if not address:
        raise ValueError("support email is invalid")
    reference = safe_invoice_number.strip()
    decoded_reference = unquote(reference)
    if not reference or any(char in decoded_reference for char in "\r\n"):
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
