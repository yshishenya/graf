import AVFoundation
import CryptoKit
import Foundation
import TwoBrainRecShared
@testable import TwoBrainRecAppCore
import XCTest

final class RecordingDeletionRecoveryAcceptanceTests: XCTestCase {
    func testSavingAndUnboundCaptureRequireExplicitActionBeforeBindingOrDeletion() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let (directory, completed) = try makePackage(root: root)
        let client = RecoveryNetworkProbe()
        let service = DesktopUploadQueueService(queueURL: root.appendingPathComponent("queue.json"), recordingsRootURL: root, client: client)
        var active = completed; active.status = .active
        let saving = try service.enqueueSaving(manifest: active, directoryURL: directory)
        XCTAssertEqual(saving.state, .saving)
        XCTAssertEqual(saving.isLocalUnbound, true)
        XCTAssertFalse(DesktopUploadQueueService.canDeleteLocalCopy(item: saving, recordingsRootURL: root))
        XCTAssertThrowsError(try service.requestDeletion(itemIDs: [saving.id]))
        XCTAssertTrue(try service.currentDeletionOperations().isEmpty)
        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.path))

        let ready = try service.enqueue(manifest: completed, directoryURL: directory)
        XCTAssertEqual(ready.id, saving.id)
        XCTAssertTrue(ready.artifactProfile.isUploadable)
        XCTAssertNil(ready.ownerScope)
        XCTAssertEqual(ready.isLocalUnbound, true)
        XCTAssertEqual(ready.serverCreationAttempted, false)
        let scope = try makeScope()
        service.setDeletionScope(scope)
        _ = try await service.processDueItems()
        let unbound = try XCTUnwrap(service.loadItems().first)
        XCTAssertNil(unbound.ownerScope, "Signing in does not silently bind a local recording")
        XCTAssertEqual(unbound.isLocalUnbound, true)
        let calls = await client.calls
        XCTAssertEqual(calls, 0, "Unbound content cannot reach reconciliation or upload")

        // A separate explicit send action is allowed to bind this otherwise uploadable item.
        let bound = try service.retry(itemId: ready.id)
        XCTAssertEqual(bound.ownerScope, scope)
        XCTAssertEqual(bound.isLocalUnbound, false)
        XCTAssertEqual(bound.id, ready.id)
    }

    func testRetryAfterSurvivesRestartAndDefersEveryOperationInScope() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let scope = try makeScope()
        let attempts = RecoveryNetworkProbe()
        let client = DesktopUploadClient(baseURL: URL(string: scope.serverOrigin)!, headers: [:], partSizeBytes: 65536,
            authSessionTokenProvider: { _ in "synthetic-recovery-session" }, requestExecutor: { request in
                let url = try XCTUnwrap(request.url)
                let body: [String: Any]
                var status = 200
                var headers: [String: String] = [:]
                if url.path.hasSuffix("notification-context") {
                    body = ["workspace_id": scope.workspaceID, "user_id": scope.actorUserID, "recording_deletion_protocol_version": 1]
                } else {
                    let count = await attempts.record()
                    XCTAssertEqual(request.httpMethod, "POST")
                    XCTAssertEqual(request.value(forHTTPHeaderField: "X-Graf-Expected-Actor"), scope.actorUserID)
                    if count == 1 {
                        status = 429; headers["Retry-After"] = "120"
                        body = ["code": "rate_limit_exceeded"]
                    } else {
                        body = ["receipt_type": "meeting_deletion", "request_id": UUID().uuidString,
                                "meeting_id": url.deletingLastPathComponent().lastPathComponent, "deletion_epoch": 1]
                    }
                }
                return (try JSONSerialization.data(withJSONObject: body),
                        try XCTUnwrap(HTTPURLResponse(url: url, statusCode: status, httpVersion: nil, headerFields: headers)))
            })
        let queue = root.appendingPathComponent("queue.json")
        let service = DesktopUploadQueueService(queueURL: queue, recordingsRootURL: root, client: client, clock: { Date(timeIntervalSince1970: 100) })
        try await service.refreshDeletionScope()
        let operations = try (0..<2).map { _ in
            try RecordingDeletionOperation(scope: scope, target: .meeting(UUID().uuidString.lowercased()), requestedAt: Date(timeIntervalSince1970: 1))
        }
        try service.persistDeletionRequests(operations)
        do { try await service.processDeletionRequests(); XCTFail("429 must remain pending") } catch {}
        let pending = try service.currentDeletionOperations()
        XCTAssertEqual(pending[0].phase, .resolving)
        XCTAssertEqual(pending[0].waitReason, .rateLimit)
        XCTAssertTrue(pending.allSatisfy { $0.nextAttemptAt == Date(timeIntervalSince1970: 220) && $0.receipt == nil })
        for seconds in [100.0, 219.0, 220.0] {
            let restarted = DesktopUploadQueueService(queueURL: queue, recordingsRootURL: root, client: client, clock: { Date(timeIntervalSince1970: seconds) })
            _ = try restarted.loadItems()
            try await restarted.processDeletionRequests()
            let stored = try restarted.currentDeletionOperations()
            XCTAssertEqual(stored.map(\.id), operations.map(\.id))
            XCTAssertEqual(stored.map(\.target), operations.map(\.target))
            let count = await attempts.calls
            if seconds < 220 {
                XCTAssertEqual(count, 1)
                XCTAssertEqual(stored, pending)
            } else {
                XCTAssertEqual(count, 3)
                XCTAssertTrue(stored.allSatisfy { $0.phase == .accepted && $0.receipt?.matches($0.target) == true })
            }
        }
    }

    func testUserDeletionSaveFailureLeavesFilesAndMemoryUntouchedBeforeAnyNetwork() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let (directory, manifest) = try makePackage(root: root)
        let queue = root.appendingPathComponent("queue.json")
        let client = RecoveryNetworkProbe()
        let service = DesktopUploadQueueService(queueURL: queue, recordingsRootURL: root, client: client)
        let item = try service.enqueue(manifest: manifest, directoryURL: directory)
        let before = try Data(contentsOf: queue)
        let files = try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
        let bytes = try files.map { try Data(contentsOf: $0) }
        // Keep the already loaded document while making its atomic destination unwritable.
        try FileManager.default.removeItem(at: queue)
        try FileManager.default.createDirectory(at: queue, withIntermediateDirectories: true)
        try Data([1]).write(to: queue.appendingPathComponent("block-replacement"))
        XCTAssertThrowsError(try service.requestDeletion(itemIDs: [item.id]))
        XCTAssertEqual(try service.loadItems(), [item])
        XCTAssertTrue(try service.currentDeletionOperations().isEmpty)
        XCTAssertEqual(try files.map { try Data(contentsOf: $0) }, bytes)
        try FileManager.default.removeItem(at: queue)
        try before.write(to: queue)
        try await service.processDeletionRequests()
        try service.finishLocalOnlyDeletions()
        XCTAssertEqual(try files.map { try Data(contentsOf: $0) }, bytes)
        let calls = await client.calls
        XCTAssertEqual(calls, 0)
    }

    func testRestoredFilesCannotResurrectTerminalOriginDuringRealScan() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let (directory, manifest) = try makePackage(root: root)
        let files = try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
        let backup = try files.map { ($0.lastPathComponent, try Data(contentsOf: $0)) }
        let queue = root.appendingPathComponent("queue.json")
        let service = DesktopUploadQueueService(queueURL: queue, recordingsRootURL: root, client: nil)
        let original = try service.enqueue(manifest: manifest, directoryURL: directory)
        XCTAssertTrue(original.artifactProfile.isUploadable)
        try service.requestDeletion(itemIDs: [original.id])
        try service.finishLocalOnlyDeletions()
        XCTAssertFalse(FileManager.default.fileExists(atPath: directory.path))
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        for (name, bytes) in backup { try bytes.write(to: directory.appendingPathComponent(name)) }
        let client = RecoveryNetworkProbe()
        let restarted = DesktopUploadQueueService(queueURL: queue, recordingsRootURL: root, client: client)
        restarted.setDeletionScope(try makeScope())
        let scanned = try restarted.scanAndEnqueueCompletedRecordings()
        XCTAssertEqual(scanned.count, 1)
        XCTAssertEqual(scanned.first?.id, original.id)
        XCTAssertEqual(scanned.first?.state, .terminalDeleted)
        XCTAssertTrue(try XCTUnwrap(scanned.first).hasConfirmedDeletion)
        XCTAssertTrue(EmbeddedCabinetLocalRecordingRow.rows(for: scanned, recordingsRootURL: root).isEmpty)
        XCTAssertThrowsError(try restarted.localPlaybackURL(itemId: original.id))
        _ = try await restarted.processDueItems()
        let calls = await client.calls
        XCTAssertEqual(calls, 0)
        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.appendingPathComponent("meeting-review.m4a").path), "The restored artifact exists; it is its authority to open/send that is revoked")
    }

    private func makeScope() throws -> RecordingDeletionScope {
        try RecordingDeletionScope(serverOrigin: "https://graf.invalid", workspaceID: UUID().uuidString.lowercased(), actorUserID: UUID().uuidString.lowercased())
    }

    private func makePackage(root: URL) throws -> (URL, LocalRecordingManifest) {
        let directory = root.appendingPathComponent("synthetic-package")
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        var manifest = LocalRecordingManifestService().activeV5Manifest(
            sessionId: "synthetic-session", directoryId: directory.lastPathComponent, startedAt: Date(),
            scopeApproval: CaptureScopeApproval(scopeApprovalId: "synthetic-scope", scopeKind: .display,
                sourceDisplayName: "Synthetic", approvedAt: Date(), approvalMode: .userConfirmedSuggestedScope, eligibleReason: .manualMeetingScope),
            permissions: SystemAudioPermissionSnapshot(microphone: .granted, systemAudio: .granted, evaluatedAt: Date()))
        manifest.status = .saved; manifest.transcriptionReadiness = .ready
        manifest.stoppedAt = manifest.startedAt.addingTimeInterval(1)
        for index in manifest.tracks.indices {
            let playback = manifest.tracks[index].role == .reviewPlayback
            let rate = playback ? 48_000.0 : 16_000.0
            let format = try XCTUnwrap(AVAudioFormat(standardFormatWithSampleRate: rate, channels: 1))
            let buffer = try XCTUnwrap(AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(rate)))
            buffer.frameLength = buffer.frameCapacity
            buffer.floatChannelData![0].initialize(repeating: 0.05, count: Int(buffer.frameLength))
            let url = directory.appendingPathComponent(manifest.tracks[index].fileName)
            let settings: [String: Any] = playback
                ? [AVFormatIDKey: Int(kAudioFormatMPEG4AAC), AVSampleRateKey: rate, AVNumberOfChannelsKey: 1, AVEncoderBitRateKey: 64_000]
                : [AVFormatIDKey: Int(kAudioFormatLinearPCM), AVSampleRateKey: rate, AVNumberOfChannelsKey: 1,
                   AVLinearPCMBitDepthKey: 16, AVLinearPCMIsFloatKey: false, AVLinearPCMIsBigEndianKey: false]
            var file: AVAudioFile? = try AVAudioFile(forWriting: url, settings: settings)
            try file?.write(from: buffer); file = nil
            let bytes = try Data(contentsOf: url)
            manifest.tracks[index].status = .saved
            manifest.tracks[index].durationMs = 1000
            manifest.tracks[index].byteCount = Int64(bytes.count)
            manifest.tracks[index].sha256 = SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
            manifest.tracks[index].frameCount = Int64(rate)
            manifest.tracks[index].timelineStartMs = 0
            manifest.tracks[index].timelineAligned = true
            if playback { manifest.tracks[index].aacPresentationFrameDelta = 0 }
        }
        XCTAssertTrue(manifest.isComplete)
        try LocalRecordingManifestService().write(manifest, to: directory.appendingPathComponent("manifest.json"))
        return (directory, manifest)
    }
}

private actor RecoveryNetworkProbe: DesktopUploadClientProtocol {
    var calls = 0
    func record() -> Int { calls += 1; return calls }
    func reconcile(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadReconciliation? {
        calls += 1; XCTFail("This recording must not reach the network"); return nil
    }
    func upload(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadResult {
        calls += 1; XCTFail("This recording must not be uploaded"); throw RecordingDeletionError.invalidIdentity
    }
    func listLocalPurgeTasks() async throws -> [DesktopLocalPurgeTask] {
        calls += 1; XCTFail("This recording must not request purge tasks"); return []
    }
    func acknowledgeLocalPurgeTask(
        _ task: DesktopLocalPurgeTask, state: DesktopLocalPurgeTaskState, reasonCode: String, completedAt: Date?
    ) async throws -> DesktopLocalPurgeTask {
        calls += 1; XCTFail("This recording must not acknowledge purge tasks"); return task
    }
}
