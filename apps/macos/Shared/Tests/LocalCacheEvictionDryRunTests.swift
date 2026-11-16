import Foundation
import XCTest
import TwoBrainRecShared
@testable import TwoBrainRecAppCore

final class LocalCacheEvictionDryRunTests: XCTestCase {
    private var root: URL!
    private var recordingsRoot: URL!
    private var queueURL: URL!
    private var reportDirectory: URL!
    private let now = Date(timeIntervalSince1970: 1_800_000_000)
    private static let serverRevision = "11111111-1111-4111-8111-111111111111"

    override func setUpWithError() throws {
        root = FileManager.default.temporaryDirectory
            .appendingPathComponent("f296-dry-run-\(UUID().uuidString)", isDirectory: true)
        recordingsRoot = root.appendingPathComponent("Recordings", isDirectory: true)
        reportDirectory = root.appendingPathComponent("LocalCacheEviction", isDirectory: true)
        queueURL = root.appendingPathComponent("upload-queue.json")
        try FileManager.default.createDirectory(at: recordingsRoot, withIntermediateDirectories: true)
    }

    override func tearDownWithError() throws {
        if let root {
            try? FileManager.default.removeItem(at: root)
        }
    }

    func testDryRunDoesNotMutateQueueOrRecordings() async throws {
        let items = try [
            makeFixtureItem(directoryId: "recording-1", revision: "rev-1", meetingId: "meeting-1"),
            makeFixtureItem(directoryId: "recording-2", revision: "rev-2", meetingId: "meeting-2"),
        ]
        try writeQueue(schemaVersion: "desktop-upload-queue.v1", items: items)
        let queueBytesBefore = try Data(contentsOf: queueURL)
        let queueStateBefore = try queueSnapshot()
        let queueMtimeBefore = try modificationDate(queueURL)
        let treeBefore = try treeSignature(recordingsRoot)

        let outcome = await makeService(
            client: makeProofFetcher(),
            scope: try scope()
        ).run()

        guard case .completed(_, _, let inspected, let eligible, let eligibleBytes) = outcome else {
            return XCTFail("unexpected outcome \(outcome)")
        }
        XCTAssertEqual(inspected, 2)
        XCTAssertEqual(eligible, 2)
        XCTAssertGreaterThan(eligibleBytes, 0)
        XCTAssertEqual(try Data(contentsOf: queueURL), queueBytesBefore)
        XCTAssertEqual(try queueSnapshot(), queueStateBefore)
        XCTAssertEqual(try modificationDate(queueURL), queueMtimeBefore)
        XCTAssertEqual(try treeSignature(recordingsRoot), treeBefore)
        XCTAssertFalse(FileManager.default.fileExists(
            atPath: root.appendingPathComponent("Quarantine").path
        ))
        XCTAssertFalse(FileManager.default.fileExists(
            atPath: queueURL.deletingLastPathComponent().appendingPathComponent("Quarantine").path
        ))

        let report = try readReport()
        XCTAssertEqual(report["schemaVersion"] as? String, "local-cache-eviction-dry-run.v1")
        XCTAssertEqual((report["totals"] as? [String: Any])?["inspected"] as? Int, 2)
        XCTAssertEqual((report["totals"] as? [String: Any])?["eligible"] as? Int, 2)
        XCTAssertEqual(report["truncated"] as? Bool, false)
        XCTAssertEqual(report["availableItemCount"] as? Int, 2)
        let rawJSON = String(decoding: try Data(contentsOf: queueURL), as: UTF8.self)
        XCTAssertTrue(rawJSON.contains("desktop-upload-queue.v1"))
    }

    func testMalformedItemIsReportedWithoutQuarantineOrRewrite() async throws {
        let valid = try makeFixtureItem(directoryId: "recording-valid", revision: "rev-1",
                                        meetingId: "meeting-1")
        try writeQueue(
            schemaVersion: "desktop-upload-queue.v1",
            items: [],
            rawItems: [try encodedItem(valid), ["id": 42]]
        )
        let queueBytesBefore = try Data(contentsOf: queueURL)
        let queueStateBefore = try queueSnapshot()

        let outcome = await makeService(client: makeProofFetcher(), scope: try scope()).run()

        guard case .completed(_, _, let inspected, let eligible, _) = outcome else {
            return XCTFail("unexpected outcome \(outcome)")
        }
        XCTAssertEqual(inspected, 2)
        XCTAssertEqual(eligible, 1)

        let report = try readReport()
        let reportItems = try XCTUnwrap(report["items"] as? [[String: Any]])
        let undecodable = reportItems.filter { $0["state"] as? String == "undecodable" }
        XCTAssertEqual(undecodable.count, 1)
        XCTAssertEqual(undecodable.first?["primaryReason"] as? String, "queue_item_undecodable")
        XCTAssertEqual(undecodable.first?["verdict"] as? String, "keep")
        XCTAssertEqual(undecodable.first?["bytes"] as? Int, 0)
        XCTAssertNil(undecodable.first?["server"])

        XCTAssertEqual(try Data(contentsOf: queueURL), queueBytesBefore)
        XCTAssertEqual(try queueSnapshot(), queueStateBefore)
        XCTAssertFalse(FileManager.default.fileExists(
            atPath: queueURL.deletingLastPathComponent().appendingPathComponent("Quarantine").path
        ))
    }

    func testScopeChangeAbortsWithoutWritingAReport() async throws {
        let item = try makeFixtureItem(directoryId: "recording-1", revision: "rev-1",
                                       meetingId: "meeting-1")
        try writeQueue(schemaVersion: "desktop-upload-queue.v3", items: [item])
        let fence = FenceBox(allowedChecks: 3)

        let outcome = await makeService(
            client: makeProofFetcher(),
            scope: try scope(),
            runFence: { fence.check() }
        ).run()

        XCTAssertEqual(outcome, .abortedScopeChanged)
        XCTAssertFalse(FileManager.default.fileExists(atPath: reportDirectory.path))
    }

    func testFootprintUsesActualBytesInsteadOfHistoricalQueueMetadata() async throws {
        let first = try makeFixtureItem(
            directoryId: "recording-large-1",
            revision: "rev-1",
            meetingId: "meeting-1",
            mediaBytes: 1_500_000_000
        )
        let second = try makeFixtureItem(
            directoryId: "recording-large-2",
            revision: "rev-2",
            meetingId: "meeting-2"
        )
        try writeQueue(schemaVersion: "desktop-upload-queue.v1", items: [first, second])
        let measured: [String: Int64] = [
            "recording-large-1": 600_000_000,
            "recording-large-2": 500_000_000,
        ]

        let outcome = await makeService(
            client: makeProofFetcher(),
            scope: try scope(),
            measureFootprint: { url in measured[url.lastPathComponent] ?? 0 }
        ).run()

        guard case .completed(_, _, let inspected, _, _) = outcome else {
            return XCTFail("unexpected outcome \(outcome)")
        }
        XCTAssertEqual(inspected, 2)
        let report = try readReport()
        let totals = try XCTUnwrap(report["totals"] as? [String: Any])
        let eligibleBytes = totals["eligibleBytes"] as? Int64 ?? Int64(totals["eligibleBytes"] as? Int ?? 0)
        let rejectedBytes = totals["rejectedBytes"] as? Int64 ?? Int64(totals["rejectedBytes"] as? Int ?? 0)
        XCTAssertEqual(eligibleBytes + rejectedBytes, 1_100_000_000)
        let json = String(decoding: try JSONSerialization.data(withJSONObject: report), as: UTF8.self)
        XCTAssertFalse(json.contains("1500000000"))
        XCTAssertEqual((report["items"] as? [[String: Any]])?.compactMap { $0["bytes"] as? Int }.sorted(), [
            500_000_000, 600_000_000,
        ])
    }

    func testReportDirectoryInsideRecordingsRootIsRejected() async throws {
        let item = try makeFixtureItem(directoryId: "recording-1", revision: "rev-1",
                                       meetingId: "meeting-1")
        try writeQueue(schemaVersion: "desktop-upload-queue.v1", items: [item])
        let inside = recordingsRoot.appendingPathComponent("Reports", isDirectory: true)

        let now = self.now
        let outcome = await LocalCacheEvictionDryRunService(
            queueURL: queueURL,
            recordingsRootURL: recordingsRoot,
            reportDirectoryURL: inside,
            client: makeProofFetcher(),
            scope: try scope(),
            clock: { now }
        ).run()

        XCTAssertEqual(outcome, .reportDirectoryRejected)
        XCTAssertFalse(FileManager.default.fileExists(atPath: inside.path))
    }

    func testHashMismatchIsNotPotentiallyEligible() async throws {
        let item = try makeFixtureItem(
            directoryId: "recording-hash-mismatch",
            revision: "rev-1",
            meetingId: "meeting-1",
            mediaSha: String(repeating: "f", count: 64)
        )
        try writeQueue(schemaVersion: "desktop-upload-queue.v1", items: [item])

        let outcome = await makeService(client: makeProofFetcher(), scope: try scope()).run()

        guard case .completed(_, _, let inspected, let eligible, let eligibleBytes) = outcome else {
            return XCTFail("unexpected outcome \(outcome)")
        }
        XCTAssertEqual(inspected, 1)
        XCTAssertEqual(eligible, 0)
        XCTAssertEqual(eligibleBytes, 0)
        let report = try readReport()
        let reportItem = try XCTUnwrap((report["items"] as? [[String: Any]])?.first)
        XCTAssertEqual(reportItem["verdict"] as? String, "keep")
        XCTAssertEqual(reportItem["primaryReason"] as? String, "local_integrity_unverified")
    }

    func testNoProofClientNeverBecomesEligible() async throws {
        let item = try makeFixtureItem(directoryId: "recording-1", revision: "rev-1",
                                       meetingId: "meeting-1")
        try writeQueue(schemaVersion: "desktop-upload-queue.v1", items: [item])

        let outcome = await makeService(client: nil, scope: try scope()).run()

        guard case .completed(_, _, let inspected, let eligible, let eligibleBytes) = outcome else {
            return XCTFail("unexpected outcome \(outcome)")
        }
        XCTAssertEqual(inspected, 1)
        XCTAssertEqual(eligible, 0)
        XCTAssertEqual(eligibleBytes, 0)
        let report = try readReport()
        let reportItem = try XCTUnwrap((report["items"] as? [[String: Any]])?.first)
        XCTAssertEqual(reportItem["verdict"] as? String, "keep")
        XCTAssertEqual(reportItem["primaryReason"] as? String, "dependency_unavailable")
    }

    func testRunIsBoundedTo200ItemsAndTwoConcurrentRequests() async throws {
        let template = try makeFixtureItem(
            directoryId: "template",
            revision: "rev-template",
            meetingId: "meeting-template"
        )
        var rawItems: [Any] = []
        for index in 0..<205 {
            var item = template
            item.id = "queue-\(index)"
            item.sessionId = "session-\(index)"
            item.directoryId = "recording-\(index)"
            item.localMediaRevisionId = "rev-\(index)"
            item.meetingId = "meeting-\(index)"
            item.serverTruth.meetingId = "meeting-\(index)"
            rawItems.append(try encodedItemObject(item))
        }
        try writeQueue(schemaVersion: "desktop-upload-queue.v1", items: [], rawItems: rawItems)
        let probe = ConcurrencyProbe()
        let now = self.now

        let outcome = await makeService(
            client: FakeProofFetcher(fingerprint: "session") { item in
                await probe.enter()
                try? await Task.sleep(nanoseconds: 5_000_000)
                await probe.leave()
                return LocalCacheEvictionDryRunTests.reconciliation(for: item, now: now)
            },
            scope: try scope()
        ).run()

        guard case .completed(_, _, let inspected, _, _) = outcome else {
            return XCTFail("unexpected outcome \(outcome)")
        }
        XCTAssertEqual(inspected, 200)
        let report = try readReport()
        XCTAssertEqual(report["truncated"] as? Bool, true)
        XCTAssertEqual(report["availableItemCount"] as? Int, 205)
        let maximum = await probe.maximumConcurrency()
        XCTAssertLessThanOrEqual(maximum, 2)
        XCTAssertGreaterThan(maximum, 1)
    }

    func testRequestTimeoutBecomesDependencyUnavailable() async throws {
        let item = try makeFixtureItem(directoryId: "recording-1", revision: "rev-1",
                                       meetingId: "meeting-1")
        try writeQueue(schemaVersion: "desktop-upload-queue.v1", items: [item])
        let configuration = LocalCacheEvictionDryRunConfiguration(
            requestTimeout: 0.05,
            totalTimeout: 5,
            footprintTimeout: 2
        )

        let outcome = await makeService(
            client: FakeProofFetcher(fingerprint: "session") { _ in
                try await Task.sleep(nanoseconds: 5_000_000_000)
                return nil
            },
            scope: try scope(),
            configuration: configuration
        ).run()

        guard case .completed(_, _, let inspected, let eligible, _) = outcome else {
            return XCTFail("unexpected outcome \(outcome)")
        }
        XCTAssertEqual(inspected, 1)
        XCTAssertEqual(eligible, 0)
        let report = try readReport()
        let reportItem = try XCTUnwrap((report["items"] as? [[String: Any]])?.first)
        XCTAssertEqual(reportItem["allReasons"] as? [String], ["dependency_unavailable"])
    }

    func testReportIsWrittenAtomicallyWithOwnerOnlyPermissions() async throws {
        let item = try makeFixtureItem(directoryId: "recording-1", revision: "rev-1",
                                       meetingId: "meeting-1")
        try writeQueue(schemaVersion: "desktop-upload-queue.v1", items: [item])

        let outcome = await makeService(client: makeProofFetcher(), scope: try scope()).run()

        guard case .completed(let reportURL, let latestURL, _, _, _) = outcome else {
            return XCTFail("unexpected outcome \(outcome)")
        }
        XCTAssertTrue(FileManager.default.fileExists(atPath: reportURL.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: latestURL.path))
        XCTAssertTrue(LocalCustodyFileProtection.isProtected(reportURL))
        XCTAssertTrue(LocalCustodyFileProtection.isProtected(latestURL))
        XCTAssertEqual(try Data(contentsOf: reportURL), try Data(contentsOf: latestURL))
        let files = try FileManager.default.contentsOfDirectory(atPath: reportDirectory.path)
        XCTAssertEqual(files.count, 2)
    }

    func testDiagnosticsEntryPointRequiresAnExplicitOptIn() async {
        let outcome = await LocalCacheEvictionDryRunDiagnostics.runIfRequested(
            environment: [:],
            queueURL: queueURL,
            recordingsRootURL: recordingsRoot,
            reportDirectoryURL: reportDirectory,
            log: { _ in }
        )
        XCTAssertEqual(outcome, .notRequested)
        XCTAssertFalse(FileManager.default.fileExists(atPath: reportDirectory.path))
    }

    func testDiagnosticsFingerprintFenceAbortsWithoutWritingAReport() async throws {
        try writeQueue(schemaVersion: "desktop-upload-queue.v1", items: [])
        let fingerprint = FingerprintSequenceBox(["session-a", "session-b"])

        let outcome = await LocalCacheEvictionDryRunDiagnostics.runIfRequested(
            environment: [LocalCacheEvictionDryRunDiagnostics.environmentKey: "1"],
            queueURL: queueURL,
            recordingsRootURL: recordingsRoot,
            reportDirectoryURL: reportDirectory,
            client: nil,
            scopeResolver: { nil },
            fingerprintProvider: { fingerprint.next() },
            log: { _ in }
        )

        XCTAssertEqual(outcome, .abortedScopeChanged)
        XCTAssertFalse(FileManager.default.fileExists(atPath: reportDirectory.path))
    }

    func testDiagnosticsStableFingerprintWritesAReport() async throws {
        try writeQueue(schemaVersion: "desktop-upload-queue.v1", items: [])

        let outcome = await LocalCacheEvictionDryRunDiagnostics.runIfRequested(
            environment: [LocalCacheEvictionDryRunDiagnostics.environmentKey: "1"],
            queueURL: queueURL,
            recordingsRootURL: recordingsRoot,
            reportDirectoryURL: reportDirectory,
            client: nil,
            scopeResolver: { nil },
            fingerprintProvider: { "session-a" },
            log: { _ in }
        )

        guard case .completed(_, _, let inspected, let eligible, let eligibleBytes) = outcome else {
            return XCTFail("unexpected outcome \(outcome)")
        }
        XCTAssertEqual(inspected, 0)
        XCTAssertEqual(eligible, 0)
        XCTAssertEqual(eligibleBytes, 0)
        XCTAssertTrue(FileManager.default.fileExists(atPath: reportDirectory.path))
    }

    func testReportContainsNoLocalPathsOrRawIdentities() async throws {
        let item = try makeFixtureItem(directoryId: "private-recording",
                                       revision: "private-revision",
                                       meetingId: "private-meeting")
        try writeQueue(schemaVersion: "desktop-upload-queue.v1", items: [item])

        _ = await makeService(client: makeProofFetcher(), scope: try scope()).run()

        let json = String(decoding: try JSONSerialization.data(withJSONObject: try readReport()),
                          as: UTF8.self)
        XCTAssertFalse(json.contains(root.path))
        XCTAssertFalse(json.contains("private-recording"))
        XCTAssertFalse(json.contains("private-revision"))
        XCTAssertFalse(json.contains("private-meeting"))
        XCTAssertTrue(json.contains("rec_fpr_"))
        XCTAssertFalse(json.contains("meeting-transcription.wav"))
    }

    // MARK: - Service fixture

    private func makeService(
        client: (any DesktopServerProofFetching)?,
        scope: RecordingDeletionScope,
        configuration: LocalCacheEvictionDryRunConfiguration = LocalCacheEvictionDryRunConfiguration(),
        runFence: (@Sendable () -> Bool)? = nil,
        measureFootprint: @escaping @Sendable (URL) throws -> Int64 = {
            try LocalRecordingFootprintMeasurer.measure(at: $0).bytes
        }
    ) -> LocalCacheEvictionDryRunService {
        let now = self.now
        return LocalCacheEvictionDryRunService(
            queueURL: queueURL,
            recordingsRootURL: recordingsRoot,
            reportDirectoryURL: reportDirectory,
            client: client,
            configuration: configuration,
            scope: scope,
            runFence: runFence,
            clock: { now },
            measureFootprint: measureFootprint
        )
    }

    private func makeProofFetcher() -> FakeProofFetcher {
        let now = self.now
        return FakeProofFetcher(fingerprint: "session") { item in
            LocalCacheEvictionDryRunTests.reconciliation(for: item, now: now)
        }
    }

    private static func reconciliation(
        for item: DesktopUploadQueueItem,
        now: Date
    ) -> DesktopUploadReconciliation {
        DesktopUploadReconciliation(
            serverTruth: item.serverTruth,
            conflictState: .none,
            proof: DesktopServerProof(
                meetingId: item.meetingId,
                deletionState: "none",
                accessState: "owner",
                conflictState: "none",
                playback: DesktopPlaybackProof(
                    state: "available",
                    canPlay: true,
                    reasonCode: "canonical_ready",
                    mediaRevisionId: LocalCacheEvictionDryRunTests.serverRevision,
                    localMediaRevisionId: item.localMediaRevisionId,
                    objectVerified: true,
                    verifiedAt: ServerTimestamp(date: now.addingTimeInterval(-10)),
                    automaticRecovery: false
                ),
                uploadSession: DesktopUploadSessionProof(sessionId: "active-session", status: "active"),
                finalizedUpload: DesktopFinalizedUploadProof(
                    sessionId: "session-1",
                    mediaRevisionId: LocalCacheEvictionDryRunTests.serverRevision,
                    localMediaRevisionId: item.localMediaRevisionId,
                    archiveAudio: true,
                    finalizedAt: ServerTimestamp(date: now.addingTimeInterval(-8 * 24 * 60 * 60)),
                    status: "finalized"
                ),
                retention: DesktopRetentionProof(
                    deleteAfter: ServerTimestamp(date: now.addingTimeInterval(300 * 24 * 60 * 60)),
                    policyState: "active"
                )
            ),
            fetchedAt: now.addingTimeInterval(-1)
        )
    }

    // MARK: - Queue and artifact fixtures

    private func scope() throws -> RecordingDeletionScope {
        try RecordingDeletionScope(
            serverOrigin: "https://sync.invalid",
            workspaceID: "workspace-a",
            actorUserID: "owner-a"
        )
    }

    private func makeFixtureItem(
        directoryId: String,
        revision: String,
        meetingId: String,
        mediaBytes: Int64 = 1_000,
        mediaSha: String? = nil
    ) throws -> DesktopUploadQueueItem {
        let directory = recordingsRoot.appendingPathComponent(directoryId, isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let wavData = Data(repeating: 2, count: 1_000)
        try Data(repeating: 1, count: 128).write(to: directory.appendingPathComponent("manifest.json"))
        try wavData.write(to: directory.appendingPathComponent("meeting-transcription.wav"))
        try Data(repeating: 3, count: 500).write(to: directory.appendingPathComponent("meeting-review.m4a"))

        return DesktopUploadQueueItem(
            id: "queue-\(directoryId)",
            sessionId: "session-\(directoryId)",
            directoryId: directoryId,
            localMediaRevisionId: revision,
            directoryPath: directory.path,
            manifestPath: directory.appendingPathComponent("manifest.json").path,
            microphonePath: "metadata-only",
            systemAudioPath: "metadata-only",
            state: .uploaded,
            retryMode: .terminal,
            retentionDeadline: now.addingTimeInterval(300 * 24 * 60 * 60),
            createdAt: now.addingTimeInterval(-400 * 24 * 60 * 60),
            updatedAt: now.addingTimeInterval(-60 * 24 * 60 * 60),
            meetingId: meetingId,
            mediaRevisionId: "media-\(revision)",
            artifactProfile: ArtifactCompletenessProfile(
                schemaVersion: LocalRecordingManifest.schemaVersion,
                manifestPresent: true,
                microphonePresent: false,
                systemAudioPresent: false,
                manifestSha256: String(repeating: "a", count: 64),
                microphoneSha256: nil,
                systemAudioSha256: nil,
                manifestSizeBytes: 128,
                microphoneSizeBytes: 0,
                systemAudioSizeBytes: 0,
                durationSeconds: 60,
                trackCompleteness: [
                    UploadTrackCompleteness(
                        transportRole: .manifest,
                        fileName: "manifest.json",
                        present: true,
                        byteCount: 128,
                        sha256: String(repeating: "a", count: 64),
                        durationSeconds: 1
                    ),
                    UploadTrackCompleteness(
                        transportRole: .media,
                        fileName: "meeting-transcription.wav",
                        present: true,
                        byteCount: mediaBytes,
                        sha256: mediaSha ?? LocalCacheFingerprint.sha256Hex(wavData),
                        durationSeconds: 60
                    ),
                    UploadTrackCompleteness(
                        transportRole: .playback,
                        fileName: "meeting-review.m4a",
                        present: true,
                        byteCount: 500,
                        sha256: String(repeating: "c", count: 64),
                        durationSeconds: 60
                    ),
                ],
                isUploadable: true
            ),
            serverTruth: ServerTruthFingerprint(
                meetingId: meetingId,
                uploadStatus: "finalized"
            ),
            retentionDecision: RetentionDecision(
                decision: .retain,
                decidedAt: now,
                reason: "test",
                localArtifactsRetained: true,
                policyReference: "test"
            )
        ).withOwnerScope(try scope())
    }

    private func encodedItem(_ item: DesktopUploadQueueItem) throws -> Any {
        try encodedItemObject(item)
    }

    private func encodedItemObject(_ item: DesktopUploadQueueItem) throws -> Any {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        let data = try encoder.encode(item)
        return try JSONSerialization.jsonObject(with: data)
    }

    private func writeQueue(
        schemaVersion: String,
        items: [DesktopUploadQueueItem],
        rawItems: [Any]? = nil
    ) throws {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        let object: [String: Any] = [
            "schemaVersion": schemaVersion,
            "updatedAt": ISO8601DateFormatter().string(from: now),
            "items": try rawItems ?? items.map(encodedItemObject),
        ]
        let data = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
        try data.write(to: queueURL, options: .atomic)
    }

    private func modificationDate(_ url: URL) throws -> Date {
        let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
        return try XCTUnwrap(attributes[.modificationDate] as? Date)
    }

    private func queueSnapshot() throws -> NSDictionary {
        try XCTUnwrap(
            try JSONSerialization.jsonObject(with: Data(contentsOf: queueURL)) as? NSDictionary
        )
    }

    private func treeSignature(_ root: URL) throws -> [String: String] {
        guard let enumerator = FileManager.default.enumerator(
            at: root,
            includingPropertiesForKeys: [.isRegularFileKey, .fileSizeKey, .contentModificationDateKey]
        ) else {
            throw CocoaError(.fileReadUnknown)
        }
        var signature: [String: String] = [:]
        for case let url as URL in enumerator {
            let values = try url.resourceValues(forKeys: [
                .isRegularFileKey, .fileSizeKey, .contentModificationDateKey,
            ])
            guard values.isRegularFile == true else { continue }
            let relative = url.path.replacingOccurrences(of: root.path + "/", with: "")
            signature[relative] = "\(values.fileSize ?? 0)|\(values.contentModificationDate?.timeIntervalSince1970 ?? 0)"
        }
        return signature
    }

    private func readReport() throws -> [String: Any] {
        let latest = reportDirectory.appendingPathComponent("latest.json")
        return try XCTUnwrap(
            try JSONSerialization.jsonObject(with: Data(contentsOf: latest)) as? [String: Any]
        )
    }
}

// MARK: - Test doubles

private struct FakeProofFetcher: DesktopServerProofFetching {
    let fingerprint: String?
    let handler: @Sendable (DesktopUploadQueueItem) async throws -> DesktopUploadReconciliation?

    var recordingSessionFingerprint: String? { fingerprint }

    func fetchServerProof(for item: DesktopUploadQueueItem) async throws -> DesktopUploadReconciliation? {
        try await handler(item)
    }
}

private final class FenceBox: @unchecked Sendable {
    private let lock = NSLock()
    private let allowedChecks: Int
    private var checks = 0

    init(allowedChecks: Int) {
        self.allowedChecks = allowedChecks
    }

    func check() -> Bool {
        lock.lock()
        defer { lock.unlock() }
        checks += 1
        return checks <= allowedChecks
    }
}

private final class FingerprintSequenceBox: @unchecked Sendable {
    private let lock = NSLock()
    private let values: [String]
    private var calls = 0

    init(_ values: [String]) {
        self.values = values
    }

    func next() -> String {
        lock.lock(); defer { lock.unlock() }
        let value = values[min(calls, values.count - 1)]
        calls += 1
        return value
    }
}

private actor ConcurrencyProbe {
    private var active = 0
    private var maximum = 0

    func enter() {
        active += 1
        maximum = max(maximum, active)
    }

    func leave() {
        active -= 1
    }

    func maximumConcurrency() -> Int {
        maximum
    }
}

private extension DesktopUploadQueueItem {
    func withOwnerScope(_ scope: RecordingDeletionScope) -> DesktopUploadQueueItem {
        var copy = self
        copy.ownerScope = scope
        copy.isLocalUnbound = false
        return copy
    }
}
