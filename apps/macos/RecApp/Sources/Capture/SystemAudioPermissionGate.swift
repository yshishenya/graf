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
        if microphone == .stale || systemAudio == .stale {
            return SystemAudioPermissionPresentation(
                title: "Права нужно проверить заново",
                message: "Повторите проверку прав перед записью.",
                recoveryAction: .retryPermissionCheck
            )
        }

        let micMissing = microphone != .granted
        let systemMissing = systemAudio != .granted

        if micMissing && systemMissing {
            return SystemAudioPermissionPresentation(
                title: "Нужны права на запись",
                message: "Разрешите доступ к микрофону и записи системного звука в настройках macOS, затем повторите запись.",
                recoveryAction: .grantBoth
            )
        }
        if micMissing {
            return SystemAudioPermissionPresentation(
                title: "Нужен доступ к микрофону",
                message: "Разрешите доступ к микрофону в настройках macOS, затем повторите запись.",
                recoveryAction: .grantMicrophone
            )
        }
        if systemMissing {
            return SystemAudioPermissionPresentation(
                title: "Нужна запись системного звука",
                message: "Разрешите запись системного звука в настройках macOS, затем повторите запись.",
                recoveryAction: .grantSystemAudio
            )
        }
        return SystemAudioPermissionPresentation(
            title: "Права нужно проверить заново",
            message: "Повторите проверку прав перед записью.",
            recoveryAction: .retryPermissionCheck
        )
    }
}
