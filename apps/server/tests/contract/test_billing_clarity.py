"""Financial disclosures must survive native details being closed (F280)."""

from html.parser import HTMLParser

import pytest

from twobrain_rec_server.billing.catalog import plan_descriptor
from twobrain_rec_server.cabinet.templates import render_template


class Page(HTMLParser):
    """Inspect native HTML visibility; actual CSS/layout is checked in the browser."""

    def __init__(self, html):
        super().__init__()
        self.stack = []
        self.nodes = []
        self.words = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = (tag, dict(attrs))
        self.nodes.append(node)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        for index, (tag, attrs) in enumerate(self.stack):
            if tag in {"script", "style"} or "hidden" in attrs:
                return
            if tag == "details" and "open" not in attrs and not any(
                child[0] == "summary" for child in self.stack[index + 1:]
            ):
                return
        self.words.append(data)

    @property
    def visible(self):
        return " ".join(" ".join(self.words).split())


def checkout(**overrides):
    context = dict(
        plan=plan_descriptor("personal"),
        billing_enabled=True,
        catalog_ready=True,
        checkout_quote_id="synthetic-quote",
        checkout_idempotency_key="synthetic-key",
        csrf_token="synthetic-csrf",
        offer_version_label="synthetic-offer-version",
        catalog_storage_label="5 ГБ",
        checkout_cycle="month",
        checkout_period_label="29.09.2026 — 29.10.2026",
        checkout_next_attempt_label="26.10.2026",
        monthly_price_label="1 000 ₽",
        annual_price_label="10 000 ₽",
        receipt_contact_ready=True,
        checkout_has_discount=False,
    )
    context.update(overrides)
    return render_template("cabinet/pages/billing_checkout_content.html", **context)


@pytest.mark.parametrize("cycle,amount", [("month", "1 000 ₽"), ("year", "10 000 ₽")])
@pytest.mark.parametrize("discount", [False, True])
def test_checkout_keeps_full_financial_terms_outside_optional_details(cycle, amount, discount):
    payable = "900 ₽" if discount else amount
    page = Page(checkout(
        checkout_cycle=cycle,
        checkout_has_discount=discount,
        checkout_preview={
            "list_amount_label": amount,
            "payable_amount_label": payable,
            "discount_label": "−100 ₽" if discount else "0 ₽",
            "next_amount_label": amount,
            "cycle_label": "месяц" if cycle == "month" else "год",
        },
    ))
    for term in ("Личный", "5 ГБ", payable, amount, "29.09.2026 — 29.10.2026", "26.10.2026", "При автопродлении", "оферту"):
        assert term in page.visible
    assert ("Разовая скидка" in page.visible) == discount
    assert ("−100 ₽" in page.visible) == discount
    assert "synthetic-offer-version" not in page.visible
    assert "Отключить" in page.visible and "Подписке" in page.visible
    consents = [attrs for tag, attrs in page.nodes if tag == "input" and attrs.get("type") == "checkbox"]
    assert {item["name"] for item in consents} == {"offer_consent", "recurring_consent"}
    offer = next(item for item in consents if item["name"] == "offer_consent")
    recurring = next(item for item in consents if item["name"] == "recurring_consent")
    assert "required" in offer and "checked" not in offer
    assert "required" not in recurring and "checked" in recurring
    assert "Списание при автопродлении" in page.visible
    assert any(attrs.get("name") == "offer_version" and attrs.get("type") == "hidden" and attrs.get("value") == "synthetic-offer-version" for _, attrs in page.nodes)


@pytest.mark.parametrize("blocked", [None, False])
def test_checkout_unavailable_account_removes_payment_action_without_pending_claim(blocked):
    context = {"checkout_result": "account_unavailable"}
    if blocked is not None:
        context["checkout_blocked"] = blocked
    page = Page(checkout(**context))
    assert "Оплата для этого аккаунта сейчас недоступна. Обратитесь в поддержку." in page.visible
    assert "Платеж уже создан" not in page.visible
    assert not any(tag == "form" and attrs.get("action") == "/billing/checkout/start" for tag, attrs in page.nodes)
    assert not any(tag == "button" and "data-billing-primary" in attrs for tag, attrs in page.nodes)
    assert not any(attrs.get("name") in {"quote_id", "idempotency_key", "offer_consent", "recurring_consent"} for _, attrs in page.nodes)


@pytest.mark.parametrize("cycle,expected", [("month", "month"), ("year", "year"), ("unexpected", "month")])
def test_checkout_manual_preview_recovery_retains_only_allowlisted_period(cycle, expected):
    page = Page(checkout(checkout_cycle=cycle, checkout_promo_code="SYNTHETIC"))
    links = [attrs for tag, attrs in page.nodes if tag == "a" and "data-billing-preview-recovery" in attrs]
    assert len(links) == 1
    assert links[0]["href"] == f"/billing/checkout?cycle={expected}"
    assert "hidden" in links[0]


def test_checkout_coupon_opens_for_error_but_never_enables_invalid_quote():
    page = Page(checkout(promo_preview_error="Проверьте промокод", checkout_promo_code="SYNTHETIC"))
    assert "Проверьте промокод" in page.visible
    assert any(tag == "details" and "open" in attrs for tag, attrs in page.nodes)
    assert not any(attrs.get("action") == "/billing/checkout/start" for _, attrs in page.nodes)


def test_checkout_missing_receipt_contact_provides_recovery_without_money_form():
    page = Page(checkout(
        receipt_contact_ready=False,
        receipt_contact_message="Подтвердите почту для чека.",
        receipt_contact_action_url="/settings/account#account-providers-title",
    ))
    assert "Подтвердите почту для чека" in page.visible
    assert any(attrs.get("href") == "/settings/account#account-providers-title" for _, attrs in page.nodes)
    assert not any(attrs.get("action") == "/billing/checkout/start" for _, attrs in page.nodes)
    assert any(tag == "form" and attrs.get("id") == "billing-promo-preview" and attrs.get("action") == "/billing/checkout/preview" for tag, attrs in page.nodes)
    assert any(tag == "input" and attrs.get("name") == "promo_code" and attrs.get("type") == "text" and attrs.get("form") == "billing-promo-preview" for tag, attrs in page.nodes)
    assert any(tag == "button" and attrs.get("form") == "billing-promo-preview" and attrs.get("name") == "preview_action" and attrs.get("value") == "apply" for tag, attrs in page.nodes)
    assert "Есть промокод?" in page.visible
    assert not any(tag == "input" and attrs.get("name") in {"offer_consent", "recurring_consent", "quote_id", "idempotency_key"} for tag, attrs in page.nodes)
    assert not any(tag == "button" and "data-billing-primary" in attrs for tag, attrs in page.nodes)
    assert "Оплатить" not in page.visible


@pytest.mark.parametrize("purpose,recurring", [("storage_upgrade", True), ("storage_upgrade", False), ("early_renewal", False), ("storage_schedule", False)])
def test_purchase_keeps_future_price_capacity_transitions_and_payment_intent_visible(purpose, recurring):
    deferred = purpose == "storage_schedule"
    page = Page(render_template(
        "cabinet/pages/billing_purchase_content.html",
        csrf_token="synthetic",
        purchase_error=None,
        purchase={
            "quote_id": "synthetic",
            "purpose": purpose,
            "title": "Проверка покупки",
            "capacity_label": "10 ГБ",
            "current_capacity_label": "5 ГБ",
            "list_label": "150 ₽",
            "discount_label": "0 ₽",
            "has_discount": False,
            "payable_label": "0 ₽" if deferred else "150 ₽",
            "base_label": "1 000 ₽",
            "storage_label": "250 ₽",
            "next_label": "1 250 ₽",
            "cycle_label": "месяц",
            "period_label": "29.09.2026 — 29.10.2026",
            "next_attempt_label": "26.10.2026" if recurring else None,
            "recurring_allowed": recurring,
            "method_label": "•••• 4242" if purpose == "early_renewal" else None,
            "deferred": deferred,
            "timeline": [
                {"start": "29.09.2026", "end": "29.10.2026", "capacity": "10 ГБ", "bonus": False},
                {"start": "29.10.2026", "end": "29.11.2026", "capacity": "20 ГБ", "bonus": False},
            ],
        },
    ))
    for term in ("10 ГБ", "20 ГБ", "1 250 ₽", "29.10.2026", "29.11.2026", "месяц", "Автопродление"):
        assert term in page.visible
    assert "Разовая скидка" not in page.visible
    assert "пакетов" not in page.visible
    if recurring:
        assert "Включено" in page.visible and "26.10.2026" in page.visible
    else:
        assert "автоматического списания не будет" in page.visible
    if deferred:
        assert "0 ₽" in page.visible
        assert "Файлы автоматически не удаляются" in page.visible
        assert "Сохранить выбор без списания" in page.visible
    if purpose == "early_renewal":
        assert "•••• 4242" in page.visible and "с сохраненной карты" in page.visible
    consents = [attrs for tag, attrs in page.nodes if tag == "input" and attrs.get("type") == "checkbox"]
    assert len(consents) == 1 and consents[0]["name"] == "purchase_consent"
    assert "checked" not in consents[0] and "required" in consents[0]


def test_storage_choices_separate_addon_price_from_whole_plan():
    html = render_template(
        "cabinet/pages/billing_storage_content.html", csrf_token="synthetic",
        eligible=True, billing_enabled=True, current_capacity_label="5 ГБ",
        selected_package_count=1,
        storage_options=[{
            "package_count": count, "label": f"{(count + 1) * 5} ГБ",
            "addon_label": f"{count * 250} ₽", "total_label": f"{1000 + count * 250} ₽",
            "cycle_label": "месяц",
        } for count in (0, 1, 99)],
    )
    page = Page(html)
    options = [attrs for tag, attrs in page.nodes if tag == "option"]
    assert len(options) == 3
    assert "Включено в тариф" in html
    assert "+250 ₽ / месяц за хранение" in html
    assert "+24750 ₽ / месяц за хранение" in html
    assert "Вместе с тарифом — 1250 ₽ за месяц" in html
    assert "Точную доплату" in page.visible and "без списания" in page.visible
    assert "×" not in page.visible and "пакет" not in page.visible
    assert "Промокод, если есть" not in page.visible
    assert any(tag == "option" and attrs.get("value") == "99" for tag, attrs in page.nodes)


def test_referral_copy_action_does_not_promise_sharing():
    html = render_template(
        "cabinet/pages/referrals_content.html", referral_issued=True,
        referral_link="https://graf.test/r/synthetic", referral_issue_result=None,
        referral_expires_at_label="29.10.2026", support_email=None,
    )
    assert html.count('data-copy-target="referral-link"') == 1
    assert "Поделиться" not in Page(html).visible


def test_storage_without_receipt_contact_allows_capacity_choice_before_coupon_entry():
    page = Page(render_template(
        "cabinet/pages/billing_storage_content.html", csrf_token="synthetic",
        eligible=True, billing_enabled=True, current_capacity_label="10 ГБ",
        selected_package_count=0, receipt_contact_ready=False,
        storage_options=[{
            "package_count": 0, "label": "5 ГБ", "addon_label": "0 ₽", "total_label": "1 000 ₽",
            "cycle_label": "месяц",
        }],
    ))
    assert not any(tag == "input" and attrs.get("name") == "promo_code" for tag, attrs in page.nodes)
    assert "Есть промокод?" not in page.visible
    assert any(tag == "select" and attrs.get("name") == "package_count" for tag, attrs in page.nodes)
    assert any(attrs.get("action") == "/billing/storage/preview" for _, attrs in page.nodes)
    assert "Проверить доплату" in page.visible


def test_plans_distinguish_trial_capacity_from_the_two_plan_choices():
    plans = [
        {
            "code": code, "label": label, "processing_mode": "limited" if code == "free" else "unlimited",
            "processing_label": "300 минут", "storage_label": capacity,
            "monthly_amount_label": "1 000 ₽", "annual_amount_label": "10 000 ₽",
            "annual_saving_label": None, "is_current": code == "free", "catalog_ready": True,
        }
        for code, label, capacity in (
            ("free", "Бесплатный", "250 МБ"), ("trial", "Пробный", "500 МБ"),
            ("personal", "Личный", "5 ГБ"),
        )
    ]
    page = Page(render_template(
        "cabinet/pages/billing_plans_content.html", plans=plans, selected_cycle="year",
        current_plan_code="free", billing_owner=True, billing_enabled=True,
        trial_state="eligible", csrf_token="synthetic",
    ))
    cards = [attrs for tag, attrs in page.nodes if tag == "article" and "billing-plan-card" in attrs.get("class", "").split()]
    assert len(cards) == 2
    assert sum("primary" in attrs.get("class", "").split() for _, attrs in page.nodes) == 1
    for term in ("250 МБ", "500 МБ", "5 ГБ", "10 000 ₽", "за год", "Карта не нужна"):
        assert term in page.visible
    assert any(attrs.get("href") == "/billing/checkout?cycle=year" for _, attrs in page.nodes)


def test_disabled_checkout_does_not_hide_already_paid_storage_transitions():
    page = Page(render_template(
        "cabinet/pages/billing_storage_content.html", eligible=True, billing_enabled=False,
        csrf_token="synthetic", selection_version=1,
        current_capacity_label="10 ГБ", next_capacity_label="5 ГБ",
        paid_through_label="29.10.2026", storage_timeline=[
            {"start": "29.09.2026", "end": "29.10.2026", "capacity": "10 ГБ", "bonus": False},
        ],
    ))
    for term in ("10 ГБ", "5 ГБ", "29.10.2026", "Условия и оплаченные периоды"):
        assert term in page.visible
    assert [attrs.get("action") for tag, attrs in page.nodes if tag == "form"] == ["/billing/storage/cancel-selection"]
    assert "Отменить выбор следующего объема" in page.visible


def test_invoice_refund_disclosure_explains_manual_status_and_separate_renewal_control():
    html = render_template(
        "cabinet/pages/billing_invoice_content.html", support_email="support@example.test",
        invoice={
            "safe_number": "INV-SYNTHETIC", "amount_label": "1 000 ₽",
            "status_label": "Оплачен", "cycle_label": "месяц",
            "receipt_url": None, "receipt_label": "Чек готовится",
            "discount_label": None, "payment_method_label": None, "receipt_contact_label": None,
            "refund_mailto": "mailto:support@example.test?subject=INV-SYNTHETIC",
        },
    )
    page = Page(html)
    assert "1 000 ₽" in page.visible and "Помощь и возврат" in page.visible
    assert "Результат возврата" not in page.visible
    expanded = Page(html.replace(
        '<details class="settings-disclosure"><summary>Помощь и возврат</summary>',
        '<details class="settings-disclosure" open><summary>Помощь и возврат</summary>',
    ))
    for term in (
        "Результат возврата уточняйте у поддержки", "GRAF не показывает его статус",
        "Возврат не отключает автопродление", "Открытие письма не отправляет запрос",
    ):
        assert term in expanded.visible
    assert any(attrs.get("href") == "/billing/subscription" for _, attrs in expanded.nodes)
    assert not any(tag == "form" for tag, _ in expanded.nodes)


@pytest.mark.parametrize("state", ["fresh", "stale", "unavailable"])
@pytest.mark.parametrize("owner", [True, False])
def test_storage_usage_is_concise_without_losing_privacy_or_unknown_state(state, owner):
    html = render_template(
        "cabinet/pages/billing_usage_content.html", embedded=False,
        billing_owner=owner, usage_projection_state=state,
        processing_unlimited=True, processing_used_label="35 мин 39 сек",
        processing_threshold="normal", storage_used=715_230_000,
        storage_used_label="715 МБ", storage_reserved=100_000_000,
        storage_reserved_label="100 МБ", storage_capacity=10_000_000_000,
        storage_capacity_label="10 ГБ", storage_available_label="9,18 ГБ",
        storage_threshold="normal", storage_threshold_label="В норме",
    )
    page = Page(html)
    progress = [attrs for tag, attrs in page.nodes if tag == "progress"]
    assert len(progress) == int(owner and state != "unavailable")
    if owner and state != "unavailable":
        assert progress[0]["value"] == "715230000"
        assert progress[0]["max"] == "10000000000"
        assert "715 МБ из 10 ГБ" in page.visible
        assert html.index('id="usage-storage-title"') < html.index('id="usage-processing-title"')
        assert "35 мин 39 сек" not in page.visible
        assert "Состояние: В норме" not in page.visible
    else:
        assert "715 МБ" not in page.visible
    assert ("устарели" in page.visible) == (state == "stale")
    assert not any(attrs.get("href") == "/billing/storage" for _, attrs in page.nodes) if not owner else True
    assert "Нужна помощь с оплатой?" not in page.visible


def test_storage_timeline_is_optional_but_future_selection_is_visible():
    page = Page(render_template(
        "cabinet/pages/billing_storage_content.html", eligible=True, billing_enabled=False,
        csrf_token="synthetic", selection_version=1,
        current_capacity_label="10 ГБ", next_capacity_label="5 ГБ", paid_through_label="03.01.2028",
        storage_timeline=[{"start": "15.10.2026", "end": "03.11.2026", "capacity": "10 ГБ", "bonus": True}],
    ))
    assert "03.01.2028" in page.visible and "5 ГБ" in page.visible
    assert "15.10.2026" not in page.visible and "бонусный срок" not in page.visible
    assert any(tag == "details" and "open" not in attrs for tag, attrs in page.nodes)


@pytest.mark.parametrize("threshold,notice", [("80%", "Место заканчивается"), ("95%", "Место заканчивается"), ("over_capacity", "Объем хранилища превышен")])
def test_storage_warning_stays_explicit_after_simplification(threshold, notice):
    page = Page(render_template(
        "cabinet/pages/billing_usage_content.html", embedded=False, billing_owner=True,
        storage_threshold=threshold, processing_unlimited=True, processing_used_label="35 мин",
        processing_threshold="normal", storage_used=6_000_000_000, storage_capacity=5_000_000_000,
        storage_used_label="6 ГБ", storage_capacity_label="5 ГБ",
    ))
    assert notice in page.visible
    if threshold == "over_capacity":
        assert "новое аудио не сохраняется" in page.visible


def test_storage_base_capacity_copy_names_the_paid_plan_for_free_users():
    page = Page(render_template(
        "cabinet/pages/billing_storage_content.html", eligible=False, billing_enabled=True,
        current_capacity_label="500 МБ",
    ))
    assert "В тариф «Личный» включено 5 ГБ" in page.visible
    assert "500 МБ" in page.visible
