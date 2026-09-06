import Foundation
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class MeetingDetectionTelemetryTests: XCTestCase {
    func testLowScoreRollupRedactsUnknownIdentityAndIsNotUploadable() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let store = makeRollupStore(root: root)
        let decision = MeetingDetectionCandidateDecision(
            kind: .suppressed,
            candidateScore: 1,
            candidateReasons: [.stableMicDuration],
            suppressionReasons: [.lowScore]
        )

        let document = try store.recordObservation(
            MeetingDetectionAppObservation(
                bundleID: "com.example.notes",
                displayName: "Notes Helper",
                stableObservationCount: 1,
                activeDurationSeconds: 60
            ),
            decision: decision,
            registryVersion: "2026.07.08.1",
            settings: MeetingDetectionSettings()
        )
        let rollup = try XCTUnwrap(document.unknownNativeAppRollups.first)

        XCTAssertEqual(rollup.identityMode, "redacted")
        XCTAssertEqual(rollup.uploadEligibility, "local_only_low_score")
        XCTAssertNil(rollup.bundleId)
        XCTAssertNil(rollup.displayName)
        XCTAssertNil(MeetingDetectionTelemetryRollupStore.uploadableCopy(of: document))
    }

    func testHighScoreCandidateUploadSendsMetadataOnlyPayloadAndDeletesRollup() async throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let store = makeRollupStore(root: root)
        let settingsStore = MeetingDetectionSettingsStore(settingsURL: root.appendingPathComponent("settings.json"))
        try settingsStore.save(MeetingDetectionSettings())
        let transport = FakeMeetingDetectionTelemetryTransport()
        let uploader = MeetingDetectionTelemetryUploader(
            rollupStore: store,
            settingsStore: settingsStore,
            transport: transport,
            stateURL: root.appendingPathComponent("uploader-state.json"),
            clock: { Date(timeIntervalSince1970: 1_783_440_000) }
        )
        let decision = MeetingDetectionCandidateDecision(
            kind: .candidateUpload,
            candidateScore: 8,
            candidateReasons: [.stableMicDuration, .vksNameToken, .calendarOrJoinHint]
        )
        _ = try store.recordObservation(
            MeetingDetectionAppObservation(
                bundleID: "ru.trueconf.client",
                displayName: "TrueConf Meeting",
                signingTeamID: "ABCDE12345",
                version: "1.0.0",
                stableObservationCount: 4,
                activeDurationSeconds: 900,
                manualRecordNearbyCount: 1,
                calendarOrJoinHintCount: 1
            ),
            decision: decision,
            registryVersion: "2026.07.08.1",
            settings: MeetingDetectionSettings(),
            now: Date(timeIntervalSince1970: 1_783_440_000)
        )

        let outcome = try await uploader.uploadPending()
        let request = try XCTUnwrap(transport.requests.first)
        let uploaded = try MeetingDetectionCoding.decoder().decode(
            MeetingDetectionTelemetryDocument.self,
            from: request.body
        )

        XCTAssertEqual(outcome.uploadedCount, 1)
        XCTAssertEqual(request.path, MeetingDetectionTelemetryUploader.telemetryPath)
        XCTAssertTrue(request.idempotencyKey.hasPrefix("meeting-detection:2026.07.08.1:"))
        XCTAssertEqual(uploaded.unknownNativeAppRollups.first?.bundleId, "ru.trueconf.client")
        XCTAssertEqual(uploaded.unknownNativeAppRollups.first?.displayName, "TrueConf Meeting")
        XCTAssertFalse(String(data: request.body, encoding: .utf8)?.lowercased().contains("audio") ?? true)
        XCTAssertTrue(try store.pendingDocuments().isEmpty)
    }

    func testRollupRetentionRemovesOldFiles() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let store = makeRollupStore(root: root)
        let oldDate = Date(timeIntervalSince1970: 1_780_000_000)
        let newDate = Date(timeIntervalSince1970: 1_783_440_000)
        let decision = MeetingDetectionCandidateDecision(
            kind: .candidateUpload,
            candidateScore: 8,
            candidateReasons: [.stableMicDuration, .vksNameToken]
        )
        _ = try store.recordObservation(
            Self.uploadableObservation(),
            decision: decision,
            registryVersion: "2026.07.08.1",
            settings: MeetingDetectionSettings(),
            now: oldDate
        )
        let oldURL = store.documentURL(for: oldDate)
        try FileManager.default.setAttributes([.modificationDate: oldDate], ofItemAtPath: oldURL.path)

        let removed = try store.prune(now: newDate, maxAgeDays: 14)

        XCTAssertTrue(removed.map(\.lastPathComponent).contains(oldURL.lastPathComponent))
        XCTAssertFalse(FileManager.default.fileExists(atPath: oldURL.path))
        XCTAssertTrue(try store.pendingDocuments().isEmpty)
    }

    func testRecordObservationPrunesExpiredRollupsAfterWriting() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let store = makeRollupStore(root: root)
        let oldDate = Date(timeIntervalSince1970: 1_780_000_000)
        let newDate = Date(timeIntervalSince1970: 1_783_440_000)
        let decision = MeetingDetectionCandidateDecision(
            kind: .candidateUpload,
            candidateScore: 8,
            candidateReasons: [.stableMicDuration, .vksNameToken]
        )
        _ = try store.recordObservation(
            Self.uploadableObservation(),
            decision: decision,
            registryVersion: "2026.07.08.1",
            settings: MeetingDetectionSettings(),
            now: oldDate
        )
        let oldURL = store.documentURL(for: oldDate)
        try FileManager.default.setAttributes([.modificationDate: oldDate], ofItemAtPath: oldURL.path)
        _ = try store.recordObservation(
            Self.uploadableObservation(),
            decision: decision,
            registryVersion: "2026.07.08.1",
            settings: MeetingDetectionSettings(),
            now: newDate
        )

        XCTAssertFalse(FileManager.default.fileExists(atPath: oldURL.path))
        XCTAssertEqual(try store.pendingDocuments().count, 1)
    }

    func testUploaderPrunesExpiredRollupsWhenUploadDisabled() async throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let store = makeRollupStore(root: root)
        let settingsStore = MeetingDetectionSettingsStore(settingsURL: root.appendingPathComponent("settings.json"))
        try settingsStore.save(MeetingDetectionSettings(uploadMode: .localOnly))
        let oldDate = Date(timeIntervalSince1970: 1_780_000_000)
        let now = Date(timeIntervalSince1970: 1_783_440_000)
        let uploader = MeetingDetectionTelemetryUploader(
            rollupStore: store,
            settingsStore: settingsStore,
            transport: FakeMeetingDetectionTelemetryTransport(),
            stateURL: root.appendingPathComponent("state.json"),
            clock: { now }
        )
        _ = try store.recordObservation(
            Self.uploadableObservation(),
            decision: MeetingDetectionCandidateDecision(
                kind: .candidateUpload,
                candidateScore: 8,
                candidateReasons: [.stableMicDuration, .vksNameToken]
            ),
            registryVersion: "2026.07.08.1",
            settings: MeetingDetectionSettings(),
            now: oldDate
        )
        let oldURL = store.documentURL(for: oldDate)
        try FileManager.default.setAttributes([.modificationDate: oldDate], ofItemAtPath: oldURL.path)

        let outcome = try await uploader.uploadPending()

        XCTAssertEqual(outcome.skippedReason, "upload_disabled")
        XCTAssertFalse(FileManager.default.fileExists(atPath: oldURL.path))
        XCTAssertTrue(try store.pendingDocuments().isEmpty)
    }

    func testUploaderPrunesExpiredRollupsDuringBackoff() async throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let store = makeRollupStore(root: root)
        let settingsStore = MeetingDetectionSettingsStore(settingsURL: root.appendingPathComponent("settings.json"))
        try settingsStore.save(MeetingDetectionSettings())
        let oldDate = Date(timeIntervalSince1970: 1_780_000_000)
        let now = Date(timeIntervalSince1970: 1_783_440_000)
        let stateURL = root.appendingPathComponent("state.json")
        let uploader = MeetingDetectionTelemetryUploader(
            rollupStore: store,
            settingsStore: settingsStore,
            transport: FakeMeetingDetectionTelemetryTransport(),
            stateURL: stateURL,
            clock: { now }
        )
        try uploader.saveState(MeetingDetectionTelemetryUploaderState(nextAttemptAt: now.addingTimeInterval(60)))
        _ = try store.recordObservation(
            Self.uploadableObservation(),
            decision: MeetingDetectionCandidateDecision(
                kind: .candidateUpload,
                candidateScore: 8,
                candidateReasons: [.stableMicDuration, .vksNameToken]
            ),
            registryVersion: "2026.07.08.1",
            settings: MeetingDetectionSettings(),
            now: oldDate
        )
        let oldURL = store.documentURL(for: oldDate)
        try FileManager.default.setAttributes([.modificationDate: oldDate], ofItemAtPath: oldURL.path)

        let outcome = try await uploader.uploadPending()

        XCTAssertEqual(outcome.skippedReason, "backoff")
        XCTAssertFalse(FileManager.default.fileExists(atPath: oldURL.path))
        XCTAssertTrue(try store.pendingDocuments().isEmpty)
    }

    func testUploaderPersistsBackoffAfterFailureAndSkipsUntilDue() async throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let store = makeRollupStore(root: root)
        let settingsStore = MeetingDetectionSettingsStore(settingsURL: root.appendingPathComponent("settings.json"))
        try settingsStore.save(MeetingDetectionSettings())
        let failingTransport = FakeMeetingDetectionTelemetryTransport(error: TestUploadError.failed)
        let stateURL = root.appendingPathComponent("state.json")
        let now = Date(timeIntervalSince1970: 1_783_440_000)
        let uploader = MeetingDetectionTelemetryUploader(
            rollupStore: store,
            settingsStore: settingsStore,
            transport: failingTransport,
            stateURL: stateURL,
            clock: { now }
        )
        _ = try store.recordObservation(
            Self.uploadableObservation(),
            decision: MeetingDetectionCandidateDecision(
                kind: .candidateUpload,
                candidateScore: 8,
                candidateReasons: [.stableMicDuration, .vksNameToken]
            ),
            registryVersion: "2026.07.08.1",
            settings: MeetingDetectionSettings(),
            now: now
        )

        do {
            _ = try await uploader.uploadPending()
            XCTFail("upload should fail")
        } catch {
            XCTAssertEqual(error as? TestUploadError, .failed)
        }
        let state = try uploader.loadState()
        let retry = MeetingDetectionTelemetryUploader(
            rollupStore: store,
            settingsStore: settingsStore,
            transport: FakeMeetingDetectionTelemetryTransport(),
            stateURL: stateURL,
            clock: { now.addingTimeInterval(60) }
        )
        let retryOutcome = try await retry.uploadPending()

        XCTAssertEqual(state.failureCount, 1)
        XCTAssertGreaterThan(try XCTUnwrap(state.nextAttemptAt), now)
        XCTAssertEqual(retryOutcome.skippedReason, "backoff")
    }

    func testUploaderRespectsServerNextUploadAfterOnSuccess() async throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let store = makeRollupStore(root: root)
        let settingsStore = MeetingDetectionSettingsStore(settingsURL: root.appendingPathComponent("settings.json"))
        try settingsStore.save(MeetingDetectionSettings())
        let now = Date(timeIntervalSince1970: 1_783_440_000)
        let nextUploadAfter = now.addingTimeInterval(86_400)
        let stateURL = root.appendingPathComponent("state.json")
        let uploader = MeetingDetectionTelemetryUploader(
            rollupStore: store,
            settingsStore: settingsStore,
            transport: FakeMeetingDetectionTelemetryTransport(
                response: MeetingDetectionTelemetryUploadResponse(
                    batchId: "batch-test",
                    nextUploadAfter: nextUploadAfter
                )
            ),
            stateURL: stateURL,
            clock: { now }
        )
        _ = try store.recordObservation(
            Self.uploadableObservation(),
            decision: MeetingDetectionCandidateDecision(
                kind: .candidateUpload,
                candidateScore: 8,
                candidateReasons: [.stableMicDuration, .vksNameToken]
            ),
            registryVersion: "2026.07.08.1",
            settings: MeetingDetectionSettings(),
            now: now
        )

        _ = try await uploader.uploadPending()
        let state = try uploader.loadState()
        let retry = MeetingDetectionTelemetryUploader(
            rollupStore: store,
            settingsStore: settingsStore,
            transport: FakeMeetingDetectionTelemetryTransport(),
            stateURL: stateURL,
            clock: { now.addingTimeInterval(60) }
        )
        let retryOutcome = try await retry.uploadPending()

        XCTAssertEqual(state.nextAttemptAt, nextUploadAfter)
        XCTAssertEqual(state.failureCount, 0)
        XCTAssertEqual(retryOutcome.skippedReason, "backoff")
    }

    func testSettingsStorePersistsOnlyThreeStateRulesAndTelemetryPreferences() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let store = MeetingDetectionSettingsStore(settingsURL: root.appendingPathComponent("settings.json"))

        XCTAssertEqual(try store.load().uploadMode, .automaticCandidateUpload)
        XCTAssertEqual(try store.load().recordingRule(for: "yandex_telemost"), .ask)

        try store.save(MeetingDetectionSettings(
            automaticRecordingRules: ["yandex_telemost": .always]
        ))
        let saved = try store.load()

        XCTAssertEqual(saved.recordingRule(for: "yandex_telemost"), .always)
    }

    private func temporaryRoot() -> URL {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("meeting-detection-telemetry-\(UUID().uuidString)", isDirectory: true)
        try? FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        return root
    }

    private func makeRollupStore(root: URL) -> MeetingDetectionTelemetryRollupStore {
        MeetingDetectionTelemetryRollupStore(
            directoryURL: root.appendingPathComponent("rollups", isDirectory: true),
            configuration: MeetingDetectionTelemetryConfiguration(clientVersion: "macos-test", osVersionMajor: "15")
        )
    }

    private static func uploadableObservation() -> MeetingDetectionAppObservation {
        MeetingDetectionAppObservation(
            bundleID: "ru.trueconf.client",
            displayName: "TrueConf Meeting",
            signingTeamID: "ABCDE12345",
            version: "1.0.0",
            stableObservationCount: 4,
            activeDurationSeconds: 900,
            manualRecordNearbyCount: 1,
            calendarOrJoinHintCount: 1
        )
    }
}

private enum TestUploadError: Error, Equatable {
    case failed
}

private final class FakeMeetingDetectionTelemetryTransport: MeetingDetectionTelemetryTransport, @unchecked Sendable {
    private let error: Error?
    private let response: MeetingDetectionTelemetryUploadResponse
    private(set) var requests: [MeetingDetectionTelemetryUploadRequest] = []

    init(
        error: Error? = nil,
        response: MeetingDetectionTelemetryUploadResponse = MeetingDetectionTelemetryUploadResponse(batchId: "batch-test")
    ) {
        self.error = error
        self.response = response
    }

    func upload(_ request: MeetingDetectionTelemetryUploadRequest) async throws -> MeetingDetectionTelemetryUploadResponse {
        if let error {
            throw error
        }
        requests.append(request)
        return response
    }
}
#endif
