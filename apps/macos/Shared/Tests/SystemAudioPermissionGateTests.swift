import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioPermissionGateTests: XCTestCase {
    func testGrantedMicrophoneAndSystemAudioAllowsAcceptedRecording() {
        let result = gate().evaluate(microphone: .granted, systemAudio: .granted)

        XCTAssertTrue(result.allowsAcceptedRecording)
        XCTAssertEqual(result.outcome, .accepted)
        XCTAssertNil(result.presentation)
        XCTAssertEqual(result.manifestFailureReason, .none)
    }

    func testDeniedMicrophoneBlocksNormalAcceptedRecording() {
        let result = gate().evaluate(microphone: .denied, systemAudio: .granted)

        XCTAssertFalse(result.allowsAcceptedRecording)
        XCTAssertEqual(result.outcome, .blocked)
        XCTAssertEqual(result.presentation?.recoveryAction, .grantMicrophone)
        XCTAssertEqual(result.manifestFailureReason, .permissionDenied)
    }

    func testDeniedSystemAudioBlocksNormalAcceptedRecording() {
        let result = gate().evaluate(microphone: .granted, systemAudio: .denied)

        XCTAssertFalse(result.allowsAcceptedRecording)
        XCTAssertEqual(result.outcome, .blocked)
        XCTAssertEqual(result.presentation?.recoveryAction, .grantSystemAudio)
        XCTAssertEqual(result.manifestFailureReason, .permissionDenied)
    }

    func testExplicitDegradedAttemptIsLabelledBeforeStart() {
        let result = gate().evaluate(
            microphone: .granted,
            systemAudio: .denied,
            explicitDegradedAttempt: true
        )

        XCTAssertFalse(result.allowsAcceptedRecording)
        XCTAssertTrue(result.allowsExplicitDegradedAttempt)
        XCTAssertEqual(result.outcome, .degradedAttempt)
        XCTAssertEqual(result.presentation?.recoveryAction, .grantSystemAudio)
    }

    private func gate() -> SystemAudioPermissionGate {
        SystemAudioPermissionGate(clock: { Date(timeIntervalSince1970: 1) })
    }
}
#endif
