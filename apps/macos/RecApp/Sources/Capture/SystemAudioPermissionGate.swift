import Foundation
import TwoBrainRecShared

public struct SystemAudioPermissionGate: Sendable {
    public typealias Clock = @Sendable () -> Date

    private let clock: Clock

    public init(clock: @escaping Clock = Date.init) {
        self.clock = clock
    }

    public func evaluate(
        microphone: CapturePermissionState,
        systemAudio: CapturePermissionState,
        explicitDegradedAttempt: Bool = false
    ) -> SystemAudioPermissionGateResult {
        let snapshot = SystemAudioPermissionSnapshot(
            microphone: microphone,
            systemAudio: systemAudio,
            evaluatedAt: clock()
        )

        if snapshot.allowsAcceptedRecording {
            return SystemAudioPermissionGateResult(
                snapshot: snapshot,
                outcome: .accepted,
                presentation: nil,
                manifestFailureReason: .none
            )
        }

        let presentation = presentation(microphone: microphone, systemAudio: systemAudio)
        return SystemAudioPermissionGateResult(
            snapshot: snapshot,
            outcome: explicitDegradedAttempt ? .degradedAttempt : .blocked,
            presentation: presentation,
            manifestFailureReason: .permissionDenied
        )
    }

    private func presentation(
        microphone: CapturePermissionState,
        systemAudio: CapturePermissionState
    ) -> SystemAudioPermissionPresentation {
        let micMissing = microphone != .granted
        let systemMissing = systemAudio != .granted

        if micMissing && systemMissing {
            return SystemAudioPermissionPresentation(
                title: "Recording blocked: permissions required",
                message: "Grant Microphone and Screen/System Audio access in System Settings, then run the check again.",
                recoveryAction: .grantBoth
            )
        }
        if micMissing {
            return SystemAudioPermissionPresentation(
                title: "Recording blocked: microphone access required",
                message: "Grant Microphone access in System Settings, then retry recording.",
                recoveryAction: .grantMicrophone
            )
        }
        if systemMissing {
            return SystemAudioPermissionPresentation(
                title: "Recording blocked: Screen/System Audio access required",
                message: "Grant Screen/System Audio access in System Settings, then retry recording.",
                recoveryAction: .grantSystemAudio
            )
        }
        return SystemAudioPermissionPresentation(
            title: "Recording blocked: permission check stale",
            message: "Run the permission check again before recording.",
            recoveryAction: .retryPermissionCheck
        )
    }
}
