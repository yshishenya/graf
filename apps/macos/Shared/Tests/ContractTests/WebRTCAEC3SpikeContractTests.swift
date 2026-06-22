import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class WebRTCAEC3SpikeContractTests: XCTestCase {
    func testSpikeResultRequiresThresholdProfileAppStatusAndMetadataOnlyFields() throws {
        let result = WebRTCAEC3ValidationRow.acceptedFixture(
            scenarioFamily: .appStatus,
            validationKind: .appStatus,
            thresholdProfileId: "aec3-threshold-profile-v1"
        )
        let data = try JSONEncoder().encode(result)
        let object = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        let json = String(decoding: data, as: UTF8.self)

        XCTAssertEqual(object?["feature"] as? String, "039-webrtc-aec3-speakerphone-spike")
        XCTAssertEqual(object?["thresholdProfileId"] as? String, "aec3-threshold-profile-v1")
        XCTAssertEqual(object?["appStatusState"] as? String, WebRTCAEC3AppStatusState.promotedBuiltinRoute.rawValue)
        XCTAssertEqual(object?["diagnosticSafe"] as? Bool, true)
        XCTAssertFalse(json.contains("rawAudio"))
        XCTAssertFalse(json.contains("transcriptText"))
        XCTAssertFalse(json.contains("signedUrl"))
        XCTAssertFalse(json.contains("privateLocalPath"))
    }

    func testDecisionRecordContractRequiresReadinessScopeAndFailureFields() {
        let service = WebRTCAEC3EvaluationService(clock: { Date(timeIntervalSince1970: 500) })
        let row = WebRTCAEC3ValidationRow(
            rowId: "aec3-row-blocked",
            candidateId: "aec3-candidate-blocked",
            scenarioFamily: .unsafeReferenceNegativeControl,
            validationKind: .negativeControl,
            routeClass: .builtInSpeakerphone,
            baselineStatus: .unproven,
            candidateStatus: .blocked,
            lineageStatus: .blocked,
            speechPreservationStatus: .unknown,
            residualLeakageStatus: .unproven,
            timingConfidence: .failed,
            referenceStatus: .missing,
            stabilityStatus: .blockedRouteTopology,
            thresholdProfileId: "aec3-threshold-profile-v1",
            thresholdSummary: "fail_closed_reference_missing",
            appStatusState: .candidateBlocked,
            diagnosticSafe: true,
            failureReason: WebRTCAEC3FailureReason.referenceMissing.rawValue
        )
        let decision = WebRTCAEC3DecisionRecord(
            candidateId: "aec3-candidate-blocked",
            primaryOutcome: .blockedRouteTopology,
            validationRows: [row],
            nextStepRecommendation: .fallbackDecision,
            failureReason: WebRTCAEC3FailureReason.referenceMissing.rawValue
        )

        let record = service.decisionRecord(decision)

        XCTAssertEqual(record["routeScope"], WebRTCAEC3PromotionScope.builtInMacMicAndSpeakers.rawValue)
        XCTAssertEqual(record["thresholdProfileId"], "aec3-threshold-profile-v1")
        XCTAssertEqual(record["dependencyReadiness"], "not_recorded")
        XCTAssertEqual(record["failureReason"], WebRTCAEC3FailureReason.referenceMissing.rawValue)
        XCTAssertEqual(record["appStatusState"], WebRTCAEC3AppStatusState.candidateBlocked.rawValue)
    }

    func testLineageContractCoversOriginalCandidatePromotedRollbackUnprovenAndBlockedStates() {
        XCTAssertEqual(
            Set(WebRTCAEC3LineageStatus.allPackageTruthLabels),
            Set([
                .originalOnly,
                .candidateMetadata,
                .derivedCandidate,
                .promotedBuiltinRoute,
                .rolledBackToOriginal,
                .guidanceOnly,
                .unproven,
                .blocked
            ])
        )
    }
}
#endif
