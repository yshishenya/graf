import json
import re
from html import unescape
from pathlib import Path

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import seed_cabinet_meetings
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY

REPO_ROOT = Path(__file__).parents[4]
_PRODUCT_PROVIDER_RE = re.compile(
    r'<script id="graf-product-analytics-provider-config"[^>]*>\s*(.*?)\s*</script>',
    re.DOTALL,
)


def _enable_product_provider_settings(client, tmp_path: Path) -> None:
    key_file = tmp_path / "posthog_project_key"
    key_file.write_text("synthetic-posthog-key", encoding="utf-8")
    settings = client.app.state.settings
    settings.product_analytics_enabled = True
    settings.product_analytics_provider_mode = "parallel_measurement"
    settings.product_analytics_validation_mode = "provider_smoke"
    settings.product_analytics_posthog_enabled = True
    settings.product_analytics_posthog_host = "https://analytics.example.test"
    settings.product_analytics_posthog_project_key_file = key_file
    settings.product_analytics_yandex_all_pages_enabled = True
    settings.product_analytics_yandex_counter_id = "12345678"
    settings.product_analytics_legal_approved = True


def _product_provider_config(html: str) -> dict:
    match = _PRODUCT_PROVIDER_RE.search(html)
    assert match is not None
    return json.loads(unescape(match.group(1)))


def test_public_cabinet_and_admin_templates_include_provider_config_and_private_attrs() -> None:
    public_partial = (
        REPO_ROOT
        / "apps/server/src/twobrain_rec_server/public/templates/public/_product_analytics_provider.html"
    ).read_text(encoding="utf-8")
    cabinet_base = (
        REPO_ROOT / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/base.html"
    ).read_text(encoding="utf-8")
    admin_base = (
        REPO_ROOT / "apps/server/src/twobrain_rec_server/admin/templates/admin/base.html"
    ).read_text(encoding="utf-8")

    for template in (public_partial, cabinet_base, admin_base):
        assert "graf-product-analytics-provider-config" in template
        assert "analytics.js" in template
    for template in (cabinet_base, admin_base):
        assert 'data-graf-analytics-private="true"' in template
        assert 'data-ph-mask="true"' in template
        assert 'data-ym-hide-content="true"' in template
        assert 'data-ym-disable-keys="true"' in template
    assert 'data-yandex-state="blocked"' in admin_base


def test_primitives_have_provider_private_attributes_without_disabling_posthog_autocapture() -> None:
    primitives = (
        REPO_ROOT / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/primitives.html"
    ).read_text(encoding="utf-8")
    provider_macro = primitives.split("{% macro provider_private_attrs() -%}", maxsplit=1)[1]

    assert "provider_private_attrs" in primitives
    assert 'data-ph-mask="true"' in provider_macro
    assert 'data-ym-hide-content="true"' in provider_macro
    assert 'data-ph-no-capture="true"' not in provider_macro


def test_rendered_public_auth_cabinet_and_desktop_pages_include_live_product_provider_config(
    client,
    tmp_path: Path,
) -> None:
    _enable_product_provider_settings(client, tmp_path)
    seeds = seed_cabinet_meetings(client)
    deletion_meeting_id = seeds.processing_id
    deletion_request = client.post(
        f"/api/v1/cabinet/meetings/{deletion_meeting_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_DELETE_COPY},
    )
    assert deletion_request.status_code == 202
    public_cases = {
        "/": "public_landing",
        "/download": "public_download",
        "/privacy": "legal",
        "/login": "login_signup",
        "/sign-up": "login_signup",
    }
    authenticated_cases = {
        "/meetings": "recording_list",
        f"/meetings/{seeds.ready_id}": "meeting_result_detail",
        "/settings": "settings",
        "/settings/integrations/calendar": "settings",
        "/desktop/meetings": "embedded_desktop_webview",
        f"/desktop/meetings/{seeds.ready_id}": "meeting_result_detail",
        f"/meetings/{deletion_meeting_id}/deletion-report": "deletion",
        f"/desktop/meetings/{deletion_meeting_id}/deletion-report": "deletion",
        "/admin": "admin",
    }

    for path, expected_page_class in public_cases.items():
        response = client.get(path)
        assert response.status_code == 200, path
        config = _product_provider_config(response.text)
        assert config["page_class"] == expected_page_class
        assert config["posthog"]["enabled"] is True
        assert config["posthog"]["distinct_id"] == "graf_pseudo_browser_anonymous"
        assert config["posthog"]["identity_state"] == "anonymous"
        assert "/static/public/analytics.js" in response.text
        assert response.text.count("/static/public/analytics.js") == 1

    for path, expected_page_class in authenticated_cases.items():
        response = client.get(path, headers=auth_headers())
        assert response.status_code == 200, path
        config = _product_provider_config(response.text)
        assert config["page_class"] == expected_page_class
        assert config["posthog"]["enabled"] is True
        assert config["posthog"]["distinct_id"].startswith("graf_pseudo_user_")
        assert config["posthog"]["identity_state"] == "authenticated_pseudonymous"
        if expected_page_class == "admin":
            assert config["posthog"].get("workspace_pseudonym") is None
            assert config["yandex"]["state"] == "blocked"
        else:
            assert config["posthog"]["workspace_pseudonym"].startswith("graf_pseudo_workspace_")
        assert "/static/public/analytics.js" in response.text
        assert response.text.count("/static/public/analytics.js") == 1
