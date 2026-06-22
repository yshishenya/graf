import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class WebRTCAEC3ValidationCorpusTests: XCTestCase {
    func testLabGradeCorpusFixtureSatisfiesImmediatePromotionCoverageCounts() throws {
        let url = try XCTUnwrap(webRTCAEC3FixtureURL("lab-grade-corpus.json"))
        let data = try Data(contentsOf: url)
        let corpus = try JSONDecoder().decode(WebRTCAEC3ValidationCorpus.self, from: data)

        XCTAssertTrue(corpus.isEligibleForImmediatePromotion)
        XCTAssertEqual(corpus.requiredScenarioFamiliesMissing, [])
        XCTAssertEqual(corpus.totalFullFileValidations, 60)
        XCTAssertEqual(corpus.totalSlicedWindowValidations, 300)
        XCTAssertEqual(corpus.longFormRunCountByScenario.values.min(), 2)
        XCTAssertEqual(corpus.promotionCoverageFailures, [])
    }

    func testInvalidCorpusCasesNameEveryPromotionBlocker() throws {
        let url = try XCTUnwrap(webRTCAEC3FixtureURL("invalid-corpus-cases.json"))
        let data = try Data(contentsOf: url)
        let cases = try JSONDecoder().decode(WebRTCAEC3InvalidCorpusCases.self, from: data)

        XCTAssertEqual(cases.caseIds.sorted(), [
            "missing-device-coverage",
            "missing-files",
            "missing-full-files",
            "missing-long-form",
            "missing-room-coverage",
            "missing-slices",
            "missing-volume-coverage",
            "threshold-profile-mismatch"
        ])
        XCTAssertEqual(
            cases.promotionBlockers.sorted(),
            [
                "device_profile_count_below_minimum",
                "file_count_below_minimum",
                "full_file_validation_count_below_minimum",
                "long_form_full_file_run_count_below_minimum",
                "room_condition_count_below_minimum",
                "slice_count_below_minimum",
                "speaker_volume_level_count_below_minimum",
                "threshold_profile_mismatch"
            ]
        )
    }

    func testControlledRealHardwareFixtureRequiresCriticalRowsAndKeepsSupportingRoutesScoped() throws {
        let url = try XCTUnwrap(webRTCAEC3FixtureURL("controlled-real-hardware.json"))
        let data = try Data(contentsOf: url)
        let matrix = try JSONDecoder().decode(WebRTCAEC3ControlledHardwareMatrix.self, from: data)

        XCTAssertTrue(matrix.hasAllImmediatePromotionCriticalRows)
        XCTAssertEqual(matrix.criticalRows.count, 10)
        XCTAssertEqual(matrix.supportingRouteRows.count, 4)
        XCTAssertFalse(matrix.supportingRoutesCanBroadenPromotionScope)
        XCTAssertTrue(matrix.isMetadataOnly)
    }

    func testDecisionSummaryRecordIsMetadataOnlyAndPointsToFallback040() {
        let service = WebRTCAEC3EvaluationService(clock: { Date(timeIntervalSince1970: 900) })
        let decision = WebRTCAEC3DecisionRecord(
            candidateId: "aec3-summary-fallback",
            primaryOutcome: .deferToFallbackDecision,
            validationRows: [],
            nextStepRecommendation: .fallbackDecision,
            supportingRouteRows: [],
            limitations: ["fallback_required_040", "promotion_scope_built_in_mac_mic_and_speakers"],
            fallbackFeatureId: WebRTCAEC3EvaluationService.fallbackFeatureId,
            failureReason: WebRTCAEC3FailureReason.controlledHardwareMissing.rawValue
        )

        let record = service.decisionRecord(decision)

        XCTAssertEqual(record["primaryOutcomeCount"], "1")
        XCTAssertEqual(record["fallbackFeatureId"], WebRTCAEC3EvaluationService.fallbackFeatureId)
        XCTAssertEqual(record["requiresFallbackPlanning"], "true")
        XCTAssertEqual(record["limitations"], "fallback_required_040,promotion_scope_built_in_mac_mic_and_speakers")
        XCTAssertEqual(record["supportingRoutesCanBroadenPromotionScope"], "false")
        XCTAssertNil(record["rawAudio"])
        XCTAssertNil(record["transcriptText"])
        XCTAssertNil(record["signedUrl"])
        XCTAssertNil(record["privateLocalPath"])
    }
}

private func webRTCAEC3FixtureURL(_ fileName: String) -> URL? {
    let current = URL(fileURLWithPath: #filePath)
    let candidates = sequence(first: current.deletingLastPathComponent()) { directory in
        let parent = directory.deletingLastPathComponent()
        return parent.path == directory.path ? nil : parent
    }
    return candidates
        .map { $0.appendingPathComponent("Fixtures/WebRTCAEC3/\(fileName)") }
        .first { FileManager.default.fileExists(atPath: $0.path) }
}
#endif
