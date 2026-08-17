import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

@MainActor
final class SystemAudioPermissionUXTests: XCTestCase {
    func testGrantedPermissionsHaveNoRecoveryPresentation() {
        let result = SystemAudioPermissionGate().evaluate(
            microphone: .granted,
            systemAudio: .granted
        )

        XCTAssertTrue(result.allowsAcceptedRecording)
        XCTAssertNil(result.presentation)
    }

    func testManualSystemAudioGrantRequiresRestartAfterObservedUnreadyState() {
        XCTAssertFalse(
            DesktopPermissionOnboardingStatus.systemAudioPermissionTransitionRequiresRestart(
                from: nil,
                to: .granted
            )
        )
        XCTAssertTrue(
            DesktopPermissionOnboardingStatus.systemAudioPermissionTransitionRequiresRestart(
                from: .unknown,
                to: .granted
            )
        )
        XCTAssertTrue(
            DesktopPermissionOnboardingStatus.systemAudioPermissionTransitionRequiresRestart(
                from: .denied,
                to: .granted
            )
        )
        XCTAssertFalse(
            DesktopPermissionOnboardingStatus.systemAudioPermissionTransitionRequiresRestart(
                from: .granted,
                to: .granted
            )
        )
    }

    func testObservedSystemAudioGrantStaysBlockedUntilRestart() {
        let result = SystemAudioPermissionGate().evaluate(
            microphone: .granted,
            systemAudio: .stale
        )

        XCTAssertFalse(result.allowsAcceptedRecording)
        XCTAssertEqual(result.presentation?.title, "Права нужно проверить заново")
        XCTAssertEqual(result.presentation?.recoveryAction, .retryPermissionCheck)
    }

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

    func testPermissionRecoveryActionsStaySeparateAndRussian() {
        XCTAssertEqual(DesktopPermissionOnboardingView.openSettingsTitle, "Открыть настройки macOS")
        XCTAssertEqual(DesktopPermissionOnboardingView.retryTitle, "Проверить снова")
        XCTAssertEqual(DesktopPermissionOnboardingView.restartTitle, "Перезапустить GRAF")
        XCTAssertTrue(DesktopPermissionOnboardingView.microphoneDeniedDetail.contains("повторный запрос"))
        XCTAssertTrue(DesktopPermissionOnboardingView.microphoneRestrictedDetail.contains("не может обойти"))
        XCTAssertNotEqual(
            DesktopPermissionOnboardingAccessibilityIdentifier.microphoneButton,
            DesktopPermissionOnboardingAccessibilityIdentifier.systemAudioButton
        )
        XCTAssertNotEqual(
            DesktopPermissionOnboardingAccessibilityIdentifier.restartButton,
            DesktopPermissionOnboardingAccessibilityIdentifier.finishButton
        )
        let devCopy = DesktopPermissionOnboardingView.systemAudioStepDetail(for: "GRAF Dev")
        XCTAssertTrue(devCopy.contains("GRAF Dev"))
        XCTAssertTrue(devCopy.contains("отдельно"))
    }

    func testDetectorAssistedPreparingDoesNotStartRecordingAutomatically() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 1_783_440_000) },
            idFactory: { "meeting-detection-session" },
            policySnapshotProvider: { "policy-meeting-detection" }
        )

        let session = try controller.beginDetectorAssistedPreparing(
            targetID: "yandex_telemost",
            bundleID: "ru.yandex.desktop.telemost",
            displayName: "Yandex Telemost",
            startReason: .promptTimeout,
            policySnapshotRef: "sha256:" + String(repeating: "a", count: 64),
            authorizationEvidence: ["meetingDetectionPolicyVersion": "2026.08.12.1"]
        )

        XCTAssertEqual(session.state, .detecting)
        XCTAssertEqual(session.visibleIndicatorState, .ready)
        XCTAssertFalse(session.stopActionAvailable)
        XCTAssertEqual(session.triggerEvidence["trigger"], "meeting_detection")
        XCTAssertEqual(session.triggerEvidence["meetingDetectionStartReason"], "prompt_timeout")
        XCTAssertEqual(session.triggerEvidence["meetingDetectionAutoStart"], "true")
        XCTAssertEqual(session.policySnapshotRef, "sha256:" + String(repeating: "a", count: 64))
        XCTAssertEqual(session.triggerEvidence["meetingDetectionTargetId"], "yandex_telemost")
    }
}
#endif
