import CoreAudio
import Foundation
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class MeetingDetectionPolicyTests: XCTestCase {
    func testAutomaticRecordingRuleLabelsAndDefaultResolution() {
        XCTAssertEqual(AutomaticRecordingRule.always.displayName, "Всегда")
        XCTAssertEqual(AutomaticRecordingRule.ask.displayName, "Спрашивать")
        XCTAssertEqual(AutomaticRecordingRule.never.displayName, "Никогда")
        XCTAssertEqual(MeetingDetectionSettings().recordingRule(for: "zoom"), .ask)
    }

    func testExplicitTargetRulesRoundTripAndRemainIndependent() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("meeting-settings-rules-\(UUID().uuidString)", isDirectory: true)
        let url = root.appendingPathComponent("settings.json")
        defer { try? FileManager.default.removeItem(at: root) }
        let store = MeetingDetectionSettingsStore(settingsURL: url)

        var settings = MeetingDetectionSettings()
        settings.setRecordingRule(.always, for: "zoom")
        settings.setRecordingRule(.never, for: "yandex_telemost")
        try store.save(settings)

        let loaded = try store.load()
        XCTAssertEqual(loaded.recordingRule(for: "zoom"), .always)
        XCTAssertEqual(loaded.recordingRule(for: "yandex_telemost"), .never)
        XCTAssertEqual(loaded.recordingRule(for: "teams"), .ask)
        XCTAssertEqual(loaded.automaticRecordingRules, ["zoom": .always, "yandex_telemost": .never])
    }

    func testPartialExplicitRuleMapUsesAskForMissingTargets() {
        let settings = MeetingDetectionSettings(
            automaticRecordingRules: ["zoom": .always]
        )

        XCTAssertEqual(settings.recordingRule(for: "zoom"), .always)
        XCTAssertEqual(settings.recordingRule(for: "legacy_target"), .ask)
    }

    func testBulkRuleAssignmentIsAtomicAndIndividualOverrideStaysIndependent() {
        var settings = MeetingDetectionSettings()
        let targets = ["zoom", "teams", "yandex_telemost"]
        for target in targets {
            settings.setRecordingRule(.never, for: target)
        }
        XCTAssertEqual(targets.map { settings.recordingRule(for: $0) }, [.never, .never, .never])

        settings.setRecordingRule(.always, for: "teams")
        XCTAssertEqual(settings.recordingRule(for: "zoom"), .never)
        XCTAssertEqual(settings.recordingRule(for: "teams"), .always)
        XCTAssertEqual(settings.recordingRule(for: "yandex_telemost"), .never)
    }

    func testLegacyTargetSelectionMigratesToAskWithoutGlobalPermission() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("meeting-settings-rule-migration-\(UUID().uuidString)", isDirectory: true)
        let url = root.appendingPathComponent("settings.json")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        try Data(
            """
            {
              "detectionMode": "detect_and_ask",
              "uploadMode": "automatic_candidate_upload",
              "unknownIdentityUploadAllowed": true,
              "targetScopedAutoRecordEnabled": true,
              "autoRecordTargetIds": ["zoom"]
            }
            """.utf8
        ).write(to: url)

        let loaded = try MeetingDetectionSettingsStore(settingsURL: url).load()
        XCTAssertEqual(loaded.recordingRule(for: "zoom"), .ask)
        XCTAssertEqual(loaded.recordingRule(for: "teams"), .ask)
    }

    func testDefaultsAddEveryNewTargetAsAskAndPreserveExplicitRules() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("meeting-settings-defaults-\(UUID().uuidString)", isDirectory: true)
        let url = root.appendingPathComponent("settings.json")
        defer { try? FileManager.default.removeItem(at: root) }
        let store = MeetingDetectionSettingsStore(settingsURL: url)

        let applied = try XCTUnwrap(
            store.applyFirstInstallDefaults(targetIDs: ["zoom", "yandex_telemost"])
        )
        XCTAssertEqual(applied.recordingRule(for: "zoom"), .ask)
        XCTAssertEqual(applied.recordingRule(for: "yandex_telemost"), .ask)
        let withNewTarget = try XCTUnwrap(store.applyFirstInstallDefaults(targetIDs: ["teams"]))
        XCTAssertEqual(withNewTarget.recordingRule(for: "teams"), .ask)

        var edited = try store.load()
        edited.setRecordingRule(.always, for: "zoom")
        try store.save(edited)
        XCTAssertNil(try store.applyFirstInstallDefaults(targetIDs: ["zoom", "teams"]))
        XCTAssertEqual(try store.load().recordingRule(for: "zoom"), .always)
    }

    func testLegacySettingsWithoutRulesReceiveSafeAskDefaults() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("meeting-settings-legacy-\(UUID().uuidString)", isDirectory: true)
        let url = root.appendingPathComponent("settings.json")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        try Data(
            """
            {
              "detectionMode": "detect_only",
              "uploadMode": "automatic_candidate_upload",
              "unknownIdentityUploadAllowed": true,
              "targetScopedAutoRecordEnabled": false,
              "autoRecordTargetIds": []
            }
            """.utf8
        ).write(to: url)
        let store = MeetingDetectionSettingsStore(settingsURL: url)

        XCTAssertEqual(try store.load().recordingRule(for: "zoom"), .ask)
        let applied = try XCTUnwrap(store.applyFirstInstallDefaults(targetIDs: ["zoom"]))
        XCTAssertEqual(applied.automaticRecordingRules, ["zoom": .ask])
    }

    func testLegacySettingsAreRewrittenWithoutObsoleteFields() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("meeting-settings-\(UUID().uuidString)", isDirectory: true)
        let url = root.appendingPathComponent("settings.json")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        try Data(
            """
            {
              "detectionMode": "detect_and_ask",
              "uploadMode": "automatic_candidate_upload",
              "unknownIdentityUploadAllowed": true,
              "targetScopedAutoRecordEnabled": true,
              "autoRecordTargetIds": ["zoom"]
            }
            """.utf8
        ).write(to: url)
        let store = MeetingDetectionSettingsStore(settingsURL: url)

        let loaded = try store.load()
        XCTAssertEqual(loaded.automaticRecordingRules, ["zoom": .ask])
        try store.save(loaded)
        let persisted = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any])
        XCTAssertEqual(Set(persisted.keys), ["automaticRecordingRules", "unknownIdentityUploadAllowed", "uploadMode"])
    }

    func testCurrentSettingsUseOnlyTargetRule() {
        let enabled = MeetingDetectionSettings(
            automaticRecordingRules: ["zoom": .always, "never": .never]
        )
        XCTAssertTrue(enabled.allowsDetectorAssistedStart(reason: .promptButton, targetID: "meet"))
        XCTAssertTrue(enabled.allowsDetectorAssistedStart(reason: .promptTimeout, targetID: "meet"))
        XCTAssertTrue(enabled.allowsDetectorAssistedStart(reason: .savedTargetPolicy, targetID: "zoom"))
        XCTAssertFalse(enabled.allowsDetectorAssistedStart(reason: .savedTargetPolicy, targetID: "meet"))
        XCTAssertFalse(enabled.allowsDetectorAssistedStart(reason: .promptButton, targetID: "never"))
    }
    func testPromptEnabledKnownTargetCanPromptWhenCaptureGateIsReady() {
        let action = MeetingDetectionPolicy().action(
            for: MeetingDetectionCandidateDecision(
                kind: .knownTarget(targetID: "yandex_telemost", mode: .promptEnabled),
                candidateScore: 0
            ),
            settings: MeetingDetectionSettingsSnapshot(),
            prerequisites: MeetingDetectionCapturePrerequisites()
        )

        XCTAssertEqual(action, .prompt(targetID: "yandex_telemost"))
    }

    func testAlwaysRuleReturnsAutoRecordWithoutServerAuthorization() {
        let action = MeetingDetectionPolicy().action(
            for: MeetingDetectionCandidateDecision(
                kind: .knownTarget(targetID: "yandex_telemost", mode: .promptEnabled),
                candidateScore: 0
            ),
            settings: MeetingDetectionSettingsSnapshot(
                automaticRecordingRules: ["yandex_telemost": .always]
            ),
            prerequisites: MeetingDetectionCapturePrerequisites()
        )

        XCTAssertEqual(action, .autoRecord(targetID: "yandex_telemost"))
    }

    func testAskRuleProducesPromptWithoutServerAuthorization() {
        let decision = MeetingDetectionCandidateDecision(
            kind: .knownTarget(targetID: "yandex_telemost", mode: .promptEnabled),
            candidateScore: 0
        )
        let action = MeetingDetectionPolicy().action(
            for: decision,
            settings: MeetingDetectionSettingsSnapshot(
                automaticRecordingRules: ["yandex_telemost": .ask]
            ),
            prerequisites: MeetingDetectionCapturePrerequisites()
        )

        XCTAssertEqual(action, .prompt(targetID: "yandex_telemost"))
    }

    func testNeverRuleSuppressesWithoutPrompt() {
        let action = MeetingDetectionPolicy().action(
            for: MeetingDetectionCandidateDecision(
                kind: .knownTarget(targetID: "yandex_telemost", mode: .promptEnabled),
                candidateScore: 0
            ),
            settings: MeetingDetectionSettingsSnapshot(
                automaticRecordingRules: ["yandex_telemost": .never]
            ),
            prerequisites: MeetingDetectionCapturePrerequisites()
        )

        XCTAssertEqual(action, .suppress(reason: "target_policy_never"))
    }

    func testAlwaysRuleDoesNotRequireServerAuthorization() {
        let decision = MeetingDetectionCandidateDecision(
            kind: .knownTarget(targetID: "yandex_telemost", mode: .promptEnabled),
            candidateScore: 0
        )
        let policy = MeetingDetectionPolicy()
        let settings = MeetingDetectionSettingsSnapshot(
            automaticRecordingRules: ["yandex_telemost": .always]
        )

        XCTAssertEqual(
            policy.action(for: decision, settings: settings, prerequisites: MeetingDetectionCapturePrerequisites()),
            .autoRecord(targetID: "yandex_telemost")
        )
    }

    func testAskRulePromptsAndNeverRuleSuppressesEvenWhenCaptureGateIsBlocked() {
        let blocked = MeetingDetectionCapturePrerequisites(oneActionStopAvailable: false)
        let decision = MeetingDetectionCandidateDecision(
            kind: .knownTarget(targetID: "yandex_telemost", mode: .promptEnabled),
            candidateScore: 0
        )
        let policy = MeetingDetectionPolicy()

        XCTAssertEqual(
            policy.action(
                for: decision,
                settings: MeetingDetectionSettingsSnapshot(
                    automaticRecordingRules: ["yandex_telemost": .ask]
                ),
                prerequisites: blocked
            ),
            .suppress(reason: "one_action_stop_unavailable")
        )
        XCTAssertEqual(
            policy.action(
                for: decision,
                settings: MeetingDetectionSettingsSnapshot(
                    automaticRecordingRules: ["yandex_telemost": .never]
                ),
                prerequisites: blocked
            ),
            .suppress(reason: "target_policy_never")
        )
    }

    func testMissingRuleDefaultsToPrompt() {
        let action = MeetingDetectionPolicy().action(
            for: MeetingDetectionCandidateDecision(
                kind: .knownTarget(targetID: "yandex_telemost", mode: .promptEnabled),
                candidateScore: 0
            ),
            settings: MeetingDetectionSettingsSnapshot(
                automaticRecordingRules: ["zoom": .always]
            ),
            prerequisites: MeetingDetectionCapturePrerequisites()
        )

        XCTAssertEqual(action, .prompt(targetID: "yandex_telemost"))
    }

    func testUnknownCandidateNeverPrompts() {
        let action = MeetingDetectionPolicy().action(
            for: MeetingDetectionCandidateDecision(
                kind: .candidateUpload,
                candidateScore: 8,
                candidateReasons: [.stableMicDuration, .vksNameToken]
            ),
            settings: MeetingDetectionSettingsSnapshot(),
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
            settings: MeetingDetectionSettingsSnapshot(),
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
            settings: MeetingDetectionSettingsSnapshot(),
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
            settings: MeetingDetectionSettingsSnapshot(),
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
            settings: MeetingDetectionSettingsSnapshot(),
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
                automaticRecordingRules: ["yandex_telemost": .always]
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
        XCTAssertEqual(configuration.snapshotArguments.first, "show")
        XCTAssertTrue(configuration.snapshotArguments.contains("--last"))
        XCTAssertTrue(configuration.snapshotArguments.contains("2h"))
        XCTAssertEqual(configuration.snapshotArguments.last, MacOSAudioOwnershipLogStreamConfiguration.snapshotPredicate)
        XCTAssertFalse(configuration.snapshotArguments.last?.contains("AudioHAL") == true)
        XCTAssertEqual(configuration.snapshotTimeoutNanoseconds, 3_500_000_000)
    }

    func testLogStreamSupervisorRestartsAfterUnexpectedLiveCompletion() async {
        let configuration = MacOSAudioOwnershipLogStreamConfiguration(
            executableURL: URL(fileURLWithPath: "/bin/sh"),
            arguments: ["-c", "exit 0"],
            snapshotArguments: ["-c", "exit 0"],
            restartDelayNanoseconds: 1_000_000
        )
        let stream = MacOSAudioOwnershipLogStream(configuration: configuration, snapshotProvider: nil)
        var reconciledGenerations: [Int] = []
        var phases: [MacOSAudioOwnershipObserverPhase] = []

        for await observation in stream.observations() {
            switch observation {
            case .reconcile(let generation):
                reconciledGenerations.append(generation)
                if generation == 2 {
                    stream.stop()
                }
            case .lifecycle(let phase, _):
                phases.append(phase)
            case .snapshot, .ownership:
                break
            }
        }

        XCTAssertEqual(reconciledGenerations, [1, 2])
        XCTAssertTrue(phases.contains(.snapshotStarted))
        XCTAssertTrue(phases.contains(.liveStarted))
        XCTAssertTrue(phases.contains(.unexpectedFinish))
        XCTAssertTrue(phases.contains(.retryScheduled))
    }

    func testLogStreamDeliberateStopDoesNotRespawn() async {
        let configuration = MacOSAudioOwnershipLogStreamConfiguration(
            executableURL: URL(fileURLWithPath: "/bin/sh"),
            arguments: ["-c", "sleep 5"],
            snapshotArguments: ["-c", "exit 0"],
            restartDelayNanoseconds: 1_000_000
        )
        let stream = MacOSAudioOwnershipLogStream(configuration: configuration, snapshotProvider: nil)
        var reconciledGenerations: [Int] = []
        var liveGenerations: [Int] = []

        for await observation in stream.observations() {
            switch observation {
            case .reconcile(let generation):
                reconciledGenerations.append(generation)
            case .lifecycle(.liveStarted, let generation):
                liveGenerations.append(generation)
                stream.stop()
            case .snapshot, .lifecycle, .ownership:
                break
            }
        }

        XCTAssertEqual(reconciledGenerations, [1])
        XCTAssertEqual(liveGenerations, [1])
    }

    func testLogStreamStopBeforeObservationNeverStartsGeneration() async {
        let configuration = MacOSAudioOwnershipLogStreamConfiguration(
            executableURL: URL(fileURLWithPath: "/bin/sh"),
            arguments: ["-c", "sleep 5"],
            snapshotArguments: ["-c", "exit 0"],
            restartDelayNanoseconds: 1_000_000
        )
        let stream = MacOSAudioOwnershipLogStream(configuration: configuration, snapshotProvider: nil)
        stream.stop()
        var didReconcile = false

        for await observation in stream.observations() {
            if case .reconcile = observation {
                didReconcile = true
                stream.stop()
            }
        }

        XCTAssertFalse(didReconcile)
    }

    func testLogStreamCoalescesRepeatedRestartRequestsIntoOneGeneration() async {
        let configuration = MacOSAudioOwnershipLogStreamConfiguration(
            executableURL: URL(fileURLWithPath: "/bin/sh"),
            arguments: ["-c", "sleep 5"],
            snapshotArguments: ["-c", "exit 0"],
            restartDelayNanoseconds: 1_000_000
        )
        let stream = MacOSAudioOwnershipLogStream(configuration: configuration, snapshotProvider: nil)
        var reconciledGenerations: [Int] = []

        for await observation in stream.observations() {
            switch observation {
            case .reconcile(let generation):
                reconciledGenerations.append(generation)
                if generation == 2 {
                    stream.stop()
                }
            case .lifecycle(.liveStarted, generation: 1):
                stream.restart()
                stream.restart()
            case .snapshot, .lifecycle, .ownership:
                break
            }
        }

        XCTAssertEqual(reconciledGenerations, [1, 2])
    }

    func testLogStreamPublishesOnlyTheFinalAtomicSensorSnapshot() async {
        let snapshotScript = #"printf '%s\n' 'ControlCenter [com.apple.controlcenter:sensor-indicators] Active activity attributions changed to ["mic:ru.yandex.desktop.telemost"]' 'ControlCenter [com.apple.controlcenter:sensor-indicators] Active activity attributions changed to ["mic:us.zoom.xos"]'"#
        let configuration = MacOSAudioOwnershipLogStreamConfiguration(
            executableURL: URL(fileURLWithPath: "/bin/sh"),
            arguments: ["-c", "sleep 5"],
            snapshotArguments: ["-c", snapshotScript],
            snapshotTimeoutNanoseconds: 1_000_000_000,
            restartDelayNanoseconds: 1_000_000
        )
        let stream = MacOSAudioOwnershipLogStream(configuration: configuration, snapshotProvider: nil)
        var snapshotEvents: [MacOSAudioOwnershipEvent] = []

        for await observation in stream.observations() {
            switch observation {
            case .snapshot(let events, isComplete: true, generation: 1):
                snapshotEvents = events
            case .lifecycle(.liveStarted, generation: 1):
                stream.stop()
            case .reconcile, .snapshot, .lifecycle, .ownership:
                break
            }
        }

        XCTAssertEqual(snapshotEvents.count, 1)
        XCTAssertEqual(snapshotEvents.first?.bundleID, "us.zoom.xos")
        XCTAssertEqual(snapshotEvents.first?.source, .sensorIndicator)
        XCTAssertEqual(snapshotEvents.first?.state, .active)
    }

    func testLogStreamSnapshotTimeoutFallsBackToLiveWithoutRetryLoop() async {
        let configuration = MacOSAudioOwnershipLogStreamConfiguration(
            executableURL: URL(fileURLWithPath: "/bin/sh"),
            arguments: ["-c", "sleep 5"],
            snapshotArguments: ["-c", "sleep 5"],
            snapshotTimeoutNanoseconds: 1_000_000,
            restartDelayNanoseconds: 1_000_000
        )
        let stream = MacOSAudioOwnershipLogStream(configuration: configuration, snapshotProvider: nil)
        var phases: [MacOSAudioOwnershipObserverPhase] = []

        for await observation in stream.observations() {
            switch observation {
            case .lifecycle(let phase, generation: 1):
                phases.append(phase)
                if phase == .liveStarted {
                    stream.stop()
                }
            case .reconcile, .snapshot, .lifecycle, .ownership:
                break
            }
        }

        XCTAssertEqual(phases, [.snapshotStarted, .snapshotUnavailable, .liveStarted])
    }

    func testLogStreamRejectsSnapshotWhoseLatestStateIsRedacted() async {
        let snapshotScript = #"printf '%s\n' 'ControlCenter [com.apple.controlcenter:sensor-indicators] Active activity attributions changed to ["mic:us.zoom.xos"]' 'ControlCenter [com.apple.controlcenter:sensor-indicators] Active activity attributions changed to <private>'"#
        let configuration = MacOSAudioOwnershipLogStreamConfiguration(
            executableURL: URL(fileURLWithPath: "/bin/sh"),
            arguments: ["-c", "sleep 5"],
            snapshotArguments: ["-c", snapshotScript],
            snapshotTimeoutNanoseconds: 1_000_000_000
        )
        let stream = MacOSAudioOwnershipLogStream(configuration: configuration, snapshotProvider: nil)
        var snapshotWasPublished = false
        var phases: [MacOSAudioOwnershipObserverPhase] = []

        for await observation in stream.observations() {
            switch observation {
            case .snapshot:
                snapshotWasPublished = true
            case .lifecycle(let phase, generation: 1):
                phases.append(phase)
                if phase == .liveStarted {
                    stream.stop()
                }
            case .reconcile, .lifecycle, .ownership:
                break
            }
        }

        XCTAssertFalse(snapshotWasPublished)
        XCTAssertTrue(phases.contains(.snapshotUnavailable))
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
                MacOSAudioOwnershipEvent(
                    bundleID: "ai.krisp.krispMac",
                    source: .sensorIndicator,
                    state: .active,
                    observedAt: observedAt
                ),
                MacOSAudioOwnershipEvent(
                    bundleID: "ru.yandex.desktop.telemost",
                    source: .sensorIndicator,
                    state: .active,
                    observedAt: observedAt
                )
            ]
        )
        XCTAssertEqual(
            endEvents,
            [
                MacOSAudioOwnershipEvent(
                    bundleID: "ru.yandex.desktop.telemost",
                    source: .sensorIndicator,
                    state: .inactive,
                    observedAt: observedAt
                )
            ]
        )
    }

    func testDetectorKeepsBundleActiveUntilEverySourceEnds() throws {
        let registry = try MeetingDetectionPolicyTests.registry()
        let detector = MacOSMeetingActivityDetector(debounceSeconds: 1, endGraceSeconds: 2)
        let bundleID = "ru.yandex.desktop.telemost"

        _ = detector.handle(
            event: MacOSAudioOwnershipEvent(
                bundleID: bundleID,
                source: .audioHAL,
                state: .active,
                observedAt: Date(timeIntervalSince1970: 100)
            ),
            registry: registry,
            settings: MeetingDetectionSettings()
        )
        _ = detector.handle(
            event: MacOSAudioOwnershipEvent(
                bundleID: bundleID,
                source: .sensorIndicator,
                state: .active,
                observedAt: Date(timeIntervalSince1970: 101)
            ),
            registry: registry,
            settings: MeetingDetectionSettings()
        )
        XCTAssertEqual(
            detector.advance(
                now: Date(timeIntervalSince1970: 102),
                registry: registry,
                settings: MeetingDetectionSettings()
            ),
            [.promptEligible(targetID: "yandex_telemost", bundleID: bundleID)]
        )
        detector.recordConsumerOutcome(bundleID: bundleID, outcome: .accepted)

        _ = detector.handle(
            event: MacOSAudioOwnershipEvent(
                bundleID: bundleID,
                source: .audioHAL,
                state: .inactive,
                observedAt: Date(timeIntervalSince1970: 103)
            ),
            registry: registry,
            settings: MeetingDetectionSettings()
        )
        XCTAssertTrue(detector.isActive(bundleID: bundleID))
        XCTAssertTrue(
            detector.advance(
                now: Date(timeIntervalSince1970: 106),
                registry: registry,
                settings: MeetingDetectionSettings()
            ).isEmpty
        )

        _ = detector.handle(
            event: MacOSAudioOwnershipEvent(
                bundleID: bundleID,
                source: .sensorIndicator,
                state: .inactive,
                observedAt: Date(timeIntervalSince1970: 107)
            ),
            registry: registry,
            settings: MeetingDetectionSettings()
        )
        XCTAssertFalse(detector.isActive(bundleID: bundleID))
        XCTAssertEqual(
            detector.advance(
                now: Date(timeIntervalSince1970: 109),
                registry: registry,
                settings: MeetingDetectionSettings()
            ),
            [.ended(bundleID: bundleID)]
        )
    }

    func testDetectorRetriesRejectedOfferButNotAcceptedOrTerminalOffer() throws {
        let registry = try MeetingDetectionPolicyTests.registry()
        let detector = MacOSMeetingActivityDetector(debounceSeconds: 1, retryIntervalSeconds: 2)
        let bundleID = "ru.yandex.desktop.telemost"
        _ = detector.handle(
            event: MacOSAudioOwnershipEvent(
                bundleID: bundleID,
                state: .active,
                observedAt: Date(timeIntervalSince1970: 100)
            ),
            registry: registry,
            settings: MeetingDetectionSettings()
        )

        let expected = [MacOSMeetingActivityDetectorOutput.promptEligible(
            targetID: "yandex_telemost",
            bundleID: bundleID
        )]
        XCTAssertEqual(
            detector.advance(
                now: Date(timeIntervalSince1970: 102),
                registry: registry,
                settings: MeetingDetectionSettings()
            ),
            expected
        )
        detector.recordConsumerOutcome(
            bundleID: bundleID,
            outcome: .retryable(reason: "transition_in_progress"),
            at: Date(timeIntervalSince1970: 102)
        )
        XCTAssertTrue(
            detector.advance(
                now: Date(timeIntervalSince1970: 103),
                registry: registry,
                settings: MeetingDetectionSettings()
            ).isEmpty
        )
        XCTAssertEqual(
            detector.advance(
                now: Date(timeIntervalSince1970: 104),
                registry: registry,
                settings: MeetingDetectionSettings()
            ),
            expected
        )

        detector.recordConsumerOutcome(bundleID: bundleID, outcome: .accepted)
        XCTAssertTrue(
            detector.advance(
                now: Date(timeIntervalSince1970: 110),
                registry: registry,
                settings: MeetingDetectionSettings()
            ).isEmpty
        )

        detector.reset()
        XCTAssertFalse(detector.isActive(bundleID: bundleID))
        _ = detector.handle(
            event: MacOSAudioOwnershipEvent(
                bundleID: bundleID,
                state: .active,
                observedAt: Date(timeIntervalSince1970: 120)
            ),
            registry: registry,
            settings: MeetingDetectionSettings()
        )
        XCTAssertEqual(
            detector.advance(
                now: Date(timeIntervalSince1970: 122),
                registry: registry,
                settings: MeetingDetectionSettings()
            ),
            expected
        )
        detector.recordConsumerOutcome(
            bundleID: bundleID,
            outcome: .terminal(reason: "user_skipped")
        )
        XCTAssertTrue(
            detector.advance(
                now: Date(timeIntervalSince1970: 130),
                registry: registry,
                settings: MeetingDetectionSettings()
            ).isEmpty
        )
    }

    func testDetectorIgnoresDelayedAndDuplicateTransitionsAndAllowsNextMeeting() throws {
        let registry = try MeetingDetectionPolicyTests.registry()
        let detector = MacOSMeetingActivityDetector(debounceSeconds: 1, endGraceSeconds: 2)
        let settings = MeetingDetectionSettings()
        let bundleID = "ru.yandex.desktop.telemost"

        for event in [
            MacOSAudioOwnershipEvent(
                bundleID: bundleID,
                source: .audioHAL,
                state: .active,
                observedAt: Date(timeIntervalSince1970: 100)
            ),
            MacOSAudioOwnershipEvent(
                bundleID: bundleID,
                source: .sensorIndicator,
                state: .active,
                observedAt: Date(timeIntervalSince1970: 101)
            ),
        ] {
            _ = detector.handle(event: event, registry: registry, settings: settings)
        }
        XCTAssertEqual(
            detector.advance(now: Date(timeIntervalSince1970: 102), registry: registry, settings: settings),
            [.promptEligible(targetID: "yandex_telemost", bundleID: bundleID)]
        )
        detector.recordConsumerOutcome(bundleID: bundleID, outcome: .accepted)

        for event in [
            MacOSAudioOwnershipEvent(
                bundleID: bundleID,
                source: .audioHAL,
                state: .inactive,
                observedAt: Date(timeIntervalSince1970: 103)
            ),
            MacOSAudioOwnershipEvent(
                bundleID: bundleID,
                source: .audioHAL,
                state: .inactive,
                observedAt: Date(timeIntervalSince1970: 104)
            ),
            MacOSAudioOwnershipEvent(
                bundleID: bundleID,
                source: .audioHAL,
                state: .active,
                observedAt: Date(timeIntervalSince1970: 102)
            ),
            MacOSAudioOwnershipEvent(
                bundleID: bundleID,
                source: .sensorIndicator,
                state: .inactive,
                observedAt: Date(timeIntervalSince1970: 105)
            ),
        ] {
            _ = detector.handle(event: event, registry: registry, settings: settings)
        }
        XCTAssertFalse(detector.isActive(bundleID: bundleID))

        _ = detector.handle(
            event: MacOSAudioOwnershipEvent(
                bundleID: bundleID,
                source: .audioHAL,
                state: .active,
                observedAt: Date(timeIntervalSince1970: 106)
            ),
            registry: registry,
            settings: settings
        )
        XCTAssertTrue(detector.isActive(bundleID: bundleID))
        XCTAssertTrue(
            detector.advance(now: Date(timeIntervalSince1970: 108), registry: registry, settings: settings).isEmpty
        )
        _ = detector.handle(
            event: MacOSAudioOwnershipEvent(
                bundleID: bundleID,
                source: .audioHAL,
                state: .inactive,
                observedAt: Date(timeIntervalSince1970: 109)
            ),
            registry: registry,
            settings: settings
        )
        XCTAssertEqual(
            detector.advance(now: Date(timeIntervalSince1970: 111), registry: registry, settings: settings),
            [.ended(bundleID: bundleID)]
        )

        _ = detector.handle(
            event: MacOSAudioOwnershipEvent(
                bundleID: bundleID,
                source: .audioHAL,
                state: .active,
                observedAt: Date(timeIntervalSince1970: 120)
            ),
            registry: registry,
            settings: settings
        )
        XCTAssertEqual(
            detector.advance(now: Date(timeIntervalSince1970: 122), registry: registry, settings: settings),
            [.promptEligible(targetID: "yandex_telemost", bundleID: bundleID)]
        )
    }

    func testDetectorReoffersAfterRetryablePolicySuppressionRecovers() throws {
        let registry = try MeetingDetectionPolicyTests.registry()
        let detector = MacOSMeetingActivityDetector(debounceSeconds: 1, retryIntervalSeconds: 2)
        let bundleID = "ru.yandex.desktop.telemost"
        let settings = MeetingDetectionSettings(
            automaticRecordingRules: ["yandex_telemost": .always]
        )
        _ = detector.handle(
            event: MacOSAudioOwnershipEvent(
                bundleID: bundleID,
                state: .active,
                observedAt: Date(timeIntervalSince1970: 100)
            ),
            registry: registry,
            settings: settings
        )
        let blocked = MeetingDetectionCapturePrerequisites(
            recordingPrerequisite: RecordingPrerequisiteGate().evaluate(
                recordingPrerequisite(policyAllowsRecording: false)
            )
        )
        XCTAssertEqual(
            detector.advance(
                now: Date(timeIntervalSince1970: 102),
                registry: registry,
                settings: settings,
                prerequisites: blocked
            ),
            [.suppressed(bundleID: bundleID, reason: RecordingStartBlocker.policyDisabled.rawValue)]
        )
        detector.recordConsumerOutcome(
            bundleID: bundleID,
            outcome: .retryable(reason: RecordingStartBlocker.policyDisabled.rawValue),
            at: Date(timeIntervalSince1970: 102)
        )

        XCTAssertTrue(
            detector.advance(
                now: Date(timeIntervalSince1970: 103),
                registry: registry,
                settings: settings
            ).isEmpty
        )
        XCTAssertEqual(
            detector.advance(
                now: Date(timeIntervalSince1970: 104),
                registry: registry,
                settings: settings
            ),
            [.autoRecordEligible(targetID: "yandex_telemost", bundleID: bundleID)]
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

    func testDetectorEmitsAutoRecordEligibleForOptedInTarget() throws {
        let registry = try MeetingDetectionPolicyTests.registry()
        let detector = MacOSMeetingActivityDetector(debounceSeconds: 5)
        let settings = MeetingDetectionSettings(
            automaticRecordingRules: ["yandex_telemost": .always]
        )
        let event = MacOSAudioOwnershipEvent(
            bundleID: "ru.yandex.desktop.telemost",
            displayName: "Yandex Telemost",
            state: .active,
            observedAt: Date(timeIntervalSince1970: 100)
        )

        _ = detector.handle(
            event: event,
            registry: registry,
            settings: settings
        )

        XCTAssertEqual(
            detector.advance(
                now: Date(timeIntervalSince1970: 106),
                registry: registry,
                settings: settings
            ),
            [.autoRecordEligible(targetID: "yandex_telemost", bundleID: "ru.yandex.desktop.telemost")]
        )
        XCTAssertTrue(
            detector.advance(
                now: Date(timeIntervalSince1970: 107),
                registry: registry,
                settings: settings
            ).isEmpty
        )
    }

    func testDetectorSelectedTargetWithoutAcknowledgementEmitsPromptInsteadOfAutoRecord() throws {
        let registry = try MeetingDetectionPolicyTests.registry()
        let detector = MacOSMeetingActivityDetector(debounceSeconds: 1)
        let settings = MeetingDetectionSettings(
            automaticRecordingRules: ["yandex_telemost": .ask]
        )
        _ = detector.handle(
            event: MacOSAudioOwnershipEvent(
                bundleID: "ru.yandex.desktop.telemost",
                state: .active,
                observedAt: Date(timeIntervalSince1970: 100)
            ),
            registry: registry,
            settings: settings
        )

        XCTAssertEqual(
            detector.advance(
                now: Date(timeIntervalSince1970: 102),
                registry: registry,
                settings: settings
            ),
            [.promptEligible(targetID: "yandex_telemost", bundleID: "ru.yandex.desktop.telemost")]
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
            policyAllowsRecording: policyAllowsRecording,
            microphonePermissionGranted: true,
            systemAudioPermissionGranted: true,
            storageRisk: storageRisk,
            indicatorAvailable: true,
            sourceAppEligibility: .eligible,
            evaluatedAt: Date(timeIntervalSince1970: 1_779_887_120)
        )
    }

    func testCurrentSnapshotsPreserveOneFortyFiveMinuteCallAndEndGrace() throws {
        let registry = try Self.registry()
        let detector = MacOSMeetingActivityDetector()
        let settings = MeetingDetectionSettings()
        let bundleID = "ru.yandex.desktop.telemost"
        var lastEvidence = Date(timeIntervalSince1970: 0)
        var offers = 0
        for seconds in stride(from: 0, through: 2700, by: 2) {
            let now = Date(timeIntervalSince1970: Double(seconds))
            detector.reconcileSnapshot(activeBundleIDs: [bundleID], observedAt: now)
            lastEvidence = now
            let outputs = detector.advance(now: now, registry: registry, settings: settings)
            offers += outputs.count
            if !outputs.isEmpty { detector.recordConsumerOutcome(bundleID: bundleID, outcome: .accepted, at: now) }
            XCTAssertFalse(MacOSMeetingActivityDetector.recordingEvidenceExpired(lastObservedAt: lastEvidence, now: now))
        }
        XCTAssertEqual(offers, 1)
        // A successful full native snapshot must also clear prior legacy source state.
        detector.reconcile(event: .init(bundleID: bundleID, source: .audioHAL, state: .active, observedAt: lastEvidence))
        let endedAt = Date(timeIntervalSince1970: 2702)
        detector.reconcileSnapshot(activeBundleIDs: [], observedAt: endedAt)
        XCTAssertFalse(detector.isActive(bundleID: bundleID))
        detector.reconcileSnapshot(activeBundleIDs: [], observedAt: endedAt.addingTimeInterval(10))
        XCTAssertTrue(detector.advance(now: endedAt.addingTimeInterval(14), registry: registry, settings: settings).isEmpty)
        XCTAssertEqual(detector.advance(now: endedAt.addingTimeInterval(15), registry: registry, settings: settings), [.ended(bundleID: bundleID)])
        // No observations (including unavailable snapshots) means no renewal.
        XCTAssertFalse(MacOSMeetingActivityDetector.recordingEvidenceExpired(lastObservedAt: lastEvidence, now: lastEvidence.addingTimeInterval(599)))
        XCTAssertTrue(MacOSMeetingActivityDetector.recordingEvidenceExpired(lastObservedAt: lastEvidence, now: lastEvidence.addingTimeInterval(600)))
    }

    func testCurrentSnapshotsPreserveManualSuppressionAndTransientInactivity() throws {
        let registry = try Self.registry(), settings = MeetingDetectionSettings()
        let detector = MacOSMeetingActivityDetector()
        let bundleID = "ru.yandex.desktop.telemost", now = Date(timeIntervalSince1970: 100)
        detector.reconcileSnapshot(activeBundleIDs: [bundleID], observedAt: now)
        XCTAssertEqual(detector.advance(now: now.addingTimeInterval(5), registry: registry, settings: settings).count, 1)
        detector.recordConsumerOutcome(bundleID: bundleID, outcome: .terminal(reason: "manually_stopped_current_meeting"), at: now)
        detector.reconcileSnapshot(activeBundleIDs: [], observedAt: now.addingTimeInterval(10))
        detector.reconcileSnapshot(activeBundleIDs: [bundleID], observedAt: now.addingTimeInterval(12))
        XCTAssertTrue(detector.advance(now: now.addingTimeInterval(2700), registry: registry, settings: settings).isEmpty)
    }

    func testNativeSnapshotsNeverRunOldLogActiveEvenWhenUnavailable() async {
        // Would emit stale active indefinitely if the journal child were launched.
        let staleLog = #"printf '%s\n' 'ControlCenter [com.apple.controlcenter:sensor-indicators] Active activity attributions changed to ["mic:ru.yandex.desktop.telemost"]'"#
        for snapshot: MacOSAudioInputActivitySnapshot.Value? in [.init(activeBundleIDs: []), .init(activeBundleIDs: [], isComplete: false), nil] {
            let stream = MacOSAudioOwnershipLogStream(
                configuration: .init(executableURL: URL(fileURLWithPath: "/bin/sh"), arguments: ["-c", staleLog], snapshotArguments: ["-c", staleLog]),
                snapshotProvider: { snapshot }, snapshotIntervalNanoseconds: 1_000_000
            )
            var samples = 0, logActiveCount = 0
            for await observation in stream.observations() {
                switch observation {
                case .snapshot(let events, let isComplete, _):
                    XCTAssertTrue(events.isEmpty)
                    XCTAssertEqual(isComplete, snapshot?.isComplete)
                    samples += 1
                case .lifecycle(.snapshotUnavailable, _): samples += 1
                case .ownership: logActiveCount += 1
                default: break
                }
                if samples == 3 { stream.stop() }
            }
            XCTAssertEqual(samples, 3)
            XCTAssertEqual(logActiveCount, 0)
        }
    }

    func testNativeObserverRestartDoesNotReplayRecordingOffer() async throws {
        let registry = try Self.registry(), detector = MacOSMeetingActivityDetector(debounceSeconds: 0)
        let bundleID = "ru.yandex.desktop.telemost"
        let stream = MacOSAudioOwnershipLogStream(snapshotProvider: { .init(activeBundleIDs: [bundleID]) }, snapshotIntervalNanoseconds: 1_000_000)
        var snapshots = 0, offers = 0, generations: [Int] = []
        for await observation in stream.observations() {
            switch observation {
            case .reconcile(let generation): generations.append(generation)
            case .snapshot(let events, _, _):
                let observedAt = try XCTUnwrap(events.first?.observedAt)
                detector.reconcileSnapshot(activeBundleIDs: Set(events.map(\.bundleID)), observedAt: observedAt)
                let outputs = detector.advance(now: observedAt, registry: registry, settings: .init())
                offers += outputs.count
                detector.recordConsumerOutcome(bundleID: bundleID, outcome: .accepted, at: observedAt)
                snapshots += 1
                if snapshots == 1 { stream.restart() }
                if snapshots == 3 { stream.stop() }
            default: break
            }
        }
        XCTAssertEqual(generations, [1,2])
        XCTAssertEqual(offers, 1)
    }

    func testCoreAudioAttributionSelectsOuterAppNotNestedHelper() {
        XCTAssertEqual(MacOSAudioInputActivitySnapshot.containingApplicationURL(for: URL(fileURLWithPath: "/Applications/Telemost.app/Contents/Frameworks/QtWebEngineProcess.app/Contents/MacOS/QtWebEngineProcess"))?.path, "/Applications/Telemost.app")
        XCTAssertNil(MacOSAudioInputActivitySnapshot.containingApplicationURL(for: URL(fileURLWithPath: "/usr/bin/unknown")))
    }

    func testMixedCurrentInputSnapshotRetainsReliableMeetingBesideUnreadableProcess() throws {
        let meetingID = "ru.yandex.desktop.telemost"
        for processes: [AudioObjectID] in [[10, 20], [20, 10]] {
            let readings = MacOSAudioInputActivitySnapshot.Readings(
                propertyData: { object, selector in
                    if selector == kAudioHardwarePropertyProcessObjectList {
                        return processes.withUnsafeBytes { Data($0) }
                    }
                    guard object == 10 else { return nil }
                    var value: UInt32 = selector == kAudioProcessPropertyIsRunningInput ? 1 : 100
                    return withUnsafeBytes(of: &value) { Data($0) }
                },
                executableURL: { _ in URL(fileURLWithPath: "/Applications/Telemost.app/Contents/MacOS/Telemost") },
                applicationBundleID: { _ in meetingID }
            )
            XCTAssertEqual(MacOSAudioInputActivitySnapshot.activeBundleIDs(readings: readings)?.activeBundleIDs, [meetingID], "An unreadable neighbor must not discard current meeting evidence")
        }
    }

    func testMixedSnapshotsIsolateEveryUnreadableProcessInBothOrders() throws {
        let failures: [(String, InputProcess)] = [
            ("unreadable input", .init(runningData: nil)),
            ("malformed input size", .init(runningData: Data([1]))),
            ("invalid input flag", .init(runningData: Self.scalarData(UInt32(2)))),
            ("unreadable PID", .init(pidData: nil)),
            ("invalid PID", .init(pidData: Self.scalarData(pid_t(0)))),
            ("malformed PID size", .init(pidData: Data([100]))),
            ("unreadable path", .init(executablePath: nil)),
            ("missing app bundle", .init(appBundleID: nil)),
            ("malformed app bundle", .init(appBundleID: "ru..telemost")),
            ("exited process", .init(runningData: nil, pidData: nil, executablePath: nil))
        ]
        for (reason, unreadable) in failures {
            for processes: [AudioObjectID] in [[10, 20], [20, 10]] {
                let readings = Self.inputReadings(processes: processes, samples: [10: .meeting, 20: unreadable])
                let snapshot = try XCTUnwrap(MacOSAudioInputActivitySnapshot.activeBundleIDs(readings: readings), reason)
                XCTAssertEqual(snapshot.activeBundleIDs, [Self.meetingBundleID], reason)
                XCTAssertFalse(snapshot.isComplete, reason)
            }
        }
    }

    func testCurrentProcessListFailureAndMalformedSizesRemainUnavailable() {
        for data: Data? in [nil, Data([1]), Data([1, 2, 3, 4, 5])] {
            var readings = Self.inputReadings(processes: [], samples: [:])
            readings.propertyData = { _, _ in data }
            XCTAssertNil(MacOSAudioInputActivitySnapshot.activeBundleIDs(readings: readings))
        }
        XCTAssertEqual(MacOSAudioInputActivitySnapshot.activeBundleIDs(readings: Self.inputReadings(processes: [], samples: [:])), .init(activeBundleIDs: [], isComplete: true))
    }

    func testKnownInactiveAndNonAppProcessesDoNotMakeCoverageIncomplete() throws {
        let readings = Self.inputReadings(processes: [10, 20, 30], samples: [
            10: .meeting,
            20: .init(runningData: Self.scalarData(UInt32(0)), pidData: nil, executablePath: nil),
            30: .init(executablePath: "/usr/bin/known-tool", appBundleID: nil, processBundleID: Self.meetingBundleID)
        ])
        let snapshot = try XCTUnwrap(MacOSAudioInputActivitySnapshot.activeBundleIDs(readings: readings))
        XCTAssertEqual(snapshot, .init(activeBundleIDs: [Self.meetingBundleID], isComplete: true))
    }

    func testDirectCurrentBundleIDFallbackIsExactAndOuterAppRemainsAuthoritative() throws {
        for fallback: InputProcess in [
            .init(pidData: nil, processBundleID: Self.meetingBundleID),
            .init(executablePath: nil, processBundleID: Self.meetingBundleID)
        ] {
            let snapshot = try XCTUnwrap(MacOSAudioInputActivitySnapshot.activeBundleIDs(readings: Self.inputReadings(processes: [20], samples: [20: fallback])))
            XCTAssertEqual(snapshot, .init(activeBundleIDs: [Self.meetingBundleID], isComplete: false))
        }
        for malformedID in ["", "QtWebEngineProcess", "ru..telemost", "ru.yandex.desktop.telemost\n", "Telemost app"] {
            let snapshot = try XCTUnwrap(MacOSAudioInputActivitySnapshot.activeBundleIDs(readings: Self.inputReadings(processes: [20], samples: [20: .init(executablePath: nil, processBundleID: malformedID)])))
            XCTAssertEqual(snapshot, .init(activeBundleIDs: [], isComplete: false), malformedID)
        }
        let helperPath = "/Applications/Telemost.app/Contents/Frameworks/QtWebEngineProcess.app/Contents/MacOS/QtWebEngineProcess"
        let outer = Self.inputReadings(processes: [20], samples: [20: .init(executablePath: helperPath, appBundleID: Self.meetingBundleID, processBundleID: "org.qt-project.QtWebEngineProcess")])
        XCTAssertEqual(MacOSAudioInputActivitySnapshot.activeBundleIDs(readings: outer), .init(activeBundleIDs: [Self.meetingBundleID], isComplete: true))
        // An app path with unreadable outer identity must not adopt a different helper identity.
        let malformedOuter = Self.inputReadings(processes: [20], samples: [20: .init(executablePath: helperPath, appBundleID: nil, processBundleID: Self.meetingBundleID)])
        XCTAssertEqual(MacOSAudioInputActivitySnapshot.activeBundleIDs(readings: malformedOuter), .init(activeBundleIDs: [], isComplete: false))
    }

    func testUnapprovedExactBundleIDDoesNotBecomeRecordingTarget() throws {
        let unknownID = "org.test.unapproved"
        let snapshot = try XCTUnwrap(MacOSAudioInputActivitySnapshot.activeBundleIDs(readings: Self.inputReadings(processes: [20], samples: [20: .init(executablePath: nil, processBundleID: unknownID)])))
        XCTAssertEqual(snapshot.activeBundleIDs, [unknownID])
        let detector = MacOSMeetingActivityDetector(debounceSeconds: 0)
        let now = Date(timeIntervalSince1970: 100)
        detector.reconcileSnapshot(activeBundleIDs: snapshot.activeBundleIDs, observedAt: now, isComplete: snapshot.isComplete)
        let outputs = detector.advance(now: now.addingTimeInterval(300), registry: try Self.registry(), settings: .init())
        for output in outputs {
            if case .autoRecordEligible = output { XCTFail("Unapproved ID cannot auto-record") }
            if case .promptEligible = output { XCTFail("Unapproved ID cannot offer a recording") }
        }
    }

    func testMixedSnapshotObserverDetectorAndRecordingPredicatePreserveFortyFiveMinutes() async throws {
        let registry = try Self.registry()
        for processOrder: [AudioObjectID] in [[10, 20], [20, 10]] {
            let readings = Self.inputReadings(processes: processOrder, samples: [10: .meeting, 20: .init(runningData: nil)])
            let clock = SnapshotClock()
            let stream = MacOSAudioOwnershipLogStream(
                snapshotProvider: { MacOSAudioInputActivitySnapshot.activeBundleIDs(readings: readings) },
                snapshotIntervalNanoseconds: 1_000_000,
                snapshotClock: { clock.next() }
            )
            defer { stream.stop() }
            let detector = MacOSMeetingActivityDetector()
            var lastEvidence = Date(timeIntervalSince1970: 0)
            var snapshots = 0, offers = 0
            for await observation in stream.observations() {
                guard case .snapshot(let events, let isComplete, _) = observation else { continue }
                let observedAt = try XCTUnwrap(events.first?.observedAt)
                let bundleIDs = Set(events.map(\.bundleID))
                XCTAssertFalse(isComplete)
                XCTAssertEqual(bundleIDs, [Self.meetingBundleID])
                detector.reconcileSnapshot(activeBundleIDs: bundleIDs, observedAt: observedAt, isComplete: isComplete)
                // Same current-target renewal condition and expiry predicate as the app.
                if bundleIDs.contains(Self.meetingBundleID) { lastEvidence = observedAt }
                for output in detector.advance(now: observedAt, registry: registry, settings: .init()) {
                    guard case .promptEligible = output else { XCTFail("Unexpected lifecycle output: \(output)"); continue }
                    offers += 1
                    detector.recordConsumerOutcome(bundleID: Self.meetingBundleID, outcome: .accepted, at: observedAt)
                }
                XCTAssertFalse(MacOSMeetingActivityDetector.recordingEvidenceExpired(lastObservedAt: lastEvidence, now: observedAt))
                snapshots += 1
                if observedAt.timeIntervalSince1970 >= 2700 { stream.stop(); break }
            }
            XCTAssertEqual(snapshots, 1351)
            XCTAssertEqual(offers, 1)
            XCTAssertTrue(detector.isActive(bundleID: Self.meetingBundleID))
        }
    }

    func testPartialEmptyOrUnknownSnapshotsNeverEndAtFifteenSecondsOrRenewEvidence() async throws {
        let registry = try Self.registry()
        for sample: InputProcess in [.init(runningData: nil), .init(executablePath: nil, processBundleID: "org.test.unapproved")] {
            let readings = Self.inputReadings(processes: [20], samples: [20: sample])
            let clock = SnapshotClock()
            let stream = MacOSAudioOwnershipLogStream(
                snapshotProvider: { MacOSAudioInputActivitySnapshot.activeBundleIDs(readings: readings) },
                snapshotIntervalNanoseconds: 1_000_000,
                snapshotClock: { clock.next() }
            )
            defer { stream.stop() }
            let detector = MacOSMeetingActivityDetector(debounceSeconds: 0)
            let initial = Date(timeIntervalSince1970: 0)
            detector.reconcileSnapshot(activeBundleIDs: [Self.meetingBundleID], observedAt: initial)
            XCTAssertEqual(detector.advance(now: initial, registry: registry, settings: .init()).count, 1)
            detector.recordConsumerOutcome(bundleID: Self.meetingBundleID, outcome: .accepted, at: initial)
            var lastEvidence = initial
            var snapshots = 0
            for await observation in stream.observations() {
                guard case .snapshot(let events, let isComplete, _) = observation else { continue }
                // Empty observations carry no event timestamp; their injected clock advances by2s.
                let observedAt = events.first?.observedAt ?? Date(timeIntervalSince1970: Double(snapshots * 2))
                let bundleIDs = Set(events.map(\.bundleID))
                XCTAssertFalse(isComplete)
                XCTAssertFalse(bundleIDs.contains(Self.meetingBundleID))
                detector.reconcileSnapshot(activeBundleIDs: bundleIDs, observedAt: observedAt, isComplete: isComplete)
                if bundleIDs.contains(Self.meetingBundleID) { lastEvidence = observedAt }
                let outputs = detector.advance(now: observedAt, registry: registry, settings: .init())
                XCTAssertFalse(outputs.contains(.ended(bundleID: Self.meetingBundleID)))
                XCTAssertTrue(detector.isActive(bundleID: Self.meetingBundleID))
                XCTAssertEqual(lastEvidence, initial)
                XCTAssertEqual(MacOSMeetingActivityDetector.recordingEvidenceExpired(lastObservedAt: lastEvidence, now: observedAt), observedAt.timeIntervalSince(initial) >= 600)
                snapshots += 1
                if observedAt.timeIntervalSince(initial) >= 600 { stream.stop(); break }
            }
            XCTAssertEqual(snapshots, 301)
            // A later complete empty snapshot still proves absence and preserves the15s grace.
            let endedAt = Date(timeIntervalSince1970: 602)
            detector.reconcileSnapshot(activeBundleIDs: [], observedAt: endedAt, isComplete: true)
            XCTAssertFalse(detector.isActive(bundleID: Self.meetingBundleID))
            XCTAssertTrue(detector.advance(now: endedAt.addingTimeInterval(14), registry: registry, settings: .init()).isEmpty)
            XCTAssertEqual(detector.advance(now: endedAt.addingTimeInterval(15), registry: registry, settings: .init()), [.ended(bundleID: Self.meetingBundleID)])
        }
    }

    private static let meetingBundleID = "ru.yandex.desktop.telemost"

    private struct InputProcess: Sendable {
        var runningData: Data? = MeetingDetectionPolicyTests.scalarData(UInt32(1))
        var pidData: Data? = MeetingDetectionPolicyTests.scalarData(pid_t(200))
        var executablePath: String? = "/Applications/Neighbor.app/Contents/MacOS/Neighbor"
        var appBundleID: String? = "org.test.neighbor"
        var processBundleID: String?
        static var meeting: Self {
            .init(pidData: MeetingDetectionPolicyTests.scalarData(pid_t(100)), executablePath: "/Applications/Telemost.app/Contents/MacOS/Telemost", appBundleID: MeetingDetectionPolicyTests.meetingBundleID)
        }
    }

    private static func scalarData<T>(_ value: T) -> Data {
        var value = value
        return withUnsafeBytes(of: &value) { Data($0) }
    }

    private static func inputReadings(processes: [AudioObjectID], samples: [AudioObjectID: InputProcess]) -> MacOSAudioInputActivitySnapshot.Readings {
        .init(propertyData: { object, selector in
            if selector == kAudioHardwarePropertyProcessObjectList { return processes.withUnsafeBytes { Data($0) } }
            if selector == kAudioProcessPropertyIsRunningInput { return samples[object]?.runningData }
            if selector == kAudioProcessPropertyPID { return samples[object]?.pidData }
            return nil
        }, executableURL: { pid in
            guard let sample = samples.values.first(where: { $0.pidData == Self.scalarData(pid) }), let path = sample.executablePath else { return nil }
            return URL(fileURLWithPath: path)
        }, applicationBundleID: { appURL in
            samples.values.first(where: { sample in
                guard let path = sample.executablePath else { return false }
                return MacOSAudioInputActivitySnapshot.containingApplicationURL(for: URL(fileURLWithPath: path)) == appURL
            })?.appBundleID
        }, processBundleID: { samples[$0]?.processBundleID })
    }

    private final class SnapshotClock: @unchecked Sendable {
        private let lock = NSLock()
        private var tick = 0
        func next() -> Date {
            lock.lock(); defer { lock.unlock() }
            defer { tick += 1 }
            return Date(timeIntervalSince1970: Double(tick * 2))
        }
    }

    private static func registry() throws -> MeetingTargetRegistryDocument {
        try MeetingDetectionCoding.decoder().decode(
            MeetingTargetRegistryDocument.self,
            from: MeetingTargetRegistryTests.seedRegistryData()
        )
    }
}
#endif
