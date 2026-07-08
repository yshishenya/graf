import Foundation
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class MeetingDetectionPolicyTests: XCTestCase {
    func testPromptEnabledKnownTargetCanPromptWhenCaptureGateIsReady() {
        let action = MeetingDetectionPolicy().action(
            for: MeetingDetectionCandidateDecision(
                kind: .knownTarget(targetID: "yandex_telemost", mode: .promptEnabled),
                candidateScore: 0
            ),
            settings: MeetingDetectionSettingsSnapshot(detectionMode: .detectAndAsk),
            prerequisites: MeetingDetectionCapturePrerequisites()
        )

        XCTAssertEqual(action, .prompt(targetID: "yandex_telemost"))
    }

    func testTargetScopedAutoRecordRequiresExplicitTargetOptIn() {
        let action = MeetingDetectionPolicy().action(
            for: MeetingDetectionCandidateDecision(
                kind: .knownTarget(targetID: "yandex_telemost", mode: .promptEnabled),
                candidateScore: 0
            ),
            settings: MeetingDetectionSettingsSnapshot(
                detectionMode: .detectAndAsk,
                targetScopedAutoRecordEnabled: true,
                autoRecordTargetIds: ["yandex_telemost"]
            ),
            prerequisites: MeetingDetectionCapturePrerequisites()
        )

        XCTAssertEqual(action, .autoRecord(targetID: "yandex_telemost"))
    }

    func testDetectOnlyModeNeverPromptsOrAutoRecords() {
        let action = MeetingDetectionPolicy().action(
            for: MeetingDetectionCandidateDecision(
                kind: .knownTarget(targetID: "zoom", mode: .promptEnabled),
                candidateScore: 0
            ),
            settings: MeetingDetectionSettingsSnapshot(
                detectionMode: .detectOnly,
                targetScopedAutoRecordEnabled: true,
                autoRecordTargetIds: ["zoom"]
            ),
            prerequisites: MeetingDetectionCapturePrerequisites()
        )

        XCTAssertEqual(action, .detectOnly(targetID: "zoom"))
    }

    func testUnknownCandidateNeverPrompts() {
        let action = MeetingDetectionPolicy().action(
            for: MeetingDetectionCandidateDecision(
                kind: .candidateUpload,
                candidateScore: 8,
                candidateReasons: [.stableMicDuration, .vksNameToken]
            ),
            settings: MeetingDetectionSettingsSnapshot(detectionMode: .detectAndAsk),
            prerequisites: MeetingDetectionCapturePrerequisites()
        )

        XCTAssertEqual(action, .detectOnly(targetID: nil))
    }

    func testUnsupportedBrowserMetadataStatesRemainManualOnly() {
        let action = MeetingDetectionPolicy().action(
            for: BrowserMeetingTargetEvaluation(
                kind: .manualOnly(targetID: "google_meet_web", reason: "unsupported_browser_metadata"),
                serviceFamily: "google_meet",
                signals: [.browserMetadata]
            ),
            settings: MeetingDetectionSettingsSnapshot(detectionMode: .detectAndAsk),
            prerequisites: MeetingDetectionCapturePrerequisites()
        )

        XCTAssertEqual(action, .detectOnly(targetID: "google_meet_web"))
    }

    func testDisabledModeSuppressesBrowserEvaluation() {
        let action = MeetingDetectionPolicy().action(
            for: BrowserMeetingTargetEvaluation(
                kind: .manualOnly(targetID: "google_meet_web", reason: "unsupported_browser_metadata"),
                serviceFamily: "google_meet",
                signals: [.browserMetadata]
            ),
            settings: MeetingDetectionSettingsSnapshot(detectionMode: .disabled),
            prerequisites: MeetingDetectionCapturePrerequisites()
        )

        XCTAssertEqual(action, .suppress(reason: "detection_disabled"))
    }

    func testSafeBrowserJoinedTargetPromptsThroughExistingCaptureGates() {
        let action = MeetingDetectionPolicy().action(
            for: BrowserMeetingTargetEvaluation(
                kind: .safeJoinedTarget(targetID: "yandex_telemost_web", mode: .promptEnabled),
                serviceFamily: "yandex_telemost",
                signals: [.browserMetadata, .calendarOrJoinIntent]
            ),
            settings: MeetingDetectionSettingsSnapshot(detectionMode: .detectAndAsk),
            prerequisites: MeetingDetectionCapturePrerequisites()
        )

        XCTAssertEqual(action, .prompt(targetID: "yandex_telemost_web"))
    }

    func testCaptureGateBlocksPromptWhenVisibleStopWouldNotBeAvailable() {
        let action = MeetingDetectionPolicy().action(
            for: MeetingDetectionCandidateDecision(
                kind: .knownTarget(targetID: "zoom", mode: .promptEnabled),
                candidateScore: 0
            ),
            settings: MeetingDetectionSettingsSnapshot(detectionMode: .detectAndAsk),
            prerequisites: MeetingDetectionCapturePrerequisites(oneActionStopAvailable: false)
        )

        XCTAssertEqual(action, .suppress(reason: "capture_prerequisite_blocked"))
    }

    func testDetectorDebouncesKnownTargetBeforePrompt() throws {
        let registry = try MeetingDetectionPolicyTests.registry()
        let detector = MacOSMeetingActivityDetector(debounceSeconds: 5)
        let event = MacOSAudioOwnershipEvent(
            bundleID: "ru.yandex.desktop.telemost",
            displayName: "Yandex Telemost",
            state: .active,
            observedAt: Date(timeIntervalSince1970: 100)
        )

        XCTAssertTrue(detector.handle(event: event, registry: registry, settings: MeetingDetectionSettings()).isEmpty)
        XCTAssertTrue(detector.advance(now: Date(timeIntervalSince1970: 104), registry: registry, settings: MeetingDetectionSettings()).isEmpty)
        XCTAssertEqual(
            detector.advance(now: Date(timeIntervalSince1970: 106), registry: registry, settings: MeetingDetectionSettings()),
            [.promptEligible(targetID: "yandex_telemost", bundleID: "ru.yandex.desktop.telemost")]
        )
        XCTAssertEqual(
            detector.handle(
                event: MacOSAudioOwnershipEvent(
                    bundleID: "ru.yandex.desktop.telemost",
                    state: .inactive,
                    observedAt: Date(timeIntervalSince1970: 110)
                ),
                registry: registry,
                settings: MeetingDetectionSettings()
            ),
            []
        )
        XCTAssertEqual(
            detector.advance(now: Date(timeIntervalSince1970: 124), registry: registry, settings: MeetingDetectionSettings()),
            []
        )
        XCTAssertEqual(
            detector.advance(now: Date(timeIntervalSince1970: 125), registry: registry, settings: MeetingDetectionSettings()),
            [.ended(bundleID: "ru.yandex.desktop.telemost")]
        )
    }

    func testDetectorSuppressesBrowserAndKrispAttribution() throws {
        let registry = try MeetingDetectionPolicyTests.registry()
        let detector = MacOSMeetingActivityDetector(debounceSeconds: 1)

        _ = detector.handle(
            event: MacOSAudioOwnershipEvent(
                bundleID: "com.google.Chrome",
                displayName: "Chrome",
                state: .active,
                observedAt: Date(timeIntervalSince1970: 100)
            ),
            registry: registry,
            settings: MeetingDetectionSettings()
        )
        _ = detector.handle(
            event: MacOSAudioOwnershipEvent(
                bundleID: "ai.krisp.mac",
                displayName: "Krisp",
                state: .active,
                observedAt: Date(timeIntervalSince1970: 100)
            ),
            registry: registry,
            settings: MeetingDetectionSettings()
        )
        let outputs = detector.advance(now: Date(timeIntervalSince1970: 102), registry: registry, settings: MeetingDetectionSettings())

        XCTAssertTrue(outputs.contains(.suppressed(bundleID: "com.google.Chrome", reason: "browser_bundle")))
        XCTAssertTrue(outputs.contains(.suppressed(bundleID: "ai.krisp.mac", reason: "audio_utility")))
    }

    func testDetectorReevaluatesUnknownCandidateAfterShortDuration() throws {
        let registry = try MeetingDetectionPolicyTests.registry()
        let detector = MacOSMeetingActivityDetector(debounceSeconds: 5)

        _ = detector.handle(
            event: MacOSAudioOwnershipEvent(
                bundleID: "ru.yandex.futuremeet",
                displayName: "Yandex Future Meet",
                state: .active,
                observedAt: Date(timeIntervalSince1970: 100)
            ),
            registry: registry,
            settings: MeetingDetectionSettings()
        )

        XCTAssertTrue(
            detector.advance(now: Date(timeIntervalSince1970: 106), registry: registry, settings: MeetingDetectionSettings()).isEmpty
        )
        let outputs = detector.advance(
            now: Date(timeIntervalSince1970: 131),
            registry: registry,
            settings: MeetingDetectionSettings()
        )

        guard case .candidateObserved(
            bundleID: let bundleID,
            score: let score,
            observation: _,
            decision: _
        ) = try XCTUnwrap(outputs.first) else {
            XCTFail("Expected candidate observation after duration threshold")
            return
        }
        XCTAssertEqual(bundleID, "ru.yandex.futuremeet")
        XCTAssertGreaterThanOrEqual(score, 5)
    }

    private static func registry() throws -> MeetingTargetRegistryDocument {
        try MeetingDetectionCoding.decoder().decode(
            MeetingTargetRegistryDocument.self,
            from: MeetingTargetRegistryTests.seedRegistryData()
        )
    }
}
#endif
