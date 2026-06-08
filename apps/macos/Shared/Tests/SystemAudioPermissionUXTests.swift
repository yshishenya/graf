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

        XCTAssertEqual(result.presentation?.title, "Recording blocked: permissions required")
        XCTAssertTrue(result.presentation?.message.contains("Microphone") == true)
        XCTAssertTrue(result.presentation?.message.contains("Screen/System Audio") == true)
        XCTAssertTrue(result.presentation?.message.contains("retry recording") == true)
        XCTAssertFalse(result.presentation?.message.localizedCaseInsensitiveContains("run the check") == true)
        XCTAssertEqual(result.presentation?.recoveryAction, .grantBoth)
    }

    func testSystemAudioCopyDoesNotMentionVirtualDevices() {
        let result = SystemAudioPermissionGate().evaluate(
            microphone: .granted,
            systemAudio: .restricted
        )

        XCTAssertTrue(result.presentation?.message.contains("Screen/System Audio") == true)
        XCTAssertFalse(result.presentation?.message.localizedCaseInsensitiveContains("virtual") == true)
        XCTAssertFalse(result.presentation?.message.localizedCaseInsensitiveContains("driver") == true)
    }
}
#endif
