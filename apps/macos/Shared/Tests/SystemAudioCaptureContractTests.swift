import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioCaptureContractTests: XCTestCase {
    func testSystemAudioSessionRequiresPermissionScopeFramesAndNoFailureForAcceptance() {
        let denied = SystemAudioCaptureSession(
            sessionId: "session",
            permissionState: .denied,
            scopeKind: .application,
            sourceDisplayName: "Telemost",
            frameCount: 1_600
        )
        XCTAssertFalse(denied.canBeAccepted)

        let accepted = SystemAudioCaptureSession(
            sessionId: "session",
            permissionState: .granted,
            scopeApprovalId: "scope-1",
            scopeKind: .application,
            sourceDisplayName: "Telemost",
            frameCount: 1_600
        )
        XCTAssertTrue(accepted.canBeAccepted)
    }

    func testMicrophoneSessionRequiresPermissionFramesAndNoFailureForAcceptance() {
        let empty = MicrophoneCaptureSession(
            sessionId: "session",
            permissionState: .granted,
            inputDisplayName: "MacBook Pro Microphone",
            frameCount: 0
        )
        XCTAssertFalse(empty.canBeAccepted)

        let accepted = MicrophoneCaptureSession(
            sessionId: "session",
            permissionState: .granted,
            inputDisplayName: "MacBook Pro Microphone",
            frameCount: 1_600
        )
        XCTAssertTrue(accepted.canBeAccepted)
    }

    func testScopeApprovalCannotBecomeBackgroundAudioTrigger() {
        let approval = CaptureScopeApproval(
            scopeApprovalId: "scope-1",
            scopeKind: .window,
            sourceDisplayName: "Meeting Window",
            approvedAt: Date(timeIntervalSince1970: 1),
            approvalMode: .manualSelection,
            eligibleReason: .manualMeetingScope
        )

        XCTAssertTrue(approval.isAcceptedForMeetingRecording)
        XCTAssertTrue(approval.notTriggerForBackgroundAudio)
    }

    func testCaptureHealthUsesCombinedAppHelperCpuAndNoHALGate() {
        let health = CaptureHealthSnapshot(
            recordingSessionId: "session",
            phase: .activeRecording,
            sampledAt: Date(timeIntervalSince1970: 1),
            coreaudiodCpuPercent: 7,
            appCpuPercent: 14,
            helperCpuPercent: 8
        )

        XCTAssertEqual(health.appHelperCpuPercent, 22)
        XCTAssertTrue(health.passesNoHALGate)
    }
}
#endif
