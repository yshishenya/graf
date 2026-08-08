from pathlib import Path

from twobrain_rec_server.cabinet.auth_return import _safe_local_path


def test_shared_with_me_contract_has_separate_routes_and_safe_target() -> None:
    browser = Path("src/twobrain_rec_server/cabinet/web_routes/browser.py").read_text(
        encoding="utf-8"
    )
    desktop = Path("src/twobrain_rec_server/cabinet/web_routes/desktop.py").read_text(
        encoding="utf-8"
    )
    template = Path(
        "src/twobrain_rec_server/cabinet/templates/cabinet/pages/"
        "shared_with_me_list_content.html"
    ).read_text(encoding="utf-8")

    assert '@router.get("/shared-with-me"' in browser
    assert '@router.get("/desktop/shared-with-me"' in desktop
    assert "active_nav=\"shared-with-me\"" in Path(
        "src/twobrain_rec_server/cabinet/rendering.py"
    ).read_text(encoding="utf-8")
    assert "/shared-meetings/" in Path(
        "src/twobrain_rec_server/cabinet/queries.py"
    ).read_text(encoding="utf-8")
    assert "Поделились со мной" in template
    assert "data-manual-upload-open" not in template
    assert "selection-delete" not in template


def test_shared_with_me_lookup_is_select_only_and_current_user_bound() -> None:
    migration = Path(
        "src/twobrain_rec_server/db/migrations/versions/0042_shared_with_me_lookup.py"
    ).read_text(encoding="utf-8")

    assert "for select" in migration
    assert "grantee_user_id = rec_current_user_id()" in migration
    assert "audience_type = 'user'" in migration
    assert "status = 'active'" in migration


def test_shared_with_me_paths_remain_safe_local_auth_return_targets() -> None:
    assert _safe_local_path("/shared-with-me") == ("/shared-with-me", "/shared-with-me")
    assert _safe_local_path("/desktop/shared-with-me") == (
        "/desktop/shared-with-me",
        "/desktop/shared-with-me",
    )
