"""F240 source-palette and synthetic-render contracts, not browser evidence.

These checks calculate WCAG ratios for declared opaque sRGB palette pairs and
guard theme inheritance. They do not calculate the browser cascade, opacity,
color-mix, layout, focus, or open-dialog styles. The CUA matrix covers those.
"""

import re
import wave
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.fixtures.calendar_visual_ui_harness import (
    SYNTHETIC_DURATION_SECONDS,
    SYNTHETIC_MEETING_ID,
    app,
)
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY

CABINET_CSS = (
    Path(__file__).resolve().parents[2]
    / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css"
)
BACKGROUNDS = ("--bg", "--panel", "--surface", "--surface-2", "--surface-3")
TEXT_COLORS = ("--text", "--muted", "--subtle", "--accent", "--danger-text")
SHARED_COLORS = frozenset(
    (*BACKGROUNDS, *TEXT_COLORS, "--line", "--accent-solid", "--accent-foreground", "--focus-ring")
)


def _declarations(block: str) -> dict[str, str]:
    return {
        name: value.strip()
        for name, value in re.findall(r"(--[\w-]+|color-scheme)\s*:\s*([^;{}]+);", block)
    }


def _luminance(color: str) -> float:
    assert re.fullmatch(r"#[\da-fA-F]{3}(?:[\da-fA-F]{3})?", color), color
    value = color.lstrip("#")
    if len(value) == 3:
        value = "".join(channel * 2 for channel in value)
    channels = [int(value[offset : offset + 2], 16) / 255 for offset in (0, 2, 4)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return sum(
        channel * weight for channel, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True)
    )


def _contrast(foreground: str, background: str) -> float:
    light, dark = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def assert_theme_palette_contract(css: str) -> None:
    """Also callable with `git show <baseline>:.../cabinet.css` for negative control.

    Match this stylesheet's three known palette blocks, not general CSS syntax.
    The leaf-rule scan only rejects component overrides of shared root tokens.
    """
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    selectors = (":root", 'html[data-theme="light"]', ":root:not([data-theme])")
    blocks = [
        re.findall(rf"(?m)^{re.escape(selectors[0])}\s*\{{([^{{}}]*)\}}", css),
        re.findall(rf"{re.escape(selectors[1])}\s*\{{([^{{}}]*)\}}", css),
        re.findall(
            r"@media\s*\(prefers-color-scheme:\s*light\)\s*\{\s*"
            rf"{re.escape(selectors[2])}\s*\{{([^{{}}]*)\}}\s*\}}",
            css,
        ),
    ]
    for selector, matches in zip(selectors, blocks, strict=True):
        assert len(matches) == 1, f"Expected one canonical {selector} palette, got {len(matches)}"
    dark, explicit_light, system_light = [_declarations(matches[0]) for matches in blocks]
    assert dark["color-scheme"] == "dark"
    assert explicit_light["color-scheme"] == "light"
    assert explicit_light == system_light, "System light palette differs from explicit light"
    assert dark.keys() >= SHARED_COLORS, f"Missing shared colors: {SHARED_COLORS - dark.keys()}"

    # Root overrides for accessibility (e.g. prefers-contrast) remain allowed.
    # A sidebar/dialog may not shadow these tokens with its own dark palette.
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selector, body = match.groups()
        overrides = {
            name
            for name in _declarations(body)
            if name in SHARED_COLORS or name.startswith("--surface")
        }
        if overrides:
            assert selector.strip() in (*selectors, 'html[data-theme="dark"]'), (
                f"Scoped theme-token shadow: {selector.strip()}: {sorted(overrides)}"
            )

    failures = []
    for theme, palette in (("dark", dark), ("light", dark | explicit_light)):
        pairs = (
            [(text, surface, 4.5) for text in TEXT_COLORS for surface in BACKGROUNDS]
            + [
                (control, surface, 3.0)
                for control in ("--line", "--focus-ring")
                for surface in BACKGROUNDS
            ]
            + [
                ("--accent-foreground", "--accent-solid", 4.5),
                ("--accent-foreground", "--accent-hover", 4.5),
            ]
        )
        for foreground, background, minimum in pairs:
            ratio = _contrast(palette[foreground], palette[background])
            if ratio < minimum:
                failures.append(f"{theme} {foreground}/{background}: {ratio:.2f} < {minimum}")
    assert not failures, "Declared palette contrast:\n" + "\n".join(failures)


def test_declared_theme_palettes_have_contrast_and_share_root_tokens() -> None:
    assert_theme_palette_contract(CABINET_CSS.read_text(encoding="utf-8"))


def test_theme_components_keep_contrast_tokens_and_visible_interaction_cues() -> None:
    # Source declarations only; the browser matrix owns the computed cascade.
    css = re.sub(r"/\*.*?\*/", "", CABINET_CSS.read_text(encoding="utf-8"), flags=re.S)
    css = re.sub(r"\s+", " ", css)
    solid = {"background": "var(--accent-solid)", "border-color": "var(--accent-solid)"}
    hover = {"background": "var(--accent-hover)", "border-color": "var(--accent-hover)"}
    contracts = {
        "input::placeholder, textarea::placeholder": {"color": "var(--muted)", "opacity": "1"},
        ".primary:hover": hover,
        ".auth-form .primary:hover": hover,
        ".cabinet-button--primary:hover, .cabinet-link--primary:hover": hover,
        ".cabinet-switch input:checked + .cabinet-switch__track": solid,
        ".cabinet-switch input:checked + .cabinet-switch__track::after": {
            "background": "var(--accent-foreground)"
        },
        ".theme-picker__option input:checked + span": solid | {"color": "var(--accent-foreground)"},
        ".dot, .speaker-dot, .speaker-manager-dot, .speaker-manager-marker": {
            "box-shadow": "inset 0 0 0 1px var(--text)"
        },
        ".timeline-segment": {"box-shadow": "inset 0 0 0 1px var(--text)"},
        ".timeline-track:hover, .timeline-track.is-pressed": {
            "box-shadow": "0 0 0 1px var(--focus-ring)"
        },
        ".timeline-lane.is-active .timeline-track:hover, .timeline-lane.is-active .timeline-track.is-pressed": {
            "box-shadow": "0 0 0 3px var(--focus-ring)"
        },
        ".auth-resend:hover": {"text-decoration": "underline", "text-underline-offset": "3px"},
    }
    for selector, expected in contracts.items():
        # Inspect the base rule; later forced-colors rules deliberately use system colors.
        match = re.search(rf"(?:^|[{{}}])\s*{re.escape(selector)}\s*\{{([^{{}}]*)\}}", css)
        assert match, f"Missing component rule: {selector}"
        actual = dict(re.findall(r"([\w-]+):\s*([^;{}]+);", match[1]))
        assert actual.items() >= expected.items(), f"{selector}: expected {expected}, got {actual}"


def test_contrast_calculation_uses_srgb_relative_luminance() -> None:
    assert _contrast("#000", "#fff") == pytest.approx(21)
    assert _contrast("#fff", "#ffffff") == pytest.approx(1)
    assert _contrast("#777777", "#ffffff") == pytest.approx(4.478, abs=0.001)


@pytest.mark.parametrize("selector", [".sidebar", ".delete-dialog", ".speaker-manager-popover"])
def test_palette_contract_rejects_component_token_shadows(selector: str) -> None:
    css = CABINET_CSS.read_text(encoding="utf-8")
    with pytest.raises(AssertionError, match="Scoped theme-token shadow"):
        assert_theme_palette_contract(css + f"\n{selector} {{ --text: #eee; }}")


def test_palette_contract_rejects_late_root_palette() -> None:
    css = CABINET_CSS.read_text(encoding="utf-8")
    with pytest.raises(AssertionError, match="Expected one canonical :root palette"):
        assert_theme_palette_contract(css + "\n:root { --text: #eee; }")


def test_palette_contract_rejects_system_light_drift() -> None:
    css = CABINET_CSS.read_text(encoding="utf-8")
    css = css.replace(":root:not([data-theme]) {", ":root:not([data-theme]) { --theme-drift: 1;", 1)
    with pytest.raises(AssertionError, match="System light palette differs"):
        assert_theme_palette_contract(css)


def test_palette_contract_rejects_low_contrast_text() -> None:
    css = CABINET_CSS.read_text(encoding="utf-8")
    css = re.sub(r"--text:\s*#[\da-fA-F]+;", "--text: #fff;", css)
    with pytest.raises(AssertionError, match=r"light --text/--panel: 1\.00 < 4\.5"):
        assert_theme_palette_contract(css)


class _Page(HTMLParser):
    def __init__(self, html: str) -> None:
        super().__init__()
        self.nodes: list[tuple[str, dict[str, str | None]]] = []
        self.feed(html)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.nodes.append((tag, dict(attrs)))

    def marked(self, attribute: str) -> list[dict[str, str | None]]:
        return [attrs for _, attrs in self.nodes if attribute in attrs]


@pytest.fixture
def theme_client():
    # Use this isolated renderer app, not conftest's database-backed client.
    with TestClient(app, base_url="http://127.0.0.1") as client:
        yield client


@pytest.mark.parametrize("prefix", ["", "/desktop"])
@pytest.mark.parametrize("theme", ["light", "dark", "system"])
def test_populated_list_renders_theme_and_real_profile_upload_delete_hooks(
    theme_client, prefix: str, theme: str
) -> None:
    response = theme_client.get(f"{prefix}/meetings?mode=populated&theme={theme}")
    assert response.status_code == 200
    page = _Page(response.text)
    html = next(attrs for tag, attrs in page.nodes if tag == "html")
    assert html.get("data-theme") == (None if theme == "system" else theme)
    assert len(page.marked("data-meeting-row")) == 3
    assert len(page.marked("data-meeting-select")) == 3
    for hook in (
        "data-profile-menu-trigger",
        "data-profile-menu",
        "data-manual-upload-open",
        "data-manual-upload-dialog",
        "data-row-delete",
        "data-delete-dialog",
        "data-delete-error",
    ):
        assert page.marked(hook), hook
    assert (
        page.marked("data-bounded-delete-copy")[0]["data-bounded-delete-copy"]
        == BOUNDED_DELETE_COPY
    )
    assert "theme@example.test" in response.text
    assert f'href="{prefix}/meetings/{SYNTHETIC_MEETING_ID}"' in response.text
    assert not page.marked("data-upload-progress-poll")


@pytest.mark.parametrize("prefix", ["", "/desktop"])
@pytest.mark.parametrize("theme", ["light", "dark", "system"])
def test_synthetic_detail_renders_speakers_and_enabled_player(
    theme_client, prefix: str, theme: str
) -> None:
    response = theme_client.get(f"{prefix}/meetings/synthetic-theme?theme={theme}")
    assert response.status_code == 200
    page = _Page(response.text)
    html = next(attrs for tag, attrs in page.nodes if tag == "html")
    assert html.get("data-theme") == (None if theme == "system" else theme)
    assert len(page.marked("data-transcript-turn")) == 2
    assert len(page.marked("data-speaker-lane")) == 2
    assert page.marked("data-speaker-manager-toggle")
    assert page.marked("data-speaker-name-open")
    assert page.marked("data-playback-shell")[0]["data-playback-state"] == "available"
    for hook in (
        "data-playback-toggle",
        "data-playback-skip",
        "data-playback-speed-toggle",
        "data-playback-progress",
    ):
        assert page.marked(hook), hook
        assert all("disabled" not in attrs for attrs in page.marked(hook)), hook
    assert page.marked("data-playback-player")[0]["src"] == "/synthetic/theme.wav"
    assert page.marked("data-playback-poll-active")[0]["data-playback-poll-active"] == "false"
    assert (
        theme_client.get(f"{prefix}/meetings/{SYNTHETIC_MEETING_ID}?theme={theme}").status_code
        == 200
    )


@pytest.mark.parametrize("prefix", ["", "/desktop"])
def test_synthetic_share_routes_render_real_dialog(theme_client, prefix: str) -> None:
    response = theme_client.get(f"{prefix}/meetings/{SYNTHETIC_MEETING_ID}/share")
    assert response.status_code == 200
    page = _Page(response.text)
    assert page.marked("data-share-dialog")[0]["id"] == "meeting-share-dialog"
    assert page.marked("data-share-recipient-form")[0]["data-meeting-id"] == str(
        SYNTHETIC_MEETING_ID
    )
    assert page.marked("data-share-status")[0]["role"] == "status"
    assert theme_client.get(
        f"{prefix}/meetings/00000000-0000-4000-8000-000000000241/share"
    ).status_code in (404, 405)


@pytest.mark.parametrize("path", ["/login", "/login/email/code"])
@pytest.mark.parametrize("query", ["", "?theme=light", "?theme=dark", "?error=email_code_wrong"])
def test_real_auth_pages_leave_theme_to_os(theme_client, path: str, query: str) -> None:
    response = theme_client.get(path + query)
    assert response.status_code == 200
    page = _Page(response.text)
    assert not page.marked("data-theme")
    assert any(tag == "form" and attrs.get("method") == "post" for tag, attrs in page.nodes)
    if path.endswith("/code"):
        assert len(page.marked("data-code-slot")) == 6
        assert page.marked("data-code-form")[0]["action"] == "/login/email/verify"
        assert "theme@example.test" in response.text
    else:
        assert any(
            attrs.get("action") == "/login/email/start"
            for tag, attrs in page.nodes
            if tag == "form"
        )
    if "error=" in query:
        assert any(attrs.get("role") == "alert" for _, attrs in page.nodes)


@pytest.mark.parametrize("prefix", ["", "/desktop"])
def test_harness_preserves_empty_default_and_calendar_routes(theme_client, prefix: str) -> None:
    for query in ("", "?mode=empty"):
        response = theme_client.get(f"{prefix}/meetings{query}")
        assert response.status_code == 200
        assert not _Page(response.text).marked("data-meeting-row")
    for mode in (
        "connected",
        "empty",
        "selection",
        "selection-limit",
        "syncing",
        "stale",
        "credentials",
    ):
        assert (
            theme_client.get(f"{prefix}/settings/integrations/calendar?mode={mode}").status_code
            == 200
        )
    response = theme_client.post(
        f"{prefix}/settings/integrations/calendar/synthetic/disconnect", follow_redirects=False
    )
    assert response.status_code == 303
    assert (
        response.headers["location"]
        == f"{prefix}/settings/integrations/calendar?mode=empty&disconnect_result=success"
    )


def test_playback_source_is_generated_local_silence(theme_client) -> None:
    response = theme_client.get("/synthetic/theme.wav")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    with wave.open(BytesIO(response.content), "rb") as audio:
        assert audio.getnchannels() == 1
        assert audio.getsampwidth() == 1
        assert audio.getnframes() / audio.getframerate() == SYNTHETIC_DURATION_SECONDS
        assert set(audio.readframes(audio.getnframes())) == {128}
