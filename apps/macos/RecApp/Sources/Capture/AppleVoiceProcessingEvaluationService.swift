import Foundation
import TwoBrainRecShared

public struct AppleProcessingOutcomeSummary: Equatable, Sendable {
    public var feature: String
    public var candidateId: String
    public var primaryOutcome: AppleProcessingOutcomeState
    public var primaryOutcomeCount: Int
    public var nextStepRecommendation: AppleProcessingNextStepRecommendation
    public var canClaimCleanBuiltinSpeakerphone: Bool
    public var diagnosticSafe: Bool
    public var failureReason: String?
    public var userFacingSummary: String
    public var releaseSummary: String

    public init(
        feature: String = "038-apple-voice-processing-spike",
        candidateId: String,
        primaryOutcome: AppleProcessingOutcomeState,
        primaryOutcomeCount: Int = 1,
        nextStepRecommendation: AppleProcessingNextStepRecommendation,
        canClaimCleanBuiltinSpeakerphone: Bool,
        diagnosticSafe: Bool,
        failureReason: String?,
        userFacingSummary: String,
        releaseSummary: String
    ) {
        self.feature = feature
        self.candidateId = candidateId
        self.primaryOutcome = primaryOutcome
        self.primaryOutcomeCount = primaryOutcomeCount
        self.nextStepRecommendation = nextStepRecommendation
        self.canClaimCleanBuiltinSpeakerphone = canClaimCleanBuiltinSpeakerphone
        self.diagnosticSafe = diagnosticSafe
        self.failureReason = failureReason
        self.userFacingSummary = userFacingSummary
        self.releaseSummary = releaseSummary
    }

    public var containsCleanSpeakerphoneClaim: Bool {
        [userFacingSummary, releaseSummary].contains { text in
            text.range(of: "clean speakerphone", options: [.caseInsensitive]) != nil ||
                text.range(of: "clean recording", options: [.caseInsensitive]) != nil ||
                text.range(of: "чист", options: [.caseInsensitive]) != nil
        }
    }
}

public struct AppleVoiceProcessingEvaluationService: Sendable {
    public typealias Clock = @Sendable () -> Date

    private let clock: Clock
    private let threshold: LeakageThresholdVersion

    public init(
        threshold: LeakageThresholdVersion = .v1,
        clock: @escaping Clock = Date.init
    ) {
        self.threshold = threshold
        self.clock = clock
    }

    public func probeCandidate(
        candidateId: String,
        candidateKind: AppleProcessingCandidateKind,
        routeClass: AppleProcessingRouteClass,
        featureGateEnabled: Bool,
        apiAvailable: Bool,
        processingEnabled: Bool
    ) -> AppleProcessingCandidate {
        AppleProcessingCandidate(
            candidateId: candidateId,
            candidateKind: candidateKind,
            routeClass: routeClass,
            featureGateEnabled: featureGateEnabled,
            apiAvailable: apiAvailable,
            processingEnabled: processingEnabled,
            observedAt: clock(),
            failureReason: probeFailureReason(
                featureGateEnabled: featureGateEnabled,
                apiAvailable: apiAvailable,
                processingEnabled: processingEnabled
            )
        )
    }

    public func compareLeakage(
        candidateId: String,
        candidateKind: AppleProcessingCandidateKind,
        routeClass: AppleProcessingRouteClass,
        scenario: AppleProcessingScenario,
        baseline: LeakageMeasurement?,
        candidate: LeakageMeasurement?,
        lineageStatus: AppleProcessingLineageStatus,
        speechPreservationStatus: AppleSpeechPreservationStatus,
        alignmentStatus: AppleProcessingAlignmentStatus,
        diagnosticSafe: Bool = true
    ) -> AppleProcessingValidationRow {
        AppleProcessingValidationRow(
            candidateId: candidateId,
            candidateKind: candidateKind,
            routeClass: routeClass,
            scenario: scenario,
            baselineStatus: baselineEvidenceStatus(baseline),
            candidateStatus: candidateEvidenceStatus(candidate),
            lineageStatus: lineageStatus,
            speechPreservationStatus: speechPreservationStatus,
            alignmentStatus: alignmentStatus,
            stabilityStatus: stabilityStatus(
                candidate: candidate,
                lineageStatus: lineageStatus,
                speechPreservationStatus: speechPreservationStatus,
                alignmentStatus: alignmentStatus,
                diagnosticSafe: diagnosticSafe
            ),
            diagnosticSafe: diagnosticSafe,
            failureReason: failureReason(
                candidate: candidate,
                lineageStatus: lineageStatus,
                speechPreservationStatus: speechPreservationStatus,
                alignmentStatus: alignmentStatus,
                diagnosticSafe: diagnosticSafe
            )
        )
    }

    public func failClosedRow(
        candidateId: String,
        candidateKind: AppleProcessingCandidateKind,
        routeClass: AppleProcessingRouteClass,
        scenario: AppleProcessingScenario,
        reason: AppleProcessingFailureReason,
        diagnosticSafe: Bool = true
    ) -> AppleProcessingValidationRow {
        let mapping = failClosedMapping(for: reason, diagnosticSafe: diagnosticSafe)
        return AppleProcessingValidationRow(
            candidateId: candidateId,
            candidateKind: candidateKind,
            routeClass: routeClass,
            scenario: scenario,
            baselineStatus: .notMeasured,
            candidateStatus: mapping.candidateStatus,
            lineageStatus: mapping.lineageStatus,
            speechPreservationStatus: mapping.speechPreservationStatus,
            alignmentStatus: mapping.alignmentStatus,
            stabilityStatus: mapping.stabilityStatus,
            diagnosticSafe: diagnosticSafe,
            failureReason: reason.rawValue
        )
    }

    public func outcome(
        candidateId: String,
        rows: [AppleProcessingValidationRow],
        fallbackFailureReason: String?
    ) -> AppleProcessingOutcome {
        if rowsContainAcceptedBuiltinSpeakerphone(rows) {
            return AppleProcessingOutcome(
                candidateId: candidateId,
                primaryOutcome: .acceptedForBuiltinSpeakerphone,
                validationRows: rows,
                nextStepRecommendation: .promoteAppleProcessing
            )
        }

        let normalizedStatuses = Set(rows.map(\.normalizedStabilityStatus))
        if normalizedStatuses.contains(.blockedRouteTopology) {
            return blockedOutcome(
                candidateId: candidateId,
                rows: rows,
                primaryOutcome: .blockedRouteTopology,
                nextStep: .deferToWebRTCAEC3,
                failureReason: fallbackFailureReason ?? "blocked_route_topology"
            )
        }
        if normalizedStatuses.contains(.blockedQuality) {
            return blockedOutcome(
                candidateId: candidateId,
                rows: rows,
                primaryOutcome: .blockedQuality,
                nextStep: .deferToWebRTCAEC3,
                failureReason: fallbackFailureReason ?? "blocked_quality"
            )
        }
        if normalizedStatuses.contains(.blockedStability) {
            return blockedOutcome(
                candidateId: candidateId,
                rows: rows,
                primaryOutcome: .blockedStability,
                nextStep: .deferToWebRTCAEC3,
                failureReason: fallbackFailureReason ?? "blocked_stability"
            )
        }
        if !rows.isEmpty && rows.allSatisfy({ $0.lineageStatus == .guidanceOnly }) {
            return AppleProcessingOutcome(
                candidateId: candidateId,
                primaryOutcome: .acceptedForGuidanceOnly,
                validationRows: rows,
                nextStepRecommendation: .guidanceOnly,
                failureReason: fallbackFailureReason
            )
        }

        return AppleProcessingOutcome(
            candidateId: candidateId,
            primaryOutcome: .deferToWebRTCAEC3,
            validationRows: rows,
            nextStepRecommendation: .deferToWebRTCAEC3,
            failureReason: fallbackFailureReason ?? "required_builtin_speakerphone_rows_missing"
        )
    }

    public func decisionRecord(_ outcome: AppleProcessingOutcome) -> [String: String] {
        [
            "feature": outcome.feature,
            "candidateId": outcome.candidateId,
            "primaryOutcome": outcome.primaryOutcome.rawValue,
            "nextStepRecommendation": outcome.nextStepRecommendation.rawValue,
            "canClaimCleanBuiltinSpeakerphone": String(outcome.canClaimCleanBuiltinSpeakerphone),
            "diagnosticSafe": String(outcome.diagnosticSafe),
            "failureReason": outcome.failureReason ?? "",
            "validationRowCount": String(outcome.validationRows.count),
            "recordedAt": String(Int(clock().timeIntervalSince1970))
        ]
    }

    public func finalOutcomeSummary(_ outcome: AppleProcessingOutcome) -> AppleProcessingOutcomeSummary {
        let nextStep = normalizedNextStep(for: outcome.primaryOutcome)
        let canClaim = outcome.canClaimCleanBuiltinSpeakerphone
        return AppleProcessingOutcomeSummary(
            feature: outcome.feature,
            candidateId: outcome.candidateId,
            primaryOutcome: outcome.primaryOutcome,
            nextStepRecommendation: nextStep,
            canClaimCleanBuiltinSpeakerphone: canClaim,
            diagnosticSafe: outcome.diagnosticSafe && outcome.validationRows.allSatisfy(\.diagnosticSafe),
            failureReason: outcome.failureReason,
            userFacingSummary: userFacingSummary(for: outcome, nextStep: nextStep, canClaim: canClaim),
            releaseSummary: releaseSummary(for: outcome, nextStep: nextStep, canClaim: canClaim)
        )
    }

    private func rowsContainAcceptedBuiltinSpeakerphone(_ rows: [AppleProcessingValidationRow]) -> Bool {
        let acceptedScenarios = Set(
            rows
                .filter(\.isAcceptedForBuiltinSpeakerphone)
                .map(\.scenario)
        )
        return Set(AppleProcessingScenario.builtinSpeakerphoneAcceptanceScenarios)
            .isSubset(of: acceptedScenarios)
    }

    private func blockedOutcome(
        candidateId: String,
        rows: [AppleProcessingValidationRow],
        primaryOutcome: AppleProcessingOutcomeState,
        nextStep: AppleProcessingNextStepRecommendation,
        failureReason: String
    ) -> AppleProcessingOutcome {
        AppleProcessingOutcome(
            candidateId: candidateId,
            primaryOutcome: primaryOutcome,
            validationRows: rows,
            nextStepRecommendation: nextStep,
            failureReason: failureReason
        )
    }

    private func normalizedNextStep(
        for primaryOutcome: AppleProcessingOutcomeState
    ) -> AppleProcessingNextStepRecommendation {
        switch primaryOutcome {
        case .acceptedForBuiltinSpeakerphone:
            return .promoteAppleProcessing
        case .acceptedForGuidanceOnly:
            return .guidanceOnly
        case .acceptedForHeadsetRoutesOnly:
            return .headsetRoutesOnly
        case .blockedRouteTopology, .blockedQuality, .blockedStability, .deferToWebRTCAEC3:
            return .deferToWebRTCAEC3
        }
    }

    private func userFacingSummary(
        for outcome: AppleProcessingOutcome,
        nextStep: AppleProcessingNextStepRecommendation,
        canClaim: Bool
    ) -> String {
        switch outcome.primaryOutcome {
        case .acceptedForBuiltinSpeakerphone:
            return canClaim
                ? "Apple processing passed the built-in route evidence; package gates still decide readiness."
                : "Apple processing needs complete built-in route evidence before any stronger user promise."
        case .acceptedForGuidanceOnly:
            return "Apple processing can guide setup only; local package evidence remains authoritative."
        case .acceptedForHeadsetRoutesOnly:
            return "Apple processing is limited to headset-style routes; built-in speaker recording keeps current limits."
        case .blockedRouteTopology:
            return "Apple processing is blocked by route topology; next step is \(nextStep.rawValue)."
        case .blockedQuality:
            return "Apple processing is blocked by quality evidence; next step is \(nextStep.rawValue)."
        case .blockedStability:
            return "Apple processing is blocked by stability evidence; next step is \(nextStep.rawValue)."
        case .deferToWebRTCAEC3:
            return "Apple processing did not prove the product route; next step is \(nextStep.rawValue)."
        }
    }

    private func releaseSummary(
        for outcome: AppleProcessingOutcome,
        nextStep: AppleProcessingNextStepRecommendation,
        canClaim: Bool
    ) -> String {
        "038 outcome=\(outcome.primaryOutcome.rawValue); next=\(nextStep.rawValue); claimAllowed=\(canClaim); rows=\(outcome.validationRows.count); reason=\(outcome.failureReason ?? "none")"
    }

    private func probeFailureReason(
        featureGateEnabled: Bool,
        apiAvailable: Bool,
        processingEnabled: Bool
    ) -> String? {
        if !featureGateEnabled {
            return "feature_gate_disabled"
        }
        if !apiAvailable {
            return "apple_processing_unavailable"
        }
        if !processingEnabled {
            return AppleProcessingFailureReason.failedToEnable.rawValue
        }
        return nil
    }

    private func failClosedMapping(
        for reason: AppleProcessingFailureReason,
        diagnosticSafe: Bool
    ) -> (
        candidateStatus: AppleProcessingEvidenceStatus,
        lineageStatus: AppleProcessingLineageStatus,
        speechPreservationStatus: AppleSpeechPreservationStatus,
        alignmentStatus: AppleProcessingAlignmentStatus,
        stabilityStatus: AppleProcessingStabilityStatus
    ) {
        guard diagnosticSafe else {
            return (.blocked, .blocked, .unknown, .failed, .blockedStability)
        }

        switch reason {
        case .userSystemControlled:
            return (.unproven, .guidanceOnly, .notMeasured, .notMeasured, .unproven)
        case .missingFarEndReference, .routeTopologyBlocked, .routeChanged:
            return (.blocked, .blocked, .notMeasured, .failed, .blockedRouteTopology)
        case .processingUnavailable, .failedToEnable,
             .stopReleasedResources, .failedStartReleasedResources, .appQuitReleasedResources,
             .diagnosticsNotSafe:
            return (.blocked, .unproven, .notMeasured, .notMeasured, .blockedStability)
        }
    }

    private func baselineEvidenceStatus(_ measurement: LeakageMeasurement?) -> AppleProcessingEvidenceStatus {
        guard let measurement else { return .notMeasured }
        switch measurement.status {
        case .passed:
            return .accepted
        case .degraded, .blocked:
            return .degraded
        }
    }

    private func candidateEvidenceStatus(_ measurement: LeakageMeasurement?) -> AppleProcessingEvidenceStatus {
        guard let measurement else { return .unproven }
        guard measurement.confidence ?? 1 >= threshold.minimumConfidence else {
            return .unproven
        }
        guard measurement.dropoutObserved != true, measurement.clippingObserved != true else {
            return .blocked
        }
        if measurement.status == .passed,
           (measurement.leakageLevelDb ?? measurement.relativeLeakageDb) <= threshold.maximumLeakageLevelDb {
            return .accepted
        }
        return measurement.status == .blocked ? .blocked : .degraded
    }

    private func stabilityStatus(
        candidate: LeakageMeasurement?,
        lineageStatus: AppleProcessingLineageStatus,
        speechPreservationStatus: AppleSpeechPreservationStatus,
        alignmentStatus: AppleProcessingAlignmentStatus,
        diagnosticSafe: Bool
    ) -> AppleProcessingStabilityStatus {
        guard diagnosticSafe else { return .blockedStability }
        if lineageStatus == .blocked {
            return .blockedRouteTopology
        }
        if speechPreservationStatus == .suppressed {
            return .blockedQuality
        }
        if alignmentStatus == .failed {
            return .blockedStability
        }
        guard let candidate else { return .unproven }
        if candidate.clippingObserved == true || candidate.dropoutObserved == true {
            return .blockedStability
        }
        if candidateEvidenceStatus(candidate) == .accepted {
            return .accepted
        }
        return .unproven
    }

    private func failureReason(
        candidate: LeakageMeasurement?,
        lineageStatus: AppleProcessingLineageStatus,
        speechPreservationStatus: AppleSpeechPreservationStatus,
        alignmentStatus: AppleProcessingAlignmentStatus,
        diagnosticSafe: Bool
    ) -> String? {
        guard diagnosticSafe else { return "diagnostics_not_safe" }
        if lineageStatus == .blocked {
            return "lineage_blocked"
        }
        if speechPreservationStatus == .suppressed {
            return "local_speech_suppressed"
        }
        if alignmentStatus == .failed {
            return "alignment_failed"
        }
        guard let candidate else { return "candidate_missing" }
        if candidate.clippingObserved == true {
            return "clipping_observed"
        }
        if candidate.dropoutObserved == true {
            return "dropout_observed"
        }
        return candidateEvidenceStatus(candidate) == .accepted ? nil : "candidate_not_accepted"
    }
}

public final class AppleVoiceProcessingCandidateLifecycleCoordinator: @unchecked Sendable {
    public typealias Clock = @Sendable () -> Date

    private let clock: Clock
    private let lock = NSLock()
    private var activeCandidateId: String?
    private var lastReleasedCandidateId: String?
    private var startedAt: Date?
    private var lastReleasedAt: Date?
    private var lastReleaseReason: AppleProcessingLifecycleReleaseReason?

    public init(clock: @escaping Clock = Date.init) {
        self.clock = clock
    }

    public func start(candidate: AppleProcessingCandidate) -> AppleProcessingLifecycleSnapshot {
        lock.lock()
        defer { lock.unlock() }
        activeCandidateId = candidate.candidateId
        lastReleasedCandidateId = nil
        startedAt = clock()
        lastReleasedAt = nil
        lastReleaseReason = nil
        return snapshotOnLock(resourceActive: true)
    }

    public func release(reason: AppleProcessingLifecycleReleaseReason) -> AppleProcessingLifecycleSnapshot {
        lock.lock()
        defer { lock.unlock() }
        guard let releasedCandidateId = activeCandidateId else {
            return snapshotOnLock(resourceActive: false)
        }
        lastReleasedCandidateId = releasedCandidateId
        lastReleasedAt = clock()
        lastReleaseReason = reason
        activeCandidateId = nil
        return snapshotOnLock(resourceActive: false)
    }

    public func snapshot() -> AppleProcessingLifecycleSnapshot {
        lock.lock()
        defer { lock.unlock() }
        return snapshotOnLock(resourceActive: activeCandidateId != nil)
    }

    private func snapshotOnLock(resourceActive: Bool) -> AppleProcessingLifecycleSnapshot {
        AppleProcessingLifecycleSnapshot(
            activeCandidateId: activeCandidateId,
            releasedCandidateId: lastReleasedCandidateId,
            startedAt: startedAt,
            releasedAt: lastReleasedAt,
            releaseReason: lastReleaseReason,
            resourceActive: resourceActive
        )
    }
}
