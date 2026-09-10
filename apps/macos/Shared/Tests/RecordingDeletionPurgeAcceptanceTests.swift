import Foundation
import TwoBrainRecShared
@testable import TwoBrainRecAppCore
import XCTest

final class RecordingDeletionPurgeAcceptanceTests: XCTestCase {
    func testRealFilesystemFailureDoesNotBlockAnotherPackageAndRetriesAfterRepair() async throws {
        let fixture = try PurgeAcceptanceFixture(count: 2)
        defer { try? FileManager.default.removeItem(at: fixture.root) }
        let protected = fixture.items[0]
        // A real unlink failure inside the allowed root, not a simulated network/path error.
        try FileManager.default.setAttributes([.posixPermissions: 0o500], ofItemAtPath: protected.directoryPath)
        defer { try? FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: protected.directoryPath) }
        let client = PurgeAcceptanceClient(tasks: try fixture.tasks())
        let service = fixture.service(client)
        _ = try await service.acknowledgePendingLocalPurgeTasks()
        let first = await client.acknowledgements
        XCTAssertEqual(first.map(\.state), [.failed, .acknowledged])
        XCTAssertTrue(FileManager.default.fileExists(atPath: protected.microphonePath))
        XCTAssertFalse(FileManager.default.fileExists(atPath: fixture.items[1].directoryPath))
        let saved = try service.loadItems()
        XCTAssertNotEqual(saved[0].state, .terminalDeleted)
        XCTAssertEqual(saved[1].state, .terminalDeleted)

        try FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: protected.directoryPath)
        let restarted = fixture.service(client)
        _ = try await restarted.acknowledgePendingLocalPurgeTasks()
        XCTAssertFalse(FileManager.default.fileExists(atPath: protected.directoryPath))
        XCTAssertTrue(try restarted.loadItems().allSatisfy { $0.state == .terminalDeleted })
        let repaired = await client.acknowledgements
        XCTAssertEqual(repaired.last?.state, .acknowledged)
    }

    func testLostAcknowledgementRestartsAndRetriesExpiredTaskWithoutAnotherDelete() async throws {
        let fixture = try PurgeAcceptanceFixture()
        defer { try? FileManager.default.removeItem(at: fixture.root) }
        let tasks = try fixture.tasks(state: "expired")
        let client = PurgeAcceptanceClient(tasks: tasks, loseFirstAck: true)
        let service = fixture.service(client)
        do {
            _ = try await service.acknowledgePendingLocalPurgeTasks()
            XCTFail("Lost acknowledgement must remain unresolved")
        } catch let error as URLError { XCTAssertEqual(error.code, .timedOut) }
        XCTAssertFalse(FileManager.default.fileExists(atPath: fixture.items[0].directoryPath))
        XCTAssertNotEqual(try service.loadItems().first?.state, .terminalDeleted)

        let restarted = fixture.service(client)
        _ = try await restarted.acknowledgePendingLocalPurgeTasks()
        let acknowledgements = await client.acknowledgements
        XCTAssertEqual(acknowledgements.map(\.taskID), [tasks[0].taskId, tasks[0].taskId])
        XCTAssertEqual(acknowledgements.map(\.state), [.acknowledged, .acknowledged])
        XCTAssertTrue(acknowledgements.allSatisfy { $0.reason == "local_artifacts_deleted" })
        XCTAssertEqual(try restarted.loadItems().first?.state, .terminalDeleted)
        let deletes = await client.deletionRequests
        XCTAssertTrue(deletes.isEmpty, "Retry the purge ACK, never issue a new meeting deletion")
        _ = try await restarted.acknowledgePendingLocalPurgeTasks()
        let final = await client.acknowledgements
        XCTAssertEqual(final.count, 2, "The acknowledged task is terminal")
    }

    func testMissingMappingAndSymlinkNeverClaimVerifiedCleanup() async throws {
        let fixture = try PurgeAcceptanceFixture()
        defer { try? FileManager.default.removeItem(at: fixture.root) }
        let outside = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: outside, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: outside) }
        let bytes = Data("synthetic protected audio".utf8)
        let externalFile = outside.appendingPathComponent("audio.wav")
        try bytes.write(to: externalFile)
        let microphone = fixture.items[0].microphonePath
        try FileManager.default.removeItem(atPath: microphone)
        try FileManager.default.createSymbolicLink(atPath: microphone, withDestinationPath: externalFile.path)
        let missing = try PurgeAcceptanceFixture.task(meetingID: UUID().uuidString)
        let client = PurgeAcceptanceClient(tasks: try fixture.tasks() + [missing])
        _ = try await fixture.service(client).acknowledgePendingLocalPurgeTasks()
        let acknowledgements = await client.acknowledgements
        XCTAssertEqual(acknowledgements.map(\.state), [.failed, .failed])
        XCTAssertEqual(acknowledgements.map(\.reason), ["local_purge_failed", "local_purge_unverified"])
        XCTAssertEqual(try Data(contentsOf: externalFile), bytes)
        XCTAssertTrue(FileManager.default.fileExists(atPath: fixture.items[0].manifestPath))
        XCTAssertNotEqual(try fixture.service(client).loadItems().first?.state, .terminalDeleted)
    }

    func testScopeChangeDuringSuspendedResponsePreventsOldScopePurgeAndAcknowledgement() async throws {
        let fixture = try PurgeAcceptanceFixture()
        defer { try? FileManager.default.removeItem(at: fixture.root) }
        let arrived = expectation(description: "purge listing suspended")
        let gate = PurgeAcceptanceGate(arrived: arrived)
        let client = PurgeAcceptanceClient(tasks: try fixture.tasks(), listGate: gate)
        let service = fixture.service(client)
        let pending = Task { try await service.acknowledgePendingLocalPurgeTasks() }
        defer { Task { await gate.release() } }
        await fulfillment(of: [arrived], timeout: 5)
        service.setDeletionScope(try RecordingDeletionScope(
            serverOrigin: fixture.scope.serverOrigin, workspaceID: fixture.scope.workspaceID, actorUserID: "another-actor"
        ))
        await gate.release()
        let result = try await pending.value
        XCTAssertTrue(result.isEmpty)
        XCTAssertTrue(FileManager.default.fileExists(atPath: fixture.items[0].microphonePath))
        let acknowledgements = await client.acknowledgements
        XCTAssertTrue(acknowledgements.isEmpty)
        XCTAssertThrowsError(try service.localPlaybackURL(itemId: fixture.items[0].id))
    }

    func testSuspendedUploadDoesNotBlockDeletionAndConcurrentExecutorDoesNotDuplicateIt() async throws {
        let fixture = try PurgeAcceptanceFixture(state: .queued)
        defer { try? FileManager.default.removeItem(at: fixture.root) }
        let uploadArrived = expectation(description: "upload suspended")
        let deleteArrived = expectation(description: "delete suspended independently")
        let uploadGate = PurgeAcceptanceGate(arrived: uploadArrived)
        let deleteGate = PurgeAcceptanceGate(arrived: deleteArrived)
        let client = PurgeAcceptanceClient(tasks: [], uploadGate: uploadGate, deleteGate: deleteGate)
        let service = fixture.service(client)
        defer { Task { await uploadGate.release(); await deleteGate.release() } }
        let upload = Task { try await service.processDueItems() }
        await fulfillment(of: [uploadArrived], timeout: 5)
        let operations = try service.requestDeletion(itemIDs: [fixture.items[0].id])
        let deletion = Task { try await service.processDeletionRequests() }
        await fulfillment(of: [deleteArrived], timeout: 5)
        try await service.processDeletionRequests()
        let calls = await client.deletionRequests
        XCTAssertEqual(calls.map(\.id), operations.map(\.id), "A second executor must not resend an in-flight command")
        await deleteGate.release()
        try await deletion.value
        XCTAssertEqual(try service.currentDeletionOperations().first?.phase, .accepted)
        XCTAssertThrowsError(try service.localPlaybackURL(itemId: fixture.items[0].id))
        await uploadGate.release()
        _ = try await upload.value
        XCTAssertTrue(try XCTUnwrap(service.loadItems().first).lifecycleBlocksContent, "A late upload result cannot reopen the accepted deletion")
        XCTAssertEqual(try service.currentDeletionOperations().first?.id, operations.first?.id)
    }
}

private struct PurgeAcceptanceFixture {
    let root: URL
    let file: URL
    let scope: RecordingDeletionScope
    let items: [DesktopUploadQueueItem]

    init(count: Int = 1, state: UploadItemState = .uploaded) throws {
        root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        file = root.appendingPathComponent("queue.json")
        scope = try RecordingDeletionScope(serverOrigin: "https://graf.invalid", workspaceID: "workspace", actorUserID: "owner")
        var values: [DesktopUploadQueueItem] = []
        for index in 0..<count {
            var item = custodyFixtureQueueItem(id: "purge-\(index)", state: state, meetingId: UUID().uuidString.lowercased())
            let folder = root.appendingPathComponent(item.directoryId)
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
            item.ownerScope = scope
            item.isLocalUnbound = false
            item.serverCreationAttempted = true
            item.directoryPath = folder.path
            item.manifestPath = folder.appendingPathComponent("manifest.json").path
            item.microphonePath = folder.appendingPathComponent("mic.wav").path
            item.systemAudioPath = folder.appendingPathComponent("incoming.wav").path
            item.artifactProfile.trackCompleteness = [
                UploadTrackCompleteness(transportRole: .microphone, fileName: "mic.wav", present: true, byteCount: 23, sha256: nil, durationSeconds: 1),
                UploadTrackCompleteness(transportRole: .system, fileName: "incoming.wav", present: true, byteCount: 23, sha256: nil, durationSeconds: 1)
            ]
            for path in [item.manifestPath, item.microphonePath, item.systemAudioPath] {
                try Data("synthetic purge fixture".utf8).write(to: URL(fileURLWithPath: path))
            }
            values.append(item)
        }
        items = values
        let encoder = JSONEncoder(); encoder.dateEncodingStrategy = .iso8601
        try encoder.encode(DesktopUploadQueueDocument(updatedAt: Date(), items: values)).write(to: file)
    }

    func service(_ client: PurgeAcceptanceClient) -> DesktopUploadQueueService {
        let service = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: client)
        service.setDeletionScope(scope)
        return service
    }

    func tasks(state: String = "pending") throws -> [DesktopLocalPurgeTask] {
        try items.map { try Self.task(meetingID: XCTUnwrap($0.meetingId), state: state) }
    }

    static func task(meetingID: String, state: String = "pending", taskID: String = UUID().uuidString) throws -> DesktopLocalPurgeTask {
        let body = ["task_id": taskID, "meeting_id": meetingID, "task_type": "purge_local_buffers",
                    "state": state, "safe_reason": "delete_requested", "expires_at": "2020-01-01T00:00:00Z"]
        let decoder = JSONDecoder(); decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode(DesktopLocalPurgeTask.self, from: JSONSerialization.data(withJSONObject: body))
    }
}

private actor PurgeAcceptanceGate {
    let arrived: XCTestExpectation
    var continuation: CheckedContinuation<Void, Never>?
    var released = false
    init(arrived: XCTestExpectation) { self.arrived = arrived }
    func wait() async {
        guard !released else { return }
        await withCheckedContinuation { continuation in
            self.continuation = continuation
            arrived.fulfill()
        }
    }
    func release() { released = true; continuation?.resume(); continuation = nil }
}

private actor PurgeAcceptanceClient: DesktopUploadClientProtocol {
    struct Acknowledgement {
        let taskID: String
        let state: DesktopLocalPurgeTaskState
        let reason: String
    }
    var tasks: [DesktopLocalPurgeTask]
    var loseFirstAck: Bool
    let listGate: PurgeAcceptanceGate?
    let uploadGate: PurgeAcceptanceGate?
    let deleteGate: PurgeAcceptanceGate?
    var acknowledgements: [Acknowledgement] = []
    var deletionRequests: [RecordingDeletionOperation] = []

    init(tasks: [DesktopLocalPurgeTask], loseFirstAck: Bool = false, listGate: PurgeAcceptanceGate? = nil,
         uploadGate: PurgeAcceptanceGate? = nil, deleteGate: PurgeAcceptanceGate? = nil) {
        self.tasks = tasks; self.loseFirstAck = loseFirstAck
        self.listGate = listGate; self.uploadGate = uploadGate; self.deleteGate = deleteGate
    }
    func reconcile(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadReconciliation? {
        if uploadGate != nil { return nil }
        return DesktopUploadReconciliation(serverTruth: ServerTruthFingerprint(
            meetingId: item.meetingId, deletionState: "deleting", accessState: "owner"
        ), conflictState: .serverMeetingDeleted)
    }
    func upload(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadResult {
        await uploadGate?.wait()
        return DesktopUploadResult(state: .uploaded, serverTruth: ServerTruthFingerprint(meetingId: item.meetingId))
    }
    func listLocalPurgeTasks() async throws -> [DesktopLocalPurgeTask] {
        await listGate?.wait()
        return tasks
    }
    func requestRecordingDeletion(_ operation: RecordingDeletionOperation) async throws -> RecordingDeletionReceipt {
        deletionRequests.append(operation)
        await deleteGate?.wait()
        return try JSONDecoder().decode(RecordingDeletionReceipt.self, from: JSONSerialization.data(withJSONObject: [
            "receipt_type": "meeting_deletion", "request_id": UUID().uuidString,
            "meeting_id": operation.target.identifier, "deletion_epoch": 1
        ] as [String: Any]))
    }
    func acknowledgeLocalPurgeTask(_ task: DesktopLocalPurgeTask, state: DesktopLocalPurgeTaskState,
                                   reasonCode: String, completedAt: Date?) async throws -> DesktopLocalPurgeTask {
        acknowledgements.append(Acknowledgement(taskID: task.taskId, state: state, reason: reasonCode))
        if loseFirstAck { loseFirstAck = false; throw URLError(.timedOut) }
        let updated = try PurgeAcceptanceFixture.task(meetingID: task.meetingId, state: state.rawValue, taskID: task.taskId)
        tasks = tasks.map { $0.taskId == task.taskId ? updated : $0 }
        return updated
    }
}
