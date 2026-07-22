import Foundation
import TwoBrainRecShared

public enum CaptureSessionControllerError: Error, Equatable {
    case invalidTransition(String)
    case missingSession
}

public typealias CaptureModeTriggerEvidenceHook = @Sendable (_ session: CaptureSession, _ evidence: [String: String]) -> Void

@MainActor
public final class CaptureSessionController {
    public typealias Clock = @Sendable () -> Date
    public typealias IdFactory = @Sendable () -> String
    public typealias PolicySnapshotProvider = @Sendable () -> String

    public private(set) var session: CaptureSession?

    private let clock: Clock
    private let idFactory: IdFactory
    private let policySnapshotProvider: PolicySnapshotProvider
    private var readinessHooks: [CaptureMode: CaptureModeTriggerEvidenceHook?]

    public init(
        clock: @escaping Clock = Date.init,
        idFactory: @escaping IdFactory = { UUID().uuidString },
        policySnapshotProvider: @escaping PolicySnapshotProvider = { "policy-" + UUID().uuidString },
        readinessHooks: [CaptureMode: CaptureModeTriggerEvidenceHook?] = [
            .audioRecording: nil,
            .transcriptOnly: nil
        ]
    ) {
        self.clock = clock
        self.idFactory = idFactory
        self.policySnapshotProvider = policySnapshotProvider
        self.readinessHooks = readinessHooks
    }

    public func setReadinessHook(
        for mode: CaptureMode,
        _ hook: CaptureModeTriggerEvidenceHook?
    ) {
        readinessHooks[mode] = hook
    }

    public func beginPreparing(
        mode: CaptureMode,
        sourceAppEligibility: SourceAppEligibility
    ) throws -> CaptureSession {
        if let current = session, !isTerminalState(current.state), ![.idle].contains(current.state) {
            throw CaptureSessionControllerError.invalidTransition("Cannot begin preparing while session is \(current.state.rawValue)")
        }

        let next = CaptureSession(
            id: idFactory(),
            mode: mode,
            state: .detecting,
            sourceAppEligibility: sourceAppEligibility,
            policySnapshotRef: policySnapshotProvider(),
            triggerEvidence: [
                "trigger": "manual_start",
                "mode": mode.rawValue,
                "preparedAt": iso8601String(clock())
            ],
            visibleIndicatorState: .ready,
            stopActionAvailable: false,
            bufferSummaryId: nil,
            startedAt: nil,
            stoppedAt: nil
        )

        session = next
        return next
    }

    public func beginDetectorAssistedPreparing(
        targetID: String,
        bundleID: String,
        displayName: String,
        mode: CaptureMode = .audioRecording
    ) throws -> CaptureSession {
        var prepared = try beginPreparing(mode: mode, sourceAppEligibility: .eligible)
        prepared.triggerEvidence["trigger"] = "meeting_detection_prompt"
        prepared.triggerEvidence["meetingDetectionTargetId"] = targetID
        prepared.triggerEvidence["meetingDetectionBundleId"] = bundleID
        prepared.stopActionAvailable = false
        prepared.visibleIndicatorState = .ready
        session = prepared
        return prepared
    }

    public func markReady(
        sourceAppEligibility: SourceAppEligibility? = nil,
        triggerEvidence: [String: String] = [:]
    ) throws -> CaptureSession {
        guard var current = session else {
            throw CaptureSessionControllerError.missingSession
        }
        guard current.state == .detecting else {
            throw CaptureSessionControllerError.invalidTransition("Readiness can only be recorded from detecting")
        }

        if let sourceAppEligibility {
            current.sourceAppEligibility = sourceAppEligibility
        }

        var evidence = current.triggerEvidence
        evidence["readinessMode"] = current.mode.rawValue
        evidence["readinessRecordedAt"] = iso8601String(clock())
        evidence["policySnapshotRef"] = current.policySnapshotRef ?? ""

        triggerEvidence.forEach { key, value in
            evidence[key] = value
        }

        current.triggerEvidence = evidence
        current.state = .ready
        current.visibleIndicatorState = .ready
        current.stopActionAvailable = false

        session = current

        if let hook = readinessHooks[current.mode], let callback = hook {
            callback(current, evidence)
        }

        return current
    }

    public func start() throws -> CaptureSession {
        var current = try requireSession()
        if [.starting, .active, .paused, .degraded].contains(current.state) {
            return current
        }
        guard canTransition(from: current.state, to: .starting) else {
            throw CaptureSessionControllerError.invalidTransition("Cannot start from \(current.state.rawValue)")
        }

        current.state = .starting
        current.visibleIndicatorState = .ready
        current.stopActionAvailable = true
        session = current
        return current
    }

    public func markCapturing() throws -> CaptureSession {
        var current = try requireSession()
        guard canTransition(from: current.state, to: .active) else {
            throw CaptureSessionControllerError.invalidTransition("Cannot mark capturing from \(current.state.rawValue)")
        }

        current.state = .active
        current.startedAt = clock()
        current.visibleIndicatorState = .active
        current.stopActionAvailable = true
        session = current
        return current
    }

    public func pause() throws -> CaptureSession {
        var current = try requireSession()
        guard canTransition(from: current.state, to: .paused) else {
            throw CaptureSessionControllerError.invalidTransition("Cannot pause from \(current.state.rawValue)")
        }

        current.state = .paused
        current.visibleIndicatorState = .paused
        current.stopActionAvailable = true
        session = current
        return current
    }

    public func resume() throws -> CaptureSession {
        var current = try requireSession()
        guard canTransition(from: current.state, to: .active) else {
            throw CaptureSessionControllerError.invalidTransition("Cannot resume from \(current.state.rawValue)")
        }

        current.state = .active
        current.visibleIndicatorState = .active
        current.stopActionAvailable = true
        session = current
        return current
    }

    public func markDegraded(
        source: String? = nil,
        recoveryAction: String? = nil
    ) throws -> CaptureSession {
        var current = try requireSession()
        guard canTransition(from: current.state, to: .degraded) else {
            throw CaptureSessionControllerError.invalidTransition("Cannot mark degraded from \(current.state.rawValue)")
        }

        current.state = .degraded
        current.visibleIndicatorState = .degraded
        current.stopActionAvailable = true
        if let source {
            current.triggerEvidence["degradedSource"] = source
        }
        if let recoveryAction {
            current.triggerEvidence["recoveryAction"] = recoveryAction
        }
        session = current
        return current
    }

    public func requestStop(reason: RecordingStopReason = .userRequested) throws -> CaptureSession {
        var current = try requireSession()
        guard canTransition(from: current.state, to: .stopping) else {
            throw CaptureSessionControllerError.invalidTransition("Cannot stop from \(current.state.rawValue)")
        }

        current.state = .stopping
        current.stopReason = reason
        current.visibleIndicatorState = .degraded
        current.stopActionAvailable = true
        session = current
        return current
    }

    public func completeStop() throws -> CaptureSession {
        var current = try requireSession()
        guard canTransition(from: current.state, to: .stopped) else {
            throw CaptureSessionControllerError.invalidTransition("Cannot complete stop from \(current.state.rawValue)")
        }

        current.state = .stopped
        current.stoppedAt = clock()
        current.visibleIndicatorState = .hidden
        current.stopActionAvailable = false
        session = current
        return current
    }

    public func blockStart(
        reason: RecordingStartBlocker,
        recoveryAction: String
    ) throws -> CaptureSession {
        var current = try requireSession()
        guard current.state == .detecting || current.state == .ready || current.state == .starting else {
            throw CaptureSessionControllerError.invalidTransition("Cannot block start from \(current.state.rawValue)")
        }

        current.state = .failed
        current.stoppedAt = clock()
        current.visibleIndicatorState = .error
        current.stopActionAvailable = false
        current.failureCategory = reason
        current.triggerEvidence["blockedReason"] = reason.rawValue
        current.triggerEvidence["recoveryAction"] = recoveryAction
        current.triggerEvidence["blockedAt"] = iso8601String(clock())
        session = current
        return current
    }

    public func fail(
        stopReason: RecordingStopReason = .failed,
        failureCategory: RecordingStartBlocker? = nil
    ) throws -> CaptureSession {
        var current = try requireSession()
        guard canTransition(from: current.state, to: .failed) else {
            throw CaptureSessionControllerError.invalidTransition("Cannot fail from \(current.state.rawValue)")
        }

        current.state = .failed
        current.stoppedAt = clock()
        current.visibleIndicatorState = .error
        current.stopActionAvailable = false
        current.stopReason = stopReason
        current.failureCategory = failureCategory
        session = current
        return current
    }

    public func finalize() throws -> CaptureSession {
        var current = try requireSession()
        guard canTransition(from: current.state, to: .finalized) else {
            throw CaptureSessionControllerError.invalidTransition("Cannot finalize from \(current.state.rawValue)")
        }

        current.state = .finalized
        current.visibleIndicatorState = .hidden
        current.stopActionAvailable = false
        session = current
        return current
    }

    public func updateEligibility(_ value: SourceAppEligibility) throws -> CaptureSession {
        var current = try requireSession()
        current.sourceAppEligibility = value
        session = current
        return current
    }

    public func makeTrackEvidence(
        role: AudioTrackRole,
        sampleRate: Double = 48000,
        channelLayout: String = "stereo",
        state: AudioTrackState = .capturing
    ) throws -> AudioTrack {
        let current = try requireSession()
        return AudioTrack(
            id: idFactory(),
            sessionId: current.id,
            role: role,
            state: state,
            sampleRate: sampleRate,
            channelLayout: channelLayout,
            timebase: "host_time",
            clockDriftMs: nil,
            dropoutMarkerIds: [],
            finalizedAt: nil
        )
    }

    private func requireSession() throws -> CaptureSession {
        guard let current = session else {
            throw CaptureSessionControllerError.missingSession
        }
        return current
    }

    private func canTransition(from source: CaptureSessionState, to destination: CaptureSessionState) -> Bool {
        switch source {
        case .idle:
            return destination == .detecting
        case .detecting:
            return destination == .ready || destination == .failed
        case .ready:
            return destination == .starting || destination == .failed
        case .starting:
            return destination == .active || destination == .failed || destination == .stopping
        case .active:
            return destination == .paused || destination == .degraded || destination == .failed || destination == .stopping
        case .paused:
            return destination == .active || destination == .stopping || destination == .failed
        case .degraded:
            return destination == .stopping || destination == .active || destination == .failed
        case .stopping:
            return destination == .stopped || destination == .failed
        case .stopped:
            return destination == .finalized
        case .failed:
            return destination == .finalized
        case .finalized:
            return false
        }
    }

    private func isTerminalState(_ state: CaptureSessionState) -> Bool {
        state == .finalized || state == .failed || state == .stopped
    }

    private func iso8601String(_ date: Date) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.string(from: date)
    }
}
