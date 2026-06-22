import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class AppleVoiceProcessingEvaluationTests: XCTestCase {
    func testProbeCandidateRecordsFeatureGateAndAvailability() {
        let service = AppleVoiceProcessingEvaluationService(clock: { Date(timeIntervalSince1970: 100) })

        let disabled = service.probeCandidate(
            candidateId: "apple-candidate-disabled",
            candidateKind: .appOwnedGraphVoiceProcessing,
            routeClass: .builtInSpeakerphone,
            featureGateEnabled: false,
            apiAvailable: true,
            processingEnabled: true
        )
        let enabled = service.probeCandidate(
            candidateId: "apple-candidate-enabled",
            candidateKind: .appOwnedGraphVoiceProcessing,
            routeClass: .builtInSpeakerphone,
            featureGateEnabled: true,
            apiAvailable: true,
            processingEnabled: true
        )

        XCTAssertFalse(disabled.isUsableCandidate)
        XCTAssertEqual(disabled.failureReason, "feature_gate_disabled")
        XCTAssertTrue(enabled.isUsableCandidate)
        XCTAssertNil(enabled.failureReason)
    }

    func testOutcomeSelectionRequiresAllBuiltinSpeakerphoneRows() {
        let service = AppleVoiceProcessingEvaluationService()
        let acceptedRows = AppleProcessingScenario.builtinSpeakerphoneAcceptanceScenarios.map { scenario in
            AppleProcessingValidationRow(
                candidateId: "apple-candidate-001",
                candidateKind: .appOwnedGraphVoiceProcessing,
                routeClass: .builtInSpeakerphone,
                scenario: scenario,
                baselineStatus: .degraded,
                candidateStatus: .accepted,
                lineageStatus: .liveAndPersisted,
                speechPreservationStatus: .preserved,
                alignmentStatus: .accepted,
                stabilityStatus: .accepted,
                diagnosticSafe: true
            )
        }

        let accepted = service.outcome(
            candidateId: "apple-candidate-001",
            rows: acceptedRows,
            fallbackFailureReason: nil
        )
        let missingRows = service.outcome(
            candidateId: "apple-candidate-001",
            rows: Array(acceptedRows.dropLast()),
            fallbackFailureReason: nil
        )

        XCTAssertEqual(accepted.primaryOutcome, .acceptedForBuiltinSpeakerphone)
        XCTAssertTrue(accepted.canClaimCleanBuiltinSpeakerphone)
        XCTAssertEqual(missingRows.primaryOutcome, .deferToWebRTCAEC3)
        XCTAssertFalse(missingRows.canClaimCleanBuiltinSpeakerphone)
    }

    func testOutcomeSelectionFailsClosedWhenAnyRowIsDiagnosticUnsafe() {
        let service = AppleVoiceProcessingEvaluationService()
        let acceptedRows = AppleProcessingScenario.builtinSpeakerphoneAcceptanceScenarios.map { scenario in
            AppleProcessingValidationRow(
                candidateId: "apple-candidate-001",
                candidateKind: .appOwnedGraphVoiceProcessing,
                routeClass: .builtInSpeakerphone,
                scenario: scenario,
                baselineStatus: .degraded,
                candidateStatus: .accepted,
                lineageStatus: .liveAndPersisted,
                speechPreservationStatus: .preserved,
                alignmentStatus: .accepted,
                stabilityStatus: .accepted,
                diagnosticSafe: true
            )
        }
        let diagnosticUnsafeRow = AppleProcessingValidationRow(
            candidateId: "apple-candidate-001",
            candidateKind: .appOwnedGraphVoiceProcessing,
            routeClass: .builtInSpeakerphone,
            scenario: .diagnostics,
            baselineStatus: .degraded,
            candidateStatus: .accepted,
            lineageStatus: .liveAndPersisted,
            speechPreservationStatus: .preserved,
            alignmentStatus: .accepted,
            stabilityStatus: .accepted,
            diagnosticSafe: false,
            failureReason: AppleProcessingFailureReason.diagnosticsNotSafe.rawValue
        )

        let outcome = service.outcome(
            candidateId: "apple-candidate-001",
            rows: acceptedRows + [diagnosticUnsafeRow],
            fallbackFailureReason: nil
        )

        XCTAssertEqual(outcome.primaryOutcome, .blockedStability)
        XCTAssertEqual(outcome.nextStepRecommendation, .deferToWebRTCAEC3)
        XCTAssertEqual(outcome.failureReason, AppleProcessingFailureReason.diagnosticsNotSafe.rawValue)
        XCTAssertFalse(outcome.canClaimCleanBuiltinSpeakerphone)
    }

    func testDecisionRecordIsMetadataOnlyAndSingleOutcome() {
        let service = AppleVoiceProcessingEvaluationService(clock: { Date(timeIntervalSince1970: 200) })
        let outcome = AppleProcessingOutcome(
            candidateId: "apple-candidate-001",
            primaryOutcome: .acceptedForGuidanceOnly,
            validationRows: [],
            nextStepRecommendation: .guidanceOnly,
            failureReason: "system_controlled_mic_mode"
        )

        let record = service.decisionRecord(outcome)

        XCTAssertEqual(record["feature"], "038-apple-voice-processing-spike")
        XCTAssertEqual(record["primaryOutcome"], "accepted_for_guidance_only")
        XCTAssertEqual(record["candidateId"], "apple-candidate-001")
        XCTAssertEqual(record["canClaimCleanBuiltinSpeakerphone"], "false")
        XCTAssertNil(record["rawAudio"])
        XCTAssertNil(record["transcriptText"])
    }

    func testFailClosedRowsCoverUnavailableControlledReferenceAndTopologyFailures() {
        let service = AppleVoiceProcessingEvaluationService()
        let cases: [(AppleProcessingFailureReason, AppleProcessingEvidenceStatus, AppleProcessingLineageStatus, AppleProcessingStabilityStatus)] = [
            (.processingUnavailable, .blocked, .unproven, .blockedStability),
            (.failedToEnable, .blocked, .unproven, .blockedStability),
            (.userSystemControlled, .unproven, .guidanceOnly, .unproven),
            (.missingFarEndReference, .blocked, .blocked, .blockedRouteTopology),
            (.routeTopologyBlocked, .blocked, .blocked, .blockedRouteTopology)
        ]

        for (reason, candidateStatus, lineageStatus, stabilityStatus) in cases {
            let row = service.failClosedRow(
                candidateId: "apple-candidate-\(reason.rawValue)",
                candidateKind: reason == .userSystemControlled ? .micModeGuidance : .appOwnedGraphVoiceProcessing,
                routeClass: .builtInSpeakerphone,
                scenario: .routeChange,
                reason: reason
            )

            XCTAssertEqual(row.candidateStatus, candidateStatus, reason.rawValue)
            XCTAssertEqual(row.lineageStatus, lineageStatus, reason.rawValue)
            XCTAssertEqual(row.normalizedStabilityStatus, stabilityStatus, reason.rawValue)
            XCTAssertEqual(row.failureReason, reason.rawValue)
            XCTAssertTrue(row.diagnosticSafe)
            XCTAssertFalse(row.isAcceptedForBuiltinSpeakerphone)
        }
    }

    func testAppleCandidateLifecycleCoordinatorReleasesOnStopFailedStartAndAppQuit() {
        let coordinator = AppleVoiceProcessingCandidateLifecycleCoordinator(
            clock: { Date(timeIntervalSince1970: 300) }
        )
        let idleRelease = coordinator.release(reason: .stop)
        let candidate = AppleProcessingCandidate(
            candidateId: "apple-candidate-lifecycle",
            candidateKind: .appOwnedGraphVoiceProcessing,
            routeClass: .builtInSpeakerphone,
            featureGateEnabled: true,
            apiAvailable: false,
            processingEnabled: false,
            observedAt: Date(timeIntervalSince1970: 300),
            failureReason: AppleProcessingFailureReason.processingUnavailable.rawValue
        )

        XCTAssertFalse(idleRelease.resourceActive)
        XCTAssertNil(idleRelease.releasedCandidateId)
        XCTAssertNil(idleRelease.releaseReason)

        let started = coordinator.start(candidate: candidate)
        let stopped = coordinator.release(reason: .stop)
        _ = coordinator.start(candidate: candidate)
        let failedStart = coordinator.release(reason: .failedStart)
        _ = coordinator.start(candidate: candidate)
        let appQuit = coordinator.release(reason: .appQuit)

        XCTAssertTrue(started.resourceActive)
        XCTAssertEqual(started.activeCandidateId, "apple-candidate-lifecycle")
        XCTAssertFalse(stopped.resourceActive)
        XCTAssertNil(stopped.activeCandidateId)
        XCTAssertEqual(stopped.releasedCandidateId, "apple-candidate-lifecycle")
        XCTAssertEqual(stopped.releaseReason, .stop)
        XCTAssertFalse(failedStart.resourceActive)
        XCTAssertEqual(failedStart.releasedCandidateId, "apple-candidate-lifecycle")
        XCTAssertEqual(failedStart.releaseReason, .failedStart)
        XCTAssertFalse(appQuit.resourceActive)
        XCTAssertEqual(appQuit.releasedCandidateId, "apple-candidate-lifecycle")
        XCTAssertEqual(appQuit.releaseReason, .appQuit)
        XCTAssertTrue(appQuit.diagnosticSafe)
    }

    func testFinalOutcomeSummaryKeepsExactlyOnePrimaryOutcomeAndMapsNextStep() {
        let service = AppleVoiceProcessingEvaluationService()
        let cases: [(AppleProcessingOutcomeState, AppleProcessingNextStepRecommendation)] = [
            (.acceptedForBuiltinSpeakerphone, .promoteAppleProcessing),
            (.acceptedForGuidanceOnly, .guidanceOnly),
            (.acceptedForHeadsetRoutesOnly, .headsetRoutesOnly),
            (.blockedRouteTopology, .deferToWebRTCAEC3),
            (.blockedQuality, .deferToWebRTCAEC3),
            (.blockedStability, .deferToWebRTCAEC3),
            (.deferToWebRTCAEC3, .deferToWebRTCAEC3)
        ]

        for (state, expectedNextStep) in cases {
            let summary = service.finalOutcomeSummary(
                appleEvaluationOutcome(
                    state: state,
                    nextStep: .fallbackDecision,
                    failureReason: state == .acceptedForBuiltinSpeakerphone ? nil : "bounded_reason"
                )
            )

            XCTAssertEqual(summary.primaryOutcome, state)
            XCTAssertEqual(summary.primaryOutcomeCount, 1)
            XCTAssertEqual(summary.nextStepRecommendation, expectedNextStep)
            XCTAssertTrue(summary.diagnosticSafe)
        }
    }
}

private func appleEvaluationOutcome(
    state: AppleProcessingOutcomeState,
    nextStep: AppleProcessingNextStepRecommendation,
    failureReason: String? = nil
) -> AppleProcessingOutcome {
    AppleProcessingOutcome(
        candidateId: "apple-\(state.rawValue)",
        primaryOutcome: state,
        validationRows: [
            AppleProcessingValidationRow(
                candidateId: "apple-\(state.rawValue)",
                candidateKind: state == .acceptedForGuidanceOnly ? .micModeGuidance : .appOwnedGraphVoiceProcessing,
                routeClass: .builtInSpeakerphone,
                scenario: .farEndOnly,
                baselineStatus: .degraded,
                candidateStatus: state == .acceptedForBuiltinSpeakerphone ? .accepted : .unproven,
                lineageStatus: state == .acceptedForBuiltinSpeakerphone ? .liveAndPersisted : .unproven,
                speechPreservationStatus: state == .acceptedForBuiltinSpeakerphone ? .preserved : .notMeasured,
                alignmentStatus: state == .acceptedForBuiltinSpeakerphone ? .accepted : .notMeasured,
                stabilityStatus: state == .acceptedForBuiltinSpeakerphone ? .accepted : .unproven,
                diagnosticSafe: true,
                failureReason: failureReason
            )
        ],
        nextStepRecommendation: nextStep,
        failureReason: failureReason
    )
}
#endif
