from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = ROOT / "src" / "twobrain_rec_server" / "cabinet" / "static" / "cabinet"


def test_local_htmx_asset_is_pinned_with_source_and_license() -> None:
    htmx = (STATIC_DIR / "htmx-2.0.10.min.js").read_text()
    source = (STATIC_DIR / "htmx-2.0.10.source.txt").read_text()

    assert 'version:"2.0.10"' in htmx
    assert "selfRequestsOnly:true" in htmx
    assert "source: https://unpkg.com/htmx.org@2.0.10/dist/htmx.min.js" in source
    assert "package: https://www.npmjs.com/package/htmx.org/v/2.0.10" in source
    assert "license: 0BSD" in source


def test_cabinet_static_assets_do_not_reference_runtime_cdns_or_build_outputs() -> None:
    forbidden = (
        "cdn.",
        "cdnjs",
        "jsdelivr",
        "googleapis",
        "fonts.gstatic",
        "tailwind",
        "daisyui",
        "flowbite",
        "shadcn",
        "react",
        "vue",
        "svelte",
        "webpack",
        "vite",
    )
    checked = [
        STATIC_DIR / "cabinet.css",
        STATIC_DIR / "cabinet.js",
    ]

    for path in checked:
        content = path.read_text().lower()
        assert not [marker for marker in forbidden if marker in content]


def test_cabinet_brand_assets_are_local_and_nonempty() -> None:
    for filename in [
        "graf-icon.png",
        "graf-icon@2x.png",
        "favicon.ico",
        "favicon-16.png",
        "favicon-32.png",
        "apple-touch-icon.png",
        "graf-wordmark-dark.png",
        "graf-wordmark-dark@2x.png",
        "graf-wordmark-light.png",
        "graf-wordmark-light@2x.png",
    ]:
        path = STATIC_DIR / filename
        assert path.is_file()
        assert path.stat().st_size > 0


def test_cabinet_js_wires_csrf_header_for_unsafe_htmx_requests() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()

    assert 'meta[name="csrf-token"]' in script
    assert "htmx:configRequest" in script
    assert "X-CSRF-Token" in script
    assert "POST" in script
    assert "DELETE" in script


def test_cabinet_js_keeps_fragment_state_ephemeral() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()

    assert "htmx:afterSwap" in script
    assert "meeting-list-region" in script
    assert "localStorage" not in script
    assert "sessionStorage" not in script


def test_cabinet_js_uses_product_facing_ellipsis_in_async_states() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()

    for legacy_copy in [
        '"Удаляем..."',
        '"Загружаем файл..."',
        '"Продолжаем загрузку..."',
        '"Проверяем..."',
    ]:
        assert legacy_copy not in script
    for product_copy in [
        '"Удаляем…"',
        '"Загружаем файл…"',
        '"Продолжаем загрузку…"',
        '"Проверяем…"',
    ]:
        assert product_copy in script


def test_cabinet_js_owns_component_dom_behavior() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()

    for marker in [
        "data-code-form",
        "syncRefinementState",
        "auth-leaving",
        "data-delete-dialog",
        "activateDetailTab",
        "data-playback-player",
        "new FormData(form)",
        '"HX-Request": "true"',
        "if (!response.ok)",
        "const failedRows = []",
        "pendingDeleteRows = failedRows",
        "target.replaceChildren(document.importNode(feedback, true))",
        'dialog.querySelector("[data-delete-cancel]")?.focus({ preventScroll: true })',
        'deleteDialog?.addEventListener("cancel"',
        'source.matches("[data-upload-progress-poll]")',
        "listInteractionIsActive()",
        'document.querySelector("[data-delete-dialog][open], [data-manual-upload-dialog][open]")',
        "deleteReturnMeetingId",
        "isUsableFocusTarget(deleteReturnFocus)",
        "target.closest(\"[hidden], [aria-hidden='true']\") === null",
        "returnRow?.isConnected ? returnRow",
        "if (!shouldSelectAll) rows[0]?.focus({ preventScroll: true })",
        "closeDeleteDialog();",
        'event.key !== "Escape"',
        'openDisclosure.querySelector("summary")?.focus({ preventScroll: true })',
        'event.target.closest("[data-filter-disclosure], [data-sort-disclosure]")',
    ]:
        assert marker in script


def test_collapsed_sidebar_only_expands_through_the_explicit_toggle() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()

    assert ".desktop-embedded.is-rail-pinned .sidebar" in css
    assert ".desktop-embedded .sidebar:hover" not in css
    assert ".desktop-embedded .sidebar:focus-within" not in css
    assert ".desktop-embedded .sidebar-foot {\n    visibility: hidden;\n  }" in css
    assert ".desktop-embedded.is-rail-pinned .sidebar-foot {\n    visibility: visible;\n  }" in css


def test_embedded_update_slot_is_accessible_and_native_owned() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()

    for marker in [
        ".sidebar-app-update",
        "min-height: 40px;",
        "color: var(--focus-ring);",
        ".sidebar-app-update:hover",
        ".sidebar-app-update:focus-visible",
        ".sidebar-app-update[hidden]",
    ]:
        assert marker in css


def test_cabinet_js_owns_manual_upload_without_frontend_toolchain() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()
    css = (STATIC_DIR / "cabinet.css").read_text()

    for marker in [
        "initManualUpload",
        "XMLHttpRequest",
        "data-manual-upload-dialog",
        "data-manual-upload-dropzone",
        "data-upload-activity-list",
        "data-upload-activity-cancel",
        "data-upload-activity-retry",
        "data-upload-activity-recover",
        "data-upload-activity-resume",
        "data-manual-upload-submit",
        "focusDialogElement",
        'dialog.addEventListener("keydown"',
        'event.key !== "Tab"',
        'document.body.addEventListener("click"',
        "event.preventDefault();",
        "duration_seconds",
        "local_recording_id",
        "X-CSRF-Token",
        "abort",
        "refreshMeetingList",
        "workflow_started",
        "Обработка ещё не запущена",
        "authUploadFailure",
        "conflictUploadFailure",
        "window.location.reload()",
        "dragover",
        "dropEffect",
        "meeting-list-region",
    ]:
        assert marker in script
    for marker in [
        ".manual-upload-dialog",
        ".manual-upload-dropzone",
        ".manual-upload-file-card",
        ".manual-upload-validation",
        ".upload-activity-row",
        ".upload-activity-progress",
        ".upload-activity-actions",
        ".upload-activity-action",
    ]:
        assert marker in css
    assert "Длительность не прочитана" in script
    assert 'durationInput?.addEventListener("input"' not in script
    assert ".manual-upload-duration__control" not in css


def test_auth_static_assets_keep_compact_panel_and_code_autosubmit() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()
    script = (STATIC_DIR / "cabinet.js").read_text()

    assert "--auth-content-width: min(100%, 448px)" in css
    assert "width: min(520px, 100%)" in css
    assert "requestSubmit" in script
    assert "slots.every((target) => target.value.length === 1)" in script
    assert "submitted = true" in script


def test_feature_104_css_uses_shared_density_focus_and_responsive_contracts() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()

    for marker in [
        "--space-1: 8px;",
        "--space-2: 12px;",
        "--space-3: 16px;",
        "--space-4: 24px;",
        "--control-height: 36px;",
        "--meeting-row-height: 48px;",
        "--focus-ring: #b6aaff;",
        "--app-sidebar-width: 176px;",
        "--app-rail-width: 64px;",
        "outline: 2px solid var(--focus-ring);",
        ".meeting-row.cabinet-row:hover,\n.meeting-row.cabinet-row:focus-within",
        "grid-template-columns: var(--app-rail-width) minmax(0, 1fr);",
        "@media (max-width: 1120px)",
        ".new-button.manual-upload-trigger > span",
        ".desktop-embedded .cabinet-list-controls .manual-upload-trigger {",
        "grid-column: auto;",
        ".cabinet-workspace-header--brand .cabinet-workspace-header__avatar",
        '[data-icon="panel-left-close"]',
        "@media (prefers-contrast: more)",
        "@media (prefers-reduced-motion: reduce)",
    ]:
        assert marker in css

    assert "min-height: var(--meeting-row-height);" in css
    assert "min-height: var(--control-height);" in css
    assert "overflow-x: hidden" in css
    assert (
        ".desktop-embedded .cabinet-list-controls .manual-upload-trigger {\n"
        "    grid-column: auto;\n"
        "    width: 40px;\n"
        "    min-width: 40px;\n"
        "    padding: 0;\n"
        "  }"
    ) in css
    assert (
        ".desktop-embedded .cabinet-list-controls .manual-upload-trigger {\n"
        "    grid-column: 1 / -1;\n"
        "    width: 100%;\n"
        "  }"
    ) not in css
    assert 'aria-label="Сохраненные"' not in css
