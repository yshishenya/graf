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

    @MainActor
    func testDetectorAssistedPreparingDoesNotStartRecordingAutomatically() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 1_783_440_000) },
            idFactory: { "meeting-detection-session" },
            policySnapshotProvider: { "policy-meeting-detection" }
        )

        let session = try controller.beginDetectorAssistedPreparing(
            targetID: "yandex_telemost",
            bundleID: "ru.yandex.desktop.telemost",
            displayName: "Yandex Telemost"
        )

        XCTAssertEqual(session.state, .detecting)
        XCTAssertEqual(session.visibleIndicatorState, .ready)
        XCTAssertFalse(session.stopActionAvailable)
        XCTAssertEqual(session.triggerEvidence["trigger"], "meeting_detection_prompt")
        XCTAssertEqual(session.triggerEvidence["meetingDetectionTargetId"], "yandex_telemost")
    }
}
#endif
