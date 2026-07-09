import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class MeetingDetectionCandidateFilterTests: XCTestCase {
    func testKnownRegistryTargetDoesNotUploadUnknownIdentity() throws {
        let registry = try Self.registry()
        let decision = MeetingDetectionCandidateFilter().evaluate(
            observation: MeetingDetectionAppObservation(
                bundleID: "ru.yandex.desktop.telemost",
                displayName: "Yandex Telemost",
                stableObservationCount: 3,
                activeDurationSeconds: 600
            ),
            registry: registry
        )

        XCTAssertEqual(decision.kind, .knownTarget(targetID: "yandex_telemost", mode: .promptEnabled))
        XCTAssertFalse(decision.shouldUploadCandidateIdentity)
    }

    func testHighScoreRussianVKSLikeAppIsEligibleForCandidateUpload() throws {
        let decision = MeetingDetectionCandidateFilter().evaluate(
            observation: MeetingDetectionAppObservation(
                bundleID: "ru.trueconf.client",
                displayName: "TrueConf Meeting",
                signingTeamID: "ABCDE12345",
                version: "1.0.0",
                stableObservationCount: 4,
                activeDurationSeconds: 900,
                manualRecordNearbyCount: 1,
                calendarOrJoinHintCount: 1
            ),
            registry: try Self.registry()
        )

        XCTAssertEqual(decision.kind, .candidateUpload)
        XCTAssertTrue(decision.shouldUploadCandidateIdentity)
        XCTAssertGreaterThanOrEqual(decision.candidateScore, 5)
        XCTAssertTrue(decision.candidateReasons.contains(.vksNameToken))
        XCTAssertTrue(decision.candidateReasons.contains(.calendarOrJoinHint))
    }

    func testLowScoreAppIsSuppressedBeforeIdentityUpload() throws {
        let decision = MeetingDetectionCandidateFilter().evaluate(
            observation: MeetingDetectionAppObservation(
                bundleID: "com.example.notes",
                displayName: "Notes Helper",
                stableObservationCount: 1,
                activeDurationSeconds: 45
            ),
            registry: try Self.registry()
        )

        XCTAssertEqual(decision.kind, .suppressed)
        XCTAssertFalse(decision.shouldUploadCandidateIdentity)
        XCTAssertEqual(decision.suppressionReasons, [.lowScore])
    }

    func testNonTargetRuleSuppressesCandidate() throws {
        let registry = try Self.registry(nonTargetRules: [
            MeetingDetectionNonTargetRule(
                platform: .macos,
                ruleKind: .bundleID,
                ruleValue: "ru.example.notvks",
                reasonCode: "admin_marked_non_target"
            )
        ])

        let decision = MeetingDetectionCandidateFilter().evaluate(
            observation: MeetingDetectionAppObservation(
                bundleID: "ru.example.notvks",
                displayName: "Example Meeting",
                stableObservationCount: 5,
                activeDurationSeconds: 900,
                manualRecordNearbyCount: 1,
                calendarOrJoinHintCount: 1
            ),
            registry: registry
        )

        XCTAssertEqual(decision.kind, .suppressed)
        XCTAssertTrue(decision.suppressionReasons.contains(.knownNonTarget))
    }

    func testKrispIsSuppressedAsAudioUtilityWithoutDedicatedTargetRule() throws {
        let decision = MeetingDetectionCandidateFilter().evaluate(
            observation: MeetingDetectionAppObservation(
                bundleID: "ai.krisp.mac",
                displayName: "Krisp",
                stableObservationCount: 5,
                activeDurationSeconds: 900,
                manualRecordNearbyCount: 1,
                calendarOrJoinHintCount: 1
            ),
            registry: try Self.registry()
        )

        XCTAssertEqual(decision.kind, .suppressed)
        XCTAssertTrue(decision.suppressionReasons.contains(.audioUtility))
    }

    func testYandexBrowserAndOperaAreSuppressedAsBrowsers() throws {
        for bundleID in ["ru.yandex.desktop.yandex-browser", "com.operasoftware.Opera"] {
            let decision = MeetingDetectionCandidateFilter().evaluate(
                observation: MeetingDetectionAppObservation(
                    bundleID: bundleID,
                    displayName: "Browser",
                    stableObservationCount: 5,
                    activeDurationSeconds: 900,
                    manualRecordNearbyCount: 1,
                    calendarOrJoinHintCount: 1
                ),
                registry: try Self.registry()
            )

            XCTAssertEqual(decision.kind, .suppressed)
            XCTAssertTrue(decision.suppressionReasons.contains(.browserBundle), bundleID)
        }
    }

    private static func registry(
        nonTargetRules: [MeetingDetectionNonTargetRule] = []
    ) throws -> MeetingTargetRegistryDocument {
        let seed = try MeetingDetectionCoding.decoder().decode(
            MeetingTargetRegistryDocument.self,
            from: MeetingTargetRegistryTests.seedRegistryData()
        )
        return MeetingTargetRegistryDocument(
            registryVersion: seed.registryVersion,
            generatedAt: seed.generatedAt,
            targets: seed.targets,
            nonTargetRules: nonTargetRules
        )
    }
}
#endif
