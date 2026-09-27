"""Keep the single desktop channel guarded without changing server inbox delivery."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location("notification_retirement", ROOT / "scripts/check_notification_retirement.py")
assert SPEC is not None and SPEC.loader is not None
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


def test_live_desktop_has_no_retired_delivery_or_navigation():
    assert GATE.violations(ROOT) == []


@pytest.fixture
def clean_desktop(tmp_path):
    sources = tmp_path / "apps/macos/RecApp/Sources"
    notifications = sources / "Notifications"
    notifications.mkdir(parents=True)
    helper = notifications / "DesktopNotificationRetirement.swift"
    helper.write_text("import UserNotifications\nUNUserNotificationCenter.current().removeAllPendingNotificationRequests()", encoding="utf-8")
    presenter = notifications / "DesktopNotificationPresenter.swift"
    presenter.write_text("DesktopNotificationRetirement.run()", encoding="utf-8")
    bridge = sources / "Cabinet/EmbeddedCabinetNotificationSettingsBridge.swift"
    bridge.parent.mkdir(parents=True)
    bridge.write_text("version = 2", encoding="utf-8")
    template = tmp_path / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_notifications_content.html"
    template.parent.mkdir(parents=True)
    template.write_text("quiet", encoding="utf-8")
    javascript = tmp_path / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
    javascript.parent.mkdir(parents=True)
    javascript.write_text("let notificationSettingsNonce = null; const initSettingsFormState = () => {};", encoding="utf-8")
    javascript.with_name("cabinet.css").write_text("[data-local-notification-controls] { border: 0; }", encoding="utf-8")
    assert GATE.violations(tmp_path) == []
    return tmp_path


def test_gate_detects_old_channel_but_allows_only_executed_cleanup(clean_desktop):
    tmp_path = clean_desktop
    notifications = tmp_path / "apps/macos/RecApp/Sources/Notifications"
    helper = notifications / "DesktopNotificationRetirement.swift"
    presenter = notifications / "DesktopNotificationPresenter.swift"
    javascript = tmp_path / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
    presenter.write_text("import UserNotifications\nUNNotificationRequest\nrequestAuthorization()", encoding="utf-8")
    errors = GATE.violations(tmp_path)
    assert any("UNNotificationRequest" in error for error in errors)
    assert any("import UserNotifications" in error for error in errors)
    assert any("requestAuthorization" in error for error in errors)
    assert any("no presenter consumer" in error for error in errors)
    helper.write_text("UNNotificationAction", encoding="utf-8")
    assert any("UNNotificationAction" in error for error in GATE.violations(tmp_path))
    javascript.write_text("let notificationSettingsNonce = null; requestPermission(); const initSettingsFormState = () => {};", encoding="utf-8")
    assert any("cabinet.js: retired settings contract requestPermission" in error for error in GATE.violations(tmp_path))


@pytest.mark.parametrize("name", ["settings", "localRecordings", "permissions"])
@pytest.mark.parametrize("layout", ["single", "grouped", "separate"])
def test_gate_rejects_each_retired_control_action(clean_desktop, name, layout):
    path = clean_desktop / "apps/macos/RecApp/Sources/Notifications/DesktopControlPanel.swift"
    cases = {"single": name, "grouped": f"start,\n {name}, stop",
             "separate": f"start\n case {name}\n case stop"}[layout]
    path.write_text(f"public enum DesktopControlAction: Equatable {{ case {cases}; case localRecording(String) }}",
                    encoding="utf-8")
    errors = GATE.violations(clean_desktop)
    assert len(errors) == 1
    assert f"retired control member DesktopControlAction.{name}" in errors[0]


@pytest.mark.parametrize("name", [
    "calendarContextEventID", "completedRecording", "recoveryAction", "localIssues", "permissionBlocker",
])
@pytest.mark.parametrize("computed", [False, True])
def test_gate_rejects_each_retired_snapshot_property(clean_desktop, name, computed):
    path = clean_desktop / "apps/macos/RecApp/Sources/Notifications/DesktopControlPanel.swift"
    value = "{ false }" if computed else "= false"
    path.write_text(f"public struct DesktopControlSnapshot: Equatable {{ public init() {{}}; public var {name}: Bool {value} }}",
                    encoding="utf-8")
    errors = GATE.violations(clean_desktop)
    assert len(errors) == 1
    assert f"retired control member DesktopControlSnapshot.{name}" in errors[0]


@pytest.mark.parametrize("source", [
    'extension Notification.Name { static let grafOpenLocalRecordingControls = Notification.Name("old") }',
    "NotificationCenter.default.post(name: .grafOpenLocalRecordingControls, object: nil)",
])
def test_gate_rejects_retired_recording_controls_notification_globally(clean_desktop, source):
    path = clean_desktop / "apps/macos/RecApp/App/Fixture.swift"
    path.parent.mkdir(parents=True)
    path.write_text(source, encoding="utf-8")
    errors = GATE.violations(clean_desktop)
    assert len(errors) == 1
    assert "retired symbol grafOpenLocalRecordingControls" in errors[0]


def test_gate_preserves_live_methods_and_unrelated_diagnostic_fields(clean_desktop):
    path = clean_desktop / "apps/macos/RecApp/Sources/Notifications/DesktopControlPanel.swift"
    path.write_text('''
public enum DesktopControlAction {
    case start, pause, resume, stop
    case localRecording(String)
    func settings() {}
    func permissions() {}
}
public struct DesktopControlSnapshot {
    public var active: Bool { false }
    public var uploadItems: [String] = []
    func diagnostic() { let recoveryAction = "retry" }
}
struct Diagnostics {
    var calendarContextEventID: String?
    var completedRecording = false
    var recoveryAction = "retry"
    var localIssues: [String] = []
    var permissionBlocker = false
}
enum OtherAction { case settings, localRecordings, permissions }
func settings() {}
func permissions() {}
''', encoding="utf-8")
    assert GATE.violations(clean_desktop) == []


@pytest.mark.parametrize("selector", [
    "[data-local-notification-permission]",
    ".settings-page [ data-local-notification-permission ]",
    '[data-local-notification-permission="allowed"]',
])
def test_gate_rejects_obsolete_permission_css(clean_desktop, selector):
    path = clean_desktop / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css"
    path.write_text(f"/* current styles */\n{selector} {{ padding-block: 16px; }}", encoding="utf-8")
    assert any("cabinet.css:2:" in error and "data-local-notification-permission" in error
               for error in GATE.violations(clean_desktop))


def test_gate_allows_permission_selector_in_css_comment_only(clean_desktop):
    path = clean_desktop / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css"
    path.write_text("/* removed [data-local-notification-permission] {} */\n.current {}", encoding="utf-8")
    assert GATE.violations(clean_desktop) == []


@pytest.mark.parametrize("directory", ["Shared/Sources", "Shared/Tests"])
@pytest.mark.parametrize("source, symbol", [
    ("import UserNotifications", "import UserNotifications"),
    ("func deliver() { UNUserNotificationCenter.current().removeAllDeliveredNotifications() }", "UNUserNotificationCenter"),
    ("func deliver() { let request = UNNotificationRequest(identifier: id, content: content, trigger: nil) }", "UNNotificationRequest"),
    ("func deliver() { let content = UNMutableNotificationContent() }", "UNMutableNotificationContent"),
    ("func status(_ value: UNAuthorizationStatus) {}", "UNAuthorizationStatus"),
])
def test_gate_rejects_live_un_code_in_shared_sources_and_tests(clean_desktop, directory, source, symbol):
    path = clean_desktop / f"apps/macos/{directory}/Fixture.swift"
    path.parent.mkdir(parents=True)
    path.write_text("// metadata only\n" + source, encoding="utf-8")
    assert any(f"{directory}/Fixture.swift:2:" in error and symbol in error
               for error in GATE.violations(clean_desktop))


@pytest.mark.parametrize("source", [
    "// DesktopNotificationRetirement.run()\nstruct Presenter {}",
    "/* outer /* nested */ DesktopNotificationRetirement.run() */\nstruct Presenter {}",
    'let evidence = "DesktopNotificationRetirement.run()"',
    'let evidence = #"DesktopNotificationRetirement.run()"#',
    'let evidence = """\nDesktopNotificationRetirement.run()\n"""',
    "enum DesktopNotificationRetirement { static func run() {} }",
    "let cleanup = DesktopNotificationRetirement.run",
])
def test_gate_requires_cleanup_call_not_comment_string_declaration_or_reference(clean_desktop, source):
    path = clean_desktop / "apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift"
    path.write_text(source, encoding="utf-8")
    assert any("no presenter consumer" in error for error in GATE.violations(clean_desktop))


def test_gate_accepts_cleanup_call_with_whitespace_and_comments(clean_desktop):
    path = clean_desktop / "apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift"
    path.write_text("init() { DesktopNotificationRetirement /* boundary */\n . run ( /* no args */ ) }", encoding="utf-8")
    assert GATE.violations(clean_desktop) == []


@pytest.mark.parametrize("directory", ["RecApp/Sources/Notifications", "Shared/Sources", "Shared/Tests"])
def test_gate_preserves_negative_xctest_strings_and_migration_data(clean_desktop, directory):
    path = clean_desktop / f"apps/macos/{directory}/Evidence.swift"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(r'''
// Removed UNUserNotificationCenterDelegate and requestPermission.
/* outer /* UNNotificationRequest */ openSystemSettings */
XCTAssertFalse(source.contains("import UserNotifications"))
XCTAssertFalse(source.contains(#"DesktopRecordingNoticePresenter"#))
let escaped = "\"UNMutableNotificationContent\" requestPermission"
let multiline = """
UNUserNotificationCenter.current()
MeetingDetectionPromptView requestAuthorization
"""
let rawMultiline = ##"""
UNNotificationRequest "canRequestPermission"
"""##
let legacy = ["graf.local.capture.session": 123.0, "graf.local.incident.item": 123.0]
defaults.set(legacy, forKey: "graf.notifications.owner.attempts")
defaults.set(["scheduledFor": 123.0], forKey: "reservations")
''', encoding="utf-8")
    assert GATE.violations(clean_desktop) == []


@pytest.mark.parametrize("literal", [
    r'"text \(UNMutableNotificationContent())"',
    r'#"text \#(UNMutableNotificationContent())"#',
])
def test_gate_still_checks_executable_string_interpolation(clean_desktop, literal):
    path = clean_desktop / "apps/macos/Shared/Tests/Interpolated.swift"
    path.parent.mkdir(parents=True)
    path.write_text(f"let text = {literal}", encoding="utf-8")
    assert any("UNMutableNotificationContent" in error for error in GATE.violations(clean_desktop))
