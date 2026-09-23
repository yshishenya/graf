import AVFoundation
import Foundation
import TwoBrainRecShared
@testable import TwoBrainRecAppCore
import XCTest

final class DesktopUploadRetirementTests: XCTestCase {
    func testCurrentEligibilityIsRecheckedAfterReconciliationAndLateUploadResponses() async throws {
        for phase in ["reconcile", "progress", "success", "failure"] {
            let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
            defer { try? FileManager.default.removeItem(at: root) }
            let package = root.appendingPathComponent("package")
            try FileManager.default.createDirectory(at: package, withIntermediateDirectories: true)
            var item = retirementFixture(schema: LocalRecordingManifest.schemaVersion)
            item.id = DesktopUploadQueueItem.deterministicId(directoryId: item.directoryId, sessionId: item.sessionId)
            item.directoryPath = package.path
            item.manifestPath = package.appendingPathComponent("manifest.json").path
            item.ownerScope = try retirementScope()
            let historical = LocalRecordingManifest(schemaVersion: "local-recording-manifest.v4",
                sessionId: item.sessionId, createdAt: Date(timeIntervalSince1970: 10),
                startedAt: Date(timeIntervalSince1970: 10), stoppedAt: Date(timeIntervalSince1970: 80),
                status: .saved, directoryId: item.directoryId, mediaScribeSourceMode: "dual", canonicalMixProfile: nil, tracks: [])
            let file = root.appendingPathComponent("queue.json")
            let encoder = JSONEncoder(); encoder.dateEncodingStrategy = .iso8601
            try encoder.encode(DesktopUploadQueueDocument(updatedAt: Date(), items: [item])).write(to: file)
            let client = RetirementRaceClient(phase: phase)
            let service = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: client,
                clock: { Date(timeIntervalSince1970: 100) })
            service.setDeletionScope(item.ownerScope)
            await client.configure {
                try LocalRecordingManifestService().write(historical, to: package.appendingPathComponent("manifest.json"))
                let scanned = try service.scanAndEnqueueCompletedRecordings()
                XCTAssertEqual(scanned.first?.state, .blocked)
            }
            _ = try await service.processDueItems()
            let restored = try XCTUnwrap(service.loadItems().first)
            XCTAssertEqual(restored.id, item.id, phase)
            XCTAssertEqual(restored.state, .blocked, phase)
            XCTAssertFalse(restored.artifactProfile.isUploadable, phase)
            XCTAssertEqual(restored.failureReason, "unsupported_recording_source", phase)
            XCTAssertNil(restored.nextRetryAt, phase)
            let uploads = await client.uploadCount
            XCTAssertEqual(uploads, phase == "reconcile" ? 0 : 1, phase)
            _ = try await service.processDueItems()
            let repeatedUploads = await client.uploadCount
            XCTAssertEqual(repeatedUploads, uploads, phase)
        }
    }

    func testHistoricalServerProcessingReadAndPendingDeletionSurviveRetirement() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let scope = try retirementScope()
        var uploaded = retirementFixture(schema: "local-recording-manifest.v3")
        uploaded.state = .uploaded
        uploaded.ownerScope = scope
        uploaded.meetingId = "historical-meeting"
        uploaded.serverTruth = ServerTruthFingerprint(meetingId: uploaded.meetingId, processingStatus: "processing")
        var deleting = retirementFixture(schema: "local-recording-manifest.v4")
        deleting.id = "deleting"
        deleting.ownerScope = scope
        deleting.meetingId = UUID().uuidString.lowercased()
        deleting.state = .blocked
        deleting.failureReason = "existing-deletion-reason"
        let operation = try RecordingDeletionOperation(scope: scope, target: .meeting(deleting.meetingId!),
            requestedAt: Date(timeIntervalSince1970: 10))
        let file = root.appendingPathComponent("queue.json")
        let encoder = JSONEncoder(); encoder.dateEncodingStrategy = .iso8601
        try encoder.encode(DesktopUploadQueueDocument(updatedAt: Date(), items: [uploaded, deleting],
            deletionOperations: [operation])).write(to: file)
        let truth = ServerTruthFingerprint(meetingId: uploaded.meetingId, processingStatus: "processed",
            reviewAvailable: true, transcriptAvailable: true)
        let client = RetirementUploadSpy(readTruth: truth)
        let service = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: client,
            clock: { Date(timeIntervalSince1970: 100) })
        service.setDeletionScope(scope)
        _ = try await service.processDueItems()
        let items = try service.loadItems()
        let restored = try XCTUnwrap(items.first { $0.id == uploaded.id })
        XCTAssertEqual(restored.state, .uploaded)
        XCTAssertEqual(restored.serverTruth, truth)
        XCTAssertTrue(DesktopUploadCustodyProjection(item: restored).reviewAvailable)
        let pending = try XCTUnwrap(items.first { $0.id == deleting.id })
        XCTAssertEqual(pending.failureReason, deleting.failureReason)
        XCTAssertEqual(pending.deletionOperation, operation)
        XCTAssertTrue(pending.lifecycleBlocksContent)
        XCTAssertFalse(pending.artifactProfile.isUploadable)
        XCTAssertEqual(try service.currentDeletionOperations(), [operation])
        let uploads = await client.uploads
        XCTAssertTrue(uploads.isEmpty)
    }

    func testHistoricalUploadRejectsBeforeAnyNetworkOrProgressWithOrWithoutServerIdentity() async throws {
        let client = DesktopUploadClient(
            baseURL: URL(string: "https://retirement.invalid")!, headers: [:], partSizeBytes: 64 * 1024,
            authSessionTokenProvider: { _ in nil },
            requestExecutor: { _ in
                XCTFail("Retired packages must not issue even a meeting/session request")
                throw URLError(.cancelled)
            }
        )
        for version in ["local-recording-manifest.v3", "local-recording-manifest.v4", "unknown"] {
            for hasServerIdentity in [false, true] {
                var item = retirementFixture(schema: version)
                if hasServerIdentity {
                    item.meetingId = "existing-meeting"
                    item.uploadSessionId = "existing-session"
                }
                XCTAssertTrue(DesktopUploadClient.uploadFileDescriptors(for: item).isEmpty)
                XCTAssertTrue(DesktopUploadClient.uploadSessionFileDescriptors(for: item).isEmpty)
                do {
                    _ = try await client.upload(item, onProgress: { _ in
                        XCTFail("Validation must precede progress/creation")
                    })
                    XCTFail("Historical upload must fail")
                } catch let error as DesktopUploadClientError {
                    XCTAssertEqual(error.failureCategory, .schemaIncompatibility)
                }
            }
        }
    }

    func testPersistedHistoricalQueuesCannotRetryAndPreserveIdentitiesAcrossRestart() async throws {
        for queueVersion in ["desktop-upload-queue.v1", "desktop-upload-queue.v2", "desktop-upload-queue.v3"] {
            let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
            defer { try? FileManager.default.removeItem(at: root) }
            try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
            let file = root.appendingPathComponent("queue.json")
            let scope = try retirementScope()
            var items: [DesktopUploadQueueItem] = []
            for (index, state) in [UploadItemState.queued, .retrying, .uploading, .blocked, .uploaded, .terminalDeleted].enumerated() {
                var item = retirementFixture(schema: index.isMultiple(of: 2) ? "local-recording-manifest.v3" : "local-recording-manifest.v4")
                item.id = "historical-\(index)"
                item.state = state
                item.ownerScope = scope
                item.meetingId = "meeting-\(index)"
                item.uploadSessionId = "session-\(index)"
                item.nextRetryAt = Date(timeIntervalSince1970: 200)
                item.serverTruth = ServerTruthFingerprint(meetingId: item.meetingId, uploadSessionId: item.uploadSessionId,
                    acceptedBytesByTrack: ["microphone": 100])
                items.append(item)
            }
            let operation = try RecordingDeletionOperation(scope: scope, target: .ownOrigin("unrelated-origin"), requestedAt: Date(timeIntervalSince1970: 10))
            let encoder = JSONEncoder(); encoder.dateEncodingStrategy = .iso8601
            try encoder.encode(DesktopUploadQueueDocument(schemaVersion: queueVersion,
                updatedAt: Date(timeIntervalSince1970: 10), items: items, deletionOperations: [operation])).write(to: file)
            let client = RetirementUploadSpy()
            for _ in 0..<2 {
                let service = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: client,
                    clock: { Date(timeIntervalSince1970: 100) })
                service.setDeletionScope(scope)
                let loaded = try service.loadItems()
                XCTAssertEqual(loaded.count, items.count)
                XCTAssertNil(DesktopUploadQueueService.nextScheduledRetryDate(for: loaded, now: Date(timeIntervalSince1970: 100)))
                for original in items {
                    let restored = try XCTUnwrap(loaded.first { $0.id == original.id })
                    XCTAssertFalse(restored.artifactProfile.isUploadable)
                    XCTAssertEqual(restored.serverTruth, original.serverTruth)
                    XCTAssertEqual(restored.uploadSessionId, original.uploadSessionId)
                    XCTAssertEqual(restored.localMediaRevisionId, original.localMediaRevisionId)
                    XCTAssertEqual(restored.microphonePath, original.microphonePath)
                    XCTAssertEqual(restored.systemAudioPath, original.systemAudioPath)
                    let retried = try service.retry(itemId: original.id)
                    XCTAssertFalse(retried.artifactProfile.isUploadable)
                    XCTAssertFalse(EmbeddedCabinetLocalRecordingRow.rows(for: [retried], recordingsRootURL: root).contains { $0.canSend })
                    XCTAssertNil(retried.nextRetryAt)
                    if original.state == .uploaded || original.state == .terminalDeleted {
                        XCTAssertEqual(retried.state, original.state)
                    } else {
                        XCTAssertEqual(retried.state, .blocked)
                        XCTAssertEqual(retried.failureReason, "unsupported_recording_source")
                        XCTAssertEqual(DesktopUploadCustodyProjection(item: retried).retryClass, .notRetryable)
                    }
                }
                _ = try await service.processDueItems()
                XCTAssertEqual(try service.loadDeletionOperations(scope: scope), [operation])
            }
            let uploads = await client.uploads
            XCTAssertEqual(uploads, [])
        }
    }

    func testMixedQueueUploadsOnlyV5AndRetiredLocalCopyCanStillBeDeleted() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let package = root.appendingPathComponent("historical")
        try FileManager.default.createDirectory(at: package, withIntermediateDirectories: true)
        var historical = retirementFixture(schema: "local-recording-manifest.v3")
        historical.directoryPath = package.path
        historical.manifestPath = package.appendingPathComponent("manifest.json").path
        historical.microphonePath = package.appendingPathComponent("mic.wav").path
        historical.systemAudioPath = package.appendingPathComponent("incoming.wav").path
        let playbackURL = package.appendingPathComponent("meeting-review.m4a")
        let playbackBytes = try writeRetirementPlayback(to: playbackURL)
        historical.artifactProfile.trackCompleteness.append(UploadTrackCompleteness(
            transportRole: .playback, fileName: "meeting-review.m4a", present: true,
            byteCount: playbackBytes, sha256: nil, durationSeconds: 1))
        historical.isLocalUnbound = true
        historical.serverCreationAttempted = false
        for path in [historical.manifestPath, historical.microphonePath, historical.systemAudioPath] {
            try Data("synthetic".utf8).write(to: URL(fileURLWithPath: path))
        }
        var current = retirementFixture(schema: LocalRecordingManifest.schemaVersion)
        current.id = "v5"
        current.ownerScope = try retirementScope()
        let file = root.appendingPathComponent("queue.json")
        let encoder = JSONEncoder(); encoder.dateEncodingStrategy = .iso8601
        try encoder.encode(DesktopUploadQueueDocument(updatedAt: Date(), items: [historical, current])).write(to: file)
        let client = RetirementUploadSpy()
        let service = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: client,
            clock: { Date(timeIntervalSince1970: 100) })
        service.setDeletionScope(current.ownerScope)
        _ = try await service.processDueItems()
        let uploads = await client.uploads
        XCTAssertEqual(uploads, ["v5"])
        XCTAssertTrue(FileManager.default.fileExists(atPath: historical.microphonePath))
        XCTAssertEqual(try service.localPlaybackURL(itemId: historical.id), playbackURL)
        let rows = EmbeddedCabinetLocalRecordingRow.rows(for: try service.loadItems(), recordingsRootURL: root)
        let row = try XCTUnwrap(rows.first { $0.id == historical.id })
        XCTAssertTrue(row.canOpen)
        XCTAssertTrue(row.canDelete)
        XCTAssertFalse(row.canSend)
        let deleted = try service.deleteLocalCopy(itemId: historical.id)
        XCTAssertEqual(deleted.state, .terminalDeleted)
        XCTAssertFalse(FileManager.default.fileExists(atPath: package.path))
    }
}

private func writeRetirementPlayback(to url: URL) throws -> Int64 {
    let format = AVAudioFormat(standardFormatWithSampleRate: 48_000, channels: 1)!
    var file: AVAudioFile? = try AVAudioFile(forWriting: url, settings: [
        AVFormatIDKey: Int(kAudioFormatMPEG4AAC), AVSampleRateKey: 48_000.0,
        AVNumberOfChannelsKey: 1, AVEncoderBitRateKey: 64_000
    ])
    let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: 4_800)!
    buffer.frameLength = 4_800
    buffer.floatChannelData![0].initialize(repeating: 0, count: 4_800)
    try file?.write(from: buffer)
    file = nil
    return (try FileManager.default.attributesOfItem(atPath: url.path)[.size] as! NSNumber).int64Value
}

private func retirementScope() throws -> RecordingDeletionScope {
    try RecordingDeletionScope(serverOrigin: "https://retirement.invalid", workspaceID: "workspace", actorUserID: "owner")
}

/// Historical values exist only to prove persisted-data compatibility and rejection.
private func retirementFixture(schema: String) -> DesktopUploadQueueItem {
    var item = custodyFixtureQueueItem(id: "historical")
    item.artifactProfile.schemaVersion = schema
    item.artifactProfile.isUploadable = true // stale persisted eligibility must never authorize upload
    let current = schema == LocalRecordingManifest.schemaVersion
    item.artifactProfile.trackCompleteness = [
        UploadTrackCompleteness(transportRole: .manifest, fileName: "manifest.json", present: true, byteCount: 128, sha256: String(repeating: "a", count: 64)),
        UploadTrackCompleteness(transportRole: current ? .media : .microphone, fileName: current ? "meeting-transcription.wav" : "mic.wav", present: true, byteCount: 256, sha256: String(repeating: "b", count: 64)),
        UploadTrackCompleteness(transportRole: current ? .playback : .system, fileName: current ? "meeting-review.m4a" : "incoming.wav", present: true, byteCount: 512, sha256: String(repeating: "c", count: 64))
    ]
    return item
}

private actor RetirementUploadSpy: DesktopUploadClientProtocol {
    var uploads: [String] = []
    let readTruth: ServerTruthFingerprint?
    init(readTruth: ServerTruthFingerprint? = nil) { self.readTruth = readTruth }
    func reconcile(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadReconciliation? {
        readTruth.map { DesktopUploadReconciliation(serverTruth: $0) }
    }
    func upload(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadResult {
        uploads.append(item.id)
        return DesktopUploadResult(state: .uploaded, serverTruth: ServerTruthFingerprint(meetingId: "v5-meeting"))
    }
    func listLocalPurgeTasks() async throws -> [DesktopLocalPurgeTask] { [] }
    func acknowledgeLocalPurgeTask(_ task: DesktopLocalPurgeTask, state: DesktopLocalPurgeTaskState, reasonCode: String, completedAt: Date?) async throws -> DesktopLocalPurgeTask { task }
}

private actor RetirementRaceClient: DesktopUploadClientProtocol {
    let phase: String
    var revoke: (@Sendable () throws -> Void)?
    var uploadCount = 0
    init(phase: String) { self.phase = phase }
    func configure(_ revoke: @escaping @Sendable () throws -> Void) { self.revoke = revoke }
    func reconcile(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadReconciliation? {
        if phase == "reconcile" { try revoke?() }
        return DesktopUploadReconciliation(serverTruth: item.serverTruth)
    }
    func upload(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadResult {
        try await upload(item, onProgress: { _ in })
    }
    func upload(_ item: DesktopUploadQueueItem, onProgress: @escaping DesktopUploadProgressHandler) async throws -> DesktopUploadResult {
        uploadCount += 1
        try revoke?()
        if phase == "progress" {
            do {
                try await onProgress(ServerTruthFingerprint(acceptedBytesByTrack: ["media": 128]))
                XCTFail("Progress must cancel an upload whose current package is retired")
            } catch { throw error }
        }
        if phase == "failure" { throw URLError(.networkConnectionLost) }
        return DesktopUploadResult(state: .uploaded, serverTruth: ServerTruthFingerprint(meetingId: "late-meeting"))
    }
    func listLocalPurgeTasks() async throws -> [DesktopLocalPurgeTask] { [] }
    func acknowledgeLocalPurgeTask(_ task: DesktopLocalPurgeTask, state: DesktopLocalPurgeTaskState, reasonCode: String, completedAt: Date?) async throws -> DesktopLocalPurgeTask { task }
}
