import Foundation
import XCTest

final class AppLifecycleWindowRegressionTests: XCTestCase {
    func testPromptGeometryUsesRealLayout() throws {
        let root = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        let source = try String(contentsOf: root.appendingPathComponent("RecApp/App/TwoBrainRecApp.swift"), encoding: .utf8)
        var methods = ""
        for name in ["meetingDetectionPromptFrame", "clamp"] {
            let regex = try NSRegularExpression(pattern: "(?m)^    private func " + name + "\\([\\s\\S]*?^    \\}")
            let match = try XCTUnwrap(regex.firstMatch(in: source, range: NSRange(source.startIndex..., in: source)))
            let range = try XCTUnwrap(Range(match.range, in: source))
            methods += String(source[range]).replacingOccurrences(of: "private func", with: "func") + "\n"
        }
        let marginLine = try XCTUnwrap(source.split(separator: "\n").first { $0.contains("static let meetingDetectionPromptVisibleMargin:") })
        let script = """
        import AppKit
        struct Layout {
        \(marginLine)
        \(methods)
        }
        let layout = Layout()
        let size = NSSize(width: 320, height: 192)
        let normal = NSRect(x: 0, y: 25, width: 1800, height: 1100)
        let fallback = layout.meetingDetectionPromptFrame(windowSize: size, visibleFrame: normal)
        assert(fallback.size == size)
        assert(fallback.maxX == normal.maxX - 22 && fallback.maxY == normal.maxY - 22)
        let anchor = NSRect(x: 1000, y: 1125, width: 24, height: 24)
        let anchored = layout.meetingDetectionPromptFrame(windowSize: size, visibleFrame: normal, anchorFrame: anchor)
        assert(anchored.midX == anchor.midX)
        for screen in [normal, NSRect(x: -1920, y: -1080, width: 1920, height: 1040),
                       NSRect(x: -240, y: 50, width: 240, height: 160),
                       NSRect(x: 0, y: 0, width: 30, height: 20)] {
            for target in [nil, NSRect(x: screen.minX, y: screen.maxY, width: 24, height: 24),
                           NSRect(x: screen.maxX - 24, y: screen.maxY, width: 24, height: 24)] as [NSRect?] {
                let frame = layout.meetingDetectionPromptFrame(windowSize: size, visibleFrame: screen, anchorFrame: target)
                assert(screen.contains(frame) && frame.width > 0 && frame.height > 0)
                assert(frame == layout.meetingDetectionPromptFrame(windowSize: size, visibleFrame: screen, anchorFrame: target))
            }
        }
        """
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let file = directory.appendingPathComponent("prompt-layout.swift")
        try script.write(to: file, atomically: true, encoding: .utf8)
        let output = Pipe()
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/xcrun")
        process.arguments = ["swift", "-swift-version", "5", file.path]
        process.standardOutput = output
        process.standardError = output
        try process.run()
        let result = output.fileHandleForReading.readDataToEndOfFile()
        process.waitUntilExit()
        XCTAssertEqual(process.terminationStatus, 0, String(decoding: result, as: UTF8.self))
    }

    func testReopenAndActivationPreserveSelectedWindow() throws {
        let root = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        let source = try String(contentsOf: root.appendingPathComponent("RecApp/App/TwoBrainRecApp.swift"), encoding: .utf8)
        // Compile the actual private executable methods with inert window dependencies.
        // Installed AX acceptance separately verifies AppKit flags and window ordering.
        func method(_ name: String, required: Bool = true) throws -> String {
            let pattern = "(?m)^    (?:private )?func " + name + "\\([\\s\\S]*?^    \\}"
            let expression = try NSRegularExpression(pattern: pattern)
            guard let match = expression.firstMatch(in: source, range: NSRange(source.startIndex..., in: source)),
                  let range = Range(match.range, in: source) else {
                if required { throw NSError(domain: "Missing lifecycle method: " + name, code: 1) }
                return ""
            }
            return String(source[range]).replacingOccurrences(of: "private func", with: "func")
        }
        let activation = try method("applicationDidBecomeActive", required: false)
        let captureStart = try XCTUnwrap(source.range(of: "CaptureControlView("))
        let callbackExpression = try NSRegularExpression(pattern: "onMeetingDetectionSettings: (\\{[\\s\\S]*?\\n                \\})")
        let callbackMatch = try XCTUnwrap(callbackExpression.firstMatch(in: source,
            range: NSRange(captureStart.upperBound..<source.endIndex, in: source)))
        let callbackRange = try XCTUnwrap(Range(callbackMatch.range(at: 1), in: source))
        let settingsCallback = String(source[callbackRange])
        let script = """
        import Foundation
        final class Window {
            var isVisible = false
            var isKeyWindow = false
            var isMiniaturized = false
            var isOnActiveSpace = true
            var occlusionState: UInt = 0
        }
        extension UInt { var rawValue: UInt { self } }
        final class NSApplication { var windows: [Window] = []; var isActive = true; var delegate: AnyObject? }
        let NSApp = NSApplication()
        enum AppLog { static func writeRaw(event: String, detail: String) {} }
        final class Delegate {
            var mainWindow: Window? = Window()
            var presentations: [String] = []
            var settingsRoutes: [String] = []
            func presentMainWindow(reason: String) { presentations.append(reason) }
            func openSettings(_: Any?) { settingsRoutes.append("generalSettings") }
            func openLocalRecordingSettings() { settingsRoutes.append("localRecordingSettings") }
        \(try method("applicationShouldHandleReopen"))
        \(try method("logWindowVisibility"))
        \(activation)
            func activate() { \(activation.isEmpty ? "" : "applicationDidBecomeActive(Notification(name: Notification.Name(\"active\")))") }
        }
        typealias AppLifecycleDelegate = Delegate
        func check(_ condition: Bool, _ message: String) {
            if !condition { fatalError(message) }
        }
        let delegate = Delegate()
        check(delegate.applicationShouldHandleReopen(NSApp, hasVisibleWindows: false), "Keep normal reopen handling")
        check(delegate.presentations == ["reopen"], "Hidden windows require explicit Dock reopen")
        delegate.presentations = []
        delegate.mainWindow!.isMiniaturized = true
        _ = delegate.applicationShouldHandleReopen(NSApp, hasVisibleWindows: false)
        check(delegate.presentations == ["reopen"], "Minimized main window reaches existing deminiaturize path")
        delegate.presentations = []
        let settings = Window()
        settings.isVisible = true
        settings.isKeyWindow = true
        NSApp.windows = [delegate.mainWindow!, settings]
        _ = delegate.applicationShouldHandleReopen(NSApp, hasVisibleWindows: true)
        check(delegate.presentations.isEmpty, "Notification-selected settings must survive reopen")
        delegate.logWindowVisibility()
        check(delegate.presentations.isEmpty, "Delayed launch check must preserve key settings")
        NSApp.isActive = false
        delegate.logWindowVisibility()
        check(delegate.presentations.isEmpty, "Delayed launch check must not steal focus from another app")
        settings.isVisible = false
        delegate.activate()
        check(delegate.presentations.isEmpty, "Activation alone must not reveal hidden cabinet")
        delegate.logWindowVisibility()
        check(delegate.presentations == ["visibility_recovery"], "Keep startup recovery with no visible windows")
        NSApp.delegate = delegate
        let openMeetingDetectionSettings = \(settingsCallback)
        openMeetingDetectionSettings()
        check(delegate.settingsRoutes == ["localRecordingSettings"], "Capture inspector settings must open native automatic recording, not general cabinet settings")
        """
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let file = directory.appendingPathComponent("lifecycle.swift")
        try script.write(to: file, atomically: true, encoding: .utf8)
        let output = Pipe()
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/xcrun")
        process.arguments = ["swift", "-swift-version", "5", file.path]
        process.standardOutput = output
        process.standardError = output
        try process.run()
        let result = output.fileHandleForReading.readDataToEndOfFile()
        process.waitUntilExit()
        XCTAssertEqual(process.terminationStatus, 0, String(decoding: result, as: UTF8.self))
    }
}
