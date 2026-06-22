import Foundation
import TwoBrainRecShared

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
            return "apple_processing_not_enabled"
        }
        return nil
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
