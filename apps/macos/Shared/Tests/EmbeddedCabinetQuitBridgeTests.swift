import Foundation
import TwoBrainRecAppCore

#if canImport(WebKit) && canImport(XCTest)
import XCTest

final class EmbeddedCabinetQuitBridgeTests: XCTestCase {
    func testBridgeUsesDedicatedAllowlistedAction() {
        XCTAssertEqual(EmbeddedCabinetQuitBridge.messageHandlerName, "grafAppQuit")
        XCTAssertEqual(EmbeddedCabinetQuitBridge.quitAction, "quit")
        XCTAssertTrue(EmbeddedCabinetQuitBridge.isAllowedMessageBody("quit"))
        XCTAssertFalse(EmbeddedCabinetQuitBridge.isAllowedMessageBody("terminate"))
        XCTAssertFalse(EmbeddedCabinetQuitBridge.isAllowedMessageBody(["action": "quit"]))
    }

    func testDocumentScriptBindsOnlyTheEmbeddedQuitControl() {
        let script = EmbeddedCabinetQuitBridge.documentScript
        XCTAssertTrue(script.contains("data-graf-app-quit"))
        XCTAssertTrue(script.contains("window.webkit.messageHandlers.grafAppQuit"))
        XCTAssertTrue(script.contains("button.disabled"))
        XCTAssertFalse(script.contains("window.close"))
    }
}
#endif
