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
}
#endif
