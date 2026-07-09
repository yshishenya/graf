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

    func testTargetScopedAutoRecordStillPromptsWhenTargetIsUnchecked() {
        let action = MeetingDetectionPolicy().action(
            for: MeetingDetectionCandidateDecision(
                kind: .knownTarget(targetID: "yandex_telemost", mode: .promptEnabled),
                candidateScore: 0
            ),
            settings: MeetingDetectionSettingsSnapshot(
                detectionMode: .detectAndAsk,
                targetScopedAutoRecordEnabled: true,
                autoRecordTargetIds: ["zoom"]
            ),
            prerequisites: MeetingDetectionCapturePrerequisites()
        )

        XCTAssertEqual(action, .prompt(targetID: "yandex_telemost"))
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

        XCTAssertEqual(action, .suppress(reason: "one_action_stop_unavailable"))
    }

    func testRecordingPrerequisiteBlocksPromptWhenWorkspacePolicyDisallowsRecording() {
        let prerequisite = RecordingPrerequisiteGate().evaluate(recordingPrerequisite(policyAllowsRecording: false))
        let action = MeetingDetectionPolicy().action(
            for: MeetingDetectionCandidateDecision(
                kind: .knownTarget(targetID: "zoom", mode: .promptEnabled),
                candidateScore: 0
            ),
            settings: MeetingDetectionSettingsSnapshot(detectionMode: .detectAndAsk),
            prerequisites: MeetingDetectionCapturePrerequisites(recordingPrerequisite: prerequisite)
        )

        XCTAssertEqual(action, .suppress(reason: RecordingStartBlocker.policyDisabled.rawValue))
    }

    func testRecordingPrerequisiteBlocksAutoRecordEvenAfterTargetOptIn() {
        let prerequisite = RecordingPrerequisiteGate().evaluate(recordingPrerequisite(storageRisk: .critical))
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
            prerequisites: MeetingDetectionCapturePrerequisites(recordingPrerequisite: prerequisite)
        )

        XCTAssertEqual(action, .suppress(reason: RecordingStartBlocker.storageUnsafe.rawValue))
    }

    func testLogStreamPredicateCoversAudioHALAndSensorIndicators() {
        let configuration = MacOSAudioOwnershipLogStreamConfiguration()
        let predicate = configuration.arguments.last ?? ""

        XCTAssertTrue(predicate.contains("AudioHAL"))
        XCTAssertTrue(predicate.contains("runningboardd"))
        XCTAssertTrue(predicate.contains("sensor-indicators"))
        XCTAssertTrue(predicate.contains("Active activity attributions changed"))
        XCTAssertFalse(predicate.hasPrefix("eventMessage CONTAINS"))
    }

    func testLogStreamConvertsSensorIndicatorMicDiffsToOwnershipEvents() {
        let parser = MacOSAudioOwnershipParser()
        let observedAt = Date(timeIntervalSince1970: 200)
        var activeBundles: Set<String> = []

        let startEvents = MacOSAudioOwnershipLogStream.events(
            from: #"ControlCenter [com.apple.controlcenter:sensor-indicators] Active activity attributions changed to ["mic:ai.krisp.krispMac", "mic:ru.yandex.desktop.telemost"]"#,
            parser: parser,
            activeSensorMicBundleIDs: &activeBundles,
            observedAt: observedAt
        )
        let endEvents = MacOSAudioOwnershipLogStream.events(
            from: #"ControlCenter [com.apple.controlcenter:sensor-indicators] Active activity attributions changed to ["mic:ai.krisp.krispMac"]"#,
            parser: parser,
            activeSensorMicBundleIDs: &activeBundles,
            observedAt: observedAt
        )

        XCTAssertEqual(
            startEvents,
            [
                MacOSAudioOwnershipEvent(bundleID: "ai.krisp.krispMac", state: .active, observedAt: observedAt),
                MacOSAudioOwnershipEvent(bundleID: "ru.yandex.desktop.telemost", state: .active, observedAt: observedAt)
            ]
        )
        XCTAssertEqual(
            endEvents,
            [MacOSAudioOwnershipEvent(bundleID: "ru.yandex.desktop.telemost", state: .inactive, observedAt: observedAt)]
        )
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

    private func recordingPrerequisite(
        policyAllowsRecording: Bool = true,
        storageRisk: LocalBufferRiskState = .healthy
    ) -> RecordingPrerequisiteSnapshot {
        RecordingPrerequisiteSnapshot(
            routeState: .inactive,
            routeEvidenceKind: .systemAudioCapture,
            policyAllowsRecording: policyAllowsRecording,
            microphonePermissionGranted: true,
            storageRisk: storageRisk,
            indicatorAvailable: true,
            sourceAppEligibility: .eligible,
            evaluatedAt: Date(timeIntervalSince1970: 1_779_887_120)
        )
    }

    private static func registry() throws -> MeetingTargetRegistryDocument {
        try MeetingDetectionCoding.decoder().decode(
            MeetingTargetRegistryDocument.self,
            from: MeetingTargetRegistryTests.seedRegistryData()
        )
    }
}
#endif
