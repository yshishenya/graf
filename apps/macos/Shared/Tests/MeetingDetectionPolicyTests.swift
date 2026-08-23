import Foundation
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class MeetingDetectionPolicyTests: XCTestCase {
    func testFreshInstallDefaultsApplyOnlyOnceAndNeverOverwriteAnExplicitFile() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("meeting-settings-defaults-\(UUID().uuidString)", isDirectory: true)
        let url = root.appendingPathComponent("settings.json")
        defer { try? FileManager.default.removeItem(at: root) }
        let store = MeetingDetectionSettingsStore(settingsURL: url)

        let applied = try XCTUnwrap(
            store.applyFirstInstallDefaults(targetIDs: ["zoom", "yandex_telemost"])
        )
        XCTAssertEqual(applied.detectionMode, .detectAndAsk)
        XCTAssertTrue(applied.targetScopedAutoRecordEnabled)
        XCTAssertEqual(applied.autoRecordTargetIds, ["zoom", "yandex_telemost"])
        XCTAssertTrue(applied.automaticRecordingDefaultsApplied)
        XCTAssertNil(applied.assistedAutoStartAcknowledgement)
        XCTAssertNil(try store.applyFirstInstallDefaults(targetIDs: ["teams"])
        )

        var edited = try store.load()
        edited.detectionMode = .detectOnly
        edited.autoRecordTargetIds = ["zoom"]
        edited.targetScopedAutoRecordEnabled = true
        try store.save(edited)
        XCTAssertNil(try store.applyFirstInstallDefaults(targetIDs: ["teams"]))
        XCTAssertEqual(try store.load().autoRecordTargetIds, ["zoom"])
    }

    func testExistingSettingsWithoutDefaultsMarkerRemainUserControlled() throws {
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

        let loaded = try store.load()
        XCTAssertTrue(loaded.automaticRecordingDefaultsApplied)
        XCTAssertNil(try store.applyFirstInstallDefaults(targetIDs: ["zoom"]))
        XCTAssertEqual(try store.load().detectionMode, .detectOnly)
        XCTAssertTrue(try store.load().autoRecordTargetIds.isEmpty)
    }

    func testLegacySettingsKeepTargetSelectionButRequireNewAcknowledgement() throws {
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

        var loaded = try store.load()
        XCTAssertEqual(loaded.autoRecordTargetIds, ["zoom"])
        XCTAssertNil(loaded.assistedAutoStartAcknowledgement)
        XCTAssertTrue(loaded.automaticRecordingDefaultsApplied)

        loaded.assistedAutoStartAcknowledgement = AssistedAutoStartAcknowledgement(
            policyRef: "sha256:" + String(repeating: "a", count: 64),
            subjectRef: "sha256:" + String(repeating: "b", count: 64),
            deviceRef: "sha256:" + String(repeating: "c", count: 64),
            acknowledgementVersion: "ack-v1"
        )
        try store.save(loaded)
        let reloaded = try store.load()
        XCTAssertEqual(reloaded.autoRecordTargetIds, loaded.autoRecordTargetIds)
        XCTAssertEqual(
            reloaded.assistedAutoStartAcknowledgement?.policyRef,
            loaded.assistedAutoStartAcknowledgement?.policyRef
        )
        XCTAssertEqual(
            reloaded.assistedAutoStartAcknowledgement?.subjectRef,
            loaded.assistedAutoStartAcknowledgement?.subjectRef
        )
        XCTAssertEqual(
            reloaded.assistedAutoStartAcknowledgement?.deviceRef,
            loaded.assistedAutoStartAcknowledgement?.deviceRef
        )
        XCTAssertEqual(
            reloaded.assistedAutoStartAcknowledgement?.acknowledgementVersion,
            loaded.assistedAutoStartAcknowledgement?.acknowledgementVersion
        )
    }

    func testAcknowledgementMatchesExactPolicyAndAuthenticatedSubject() {
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let policy = AssistedAutoStartPolicySnapshot(
            policyRef: "sha256:" + String(repeating: "a", count: 64),
            acknowledgementSubjectRef: "sha256:" + String(repeating: "b", count: 64),
            deviceRef: "sha256:" + String(repeating: "c", count: 64),
            policyVersion: "2026.08.12.1",
            acknowledgementVersion: "ack-v1",
            issuedAt: now,
            expiresAt: now.addingTimeInterval(3_600)
        )
        let acknowledgement = AssistedAutoStartAcknowledgement(
            policyRef: policy.policyRef,
            subjectRef: policy.acknowledgementSubjectRef,
            deviceRef: policy.deviceRef,
            acknowledgementVersion: policy.acknowledgementVersion,
            acceptedAt: now
        )

        XCTAssertTrue(acknowledgement.matches(policy, at: now))
        XCTAssertFalse(AssistedAutoStartAcknowledgement(
            policyRef: policy.policyRef,
            subjectRef: "sha256:" + String(repeating: "c", count: 64),
            deviceRef: policy.deviceRef,
            acknowledgementVersion: policy.acknowledgementVersion,
            acceptedAt: now
        ).matches(policy, at: now))
        XCTAssertFalse(AssistedAutoStartAcknowledgement(
            policyRef: policy.policyRef,
            subjectRef: policy.acknowledgementSubjectRef,
            deviceRef: "sha256:" + String(repeating: "d", count: 64),
            acknowledgementVersion: policy.acknowledgementVersion,
            acceptedAt: now
        ).matches(policy, at: now))
        XCTAssertFalse(acknowledgement.matches(policy, at: policy.expiresAt))
        XCTAssertFalse(acknowledgement.matches(policy, at: now.addingTimeInterval(-1)))
        XCTAssertFalse(policy.isActive(at: now.addingTimeInterval(-1)))
    }

    func testCurrentSettingsRecheckDetectionModeAndSavedTargetOptIn() {
        let enabled = MeetingDetectionSettings(
            detectionMode: .detectAndAsk,
            targetScopedAutoRecordEnabled: true,
            autoRecordTargetIds: ["zoom"]
        )
        XCTAssertTrue(enabled.allowsDetectorAssistedStart(reason: .promptButton, targetID: "meet"))
        XCTAssertTrue(enabled.allowsDetectorAssistedStart(reason: .promptTimeout, targetID: "meet"))
        XCTAssertTrue(enabled.allowsDetectorAssistedStart(reason: .savedTargetPolicy, targetID: "zoom"))
        XCTAssertFalse(enabled.allowsDetectorAssistedStart(reason: .savedTargetPolicy, targetID: "meet"))

        var disabled = enabled
        disabled.detectionMode = .detectOnly
        XCTAssertFalse(disabled.allowsDetectorAssistedStart(reason: .promptButton, targetID: "meet"))
        XCTAssertFalse(disabled.allowsDetectorAssistedStart(reason: .promptTimeout, targetID: "meet"))
        XCTAssertFalse(disabled.allowsDetectorAssistedStart(reason: .savedTargetPolicy, targetID: "zoom"))
    }
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

    func testTargetScopedAutoRecordReturnsAutoRecordAfterExplicitOptIn() {
        let action = MeetingDetectionPolicy().action(
            for: MeetingDetectionCandidateDecision(
                kind: .knownTarget(targetID: "yandex_telemost", mode: .promptEnabled),
                candidateScore: 0
            ),
            settings: MeetingDetectionSettingsSnapshot(
                detectionMode: .detectAndAsk,
                targetScopedAutoRecordEnabled: true,
                autoRecordTargetIds: ["yandex_telemost"],
                assistedAutoStartAuthorized: true
            ),
            prerequisites: MeetingDetectionCapturePrerequisites()
        )

        XCTAssertEqual(action, .autoRecord(targetID: "yandex_telemost"))
    }

    func testSelectedTargetWithoutAcknowledgementStillProducesPrompt() {
        let decision = MeetingDetectionCandidateDecision(
            kind: .knownTarget(targetID: "yandex_telemost", mode: .promptEnabled),
            candidateScore: 0
        )
        let action = MeetingDetectionPolicy().action(
            for: decision,
            settings: MeetingDetectionSettingsSnapshot(
                detectionMode: .detectAndAsk,
                targetScopedAutoRecordEnabled: true,
                autoRecordTargetIds: ["yandex_telemost"],
                assistedAutoStartAuthorized: false
            ),
            prerequisites: MeetingDetectionCapturePrerequisites()
        )

        XCTAssertEqual(action, .prompt(targetID: "yandex_telemost"))
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
        let stream = MacOSAudioOwnershipLogStream(configuration: configuration)
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
        let stream = MacOSAudioOwnershipLogStream(configuration: configuration)
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
        let stream = MacOSAudioOwnershipLogStream(configuration: configuration)
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
        let stream = MacOSAudioOwnershipLogStream(configuration: configuration)
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
        let stream = MacOSAudioOwnershipLogStream(configuration: configuration)
        var snapshotEvents: [MacOSAudioOwnershipEvent] = []

        for await observation in stream.observations() {
            switch observation {
            case .snapshot(let events, generation: 1):
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
        let stream = MacOSAudioOwnershipLogStream(configuration: configuration)
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
        let stream = MacOSAudioOwnershipLogStream(configuration: configuration)
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
        var settings = MeetingDetectionSettings()
        settings.targetScopedAutoRecordEnabled = true
        settings.autoRecordTargetIds = ["yandex_telemost"]
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
                prerequisites: blocked,
                assistedAutoStartAuthorized: true
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
                settings: settings,
                assistedAutoStartAuthorized: true
            ).isEmpty
        )
        XCTAssertEqual(
            detector.advance(
                now: Date(timeIntervalSince1970: 104),
                registry: registry,
                settings: settings,
                assistedAutoStartAuthorized: true
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
        var settings = MeetingDetectionSettings()
        settings.targetScopedAutoRecordEnabled = true
        settings.autoRecordTargetIds = ["yandex_telemost"]
        let event = MacOSAudioOwnershipEvent(
            bundleID: "ru.yandex.desktop.telemost",
            displayName: "Yandex Telemost",
            state: .active,
            observedAt: Date(timeIntervalSince1970: 100)
        )

        _ = detector.handle(
            event: event,
            registry: registry,
            settings: settings,
            assistedAutoStartAuthorized: true
        )

        XCTAssertEqual(
            detector.advance(
                now: Date(timeIntervalSince1970: 106),
                registry: registry,
                settings: settings,
                assistedAutoStartAuthorized: true
            ),
            [.autoRecordEligible(targetID: "yandex_telemost", bundleID: "ru.yandex.desktop.telemost")]
        )
        XCTAssertTrue(
            detector.advance(
                now: Date(timeIntervalSince1970: 107),
                registry: registry,
                settings: settings,
                assistedAutoStartAuthorized: true
            ).isEmpty
        )
    }

    func testDetectorSelectedTargetWithoutAcknowledgementEmitsPromptInsteadOfAutoRecord() throws {
        let registry = try MeetingDetectionPolicyTests.registry()
        let detector = MacOSMeetingActivityDetector(debounceSeconds: 1)
        let settings = MeetingDetectionSettings(
            detectionMode: .detectAndAsk,
            targetScopedAutoRecordEnabled: true,
            autoRecordTargetIds: ["yandex_telemost"]
        )
        _ = detector.handle(
            event: MacOSAudioOwnershipEvent(
                bundleID: "ru.yandex.desktop.telemost",
                state: .active,
                observedAt: Date(timeIntervalSince1970: 100)
            ),
            registry: registry,
            settings: settings,
            assistedAutoStartAuthorized: false
        )

        XCTAssertEqual(
            detector.advance(
                now: Date(timeIntervalSince1970: 102),
                registry: registry,
                settings: settings,
                assistedAutoStartAuthorized: false
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

    private static func registry() throws -> MeetingTargetRegistryDocument {
        try MeetingDetectionCoding.decoder().decode(
            MeetingTargetRegistryDocument.self,
            from: MeetingTargetRegistryTests.seedRegistryData()
        )
    }
}
#endif
