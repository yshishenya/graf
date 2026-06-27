import Foundation

public enum ProductPrivacyControlState: String, Codable, CaseIterable, Sendable {
    case capturing
    case paused
    case resuming
    case stopping
    case stopped

    public var suppressesLocalMicrophone: Bool {
        self == .paused || self == .stopping || self == .stopped
    }
}

public enum ProductPrivacyControl: String, Codable, CaseIterable, Sendable {
    case pause
    case resume
    case stop
}

public enum ProductPrivacyLocalMicTreatment: String, Codable, CaseIterable, Sendable {
    case silenced
    case redacted
    case ended
}

public enum MeetingMuteTruthSource: String, Codable, CaseIterable, Sendable {
    case productPause = "product_pause"
    case targetAdapter = "target_adapter"
    case unsupported
    case unknown
    case stale
    case contradicted
}

public enum MeetingMuteTruthEvidenceStatus: String, Codable, CaseIterable, Sendable {
    case accepted
    case meetingMuteUnproven = "meeting_mute_unproven"
    case unsupported
    case deferred
    case degraded
}

public enum MeetingMuteTruthFreshness: String, Codable, CaseIterable, Sendable {
    case fresh
    case stale
    case unavailable
}

public enum TargetMuteFamily: String, Codable, CaseIterable, Sendable {
    case nativeApp = "native_app"
    case browserMeeting = "browser_meeting"
    case unknown
}

public enum FirstMuteTruthMatrixStatus: String, Codable, CaseIterable, Sendable {
    case pauseValidated = "pause_validated"
    case unsupported
    case deferred
}

public enum MuteTruthDecisionValue: String, Codable, CaseIterable, Sendable {
    case muteRespecting = "mute_respecting"
    case meetingMuteUnproven = "meeting_mute_unproven"
    case unsupported
    case degraded
    case failed
}

public enum MuteTruthDecisionReason: String, Codable, CaseIterable, Sendable {
    case productPauseSegmentsPresent = "product_pause_segments_present"
    case unsupportedTarget = "unsupported_target"
    case adapterMissing = "adapter_missing"
    case staleEvidence = "stale_evidence"
    case contradictedEvidence = "contradicted_evidence"
    case diagnosticRedactionFailed = "diagnostic_redaction_failed"
}

public struct ProductPrivacySegment: Codable, Equatable, Sendable {
    public var segmentId: String
    public var sessionId: String
    public var control: ProductPrivacyControl
    public var startedAt: Date
    public var endedAt: Date?
    public var startMonotonicMs: Int
    public var endMonotonicMs: Int?
    public var durationMs: Int
    public var localMicTreatment: ProductPrivacyLocalMicTreatment
    public var initiator: RecordingEvidenceInitiator
    public var diagnosticSafe: Bool

    public init(
        segmentId: String,
        sessionId: String,
        control: ProductPrivacyControl,
        startedAt: Date,
        endedAt: Date? = nil,
        startMonotonicMs: Int,
        endMonotonicMs: Int? = nil,
        durationMs: Int? = nil,
        localMicTreatment: ProductPrivacyLocalMicTreatment = .silenced,
        initiator: RecordingEvidenceInitiator = .user,
        diagnosticSafe: Bool = true
    ) {
        self.segmentId = segmentId
        self.sessionId = sessionId
        self.control = control
        self.startedAt = startedAt
        self.endedAt = endedAt
        self.startMonotonicMs = startMonotonicMs
        self.endMonotonicMs = endMonotonicMs
        self.durationMs = durationMs ?? Self.durationMs(start: startMonotonicMs, end: endMonotonicMs)
        self.localMicTreatment = localMicTreatment
        self.initiator = initiator
        self.diagnosticSafe = diagnosticSafe
    }

    public func finalized(
        endedAt: Date,
        endMonotonicMs: Int,
        treatment: ProductPrivacyLocalMicTreatment? = nil
    ) -> ProductPrivacySegment {
        ProductPrivacySegment(
            segmentId: segmentId,
            sessionId: sessionId,
            control: control,
            startedAt: startedAt,
            endedAt: endedAt,
            startMonotonicMs: startMonotonicMs,
            endMonotonicMs: endMonotonicMs,
            durationMs: Self.durationMs(start: startMonotonicMs, end: endMonotonicMs),
            localMicTreatment: treatment ?? localMicTreatment,
            initiator: initiator,
            diagnosticSafe: diagnosticSafe
        )
    }

    private static func durationMs(start: Int, end: Int?) -> Int {
        guard let end else { return 0 }
        return max(0, end - start)
    }
}

public struct MeetingMuteTruthEvidence: Codable, Equatable, Sendable {
    public var evidenceId: String
    public var sessionId: String
    public var targetId: String
    public var targetDisplayName: String
    public var source: MeetingMuteTruthSource
    public var status: MeetingMuteTruthEvidenceStatus
    public var freshness: MeetingMuteTruthFreshness
    public var limitationCopyShown: Bool
    public var recordedAt: Date
    public var adapterId: String?
    public var diagnosticSafe: Bool

    public init(
        evidenceId: String,
        sessionId: String,
        targetId: String,
        targetDisplayName: String,
        source: MeetingMuteTruthSource,
        status: MeetingMuteTruthEvidenceStatus,
        freshness: MeetingMuteTruthFreshness,
        limitationCopyShown: Bool,
        recordedAt: Date,
        adapterId: String? = nil,
        diagnosticSafe: Bool = true
    ) {
        self.evidenceId = evidenceId
        self.sessionId = sessionId
        self.targetId = targetId
        self.targetDisplayName = targetDisplayName
        self.source = source
        self.status = status
        self.freshness = freshness
        self.limitationCopyShown = limitationCopyShown
        self.recordedAt = recordedAt
        self.adapterId = adapterId
        self.diagnosticSafe = diagnosticSafe
    }
}

public struct TargetMuteCapability: Codable, Equatable, Sendable {
    public var targetId: String
    public var targetDisplayName: String
    public var targetFamily: TargetMuteFamily
    public var productPauseSupported: Bool
    public var meetingAppMuteAdapterSupported: Bool
    public var firstMatrixStatus: FirstMuteTruthMatrixStatus
    public var releaseClaim: String

    public init(
        targetId: String,
        targetDisplayName: String,
        targetFamily: TargetMuteFamily,
        productPauseSupported: Bool,
        meetingAppMuteAdapterSupported: Bool,
        firstMatrixStatus: FirstMuteTruthMatrixStatus,
        releaseClaim: String
    ) {
        self.targetId = targetId
        self.targetDisplayName = targetDisplayName
        self.targetFamily = targetFamily
        self.productPauseSupported = productPauseSupported
        self.meetingAppMuteAdapterSupported = meetingAppMuteAdapterSupported
        self.firstMatrixStatus = firstMatrixStatus
        self.releaseClaim = releaseClaim
    }

    public static let zoomNative = TargetMuteCapability(
        targetId: "zoom_native",
        targetDisplayName: "Zoom native",
        targetFamily: .nativeApp,
        productPauseSupported: true,
        meetingAppMuteAdapterSupported: false,
        firstMatrixStatus: .pauseValidated,
        releaseClaim: "GRAF Pause/Stop keeps local speech out; Zoom mute is unproven"
    )

    public static let chromeTelemost = TargetMuteCapability(
        targetId: "chrome_telemost",
        targetDisplayName: "Chrome + Telemost",
        targetFamily: .browserMeeting,
        productPauseSupported: true,
        meetingAppMuteAdapterSupported: false,
        firstMatrixStatus: .pauseValidated,
        releaseClaim: "GRAF Pause/Stop keeps local speech out; Telemost/browser mute is unproven"
    )

    public static let operaTelemost = TargetMuteCapability(
        targetId: "opera_telemost",
        targetDisplayName: "Opera + Telemost",
        targetFamily: .browserMeeting,
        productPauseSupported: true,
        meetingAppMuteAdapterSupported: false,
        firstMatrixStatus: .pauseValidated,
        releaseClaim: "GRAF Pause/Stop keeps local speech out; Telemost/browser mute is unproven"
    )

    public static let yandexTelemost = TargetMuteCapability(
        targetId: "yandex_telemost",
        targetDisplayName: "Yandex Browser + Telemost",
        targetFamily: .browserMeeting,
        productPauseSupported: false,
        meetingAppMuteAdapterSupported: false,
        firstMatrixStatus: .deferred,
        releaseClaim: "No meeting-app mute-respecting claim"
    )

    public static let unknown = TargetMuteCapability(
        targetId: "unknown",
        targetDisplayName: "Generic or unknown meeting target",
        targetFamily: .unknown,
        productPauseSupported: false,
        meetingAppMuteAdapterSupported: false,
        firstMatrixStatus: .unsupported,
        releaseClaim: "No meeting-app mute-respecting claim"
    )
}

public struct MuteTruthDecision: Codable, Equatable, Sendable {
    public var sessionId: String
    public var decision: MuteTruthDecisionValue
    public var reason: MuteTruthDecisionReason
    public var privacySegmentIds: [String]
    public var targetEvidenceIds: [String]
    public var safeForDiagnostics: Bool
    public var decidedAt: Date

    public init(
        sessionId: String,
        decision: MuteTruthDecisionValue,
        reason: MuteTruthDecisionReason,
        privacySegmentIds: [String] = [],
        targetEvidenceIds: [String] = [],
        safeForDiagnostics: Bool = true,
        decidedAt: Date
    ) {
        self.sessionId = sessionId
        self.decision = decision
        self.reason = reason
        self.privacySegmentIds = privacySegmentIds
        self.targetEvidenceIds = targetEvidenceIds
        self.safeForDiagnostics = safeForDiagnostics
        self.decidedAt = decidedAt
    }

    public static func mvpDecision(
        sessionId: String,
        privacySegments: [ProductPrivacySegment],
        targetEvidence: [MeetingMuteTruthEvidence],
        targetCapability: TargetMuteCapability?,
        decidedAt: Date
    ) -> MuteTruthDecision {
        let capability = targetCapability ?? .unknown
        let targetEvidenceIds = targetEvidence.map(\.evidenceId)
        let segmentIds = privacySegments.map(\.segmentId)
        let safeForDiagnostics = privacySegments.allSatisfy(\.diagnosticSafe) &&
            targetEvidence.allSatisfy(\.diagnosticSafe)

        if !safeForDiagnostics {
            return MuteTruthDecision(
                sessionId: sessionId,
                decision: .failed,
                reason: .diagnosticRedactionFailed,
                privacySegmentIds: segmentIds,
                targetEvidenceIds: targetEvidenceIds,
                safeForDiagnostics: false,
                decidedAt: decidedAt
            )
        }

        if capability.firstMatrixStatus == .unsupported {
            return MuteTruthDecision(
                sessionId: sessionId,
                decision: .unsupported,
                reason: .unsupportedTarget,
                privacySegmentIds: segmentIds,
                targetEvidenceIds: targetEvidenceIds,
                decidedAt: decidedAt
            )
        }

        return MuteTruthDecision(
            sessionId: sessionId,
            decision: .meetingMuteUnproven,
            reason: privacySegments.isEmpty ? .adapterMissing : .productPauseSegmentsPresent,
            privacySegmentIds: segmentIds,
            targetEvidenceIds: targetEvidenceIds,
            decidedAt: decidedAt
        )
    }
}
