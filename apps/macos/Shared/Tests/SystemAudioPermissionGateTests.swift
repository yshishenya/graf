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

    func testEveryNonGrantedPermissionStateBlocksAcceptedRecording() {
        let nonGrantedStates: [CapturePermissionState] = [.unknown, .denied, .restricted, .stale]

        for state in nonGrantedStates {
            let missingMicrophone = gate().evaluate(microphone: state, systemAudio: .granted)
            XCTAssertFalse(missingMicrophone.allowsAcceptedRecording, "microphone \(state) must block accepted recording")
            XCTAssertEqual(missingMicrophone.outcome, .blocked)
            XCTAssertEqual(missingMicrophone.manifestFailureReason, .permissionDenied)

            let missingSystemAudio = gate().evaluate(microphone: .granted, systemAudio: state)
            XCTAssertFalse(missingSystemAudio.allowsAcceptedRecording, "system audio \(state) must block accepted recording")
            XCTAssertEqual(missingSystemAudio.outcome, .blocked)
            XCTAssertEqual(missingSystemAudio.manifestFailureReason, .permissionDenied)
        }
    }

    func testStalePermissionStateRequiresRetryRatherThanGrantCopy() {
        let microphoneStale = gate().evaluate(microphone: .stale, systemAudio: .granted)
        let systemAudioStale = gate().evaluate(microphone: .granted, systemAudio: .stale)

        XCTAssertEqual(microphoneStale.presentation?.recoveryAction, .retryPermissionCheck)
        XCTAssertEqual(systemAudioStale.presentation?.recoveryAction, .retryPermissionCheck)
        XCTAssertEqual(microphoneStale.presentation?.title, "Права нужно проверить заново")
        XCTAssertEqual(systemAudioStale.presentation?.title, "Права нужно проверить заново")
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

    func testMicrophonePermissionRequestReturnsGrantedPreflightSession() async {
        let service = MicrophoneCaptureService(
            authorizer: FixtureMicrophonePermissionAuthorizer(requestedState: .granted)
        )

        let session = await service.requestPermissionAndPreflight(
            sessionId: "session",
            inputDisplayName: "Default Microphone"
        )

        XCTAssertEqual(session.permissionState, .granted)
        XCTAssertEqual(session.inputDisplayName, "Default Microphone")
    }

    func testSystemAudioAuthorizerRequestPathCanReturnGrantedState() async {
        let authorizer = FixtureSystemAudioPermissionAuthorizer(
            currentState: .unknown,
            requestedState: .granted
        )

        let requested = await authorizer.requestPermission()
        let result = gate().evaluate(microphone: .granted, systemAudio: requested)

        XCTAssertEqual(requested, .granted)
        XCTAssertTrue(result.allowsAcceptedRecording)
    }

    private func gate() -> SystemAudioPermissionGate {
        SystemAudioPermissionGate(clock: { Date(timeIntervalSince1970: 1) })
    }
}

private struct FixtureMicrophonePermissionAuthorizer: MicrophonePermissionAuthorizing {
    let requestedState: CapturePermissionState

    func currentPermissionState() -> CapturePermissionState {
        .unknown
    }

    func requestPermission() async -> CapturePermissionState {
        requestedState
    }
}

private struct FixtureSystemAudioPermissionAuthorizer: SystemAudioPermissionAuthorizing {
    let currentState: CapturePermissionState
    let requestedState: CapturePermissionState

    func currentPermissionState() -> CapturePermissionState {
        currentState
    }

    func requestPermission() async -> CapturePermissionState {
        requestedState
    }
}
#endif
