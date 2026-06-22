import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class WebRTCAEC3EvaluationTests: XCTestCase {
    func testFailClosedRowsCoverDependencyReferenceTimingFormatQualityAndResourceFailures() {
        let service = WebRTCAEC3EvaluationService()
        let cases: [(WebRTCAEC3FailureReason, WebRTCAEC3StabilityStatus)] = [
            (.dependencyUnavailable, .blockedStability),
            (.licenseBlocked, .blockedStability),
            (.packagingBlocked, .blockedStability),
            (.referenceMissing, .blockedRouteTopology),
            (.referenceLate, .blockedRouteTopology),
            (.callOrderUnsafe, .blockedStability),
            (.sampleFormatUnsupported, .blockedStability),
            (.speechSuppressed, .blockedQuality),
            (.cpuPressure, .blockedStability),
            (.memoryPressure, .blockedStability)
        ]

        for (reason, expectedStatus) in cases {
            let row = service.failClosedRow(
                candidateId: "aec3-\(reason.rawValue)",
                routeClass: .builtInSpeakerphone,
                scenarioFamily: .doubleTalk,
                reason: reason
            )

            XCTAssertEqual(row.stabilityStatus, expectedStatus, reason.rawValue)
            XCTAssertEqual(row.failureReason, reason.rawValue)
            XCTAssertFalse(row.isAcceptedForImmediatePromotion)
            XCTAssertTrue(row.diagnosticSafe)
        }
    }

    func testOutcomeSelectionRequiresCorpusControlledHardwareAndDependencyReadiness() {
        let service = WebRTCAEC3EvaluationService()
        let candidate = WebRTCAEC3Candidate(
            candidateId: "aec3-candidate-001",
            candidateKind: .nativeWebRTCAEC3,
            routeClass: .builtInSpeakerphone,
            promotionScope: .builtInMacMicAndSpeakers,
            dependencyReadiness: .ready,
            renderReferenceStatus: .present,
            captureTimingStatus: .safe,
            metricsStatus: .available,
            thresholdProfileId: WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId,
            diagnosticSafe: true
        )
        let accepted = service.outcome(
            candidate: candidate,
            corpus: webRTCAEC3AcceptedCorpus(),
            validationRows: webRTCAEC3AcceptedPromotionRows(),
            controlledHardwareRows: webRTCAEC3AcceptedControlledHardwareRows(),
            licenseReady: true,
            packagingReady: true,
            signingReady: true
        )
        let missingHardware = service.outcome(
            candidate: candidate,
            corpus: webRTCAEC3AcceptedCorpus(),
            validationRows: webRTCAEC3AcceptedPromotionRows(),
            controlledHardwareRows: [],
            licenseReady: true,
            packagingReady: true,
            signingReady: true
        )

        XCTAssertEqual(accepted.primaryOutcome, .acceptedForImmediatePromotion)
        XCTAssertEqual(accepted.nextStepRecommendation, .promoteBuiltInRoute)
        XCTAssertTrue(accepted.canClaimCleanBuiltInSpeakerphone)
        XCTAssertEqual(missingHardware.primaryOutcome, .deferToFallbackDecision)
        XCTAssertEqual(missingHardware.failureReason, WebRTCAEC3FailureReason.controlledHardwareMissing.rawValue)
        XCTAssertFalse(missingHardware.canClaimCleanBuiltInSpeakerphone)
    }

    func testOutcomeFailsClosedForLicensePackagingAndSigningReadiness() {
        let service = WebRTCAEC3EvaluationService()
        let candidate = webRTCAEC3AcceptedCandidate()

        let licenseBlocked = service.outcome(
            candidate: candidate,
            corpus: webRTCAEC3AcceptedCorpus(),
            validationRows: webRTCAEC3AcceptedPromotionRows(),
            controlledHardwareRows: webRTCAEC3AcceptedControlledHardwareRows(),
            licenseReady: false,
            packagingReady: true,
            signingReady: true
        )
        let packagingBlocked = service.outcome(
            candidate: candidate,
            corpus: webRTCAEC3AcceptedCorpus(),
            validationRows: webRTCAEC3AcceptedPromotionRows(),
            controlledHardwareRows: webRTCAEC3AcceptedControlledHardwareRows(),
            licenseReady: true,
            packagingReady: false,
            signingReady: true
        )
        let signingBlocked = service.outcome(
            candidate: candidate,
            corpus: webRTCAEC3AcceptedCorpus(),
            validationRows: webRTCAEC3AcceptedPromotionRows(),
            controlledHardwareRows: webRTCAEC3AcceptedControlledHardwareRows(),
            licenseReady: true,
            packagingReady: true,
            signingReady: false
        )

        XCTAssertEqual(licenseBlocked.primaryOutcome, .blockedStability)
        XCTAssertEqual(licenseBlocked.failureReason, WebRTCAEC3FailureReason.licenseBlocked.rawValue)
        XCTAssertEqual(packagingBlocked.primaryOutcome, .blockedStability)
        XCTAssertEqual(packagingBlocked.failureReason, WebRTCAEC3FailureReason.packagingBlocked.rawValue)
        XCTAssertEqual(signingBlocked.primaryOutcome, .blockedStability)
        XCTAssertEqual(signingBlocked.failureReason, WebRTCAEC3FailureReason.signingBlocked.rawValue)
    }

    func testDecisionRecordIsMetadataOnlyAndNamesSingleOutcome() {
        let service = WebRTCAEC3EvaluationService(clock: { Date(timeIntervalSince1970: 400) })
        let decision = WebRTCAEC3DecisionRecord(
            candidateId: "aec3-candidate-001",
            primaryOutcome: .deferToFallbackDecision,
            validationRows: [],
            nextStepRecommendation: .fallbackDecision,
            failureReason: WebRTCAEC3FailureReason.corpusIncomplete.rawValue
        )

        let record = service.decisionRecord(decision)

        XCTAssertEqual(record["feature"], "039-webrtc-aec3-speakerphone-spike")
        XCTAssertEqual(record["primaryOutcome"], "defer_to_fallback_decision")
        XCTAssertEqual(record["primaryOutcomeCount"], "1")
        XCTAssertEqual(record["candidateId"], "aec3-candidate-001")
        XCTAssertEqual(record["canClaimCleanBuiltInSpeakerphone"], "false")
        XCTAssertNil(record["rawAudio"])
        XCTAssertNil(record["transcriptText"])
        XCTAssertNil(record["signedUrl"])
        XCTAssertNil(record["privateLocalPath"])
    }

    func testRollbackEventRestoresOriginalTruthAndDecisionRemovesCleanClaim() throws {
        let service = WebRTCAEC3EvaluationService(clock: { Date(timeIntervalSince1970: 700) })

        let event = service.rollbackEvent(
            candidateId: "aec3-candidate-rollback",
            trigger: .referenceUnsafe
        )
        let decision = service.rollbackDecision(
            candidateId: "aec3-candidate-rollback",
            trigger: .referenceUnsafe
        )
        let row = try XCTUnwrap(decision.validationRows.first)

        XCTAssertTrue(event.restoresOriginalTruth)
        XCTAssertEqual(event.previousLineageStatus, .promotedBuiltinRoute)
        XCTAssertEqual(event.restoredLineageStatus, .originalOnly)
        XCTAssertTrue(event.cleanRecordingClaimRemoved)
        XCTAssertEqual(decision.primaryOutcome, .blockedStability)
        XCTAssertEqual(decision.nextStepRecommendation, .fallbackDecision)
        XCTAssertEqual(decision.failureReason, WebRTCAEC3FailureReason.referenceNotRepresentative.rawValue)
        XCTAssertFalse(decision.canClaimCleanBuiltInSpeakerphone)
        XCTAssertEqual(decision.rollbackEvents?.first, event)
        XCTAssertEqual(row.scenarioFamily, .rollback)
        XCTAssertEqual(row.validationKind, .rollback)
        XCTAssertEqual(row.lineageStatus, .rolledBackToOriginal)
        XCTAssertEqual(row.appStatusState, .rolledBackToOriginal)
        XCTAssertEqual(row.thresholdSummary, "rollback_restored_original_truth")
    }

    func testFinalDecisionSelectsExactlyOneOutcomeAndNamesFallback040WhenNotAccepted() {
        let service = WebRTCAEC3EvaluationService(clock: { Date(timeIntervalSince1970: 800) })
        let candidate = webRTCAEC3AcceptedCandidate()

        let accepted = service.finalDecision(
            candidate: candidate,
            corpus: webRTCAEC3AcceptedCorpus(),
            validationRows: webRTCAEC3AcceptedPromotionRows(),
            controlledHardwareRows: webRTCAEC3AcceptedControlledHardwareRows(),
            licenseReady: true,
            packagingReady: true,
            signingReady: true
        )
        let fallback = service.finalDecision(
            candidate: candidate,
            corpus: webRTCAEC3AcceptedCorpus(),
            validationRows: webRTCAEC3AcceptedPromotionRows(),
            controlledHardwareRows: [],
            licenseReady: true,
            packagingReady: true,
            signingReady: true
        )

        XCTAssertEqual(accepted.primaryOutcomeCount, 1)
        XCTAssertEqual(accepted.primaryOutcome, .acceptedForImmediatePromotion)
        XCTAssertEqual(accepted.nextStepRecommendation, .promoteBuiltInRoute)
        XCTAssertNil(accepted.fallbackFeatureId)
        XCTAssertFalse(accepted.requiresFallbackPlanning)
        XCTAssertTrue(accepted.decisionLimitations.contains("promotion_scope_built_in_mac_mic_and_speakers"))

        XCTAssertEqual(fallback.primaryOutcomeCount, 1)
        XCTAssertEqual(fallback.primaryOutcome, .deferToFallbackDecision)
        XCTAssertEqual(fallback.fallbackFeatureId, WebRTCAEC3EvaluationService.fallbackFeatureId)
        XCTAssertTrue(fallback.requiresFallbackPlanning)
        XCTAssertFalse(fallback.canClaimCleanBuiltInSpeakerphone)
        XCTAssertTrue(fallback.decisionLimitations.contains("fallback_required_040"))
    }

    func testSupportingRouteRowsCannotBroadenPromotionScopeOrFillBuiltInGaps() {
        let service = WebRTCAEC3EvaluationService()
        let candidate = webRTCAEC3AcceptedCandidate()
        let supportingRows = webRTCAEC3AcceptedSupportingRouteRows()

        let decision = service.finalDecision(
            candidate: candidate,
            corpus: webRTCAEC3AcceptedCorpus(),
            validationRows: [],
            supportingRouteRows: supportingRows,
            controlledHardwareRows: [],
            licenseReady: true,
            packagingReady: true,
            signingReady: true
        )
        let record = service.decisionRecord(decision)

        XCTAssertEqual(decision.primaryOutcome, .deferToFallbackDecision)
        XCTAssertEqual(decision.supportingRouteRows?.count, supportingRows.count)
        XCTAssertFalse(decision.supportingRoutesCanBroadenPromotionScope)
        XCTAssertFalse(decision.canClaimCleanBuiltInSpeakerphone)
        XCTAssertTrue(decision.decisionLimitations.contains("supporting_routes_evidence_only"))
        XCTAssertEqual(record["supportingRouteRowCount"], String(supportingRows.count))
        XCTAssertEqual(record["supportingRoutesCanBroadenPromotionScope"], "false")
        XCTAssertEqual(record["fallbackFeatureId"], WebRTCAEC3EvaluationService.fallbackFeatureId)
    }
}

private func webRTCAEC3AcceptedCandidate() -> WebRTCAEC3Candidate {
    WebRTCAEC3Candidate(
        candidateId: "aec3-candidate-001",
        candidateKind: .nativeWebRTCAEC3,
        routeClass: .builtInSpeakerphone,
        promotionScope: .builtInMacMicAndSpeakers,
        dependencyReadiness: .ready,
        renderReferenceStatus: .present,
        captureTimingStatus: .safe,
        metricsStatus: .available,
        thresholdProfileId: WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId,
        diagnosticSafe: true
    )
}

private func webRTCAEC3AcceptedCorpus() -> WebRTCAEC3ValidationCorpus {
    WebRTCAEC3ValidationCorpus(
        corpusId: "metadata-lab-corpus-v1",
        thresholdProfileId: WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId,
        diagnosticSafe: true,
        roomConditionCount: 2,
        deviceProfileCount: 2,
        speakerVolumeLevelCount: 3,
        scenarioFamilies: WebRTCAEC3ScenarioFamily.immediatePromotionRequired.map {
            WebRTCAEC3CorpusScenario(
                scenarioFamily: $0,
                fileCount: 10,
                sliceCountPerFile: 5,
                fullFileValidationCount: 10,
                longFormFullFileRunCount: 2,
                criticalGateFailures: 0
            )
        }
    )
}

private func webRTCAEC3AcceptedPromotionRows() -> [WebRTCAEC3ValidationRow] {
    WebRTCAEC3ScenarioFamily.immediatePromotionRequired.map {
        WebRTCAEC3ValidationRow.acceptedFixture(
            scenarioFamily: $0,
            validationKind: .fullFile,
            thresholdProfileId: WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId
        )
    } + [.stopQuit, .diagnostics, .appStatus, .rollback].map {
        WebRTCAEC3ValidationRow.acceptedFixture(
            scenarioFamily: $0,
            validationKind: $0 == .appStatus ? .appStatus : .controlledRealHardware,
            thresholdProfileId: WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId
        )
    }
}

private func webRTCAEC3AcceptedControlledHardwareRows() -> [ControlledRealHardwareRecordingEvidence] {
    [
        .farEndOnlyLeakage,
        .nearEndOnlySpeech,
        .doubleTalk,
        .loudSpeakerClipping,
        .routeChangeTimingStress,
        .unsafeReferenceNegativeControl,
        .stopQuit,
        .diagnostics,
        .appStatus,
        .rollback
    ].map {
        ControlledRealHardwareRecordingEvidence(
            recordingEvidenceId: "hardware-\($0.rawValue)",
            candidateId: "aec3-candidate-001",
            routeClass: .builtInSpeakerphone,
            scenarioFamily: $0,
            packageLineageStatus: $0 == .rollback ? .rolledBackToOriginal : .promotedBuiltinRoute,
            stopBehaviorStatus: .accepted,
            appStatusShown: true,
            thresholdProfileId: WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId,
            diagnosticSafe: true
        )
    }
}

private func webRTCAEC3AcceptedSupportingRouteRows() -> [WebRTCAEC3ValidationRow] {
    [
        (.wiredHeadphones, WebRTCAEC3ScenarioFamily.farEndOnlyLeakage),
        (.usbHeadset, WebRTCAEC3ScenarioFamily.nearEndOnlySpeech),
        (.bluetoothAirPodsClass, WebRTCAEC3ScenarioFamily.doubleTalk),
        (.browserTargetSupporting, WebRTCAEC3ScenarioFamily.routeChangeTimingStress)
    ].map { routeClass, scenarioFamily in
        WebRTCAEC3ValidationRow(
            rowId: "aec3-supporting-\(routeClass.rawValue)-\(scenarioFamily.rawValue)",
            candidateId: "aec3-candidate-001",
            scenarioFamily: scenarioFamily,
            validationKind: .controlledRealHardware,
            routeClass: routeClass,
            baselineStatus: .leakageDetected,
            candidateStatus: .accepted,
            lineageStatus: .guidanceOnly,
            speechPreservationStatus: .preserved,
            residualLeakageStatus: .clean,
            timingConfidence: .safe,
            referenceStatus: .present,
            stabilityStatus: .accepted,
            thresholdProfileId: WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId,
            thresholdSummary: "supporting_route_evidence_only",
            appStatusState: .fallbackRelevant,
            diagnosticSafe: true
        )
    }
}
#endif
