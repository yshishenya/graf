#!/usr/bin/env python3
"""Lexical F277 retirement guard, not a Swift parser or reachability proof.

Scan checked-in source/test trees, ignoring comments and literal string text
but retaining Swift interpolation expressions. A direct cleanup call is required;
this does not establish that its containing function/branch executes. Type aliases,
macros, conditional-compilation evaluation and Swift regex literals are not resolved.
Historical specs and server inbox/billing delivery are outside this boundary.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RETIREMENT = "apps/macos/RecApp/Sources/Notifications/DesktopNotificationRetirement.swift"
REMOVED = "apps/macos/RecApp/Sources/Notifications/DesktopRecordingNoticePresenter.swift"
CSS = "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css"
SWIFT_TREES = ("apps/macos/RecApp", "apps/macos/Shared/Sources", "apps/macos/Shared/Tests")
GLOBAL_SWIFT = (
    r"\bDesktopRecordingNoticePresenter\b",
    r"\b(?:struct|class|enum|actor|extension)\s+MeetingDetectionCountdown\b",
    r"\bonOpenNotificationSettings\b",
    r"\blastRecordingNotice\b",
    r"\bRecordingNoticeState\b",
    r"\bupdateRecordingIndicator\b",
    r"\bgrafOpenLocalRecordingControls\b",
    r"\bUNUserNotificationCenterDelegate\b",
    r"\bUN(?:Notification\w*|MutableNotificationContent|\w*NotificationTrigger|Authorization\w*)\b",
)
NOTIFICATION_ONLY = (
    r"\brequestAuthorization\b", r"\brequestPermission\b", r"\brefreshPermission\b",
    r"\bopenSystemSettings\b", r"\bcanRequestPermission\b", r"\bpermissionText\b",
    r"\bnotificationCenter\s*\([^\n]*didReceive", r"\bsetNotificationCategories\b",
)
RETIRED_CONTROL_CASES = ("settings", "localRecordings", "permissions")
RETIRED_SNAPSHOT_PROPERTIES = (
    "calendarContextEventID", "completedRecording", "recoveryAction", "localIssues", "permissionBlocker",
)


def swift_code(source: str) -> str:
    """Blank comments/string text without moving offsets; keep interpolation code.

    Supports nested block comments and ordinary/raw/multiline Swift strings.
    Delimiter scanning is deliberately lexical, not syntax/type checking.
    """
    result = list(source)
    size = len(source)

    def blank(start: int, end: int) -> None:
        result[start:end] = ["\n" if char == "\n" else " " for char in source[start:end]]

    def string(start: int, quote: int) -> int:
        hashes = source[start:quote]
        delimiter = '"""' if source.startswith('"""', quote) else '"'
        close = delimiter + hashes
        escape = "\\" + hashes
        index = quote + len(delimiter)
        blank(start, index)
        while index < size:
            if source.startswith(close, index):
                blank(index, index + len(close))
                return index + len(close)
            if source.startswith(escape, index):
                end = index + len(escape)
                if source.startswith("(", end):
                    blank(index, end + 1)
                    index = code(end + 1, interpolation=True)
                else:
                    blank(index, min(size, end + 1))
                    index = end + 1
            else:
                blank(index, index + 1)
                index += 1
        return index

    def code(index: int, interpolation: bool = False) -> int:
        parentheses = 1 if interpolation else 0
        while index < size:
            if source.startswith("//", index):
                end = source.find("\n", index)
                end = size if end < 0 else end
                blank(index, end)
                index = end
            elif source.startswith("/*", index):
                end, depth = index + 2, 1
                while end < size and depth:
                    if source.startswith("/*", end):
                        depth += 1
                        end += 2
                    elif source.startswith("*/", end):
                        depth -= 1
                        end += 2
                    else:
                        end += 1
                blank(index, end)
                index = end
            elif source[index] in '#"':
                quote = index
                while quote < size and source[quote] == "#":
                    quote += 1
                if quote < size and source[quote] == '"':
                    index = string(index, quote)
                else:
                    index += 1
            else:
                if interpolation:
                    if source[index] == "(":
                        parentheses += 1
                    elif source[index] == ")":
                        parentheses -= 1
                        if parentheses == 0:
                            blank(index, index + 1)
                            return index + 1
                index += 1
        return index

    code(0)
    return "".join(result)


def direct_type_members(source: str, kind: str, name: str):
    """Yield declaration text with nested bodies/arguments masked, preserving offsets.

    Scope the guard to the named type, not identically named diagnostic fields,
    actual settings/permission methods, or local variables inside methods.
    """
    masked = swift_code(source)
    for declaration in re.finditer(rf"\b{kind}\s+{name}\b(?!\s*\.)[^{{]*\{{", masked):
        start = declaration.end()
        braces, arguments = 1, 0
        body = []
        for char in masked[start:]:
            if char == "}":
                braces -= 1
                if braces == 0:
                    break
            visible = braces == 1 and arguments == 0
            body.append(char if visible or char == "\n" else " ")
            if char == "{":
                braces += 1
            elif braces == 1 and char in "([":
                arguments += 1
            elif braces == 1 and char in ")]":
                arguments -= 1
        yield start, "".join(body)


def retired_control_members(source: str):
    for start, body in direct_type_members(source, "enum", "DesktopControlAction"):
        for clause in re.finditer(r"\bcase\s+([^;{}]+?)(?=\b(?:case|func|var|let|init)\b|[;{}]|$)", body):
            # Comma-separated cases, including declarations split over lines.
            for item in re.finditer(r"(?:^|,)\s*(\w+)", clause.group(1)):
                if item.group(1) in RETIRED_CONTROL_CASES:
                    yield start + clause.start(1) + item.start(1), "DesktopControlAction." + item.group(1)
    for start, body in direct_type_members(source, "struct", "DesktopControlSnapshot"):
        for member in re.finditer(r"\b(?:var|let)\s+(\w+)\b", body):
            if member.group(1) in RETIRED_SNAPSHOT_PROPERTIES:
                yield start + member.start(1), "DesktopControlSnapshot." + member.group(1)


def retired_prompt_members(source: str):
    # Include direct extensions of the shared model, not extensions of its nested
    # types. Nested bodies/arguments are masked so locals/parameters stay legal.
    name = r"(?:TwoBrainRecShared\s*\.\s*)?MeetingDetectionPromptDecision"
    for start, body in direct_type_members(source, "(?:struct|extension)", name):
        for member in re.finditer(r"\b(?:var|let)\s+`?(startReason)\b`?", body):
            yield start + member.start(1), "MeetingDetectionPromptDecision.startReason"


def violations(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    if (root / REMOVED).exists():
        errors.append(f"{REMOVED}: retired wrapper exists")
    sources = root / "apps/macos/RecApp"
    paths = sorted(path for tree in SWIFT_TREES for path in (root / tree).rglob("*.swift"))
    for path in paths:
        relative = path.relative_to(root).as_posix()
        source = path.read_text(encoding="utf-8")
        code = swift_code(source)
        patterns = list(GLOBAL_SWIFT)
        if "/Notifications/" in relative or path.name == "EmbeddedCabinetNotificationSettingsBridge.swift":
            patterns.extend(NOTIFICATION_ONLY)
        if relative != RETIREMENT:
            patterns.extend((r"\bimport\s+UserNotifications\b", r"\bUNUserNotificationCenter\b"))
        for pattern in patterns:
            match = re.search(pattern, code)
            if match:
                line = source.count("\n", 0, match.start()) + 1
                errors.append(f"{relative}:{line}: retired symbol {match.group(0)}")
        for offset, name in retired_control_members(source):
            line = source.count("\n", 0, offset) + 1
            errors.append(f"{relative}:{line}: retired control member {name}")
        for offset, name in retired_prompt_members(source):
            line = source.count("\n", 0, offset) + 1
            errors.append(f"{relative}:{line}: retired prompt member {name}")
    helper = root / RETIREMENT
    presenter = sources / "Sources/Notifications/DesktopNotificationPresenter.swift"
    if not helper.is_file():
        errors.append(f"{RETIREMENT}: required own-bundle cleanup is missing")
    elif not presenter.is_file() or not re.search(
        r"\bDesktopNotificationRetirement\s*\.\s*run\s*\(\s*\)",
        swift_code(presenter.read_text(encoding="utf-8")),
    ):
        errors.append("Retirement cleanup has no presenter consumer")
    stylesheet = root / CSS
    if not stylesheet.is_file():
        errors.append(f"{CSS}: required settings stylesheet missing")
    else:
        source = stylesheet.read_text(encoding="utf-8")
        # Ignore CSS comments/string values, but preserve selector attribute names.
        masked = re.sub(r'/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
                        lambda match: re.sub(r"[^\n]", " ", match.group()), source)
        match = re.search(r"\[\s*data-local-notification-permission\b", masked, re.IGNORECASE)
        if match:
            line = source.count("\n", 0, match.start()) + 1
            errors.append(f"{CSS}:{line}: retired selector data-local-notification-permission")
    bridge = sources / "Sources/Cabinet/EmbeddedCabinetNotificationSettingsBridge.swift"
    template = root / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_notifications_content.html"
    for path in (bridge, template):
        if not path.is_file():
            errors.append(f"{path.relative_to(root)}: required settings surface missing")
            continue
        source = path.read_text(encoding="utf-8")
        for name in ("canRequestPermission", "requestPermission", "openSystemSettings", "/desktop/settings/notifications/mac"):
            if name in source:
                errors.append(f"{path.relative_to(root)}: retired settings contract {name}")
    javascript = root / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
    if not javascript.is_file():
        errors.append(f"{javascript.relative_to(root)}: required settings consumer missing")
    else:
        source = javascript.read_text(encoding="utf-8")
        start = source.find("let notificationSettingsNonce")
        end = source.find("const initSettingsFormState", start)
        if start < 0 or end < 0:
            errors.append("Notification JavaScript boundary changed; update this guard explicitly")
        else:
            for name in ("canRequestPermission", "requestPermission", "openSystemSettings",
                         "/desktop/settings/notifications/mac"):
                if name in source[start:end]:
                    errors.append(f"{javascript.relative_to(root)}: retired settings contract {name}")
    return errors


def main() -> int:
    errors = violations()
    for error in errors:
        print(error)
    print(f"notification-retirement: {'FAIL' if errors else 'PASS'} ({len(errors)} violations)")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
