import Foundation
import TwoBrainRecShared

public struct WebRTCAEC3EvaluationService: Sendable {
    public typealias Clock = @Sendable () -> Date
    public static let fallbackFeatureId = "040-speakerphone-recording-fallback-decision"

    private let thresholdProfile: WebRTCAEC3AcceptanceThresholdProfile
    private let clock: Clock

    public init(
        thresholdProfile: WebRTCAEC3AcceptanceThresholdProfile = .standardV1,
        clock: @escaping Clock = Date.init
    ) {
        self.thresholdProfile = thresholdProfile
        self.clock = clock
    }

    public func adapterUnavailableRow(candidateId: String) -> WebRTCAEC3ValidationRow {
        return failClosedRow(
            candidateId: candidateId,
            routeClass: .builtInSpeakerphone,
            scenarioFamily: .unsafeReferenceNegativeControl,
            reason: .dependencyUnavailable
        )
    }

    public func failClosedRow(
        candidateId: String,
        routeClass: WebRTCAEC3RouteClass,
        scenarioFamily: WebRTCAEC3ScenarioFamily,
        reason: WebRTCAEC3FailureReason
    ) -> WebRTCAEC3ValidationRow {
        WebRTCAEC3ValidationRow(
            rowId: "aec3-\(candidateId)-\(reason.rawValue)",
            candidateId: candidateId,
            scenarioFamily: scenarioFamily,
            validationKind: validationKind(for: reason),
            routeClass: routeClass,
            baselineStatus: .unproven,
            candidateStatus: .blocked,
            lineageStatus: .blocked,
            speechPreservationStatus: speechPreservationStatus(for: reason),
            residualLeakageStatus: .unproven,
            timingConfidence: timingConfidence(for: reason),
            referenceStatus: referenceStatus(for: reason),
            stabilityStatus: stabilityStatus(for: reason),
            thresholdProfileId: thresholdProfile.thresholdProfileId,
            thresholdSummary: thresholdSummary(for: reason),
            appStatusState: appStatusState(for: reason),
            diagnosticSafe: true,
            failureReason: reason.rawValue
        )
    }

    public func outcome(
        candidate: WebRTCAEC3Candidate,
        corpus: WebRTCAEC3ValidationCorpus,
        validationRows: [WebRTCAEC3ValidationRow],
        controlledHardwareRows: [ControlledRealHardwareRecordingEvidence],
        licenseReady: Bool,
        packagingReady: Bool,
        signingReady: Bool
    ) -> WebRTCAEC3DecisionRecord {
        if !licenseReady {
            return blockedDecision(
                candidateId: candidate.candidateId,
                rows: validationRows,
                outcome: .blockedStability,
                nextStep: .dependencyPackaging,
                reason: .licenseBlocked
            )
        }
        if !packagingReady {
            return blockedDecision(
                candidateId: candidate.candidateId,
                rows: validationRows,
                outcome: .blockedStability,
                nextStep: .dependencyPackaging,
                reason: .packagingBlocked
            )
        }
        if !signingReady {
            return blockedDecision(
                candidateId: candidate.candidateId,
                rows: validationRows,
                outcome: .blockedStability,
                nextStep: .dependencyPackaging,
                reason: .signingBlocked
            )
        }
        if !candidate.isEligibleForImmediatePromotion {
            return blockedDecision(
                candidateId: candidate.candidateId,
                rows: validationRows,
                outcome: .blockedStability,
                nextStep: .fallbackDecision,
                reason: candidateFailureReason(candidate)
            )
        }
        if !corpus.isEligibleForImmediatePromotion {
            return blockedDecision(
                candidateId: candidate.candidateId,
                rows: validationRows,
                outcome: .deferToFallbackDecision,
                nextStep: .fallbackDecision,
                reason: .corpusIncomplete
            )
        }
        if !controlledHardwareRowsSatisfyPromotion(controlledHardwareRows) {
            return blockedDecision(
                candidateId: candidate.candidateId,
                rows: validationRows,
                outcome: .deferToFallbackDecision,
                nextStep: .fallbackDecision,
                reason: .controlledHardwareMissing
            )
        }
        if validationRows.contains(where: { !$0.diagnosticSafe }) {
            return blockedDecision(
                candidateId: candidate.candidateId,
                rows: validationRows,
                outcome: .blockedStability,
                nextStep: .fallbackDecision,
                reason: .diagnosticsUnsafe
            )
        }

        let statuses = Set(validationRows.map(\.stabilityStatus))
        if statuses.contains(.blockedRouteTopology) {
            return blockedDecision(
                candidateId: candidate.candidateId,
                rows: validationRows,
                outcome: .blockedRouteTopology,
                nextStep: .fallbackDecision,
                reason: firstFailureReason(in: validationRows, fallback: .referenceMissing)
            )
        }
        if statuses.contains(.blockedQuality) {
            return blockedDecision(
                candidateId: candidate.candidateId,
                rows: validationRows,
                outcome: .blockedQuality,
                nextStep: .fallbackDecision,
                reason: firstFailureReason(in: validationRows, fallback: .speechSuppressed)
            )
        }
        if statuses.contains(.blockedStability) {
            return blockedDecision(
                candidateId: candidate.candidateId,
                rows: validationRows,
                outcome: .blockedStability,
                nextStep: .fallbackDecision,
                reason: firstFailureReason(in: validationRows, fallback: .callOrderUnsafe)
            )
        }

        if validationRowsCoverImmediatePromotion(validationRows) {
            return WebRTCAEC3DecisionRecord(
                candidateId: candidate.candidateId,
                primaryOutcome: .acceptedForImmediatePromotion,
                validationRows: validationRows,
                nextStepRecommendation: .promoteBuiltInRoute
            )
        }

        return blockedDecision(
            candidateId: candidate.candidateId,
            rows: validationRows,
            outcome: .deferToFallbackDecision,
            nextStep: .fallbackDecision,
            reason: .corpusIncomplete
        )
    }

    public func finalDecision(
        candidate: WebRTCAEC3Candidate,
        corpus: WebRTCAEC3ValidationCorpus,
        validationRows: [WebRTCAEC3ValidationRow],
        supportingRouteRows: [WebRTCAEC3ValidationRow] = [],
        controlledHardwareRows: [ControlledRealHardwareRecordingEvidence],
        licenseReady: Bool,
        packagingReady: Bool,
        signingReady: Bool
    ) -> WebRTCAEC3DecisionRecord {
        let builtInRows = validationRows.filter { $0.routeClass == .builtInSpeakerphone }
        var decision = outcome(
            candidate: candidate,
            corpus: corpus,
            validationRows: builtInRows,
            controlledHardwareRows: controlledHardwareRows,
            licenseReady: licenseReady,
            packagingReady: packagingReady,
            signingReady: signingReady
        )
        var limitations = [
            "promotion_scope_built_in_mac_mic_and_speakers",
            "supporting_routes_do_not_broaden_claim"
        ]
        if !supportingRouteRows.isEmpty {
            limitations.append("supporting_routes_evidence_only")
        }
        if decision.primaryOutcome != .acceptedForImmediatePromotion {
            limitations.append("fallback_required_040")
            decision.fallbackFeatureId = Self.fallbackFeatureId
        }
        decision.supportingRouteRows = supportingRouteRows
        decision.limitations = limitations
        return decision
    }

    public func rollbackEvent(
        candidateId: String,
        trigger: AEC3RollbackTrigger
    ) -> AEC3RollbackEvent {
        let occurredAt = clock()
        return AEC3RollbackEvent(
            rollbackId: "rollback-\(candidateId)-\(Int(occurredAt.timeIntervalSince1970))",
            candidateId: candidateId,
            trigger: trigger,
            previousLineageStatus: .promotedBuiltinRoute,
            restoredLineageStatus: .originalOnly,
            cleanRecordingClaimRemoved: true,
            appStatusShown: true,
            thresholdProfileId: thresholdProfile.thresholdProfileId,
            occurredAt: occurredAt,
            diagnosticSafe: true
        )
    }

    public func rollbackDecision(
        candidateId: String,
        trigger: AEC3RollbackTrigger
    ) -> WebRTCAEC3DecisionRecord {
        let event = rollbackEvent(candidateId: candidateId, trigger: trigger)
        let reason = rollbackFailureReason(for: trigger)
        let row = WebRTCAEC3ValidationRow(
            rowId: "aec3-\(candidateId)-rollback-\(trigger.rawValue)",
            candidateId: candidateId,
            scenarioFamily: .rollback,
            validationKind: .rollback,
            routeClass: .builtInSpeakerphone,
            baselineStatus: .unproven,
            candidateStatus: .blocked,
            lineageStatus: .rolledBackToOriginal,
            speechPreservationStatus: speechPreservationStatus(for: reason),
            residualLeakageStatus: .unproven,
            timingConfidence: timingConfidence(for: reason),
            referenceStatus: referenceStatus(for: reason),
            stabilityStatus: .rollbackRequired,
            thresholdProfileId: thresholdProfile.thresholdProfileId,
            thresholdSummary: "rollback_restored_original_truth",
            appStatusState: .rolledBackToOriginal,
            diagnosticSafe: event.diagnosticSafe,
            failureReason: reason.rawValue
        )

        return WebRTCAEC3DecisionRecord(
            candidateId: candidateId,
            primaryOutcome: .blockedStability,
            validationRows: [row],
            nextStepRecommendation: .fallbackDecision,
            rollbackEvents: [event],
            failureReason: reason.rawValue
        )
    }

    public func decisionRecord(_ decision: WebRTCAEC3DecisionRecord) -> [String: String] {
        let firstRow = decision.validationRows.first
        return [
            "feature": decision.feature,
            "candidateId": decision.candidateId,
            "primaryOutcome": decision.primaryOutcome.rawValue,
            "primaryOutcomeCount": "1",
            "nextStepRecommendation": decision.nextStepRecommendation.rawValue,
            "canClaimCleanBuiltInSpeakerphone": String(decision.canClaimCleanBuiltInSpeakerphone),
            "routeScope": routeScope(for: firstRow).rawValue,
            "thresholdProfileId": firstRow?.thresholdProfileId ?? thresholdProfile.thresholdProfileId,
            "dependencyReadiness": "not_recorded",
            "failureReason": decision.failureReason ?? "",
            "validationRowCount": String(decision.validationRows.count),
            "supportingRouteRowCount": String(decision.supportingRouteRows?.count ?? 0),
            "supportingRoutesCanBroadenPromotionScope": String(decision.supportingRoutesCanBroadenPromotionScope),
            "fallbackFeatureId": decision.fallbackFeatureId ?? "",
            "requiresFallbackPlanning": String(decision.requiresFallbackPlanning),
            "limitations": decision.decisionLimitations.joined(separator: ","),
            "appStatusState": firstRow?.appStatusState.rawValue ?? WebRTCAEC3AppStatusState.notEvaluated.rawValue,
            "rollbackEventCount": String(decision.rollbackEvents?.count ?? 0),
            "diagnosticSafe": String(decision.diagnosticSafe),
            "recordedAt": String(Int(clock().timeIntervalSince1970))
        ]
    }

    private func validationKind(for reason: WebRTCAEC3FailureReason) -> WebRTCAEC3ValidationKind {
        switch reason {
        case .stopQuitFailed:
            return .stopQuit
        case .diagnosticsUnsafe:
            return .diagnostics
        case .appStatusStale, .appStatusNoisy, .appStatusContradictsPackage:
            return .appStatus
        default:
            return .negativeControl
        }
    }

    private func blockedDecision(
        candidateId: String,
        rows: [WebRTCAEC3ValidationRow],
        outcome: WebRTCAEC3OutcomeState,
        nextStep: WebRTCAEC3NextStepRecommendation,
        reason: WebRTCAEC3FailureReason
    ) -> WebRTCAEC3DecisionRecord {
        WebRTCAEC3DecisionRecord(
            candidateId: candidateId,
            primaryOutcome: outcome,
            validationRows: rows,
            nextStepRecommendation: nextStep,
            failureReason: reason.rawValue
        )
    }

    private func controlledHardwareRowsSatisfyPromotion(
        _ rows: [ControlledRealHardwareRecordingEvidence]
    ) -> Bool {
        let passing = Set(
            rows
                .filter(\.satisfiesImmediatePromotion)
                .map(\.scenarioFamily)
        )
        return Set(WebRTCAEC3ScenarioFamily.allImmediatePromotionRequired)
            .isSubset(of: passing)
    }

    private func validationRowsCoverImmediatePromotion(_ rows: [WebRTCAEC3ValidationRow]) -> Bool {
        let accepted = Set(
            rows
                .filter(\.isAcceptedForImmediatePromotion)
                .map(\.scenarioFamily)
        )
        return Set(WebRTCAEC3ScenarioFamily.allImmediatePromotionRequired)
            .isSubset(of: accepted)
    }

    private func candidateFailureReason(_ candidate: WebRTCAEC3Candidate) -> WebRTCAEC3FailureReason {
        if candidate.dependencyReadiness == .licenseBlocked {
            return .licenseBlocked
        }
        if candidate.dependencyReadiness == .packagingBlocked {
            return .packagingBlocked
        }
        if candidate.dependencyReadiness == .signingBlocked {
            return .signingBlocked
        }
        if candidate.dependencyReadiness != .ready {
            return .dependencyUnavailable
        }
        if candidate.renderReferenceStatus != .present {
            return .referenceMissing
        }
        if candidate.captureTimingStatus != .safe {
            return .callOrderUnsafe
        }
        if candidate.routeClass != .builtInSpeakerphone ||
            candidate.promotionScope != .builtInMacMicAndSpeakers {
            return .routeNotPromotable
        }
        if candidate.thresholdProfileId.isEmpty {
            return .thresholdProfileMissing
        }
        return .diagnosticsUnsafe
    }

    private func firstFailureReason(
        in rows: [WebRTCAEC3ValidationRow],
        fallback: WebRTCAEC3FailureReason
    ) -> WebRTCAEC3FailureReason {
        guard let rawValue = rows.first(where: { $0.failureReason != nil })?.failureReason,
              let reason = WebRTCAEC3FailureReason(rawValue: rawValue) else {
            return fallback
        }
        return reason
    }

    private func routeScope(for row: WebRTCAEC3ValidationRow?) -> WebRTCAEC3PromotionScope {
        row?.routeClass == .builtInSpeakerphone ? .builtInMacMicAndSpeakers : .notPromotable
    }

    private func stabilityStatus(for reason: WebRTCAEC3FailureReason) -> WebRTCAEC3StabilityStatus {
        switch reason {
        case .referenceMissing,
             .referenceLate,
             .referenceProtected,
             .referenceSilent,
             .referenceClipped,
             .referenceNotRepresentative,
             .routeNotPromotable:
            return .blockedRouteTopology
        case .speechSuppressed, .residualLeakageHigh:
            return .blockedQuality
        case .thresholdProfileMissing,
             .thresholdProfileMismatch,
             .controlledHardwareMissing,
             .corpusIncomplete:
            return .unproven
        default:
            return .blockedStability
        }
    }

    private func speechPreservationStatus(
        for reason: WebRTCAEC3FailureReason
    ) -> WebRTCAEC3SpeechPreservationStatus {
        switch reason {
        case .speechSuppressed:
            return .suppressed
        case .residualLeakageHigh:
            return .degraded
        default:
            return .unknown
        }
    }

    private func timingConfidence(for reason: WebRTCAEC3FailureReason) -> WebRTCAEC3TimingConfidence {
        switch reason {
        case .callOrderUnsafe, .timingDrift, .jitterUnsafe:
            return .failed
        default:
            return .unknown
        }
    }

    private func referenceStatus(for reason: WebRTCAEC3FailureReason) -> WebRTCAEC3ReferenceStatus {
        switch reason {
        case .referenceMissing:
            return .missing
        case .referenceLate:
            return .late
        case .referenceProtected:
            return .protected
        case .referenceSilent:
            return .silent
        case .referenceClipped:
            return .clipped
        case .referenceNotRepresentative:
            return .notRepresentative
        default:
            return .unknown
        }
    }

    private func rollbackFailureReason(for trigger: AEC3RollbackTrigger) -> WebRTCAEC3FailureReason {
        switch trigger {
        case .routeChanged:
            return .routeNotPromotable
        case .referenceMissing:
            return .referenceMissing
        case .referenceUnsafe:
            return .referenceNotRepresentative
        case .qualityDropped:
            return .speechSuppressed
        case .timingUnsafe:
            return .callOrderUnsafe
        case .lineageIncomplete:
            return .lineageIncomplete
        case .diagnosticsUnsafe:
            return .diagnosticsUnsafe
        case .stopQuit:
            return .stopQuitFailed
        }
    }

    private func appStatusState(for reason: WebRTCAEC3FailureReason) -> WebRTCAEC3AppStatusState {
        switch reason {
        case .routeNotPromotable,
             .controlledHardwareMissing,
             .corpusIncomplete:
            return .fallbackRelevant
        case .appStatusStale, .appStatusNoisy, .appStatusContradictsPackage:
            return .requiresUserAttention
        default:
            return .candidateBlocked
        }
    }

    private func thresholdSummary(for reason: WebRTCAEC3FailureReason) -> String {
        switch reason {
        case .thresholdProfileMissing, .thresholdProfileMismatch:
            return "threshold_profile_blocks_promotion"
        default:
            return "fail_closed_\(reason.rawValue)"
        }
    }
}
