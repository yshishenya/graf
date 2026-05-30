import Foundation
import TwoBrainRecShared

public typealias SyntheticRouteProbe = @Sendable (
    _ path: RoutePath,
    _ selectedPhysicalDevice: PhysicalAudioDevice
) async -> RouteVerificationStatus

public struct RouteVerificationSnapshot: Codable, Equatable, Sendable {
    public var mic: RouteVerification
    public var speaker: RouteVerification

    public init(mic: RouteVerification, speaker: RouteVerification) {
        self.mic = mic
        self.speaker = speaker
    }

    public var canShowReady: Bool {
        mic.path == .micToVirtualInput
            && speaker.path == .remoteOutputToVirtualSpeaker
            && mic.validationType == .syntheticSignal
            && speaker.validationType == .syntheticSignal
            && mic.status == .passed
            && speaker.status == .passed
    }
}

public struct RouteVerificationService: Sendable {
    private let clock: @Sendable () -> Date
    private let idFactory: @Sendable () -> String
    private let probe: SyntheticRouteProbe
    private let selfRoutingGuard: SelfRoutingGuard

    public init(
        clock: @escaping @Sendable () -> Date = Date.init,
        idFactory: @escaping @Sendable () -> String = { UUID().uuidString },
        probe: @escaping SyntheticRouteProbe,
        selfRoutingGuard: SelfRoutingGuard = SelfRoutingGuard()
    ) {
        self.clock = clock
        self.idFactory = idFactory
        self.probe = probe
        self.selfRoutingGuard = selfRoutingGuard
    }

    @MainActor
    public func verify(selection: PhysicalDeviceSelectionViewModel) async -> RouteVerificationSnapshot {
        await verify(
            physicalInput: selection.selectedInput,
            physicalOutput: selection.selectedOutput
        )
    }

    public func verify(
        physicalInput: PhysicalAudioDevice?,
        physicalOutput: PhysicalAudioDevice?
    ) async -> RouteVerificationSnapshot {
        let startedAt = clock()

        switch selfRoutingGuard.evaluate(physicalInput: physicalInput, physicalOutput: physicalOutput) {
        case let .rejected(violation):
            return failedSnapshot(
                startedAt: startedAt,
                reason: violation.code.rawValue,
                recoveryAction: violation.recoveryAction
            )
        case .allowed:
            break
        }

        guard let physicalInput else {
            return failedSnapshot(
                startedAt: startedAt,
                reason: "physical_input_missing",
                recoveryAction: "select_physical_microphone"
            )
        }

        guard let physicalOutput else {
            return failedSnapshot(
                startedAt: startedAt,
                reason: "physical_output_missing",
                recoveryAction: "select_physical_speaker"
            )
        }

        async let micStatus = probe(.micToVirtualInput, physicalInput)
        async let speakerStatus = probe(.remoteOutputToVirtualSpeaker, physicalOutput)

        return RouteVerificationSnapshot(
            mic: verification(
                path: .micToVirtualInput,
                target: physicalInput.displayName,
                status: await micStatus,
                startedAt: startedAt
            ),
            speaker: verification(
                path: .remoteOutputToVirtualSpeaker,
                target: physicalOutput.displayName,
                status: await speakerStatus,
                startedAt: startedAt
            )
        )
    }

    private func failedSnapshot(
        startedAt: Date,
        reason: String,
        recoveryAction: String
    ) -> RouteVerificationSnapshot {
        RouteVerificationSnapshot(
            mic: verification(
                path: .micToVirtualInput,
                target: nil,
                status: .failed,
                startedAt: startedAt,
                failureReason: reason,
                recoveryAction: recoveryAction
            ),
            speaker: verification(
                path: .remoteOutputToVirtualSpeaker,
                target: nil,
                status: .failed,
                startedAt: startedAt,
                failureReason: reason,
                recoveryAction: recoveryAction
            )
        )
    }

    private func verification(
        path: RoutePath,
        target: String?,
        status: RouteVerificationStatus,
        startedAt: Date,
        failureReason: String? = nil,
        recoveryAction: String? = nil
    ) -> RouteVerification {
        RouteVerification(
            id: idFactory(),
            path: path,
            validationType: .syntheticSignal,
            target: target,
            status: status,
            failureReason: failureReason ?? defaultFailureReason(for: status),
            recoveryAction: recoveryAction ?? defaultRecoveryAction(for: status),
            startedAt: startedAt,
            finishedAt: status == .running ? nil : clock()
        )
    }

    private func defaultFailureReason(for status: RouteVerificationStatus) -> String? {
        status == .failed ? "synthetic_route_probe_failed" : nil
    }

    private func defaultRecoveryAction(for status: RouteVerificationStatus) -> String? {
        status == .failed ? "retry_route_verification" : nil
    }
}
