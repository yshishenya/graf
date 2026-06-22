import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class WebRTCAEC3ModelsTests: XCTestCase {
    func testCandidateRequiresBuiltInRouteReadyDependencyAndSafeThresholdProfileForPromotion() {
        let candidate = WebRTCAEC3Candidate(
            candidateId: "aec3-candidate-001",
            candidateKind: .nativeWebRTCAEC3,
            routeClass: .builtInSpeakerphone,
            promotionScope: .builtInMacMicAndSpeakers,
            dependencyReadiness: .ready,
            renderReferenceStatus: .present,
            captureTimingStatus: .safe,
            metricsStatus: .available,
            thresholdProfileId: "aec3-threshold-profile-v1",
            diagnosticSafe: true
        )
        let supportingRoute = WebRTCAEC3Candidate(
            candidateId: "aec3-candidate-usb",
            candidateKind: .nativeWebRTCAEC3,
            routeClass: .usbHeadset,
            promotionScope: .notPromotable,
            dependencyReadiness: .ready,
            renderReferenceStatus: .present,
            captureTimingStatus: .safe,
            metricsStatus: .available,
            thresholdProfileId: "aec3-threshold-profile-v1",
            diagnosticSafe: true
        )

        XCTAssertTrue(candidate.isEligibleForImmediatePromotion)
        XCTAssertFalse(supportingRoute.isEligibleForImmediatePromotion)
        XCTAssertEqual(candidate.feature, "039-webrtc-aec3-speakerphone-spike")
    }

    func testThresholdProfileChangeInvalidatesPromotionEvidence() {
        let profile = WebRTCAEC3AcceptanceThresholdProfile.standardV1
        let row = WebRTCAEC3ValidationRow.acceptedFixture(
            scenarioFamily: .farEndOnlyLeakage,
            validationKind: .fullFile,
            thresholdProfileId: profile.thresholdProfileId
        )
        let mismatched = WebRTCAEC3ValidationRow.acceptedFixture(
            scenarioFamily: .farEndOnlyLeakage,
            validationKind: .fullFile,
            thresholdProfileId: "aec3-threshold-profile-old"
        )

        XCTAssertTrue(row.usesThresholdProfile(profile))
        XCTAssertFalse(mismatched.usesThresholdProfile(profile))
        XCTAssertEqual(mismatched.promotionBlockingReason(expectedProfile: profile), "threshold_profile_mismatch")
    }

    func testCleanClaimRequiresOperationalStatusRollbackAndDiagnosticsRows() {
        let rows = WebRTCAEC3ScenarioFamily.immediatePromotionRequired.map {
            WebRTCAEC3ValidationRow.acceptedFixture(
                scenarioFamily: $0,
                validationKind: .fullFile,
                thresholdProfileId: WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId
            )
        }
        let decision = WebRTCAEC3DecisionRecord(
            candidateId: "aec3-candidate-001",
            primaryOutcome: .acceptedForImmediatePromotion,
            validationRows: rows,
            nextStepRecommendation: .promoteBuiltInRoute
        )

        XCTAssertFalse(decision.canClaimCleanBuiltInSpeakerphone)
    }

    func testThresholdProfileRejectsUnsafeDiagnosticSummaries() {
        let unsafe = WebRTCAEC3AcceptanceThresholdProfile(
            thresholdProfileId: "aec3-threshold-profile-unsafe",
            residualLeakageGate: "/Users/private/rawAudio.wav",
            speechPreservationGate: "near_end_speech_preserved",
            doubleTalkGate: "double_talk_preserved",
            timingDriftGate: "timing_safe",
            clippingDropoutGate: "clipping_blocks",
            cpuNoHangGate: "cpu_safe",
            stopQuitGate: "stop_safe",
            diagnosticSafetyGate: "metadata_only",
            appStatusConsistencyGate: "status_matches_truth",
            rollbackTriggerGate: "rollback_restores_original",
            declaredBeforeValidation: true
        )

        XCTAssertFalse(unsafe.canSupportPromotion)
    }
}
#endif
