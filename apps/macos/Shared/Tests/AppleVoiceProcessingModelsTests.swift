import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class AppleVoiceProcessingModelsTests: XCTestCase {
    func testAppleProcessingCandidateIsMetadataOnlyAndFeatureGated() throws {
        let candidate = AppleProcessingCandidate(
            candidateId: "apple-candidate-001",
            candidateKind: .appOwnedGraphVoiceProcessing,
            routeClass: .builtInSpeakerphone,
            featureGateEnabled: true,
            apiAvailable: true,
            processingEnabled: true,
            observedAt: Date(timeIntervalSince1970: 100)
        )

        XCTAssertTrue(candidate.isUsableCandidate)
        XCTAssertTrue(candidate.diagnosticSafe)
        XCTAssertEqual(candidate.feature, "038-apple-voice-processing-spike")

        let json = String(decoding: try JSONEncoder().encode(candidate), as: UTF8.self)
        XCTAssertFalse(json.contains("rawAudio"))
        XCTAssertFalse(json.contains("transcriptText"))
        XCTAssertFalse(json.contains("signedUrl"))
    }

    func testValidationRowRequiresLineageSpeechAlignmentAndDiagnosticSafety() {
        let accepted = AppleProcessingValidationRow(
            candidateId: "apple-candidate-001",
            candidateKind: .appOwnedGraphVoiceProcessing,
            routeClass: .builtInSpeakerphone,
            scenario: .doubleTalk,
            baselineStatus: .degraded,
            candidateStatus: .accepted,
            lineageStatus: .liveAndPersisted,
            speechPreservationStatus: .preserved,
            alignmentStatus: .accepted,
            stabilityStatus: .accepted,
            diagnosticSafe: true
        )
        let blocked = AppleProcessingValidationRow(
            candidateId: "apple-candidate-001",
            candidateKind: .appOwnedGraphVoiceProcessing,
            routeClass: .builtInSpeakerphone,
            scenario: .doubleTalk,
            baselineStatus: .degraded,
            candidateStatus: .accepted,
            lineageStatus: .liveAndPersisted,
            speechPreservationStatus: .suppressed,
            alignmentStatus: .accepted,
            stabilityStatus: .accepted,
            diagnosticSafe: true,
            failureReason: "local_speech_suppressed"
        )

        XCTAssertTrue(accepted.isAcceptedForBuiltinSpeakerphone)
        XCTAssertFalse(blocked.isAcceptedForBuiltinSpeakerphone)
        XCTAssertEqual(blocked.normalizedStabilityStatus, .blockedQuality)
    }

    func testProcessedMicrophoneEvidenceCannotSilentlyOverwriteOriginalTracks() {
        let evidence = ProcessedMicrophoneEvidence(
            candidateId: "apple-candidate-001",
            lineageStatus: .candidateMetadata,
            originalMicrophoneTrackPreserved: true,
            incomingReferencePreserved: true,
            manifestLabelsCandidate: true,
            leakageFinalizationAuthorityPreserved: true
        )

        XCTAssertTrue(evidence.preservesPackageTruth)
        XCTAssertFalse(evidence.canRedefineOriginalMicTrack)
        XCTAssertTrue(evidence.diagnosticSafe)
    }

    func testOutcomeAllowsCleanSpeakerphoneClaimOnlyWithAllRequiredRows() {
        let requiredRows = AppleProcessingScenario.builtinSpeakerphoneAcceptanceScenarios.map { scenario in
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
        let accepted = AppleProcessingOutcome(
            candidateId: "apple-candidate-001",
            primaryOutcome: .acceptedForBuiltinSpeakerphone,
            validationRows: requiredRows,
            nextStepRecommendation: .promoteAppleProcessing
        )
        let guidanceOnly = AppleProcessingOutcome(
            candidateId: "apple-candidate-001",
            primaryOutcome: .acceptedForGuidanceOnly,
            validationRows: requiredRows,
            nextStepRecommendation: .guidanceOnly
        )

        XCTAssertTrue(accepted.canClaimCleanBuiltinSpeakerphone)
        XCTAssertFalse(guidanceOnly.canClaimCleanBuiltinSpeakerphone)
    }

    func testOutcomeRejectsMissingRequiredBuiltinSpeakerphoneRows() {
        let onlyFarEnd = AppleProcessingOutcome(
            candidateId: "apple-candidate-001",
            primaryOutcome: .acceptedForBuiltinSpeakerphone,
            validationRows: [
                AppleProcessingValidationRow(
                    candidateId: "apple-candidate-001",
                    candidateKind: .appOwnedGraphVoiceProcessing,
                    routeClass: .builtInSpeakerphone,
                    scenario: .farEndOnly,
                    baselineStatus: .degraded,
                    candidateStatus: .accepted,
                    lineageStatus: .liveAndPersisted,
                    speechPreservationStatus: .preserved,
                    alignmentStatus: .accepted,
                    stabilityStatus: .accepted,
                    diagnosticSafe: true
                )
            ],
            nextStepRecommendation: .promoteAppleProcessing
        )

        XCTAssertFalse(onlyFarEnd.canClaimCleanBuiltinSpeakerphone)
    }

    func testOutcomeRejectsDiagnosticUnsafeRowsEvenWhenRequiredRowsExist() {
        let requiredRows = AppleProcessingScenario.builtinSpeakerphoneAcceptanceScenarios.map { scenario in
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
        let outcome = AppleProcessingOutcome(
            candidateId: "apple-candidate-001",
            primaryOutcome: .acceptedForBuiltinSpeakerphone,
            validationRows: requiredRows + [diagnosticUnsafeRow],
            nextStepRecommendation: .promoteAppleProcessing
        )

        XCTAssertEqual(diagnosticUnsafeRow.normalizedStabilityStatus, .blockedStability)
        XCTAssertFalse(outcome.canClaimCleanBuiltinSpeakerphone)
    }
}
#endif
