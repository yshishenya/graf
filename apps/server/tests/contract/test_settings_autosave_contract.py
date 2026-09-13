"""Autosave acknowledges persisted values, preserves unrelated fields and fences scope."""
from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import FORGED_USER_ID, USER_ID, WORKSPACE_ID


def test_settings_autosave_acknowledges_values_and_rejects_stale_scope(client):
    headers = {**auth_headers(), "X-Graf-Settings-Autosave": "true",
               "X-Graf-Expected-Actor": str(USER_ID), "X-Graf-Expected-Workspace": str(WORKSPACE_ID)}
    for prefix in ("", "/desktop"):
        profile = client.post(prefix + "/settings/account/profile", headers=headers,
                              data={"display_name": "  Новое   имя "}, follow_redirects=False)
        assert profile.status_code == 200, profile.text
        assert profile.json()["values"] == {"display_name": "Новое имя"}
        assert profile.json()["actor"] == str(USER_ID)
        assert profile.json()["workspace"] == str(WORKSPACE_ID)
        empty = client.post(prefix + "/settings/account/profile", headers=headers, data={"display_name": ""})
        assert empty.json()["values"] == {"display_name": ""}
        prefs = prefix + "/settings/account/preferences"
        assert client.post(prefs, headers=headers, data={"timezone": "Asia/Kathmandu", "theme": "dark"}).status_code == 200
        assert client.post(prefs, headers=headers, data={"theme": "light"}).json()["values"] == {"theme": "light"}
        conflict = client.post(prefs, headers=headers, data={"theme": "dark", "expected_values": '{"theme":"system"}'})
        assert conflict.status_code == 409
        stale = client.post(prefs, headers={**headers, "X-Graf-Expected-Actor": str(FORGED_USER_ID)}, data={"theme": "dark"})
        assert stale.status_code == 409
        missing = {k: v for k, v in headers.items() if k != "X-Graf-Expected-Workspace"}
        assert client.post(prefs, headers=missing, data={"theme": "dark"}).status_code == 409
        page = client.get(prefix + "/settings/account", headers=auth_headers())
        assert 'data-theme="light"' in page.text
        assert 'value="Asia/Kathmandu" selected' in page.text
        assert f'name="graf-workspace" content="{WORKSPACE_ID}"' in page.text
        calendar = prefix + "/settings/integrations/calendar/preferences"
        assert client.post(calendar, headers=headers, data={"show_upcoming_title": "true"}).status_code == 200
        response = client.post(calendar, headers=headers, data={"show_upcoming_time": "false"})
        assert response.json()["values"] == {"show_upcoming_time": False}
        rendered = client.get(prefix + "/settings/integrations/calendar", headers=auth_headers()).text
        assert 'id="show_upcoming_title-switch"' in rendered
        # Each update has an explicit acknowledgement, with no full-page redirect.
        assert response.json()["saved"] is True
