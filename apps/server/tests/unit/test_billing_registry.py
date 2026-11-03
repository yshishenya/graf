"""Official-format synthetic registries; no merchant data."""
import hashlib
from dataclasses import asdict
from datetime import date

import pytest

from twobrain_rec_server.billing.registry import RegistryInputError, parse_registry, registry_bundle

DAY = date(2026, 10, 29)


def report(kind="payments", count=1, *, start=0):
    payments = kind == "payments"
    name = "ПЛАТЕЖЕЙ" if payments else "ВОЗВРАТОВ"
    label = "платежей" if payments else "возвратов"
    columns = ("Идентификатор платежа;Сумма платежа;Валюта платежа;Время платежа;Тип платежа"
               if payments else "Идентификатор возврата;Идентификатор платежа;Сумма возврата;Валюта возврата;Время возврата")
    rows = [f"synthetic-{i};1.00;RUB;29.10.2026 10:00:00;AC" if payments
            else f"synthetic-refund-{i};synthetic-payment;1.00;RUB;29.10.2026 11:00:00"
            for i in range(start, start + count)]
    footer = f"Сумма {'принятых платежей' if payments else 'возвратов'}: {count}.00 RUB\nЧисло {label}: {count}"
    if payments:
        footer = f"Сумма принятых платежей типа AC: {count}.00 RUB\nЧисло платежей типа AC: {count}\n" + footer
    return (f"РЕЕСТР {name} ПО ДОГОВОРУ synthetic-contract (123)\nДата {label}: 2026-10-29\n"
            + columns + "\n" + "\n".join(rows) + "\n" + footer + "\nПо договору synthetic-contract\n").encode()


def part(kind="payments", count=1, *, suffix="", content=None, empty=False, start=0):
    return parse_registry(content if content is not None else report(kind, count, start=start),
                          filename=f"yoomoney-{kind}-123-2026-10-29{suffix}.csv",
                          kind=kind, shop_id="123", report_date=DAY, expected_empty=empty)


def bundle(*parts, expected_empty=()):
    return registry_bundle(parts, environment="test", shop_id="123", report_date=DAY,
                           expected_empty=frozenset(expected_empty))


def test_real_bytes_and_safe_metadata():
    value = part()
    assert value.sha256 == hashlib.sha256(report()).hexdigest()
    assert value.row_count == 1
    assert "synthetic-0" not in str(value.metadata())
    assert "1.00" not in str(value.metadata())
    assert part(content=b"\xef\xbb\xbf" + report()).sha256 != value.sha256
    assert part(content=report().replace(b"\n", b"\r\n")).sha256 != value.sha256


@pytest.mark.parametrize("old,new", [
    ("(123)", "(999)"), ("Дата платежей: 2026-10-29", "Дата платежей: 2026-10-28"),
    ("RUB;", "USD;"), (";1.00;", ";0.00;"), (";1.00;", ";1.001;"),
    ("29.10.2026 10:00:00", "28.10.2026 10:00:00"),
    ("Число платежей: 1", "Число платежей: 2"),
    ("Сумма принятых платежей: 1.00", "Сумма принятых платежей: 2.00"),
    ("Число платежей типа AC: 1", "Число платежей типа AC: 2"),
    ("Сумма принятых платежей типа AC: 1.00", "Сумма принятых платежей типа AC: 2.00"),
    ("По договору synthetic-contract", "По договору other-contract"),
    ("Тип платежа", "Идентификатор платежа"),
    ("synthetic-0;", ";"), (";AC\n", ";AC;extra\n"),
])
def test_bad_official_report_is_rejected_without_content_in_error(old, new):
    with pytest.raises(RegistryInputError) as error:
        part(content=report().decode().replace(old, new).encode())
    assert "synthetic" not in str(error.value)
    assert "999" not in str(error.value)


def test_bad_encoding_and_unsupported_filename():
    with pytest.raises(RegistryInputError):
        part(content=report() + b"\xff")
    with pytest.raises(RegistryInputError):
        part(suffix="-attempt-2")


def test_empty_requires_present_single_report_and_explicit_expectation():
    with pytest.raises(RegistryInputError):
        part(count=0)
    with pytest.raises(RegistryInputError):
        part(empty=True)
    with pytest.raises(RegistryInputError):
        part(count=0, empty=True, suffix="-part-1-last")
    value = bundle(part(), part("refunds", 0, empty=True), expected_empty=("refunds",))
    assert value.files_complete
    missing = bundle(part(), expected_empty=("refunds",))
    assert not missing.files_complete
    assert ("refunds", 0, "missing_kind") in missing.gaps


def test_multipart_duplicates_holes_and_last():
    first = part(count=10000, suffix="-part-1")
    last = part(suffix="-part-2-last", start=10000)
    assert bundle(first, last, part("refunds")).files_complete
    for bad in [(first, first), (part(), last), (first, part(suffix="-part-2-last")),
                (last, part(suffix="-part-3-last", start=10001))]:
        with pytest.raises(RegistryInputError):
            bundle(*bad)
    missing = bundle(part(suffix="-part-2-last"))
    assert ("payments", 1, "missing_part") in missing.gaps
    assert ("payments", 0, "missing_last") in bundle(first).gaps
    with pytest.raises(RegistryInputError):
        part(suffix="-part-1")


def test_digest_order_scope_and_safe_output():
    p, r = part(), part("refunds")
    assert bundle(p, r).input_digest == bundle(r, p).input_digest
    changed = registry_bundle((p, r), environment="production", shop_id="123", report_date=DAY,
                              expected_empty=frozenset())
    assert changed.input_digest != bundle(p, r).input_digest
    assert "synthetic" not in str(asdict(bundle(p, r)))


def test_many_refunds_for_one_payment_and_ignored_commission():
    assert part("refunds", 2).row_count == 2
    content = report().decode().replace("По договору", "Сумма комиссии без НДС за принятые платежи: 0.05 RUB\nПо договору")
    assert part(content=content.encode()).row_count == 1


@pytest.mark.parametrize("count", [0, 1])
@pytest.mark.parametrize("line", [";", ";;;;"])
def test_delimiter_only_record_is_not_an_empty_framing_line(count, line):
    content = report(count=count).decode().replace("Сумма принятых платежей типа AC:", line + "\nСумма принятых платежей типа AC:")
    with pytest.raises(RegistryInputError):
        part(content=content.encode(), empty=count == 0)


def test_complete_published_payment_structure_with_synthetic_values():
    # YooKassa reports-new structure, with the missing empty field restored to
    # match its 13-column header; all identifiers/content are synthetic.
    content = """РЕЕСТР ПЛАТЕЖЕЙ ПО ДОГОВОРУ synthetic-contract (123)
Дата платежей: 2026-10-29
Идентификатор платежа;Сумма платежа;Валюта платежа;Сумма за вычетом комиссии и НДС;Сумма комиссии без НДС;Время платежа;Идентификатор платежного средства;Описание;Тип платежа;Имя плательщика;Адрес плательщика;ИНН плательщика;НДС с комиссии

synthetic-1;2.00;RUB;1.91;0.07;29.10.2026 12:37:07;synthetic-method;synthetic-order;AC;;;;0,02
synthetic-2;8.00;RUB;7.66;0.28;29.10.2026 15:43:01;synthetic-method;synthetic-order;PC;;;;0,06
synthetic-3;4.00;RUB;3.83;0.14;29.10.2026 17:05:15;synthetic-method;synthetic-order;AC;;;;0,03

Сумма принятых платежей типа AC: 6.00 RUB
Сумма принятых платежей за вычетом комиссии и НДС типа AC: 5.74 RUB
Сумма комиссии без НДС за принятые платежи типа AC: 0.21 RUB
Сумма НДС с комиссии за принятые платежи типа AC: 0,05 RUB
Число платежей типа AC: 2

Сумма принятых платежей типа PC: 8.00 RUB
Сумма принятых платежей за вычетом комиссии и НДС типа PC: 7.66 RUB
Сумма комиссии без НДС за принятые платежи типа PC: 0.28 RUB
Сумма НДС с комиссии за принятые платежи типа PC: 0,06 RUB
Число платежей типа PC: 1

Сумма принятых платежей: 14.00 RUB
Сумма принятых платежей за вычетом комиссии и НДС: 13.40 RUB
Сумма комиссии без НДС за принятые платежи: 0.49 RUB
Сумма НДС с комиссии за принятые платежи: 0,11 RUB
Число платежей: 3

По договору synthetic-contract
"""
    value = part(content=content.encode())
    assert value.row_count == 3 and "13.40" not in str(value.metadata())
    with pytest.raises(RegistryInputError, match="invalid_footer"):
        part(content=content.replace("0,11 RUB", "anything").encode())


def test_published_refund_header_spacing_and_normalized_duplicates():
    content = report("refunds").decode().replace(";", "; ", 4)
    assert part("refunds", content=content.encode()).row_count == 1
    with pytest.raises(RegistryInputError, match="invalid_columns"):
        part("refunds", content=content.replace("Время возврата", "Идентификатор возврата").encode())


def test_csv_field_limit_is_pinned():
    import csv
    previous = csv.field_size_limit(32)
    try:
        with pytest.raises(RegistryInputError, match="csv_configuration_mismatch"):
            part()
    finally:
        csv.field_size_limit(previous)


def test_nonregular_input_is_rejected_without_waiting(tmp_path):
    import os

    from twobrain_rec_server.billing.registry import read_registry_files
    path = tmp_path / "yoomoney-payments-123-2026-10-29.csv"
    os.mkfifo(path)
    with pytest.raises(RegistryInputError, match="input_unreadable"):
        read_registry_files({"payments": [path]}, environment="test", shop_id="123",
                            report_date=DAY, expected_empty=frozenset())


def test_csv_limits_and_read_failures_are_bounded(tmp_path, monkeypatch):
    from twobrain_rec_server import billing
    from twobrain_rec_server.billing.registry import read_registry_files
    path = tmp_path / "yoomoney-payments-123-2026-10-29.csv"
    path.write_bytes(report())
    params = dict(environment="test", shop_id="123", report_date=DAY, expected_empty=frozenset())
    with pytest.raises(RegistryInputError, match="input_unreadable"):
        read_registry_files({"payments": [tmp_path / "absent.csv"]}, **params)
    with pytest.raises(RegistryInputError, match="input_limit"):
        read_registry_files({"payments": [path] * 65}, **params)
    monkeypatch.setattr(billing.registry, "MAX_FILE_BYTES", 32)
    with pytest.raises(RegistryInputError, match="input_limit"):
        read_registry_files({"payments": [path]}, **params)
    monkeypatch.setattr(billing.registry, "MAX_FILE_BYTES", 16 * 1024 * 1024)
    monkeypatch.setattr(billing.registry, "MAX_TOTAL_BYTES", 32)
    with pytest.raises(RegistryInputError, match="input_limit"):
        read_registry_files({"payments": [path]}, **params)


@pytest.mark.parametrize("change", [
    lambda s: s.replace("synthetic-0;1.00", "invalid identity;1.00"),
    lambda s: s.replace("29.10.2026 10:00:00", "29.10.2026 25:00:00"),
    lambda s: s.replace("29.10.2026 10:00:00", "29.10.2026 10:00"),
    lambda s: s.replace(";1.00;", ";-1.00;"),
    lambda s: s.replace(";1.00;", ";1,00;"),
    lambda s: s.replace(";AC\n", ";\n"),
    lambda s: s.replace("Число платежей: 1", "Число платежей: 1\nЧисло платежей: 1"),
    lambda s: s.replace("Число платежей: 1", "Число платежей: 1\nЧисло неизвестных: 1"),
    lambda s: s.replace("synthetic-0;1.00;RUB;29.10.2026 10:00:00;AC", "synthetic-0;1.00;RUB;29.10.2026 10:00:00;AC\nsynthetic-0;1.00;RUB;29.10.2026 10:00:00;AC"),
])
def test_negative_money_identity_time_and_footer(change):
    with pytest.raises(RegistryInputError):
        part(content=change(report().decode()).encode())
