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
            && mic.validationType == .appIOHeartbeat
            && speaker.validationType == .appIOHeartbeat
            && mic.status == .passed
            && speaker.status == .passed
    }

    public var syntheticRoutesPassed: Bool {
        mic.path == .micToVirtualInput
            && speaker.path == .remoteOutputToVirtualSpeaker
            && mic.validationType == .syntheticSignal
            && speaker.validationType == .syntheticSignal
            && mic.status == .passed
            && speaker.status == .passed
    }
}

public struct RouteVerificationService: Sendable {
    public static let lowResourceStartupTimeoutNanoseconds: UInt64 = 3_000_000_000

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

        let microphonePreflightFailure = microphoneFailure(for: physicalInput)
        let speakerPreflightFailure = speakerFailure(for: physicalOutput)

        let micStatus: RouteVerificationStatus = if microphonePreflightFailure == nil {
            await probe(.micToVirtualInput, physicalInput)
        } else {
            .failed
        }
        let speakerStatus: RouteVerificationStatus = if speakerPreflightFailure == nil {
            await probe(.remoteOutputToVirtualSpeaker, physicalOutput)
        } else {
            .failed
        }

        return RouteVerificationSnapshot(
            mic: verification(
                path: .micToVirtualInput,
                target: physicalInput.displayName,
                status: micStatus,
                startedAt: startedAt,
                failureReason: microphonePreflightFailure?.reason,
                recoveryAction: microphonePreflightFailure?.recoveryAction
            ),
            speaker: verification(
                path: .remoteOutputToVirtualSpeaker,
                target: physicalOutput.displayName,
                status: speakerStatus,
                startedAt: startedAt,
                failureReason: speakerPreflightFailure?.reason,
                recoveryAction: speakerPreflightFailure?.recoveryAction
            )
        )
    }

    public func verifyBounded(
        physicalInput: PhysicalAudioDevice?,
        physicalOutput: PhysicalAudioDevice?,
        timeoutNanoseconds: UInt64 = Self.lowResourceStartupTimeoutNanoseconds
    ) async -> RouteVerificationSnapshot {
        await withTaskGroup(of: RouteVerificationSnapshot.self) { group in
            group.addTask {
                await verify(physicalInput: physicalInput, physicalOutput: physicalOutput)
            }
            group.addTask {
                try? await Task.sleep(nanoseconds: timeoutNanoseconds)
                let now = clock()
                return failedSnapshot(
                    startedAt: now,
                    reason: "route_verification_timeout",
                    recoveryAction: "retry_audio_route_startup"
                )
            }

            let first = await group.next()!
            group.cancelAll()
            return first
        }
    }

    public func verifyLiveReadiness(
        physicalInput: PhysicalAudioDevice?,
        physicalOutput: PhysicalAudioDevice?
    ) async -> LiveRouteReadinessResult {
        let snapshot = await verify(physicalInput: physicalInput, physicalOutput: physicalOutput)
        let now = clock()

        let micSelfRouting = physicalInput.map { selfRoutingGuard.matchesVirtualMicrophone($0) } ?? false
        let speakerSelfRouting = physicalOutput.map { selfRoutingGuard.matchesVirtualSpeaker($0) } ?? false

        let microphoneEvidence = MicrophonePathEvidence(
            selectedPhysicalDeviceId: physicalInput?.id ?? "",
            selectedPhysicalDeviceName: physicalInput?.displayName ?? "",
            status: liveEvidenceStatus(from: snapshot.mic.status),
            validFrameCount: 0,
            emptyBufferCount: 0,
            capturabilityStatus: .unknown,
            selfRoutingRejected: micSelfRouting,
            failureReason: liveEvidenceFailureReason(from: snapshot.mic),
            checkedAt: now
        )

        let speakerEvidence = SpeakerPathEvidence(
            selectedPhysicalOutputId: physicalOutput?.id ?? "",
            selectedPhysicalOutputName: physicalOutput?.displayName ?? "",
            status: liveEvidenceStatus(from: snapshot.speaker.status),
            stimulusObserved: false,
            validFrameCount: 0,
            emptyBufferCount: 0,
            selfRoutingRejected: speakerSelfRouting,
            failureReason: liveEvidenceFailureReason(from: snapshot.speaker),
            checkedAt: now
        )

        let recoveryAction = snapshot.mic.recoveryAction ?? snapshot.speaker.recoveryAction
        let hasPreflightFailure = snapshot.mic.status == .failed || snapshot.speaker.status == .failed
        let status: LiveRouteReadinessStatus = hasPreflightFailure ? .failed : .stale

        return LiveRouteReadinessResult(
            status: status,
            microphoneEvidence: microphoneEvidence,
            speakerEvidence: speakerEvidence,
            checkedAt: now,
            recoveryAction: recoveryAction
        )
    }

    public func auditEvents(for result: LiveRouteReadinessResult) -> [AuditEventName] {
        var events: [AuditEventName] = [.liveRouteReadinessCheckStarted]
        switch result.status {
        case .ready:
            events.append(.liveRouteReadinessPassed)
        case .stale:
            events.append(.liveRouteReadinessStale)
        case .failed, .degraded:
            events.append(.liveRouteReadinessFailed)
        case .notStarted, .checking:
            break
        }
        return events
    }

    public static func defaultRouteSnapshot(
        input: PhysicalAudioDevice?,
        output: PhysicalAudioDevice?,
        observedAt: Date = Date()
    ) -> MacOSDefaultRouteSnapshot {
        MacOSDefaultRouteSnapshot(
            inputDeviceId: input?.id,
            inputDeviceClass: input?.deviceClass ?? .unknown,
            outputDeviceId: output?.id,
            outputDeviceClass: output?.deviceClass ?? .unknown,
            observedAt: observedAt
        )
    }

    public func userActionEvidence(
        action: UserActionKind,
        sessionId: String,
        target: MeetingTarget? = nil
    ) -> RouteEvidenceEvent {
        RouteEvidenceEvent(
            eventId: idFactory(),
            sessionId: sessionId,
            family: .userAction,
            name: "user_action.\(action.rawValue)",
            observedAt: clock(),
            source: .routeEngine,
            target: target,
            userActionKind: action
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

    private func microphoneFailure(for device: PhysicalAudioDevice) -> (reason: String, recoveryAction: String)? {
        switch device.availabilityState {
        case .available, .noisy:
            return nil
        case .muted:
            return ("physical_microphone_muted", "unmute_physical_microphone")
        case .silent:
            return ("physical_microphone_silent", "select_working_physical_microphone")
        case .disconnected:
            return ("physical_microphone_unavailable", "select_physical_microphone")
        case .profileSwitching:
            return ("bluetooth_profile_switching", "wait_for_stable_audio_profile")
        case .unsupported:
            return ("physical_microphone_unsupported", "select_built_in_or_wired_microphone")
        }
    }

    private func speakerFailure(for device: PhysicalAudioDevice) -> (reason: String, recoveryAction: String)? {
        if device.displayName.localizedCaseInsensitiveContains("Aggregate") ||
            device.displayName.localizedCaseInsensitiveContains("Многовыходное") {
            return ("aggregate_output_unmanaged", "select_single_physical_speaker")
        }

        switch device.availabilityState {
        case .available, .noisy:
            return nil
        case .muted:
            return ("physical_speaker_muted", "unmute_physical_speaker")
        case .silent:
            return ("physical_speaker_silent", "select_working_physical_speaker")
        case .disconnected:
            return ("physical_speaker_unavailable", "select_physical_speaker")
        case .profileSwitching:
            return ("bluetooth_profile_switching", "wait_for_stable_audio_profile")
        case .unsupported:
            return ("physical_speaker_unsupported", "select_built_in_or_wired_speaker")
        }
    }

    private func liveEvidenceStatus(from status: RouteVerificationStatus) -> RouteEvidenceStatus {
        switch status {
        case .passed:
            .blocked
        case .stale:
            .degraded
        case .failed:
            .failed
        case .running:
            .notStarted
        case .notStarted:
            .notStarted
        }
    }

    private func liveEvidenceFailureReason(from route: RouteVerification) -> String? {
        route.failureReason ?? "live_passthrough_evidence_missing"
    }
}
