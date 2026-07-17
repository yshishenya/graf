import Foundation
import TwoBrainRecAppCore

#if canImport(WebKit) && canImport(XCTest)
import XCTest

final class EmbeddedCabinetUpdateBridgeTests: XCTestCase {
    func testBridgeUsesOneFixedMessageAction() {
        XCTAssertEqual(EmbeddedCabinetUpdateBridge.messageHandlerName, "grafAppUpdate")
        XCTAssertEqual(EmbeddedCabinetUpdateBridge.checkForUpdatesAction, "checkForUpdates")
        XCTAssertTrue(EmbeddedCabinetUpdateBridge.isAllowedMessageBody("checkForUpdates"))
        XCTAssertFalse(EmbeddedCabinetUpdateBridge.isAllowedMessageBody("openURL"))
        XCTAssertFalse(EmbeddedCabinetUpdateBridge.isAllowedMessageBody(["action": "checkForUpdates"]))
    }

    func testVisibilityScriptOnlyChangesTheFixedBooleanSlot() {
        let visible = EmbeddedCabinetUpdateBridge.visibilityScript(showsBadge: true)
        let hidden = EmbeddedCabinetUpdateBridge.visibilityScript(showsBadge: false)

        for script in [visible, hidden] {
            XCTAssertTrue(script.contains("[data-graf-app-update]"))
            XCTAssertTrue(script.contains("button.hidden"))
            XCTAssertFalse(script.localizedCaseInsensitiveContains("http"))
            XCTAssertFalse(script.localizedCaseInsensitiveContains("version"))
            XCTAssertFalse(script.localizedCaseInsensitiveContains("release"))
        }
        XCTAssertTrue(visible.contains("button.hidden = false"))
        XCTAssertTrue(hidden.contains("button.hidden = true"))
    }

    func testDocumentScriptBindsOnlyTheFixedUpdateButton() {
        let script = EmbeddedCabinetUpdateBridge.documentScript

        XCTAssertTrue(script.contains("[data-graf-app-update]"))
        XCTAssertTrue(script.contains("window.webkit.messageHandlers.grafAppUpdate"))
        XCTAssertTrue(script.contains("postMessage('checkForUpdates')"))
        XCTAssertFalse(script.contains("innerHTML"))
        XCTAssertFalse(script.contains("fetch("))
    }

    func testNativeBridgeAcceptsOnlyAllowedMainFrameMessages() throws {
        let source = try Self.readRepositoryFile(
            "apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift"
        )

        XCTAssertTrue(source.contains("message.frameInfo.isMainFrame"))
        XCTAssertTrue(source.contains("let sourceURL = message.frameInfo.request.url"))
        XCTAssertTrue(source.contains("routePolicy.decision(for: sourceURL).decision == .allow"))
    }

    func testLocalOnlyUpdateMarkerKeepsAccessibleMinimumTarget() {
        XCTAssertEqual(DesktopMeetingShellChrome.appUpdateLabel, "Доступно обновление")
        XCTAssertEqual(
            DesktopMeetingShellChrome.appUpdateAccessibilityLabel,
            "Доступно обновление GRAF. Открыть проверку обновлений."
        )
        XCTAssertGreaterThanOrEqual(
            DesktopMeetingShellChrome.appUpdateHitSize,
            DesktopMeetingShellChrome.minimumInteractiveTarget
        )
    }

    private static func readRepositoryFile(_ relativePath: String) throws -> String {
        try String(
            contentsOf: repositoryRoot().appendingPathComponent(relativePath),
            encoding: .utf8
        )
    }

    private static func repositoryRoot() throws -> URL {
        var candidate = URL(fileURLWithPath: #filePath)
        while candidate.path != "/" {
            let marker = candidate.appendingPathComponent("apps/macos/Package.swift")
            if FileManager.default.fileExists(atPath: marker.path) {
                return candidate
            }
            candidate.deleteLastPathComponent()
        }
        throw NSError(
            domain: "EmbeddedCabinetUpdateBridgeTests",
            code: 1,
            userInfo: [NSLocalizedDescriptionKey: "Repository root not found"]
        )
    }
}
#endif
