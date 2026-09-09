import Foundation
import XCTest

final class AppLifecycleWindowRegressionTests: XCTestCase {
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
        final class NSApplication { var windows: [Window] = []; var isActive = true }
        let NSApp = NSApplication()
        enum AppLog { static func writeRaw(event: String, detail: String) {} }
        final class Delegate {
            var mainWindow: Window? = Window()
            var presentations: [String] = []
            func presentMainWindow(reason: String) { presentations.append(reason) }
        \(try method("applicationShouldHandleReopen"))
        \(try method("logWindowVisibility"))
        \(activation)
            func activate() { \(activation.isEmpty ? "" : "applicationDidBecomeActive(Notification(name: Notification.Name(\"active\")))") }
        }
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
