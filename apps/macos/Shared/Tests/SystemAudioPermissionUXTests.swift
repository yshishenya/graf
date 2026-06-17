import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioPermissionUXTests: XCTestCase {
    func testMissingBothPermissionsUsesSpecificRecoveryCopy() {
        let result = SystemAudioPermissionGate().evaluate(
            microphone: .denied,
            systemAudio: .denied
        )

        XCTAssertEqual(result.presentation?.title, "Нужны права на запись")
        XCTAssertTrue(result.presentation?.message.contains("микрофону") == true)
        XCTAssertTrue(result.presentation?.message.contains("системного звука") == true)
        XCTAssertTrue(result.presentation?.message.contains("повторите запись") == true)
        XCTAssertFalse(result.presentation?.message.localizedCaseInsensitiveContains("run the check") == true)
        XCTAssertEqual(result.presentation?.recoveryAction, .grantBoth)
    }

    func testSystemAudioCopyDoesNotMentionVirtualDevices() {
        let result = SystemAudioPermissionGate().evaluate(
            microphone: .granted,
            systemAudio: .restricted
        )

        XCTAssertTrue(result.presentation?.message.contains("системного звука") == true)
        XCTAssertFalse(result.presentation?.message.localizedCaseInsensitiveContains("virtual") == true)
        XCTAssertFalse(result.presentation?.message.localizedCaseInsensitiveContains("driver") == true)
    }
}
#endif
