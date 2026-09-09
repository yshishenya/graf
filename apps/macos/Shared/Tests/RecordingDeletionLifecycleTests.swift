import Foundation
import TwoBrainRecShared
@testable import TwoBrainRecAppCore
import XCTest

final class RecordingDeletionLifecycleTests: XCTestCase {
    func testDeletedServerTruthBlocksPlaybackProjectionEvenWhenFileIsValid() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        var item = custodyFixtureQueueItem(state: .uploaded)
        item.directoryPath = root.path
        let bytes = Data([1, 2, 3, 4])
        try bytes.write(to: URL(fileURLWithPath: item.reviewAudioPath))
        item.artifactProfile.trackCompleteness = [UploadTrackCompleteness(
            transportRole: .playback, fileName: "meeting-review.m4a", present: true,
            byteCount: Int64(bytes.count), sha256: nil, durationSeconds: 1
        )]
        XCTAssertTrue(DesktopUploadQueueService.canProjectLocalPlayback(item: item, recordingsRootURL: root))
        item.serverTruth.deletionState = "deleting"
        item.syncConflictState = .serverExpectedMetadataMismatch
        XCTAssertFalse(DesktopUploadQueueService.canProjectLocalPlayback(item: item, recordingsRootURL: root))
        XCTAssertTrue(EmbeddedCabinetLocalRecordingRow.rows(for: [item], recordingsRootURL: root).isEmpty)
    }

    func testLateUploadTransitionCannotEraseTombstone() {
        var item = custodyFixtureQueueItem(state: .uploaded)
        item.serverTruth.deletionState = "deleting"
        let late = item.withTransition(
            to: .uploaded, now: Date(), serverTruth: ServerTruthFingerprint(deletionState: "none")
        )
        XCTAssertEqual(late.serverTruth.deletionState, "deleting")
        XCTAssertTrue(late.hasConfirmedDeletion)
    }

    func testUnavailableAccessBlocksContentButDoesNotProveDeletion() {
        for status in ["denied", "unknown", "revoked"] {
            var item = custodyFixtureQueueItem()
            item.serverTruth.accessState = status
            XCTAssertTrue(item.lifecycleBlocksContent)
            XCTAssertFalse(item.hasConfirmedDeletion)
        }
    }

    func testDeletionRequestsAreDurableScopedAndIdempotent() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let file = root.appendingPathComponent("queue.json")
        let service = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: nil)
        let first = try makeOperation()
        let stored = try service.persistDeletionRequests([first])
        XCTAssertEqual(stored, [first])
        let duplicate = try RecordingDeletionOperation(
            scope: first.scope, target: first.target, requestedAt: Date()
        )
        XCTAssertEqual(try service.persistDeletionRequests([duplicate]), [first])
        let restarted = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: nil)
        XCTAssertEqual(try restarted.loadDeletionOperations(scope: first.scope), [first])
        XCTAssertTrue(try restarted.loadItems().isEmpty)
        let other = try RecordingDeletionScope(serverOrigin: "https://graf.invalid", workspaceID: "workspace", actorUserID: "other")
        XCTAssertTrue(try restarted.loadDeletionOperations(scope: other).isEmpty)
        XCTAssertThrowsError(try restarted.updateDeletionOperation(id: first.id, scope: other, phase: .accepted))
    }

    func testFailedAtomicSaveDoesNotPublishDeletionInMemory() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let parent = root.appendingPathComponent("blocked-parent")
        try Data([0]).write(to: parent)
        let service = DesktopUploadQueueService(queueURL: parent.appendingPathComponent("queue.json"), recordingsRootURL: root, client: nil)
        let operation = try makeOperation()
        XCTAssertThrowsError(try service.persistDeletionRequests([operation]))
        XCTAssertTrue(try service.loadDeletionOperations(scope: operation.scope).isEmpty)
    }

    func testServerOnlyOperationSurvivesQueueRoundTripWithoutAudioItem() throws {
        let operation = try makeOperation()
        let queue = DesktopUploadQueueDocument(
            updatedAt: Date(timeIntervalSince1970: 1),
            items: [],
            deletionOperations: [operation]
        )
        let decoded = try JSONDecoder().decode(
            DesktopUploadQueueDocument.self,
            from: JSONEncoder().encode(queue)
        )
        XCTAssertEqual(decoded.deletionOperations, [operation])
        XCTAssertTrue(decoded.items.isEmpty)
        XCTAssertTrue(decoded.deletionOperations[0].blocksContent)
    }

    func testAcceptedOperationNeverRegressesOnLateResponse() throws {
        let pending = try makeOperation()
        let receipt = try JSONDecoder().decode(RecordingDeletionReceipt.self, from: Data("""
        {"receipt_type":"meeting_deletion","request_id":"00000000-0000-0000-0000-000000000001","meeting_id":"meeting","deletion_epoch":1}
        """.utf8))
        let accepted = try pending.waitingBecause(.connection).accepting(receipt, at: Date(timeIntervalSince1970: 2))
        XCTAssertNil(accepted.waitReason)
        for latePhase in [RecordingDeletionPhase.queued, .sending, .resolving, .rejected] {
            XCTAssertEqual(accepted.applying(latePhase, at: Date()), accepted)
        }
        let verified = accepted.applying(.verified, at: Date(timeIntervalSince1970: 3))
        XCTAssertEqual(verified.applying(.accepted, at: Date()), verified)
        XCTAssertTrue(verified.blocksContent)
    }

    func testVerificationRequiresAcceptedDeletion() throws {
        let pending = try makeOperation()
        XCTAssertEqual(pending.applying(.verified, at: Date()), pending)
        XCTAssertEqual(pending.applying(.accepted, at: Date()), pending)
        var corrupted = try JSONSerialization.jsonObject(with: JSONEncoder().encode(pending)) as! [String: Any]
        corrupted["phase"] = "accepted"
        XCTAssertThrowsError(try JSONDecoder().decode(RecordingDeletionOperation.self, from: JSONSerialization.data(withJSONObject: corrupted)))
        let rejected = pending.applying(.rejected, at: Date(timeIntervalSince1970: 2))
        XCTAssertFalse(rejected.blocksContent)
    }

    func testExecutionScopeCannotBeBorrowedByAnotherActor() throws {
        let operation = try makeOperation()
        let other = try RecordingDeletionScope(
            serverOrigin: "https://graf.invalid", workspaceID: "workspace", actorUserID: "other"
        )
        XCTAssertNotEqual(operation.scope, other)
        // A manager targets a meeting ID; target identity does not impersonate its creator.
        XCTAssertEqual(operation.target, .meeting("meeting"))
    }

    func testScopeNormalizesOriginAndRejectsCredentialsAndRemotePlaintext() throws {
        let normalized = try RecordingDeletionScope(
            serverOrigin: "https://GRAF.invalid:443/", workspaceID: "workspace", actorUserID: "actor"
        )
        XCTAssertEqual(normalized.serverOrigin, "https://graf.invalid")
        for origin in ["https://user:secret@graf.invalid", "http://graf.invalid", "https://graf.invalid/path", "https://graf.invalid?token=secret"] {
            XCTAssertThrowsError(try RecordingDeletionScope(
                serverOrigin: origin, workspaceID: "workspace", actorUserID: "actor"
            ))
        }
        XCTAssertNoThrow(try RecordingDeletionScope(
            serverOrigin: "http://127.0.0.1:8081", workspaceID: "workspace", actorUserID: "actor"
        ))
    }

    func testDecodedScopeAlsoValidatesTrustBoundary() throws {
        let data = Data(#"{"serverOrigin":"https://user:secret@graf.invalid","workspaceID":"w","actorUserID":"u"}"#.utf8)
        XCTAssertThrowsError(try JSONDecoder().decode(RecordingDeletionScope.self, from: data))
    }

    func testLegacyQueueDefaultsToEmptyOperationsButFutureSchemaIsRejected() throws {
        let data = Data(#"{"schemaVersion":"desktop-upload-queue.v2","updatedAt":0,"items":[]}"#.utf8)
        let legacy = try JSONDecoder().decode(DesktopUploadQueueDocument.self, from: data)
        XCTAssertTrue(legacy.deletionOperations.isEmpty)
        let unknown = Data(#"{"schemaVersion":"desktop-upload-queue.v999","updatedAt":0,"items":[]}"#.utf8)
        XCTAssertThrowsError(try JSONDecoder().decode(DesktopUploadQueueDocument.self, from: unknown))
    }

    func testPersistedIntentBlocksEveryLocalActionAndSurvivesRestart() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let scope = try makeOperation().scope
        var item = custodyFixtureQueueItem(state: .queued)
        item.ownerScope = scope
        item.isLocalUnbound = false
        item.serverCreationAttempted = true
        let file = root.appendingPathComponent("queue.json")
        let encoder = JSONEncoder(); encoder.dateEncodingStrategy = .iso8601
        try encoder.encode(DesktopUploadQueueDocument(updatedAt: Date(), items: [item])).write(to: file)
        let service = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: nil)
        service.setDeletionScope(scope)
        XCTAssertFalse(try XCTUnwrap(service.loadItems().first).lifecycleBlocksContent)
        let operations = try service.requestDeletion(itemIDs: [item.id])
        XCTAssertEqual(operations.count, 1)
        XCTAssertTrue(try XCTUnwrap(service.loadItems().first).lifecycleBlocksContent)
        XCTAssertThrowsError(try service.localPlaybackURL(itemId: item.id))
        XCTAssertEqual(try service.retry(itemId: item.id).state, .queued)
        let restarted = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: nil)
        restarted.setDeletionScope(scope)
        XCTAssertEqual(try restarted.loadItems().first?.deletionOperation?.id, operations[0].id)
        // Derived projections are not another persisted state machine.
        let raw = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: file)) as? [String: Any])
        let rawItem = try XCTUnwrap((raw["items"] as? [[String: Any]])?.first)
        XCTAssertNil(rawItem["deletionOperation"])
        XCTAssertNil(rawItem["lifecycleAccessAvailable"])
    }

    func testNeverSubmittedDeletionIsOfflineAndOneUnsafePackageDoesNotBlockAnother() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        let outside = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root); try? FileManager.default.removeItem(at: outside) }
        let scope = try makeOperation().scope
        var items: [DesktopUploadQueueItem] = []
        for (id, folder) in [("safe", root.appendingPathComponent("safe")), ("outside", outside)] {
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
            try Data([1, 2, 3]).write(to: folder.appendingPathComponent("manifest.json"))
            var item = custodyFixtureQueueItem(id: id)
            item.ownerScope = scope
            item.serverCreationAttempted = false
            item.directoryPath = folder.path
            item.manifestPath = folder.appendingPathComponent("manifest.json").path
            item.microphonePath = folder.appendingPathComponent("mic.wav").path
            item.systemAudioPath = folder.appendingPathComponent("incoming.wav").path
            items.append(item)
        }
        let file = root.appendingPathComponent("queue.json")
        let encoder = JSONEncoder(); encoder.dateEncodingStrategy = .iso8601
        try encoder.encode(DesktopUploadQueueDocument(updatedAt: Date(), items: items)).write(to: file)
        let service = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: nil)
        service.setDeletionScope(scope)
        XCTAssertTrue(try service.requestDeletion(itemIDs: items.map(\.id)).isEmpty)
        XCTAssertTrue(FileManager.default.fileExists(atPath: items[0].manifestPath), "Intent must precede file effects")
        XCTAssertThrowsError(try service.finishLocalOnlyDeletions())
        XCTAssertFalse(FileManager.default.fileExists(atPath: items[0].directoryPath))
        XCTAssertTrue(FileManager.default.fileExists(atPath: items[1].manifestPath))
        let restarted = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: nil)
        restarted.setDeletionScope(scope)
        let saved = try restarted.loadItems()
        XCTAssertTrue(saved.allSatisfy(\.hasConfirmedDeletion))
        XCTAssertFalse(try XCTUnwrap(saved.first { $0.id == "safe" }).retentionDecision.localArtifactsRetained)
        let rows = EmbeddedCabinetLocalRecordingRow.rows(for: saved, recordingsRootURL: root)
        XCTAssertEqual(rows.count, 1)
        XCTAssertTrue(rows[0].localDeletionPending)
        XCTAssertFalse(rows[0].canOpen)
    }

    func testLegacyOwnershipIsUnavailableAndFutureQueueIsPreserved() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let file = root.appendingPathComponent("queue.json")
        let encoder = JSONEncoder(); encoder.dateEncodingStrategy = .iso8601
        try encoder.encode(DesktopUploadQueueDocument(updatedAt: Date(), items: [custodyFixtureQueueItem()])).write(to: file)
        let service = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: nil)
        service.setDeletionScope(try makeOperation().scope)
        XCTAssertFalse(try XCTUnwrap(service.loadItems().first).lifecycleAccessAvailable)
        XCTAssertThrowsError(try service.requestDeletion(itemIDs: ["custody-item"]))
        XCTAssertTrue(EmbeddedCabinetLocalRecordingRow.rows(for: try service.loadItems(), recordingsRootURL: root).isEmpty)
        let future = Data(#"{"schemaVersion":"desktop-upload-queue.v999","deletionOperations":["must survive"]}"#.utf8)
        try future.write(to: file)
        let newer = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: nil)
        XCTAssertThrowsError(try newer.scanAndEnqueueCompletedRecordings())
        XCTAssertEqual(try Data(contentsOf: file), future)
        let malformedV3 = Data(#"{"schemaVersion":"desktop-upload-queue.v3","updatedAt":0,"items":[]}"#.utf8)
        XCTAssertThrowsError(try JSONDecoder().decode(DesktopUploadQueueDocument.self, from: malformedV3))
    }

    func testDeletionBridgeRejectsUnknownVersionAndUnboundedSelection() throws {
        let valid: [String: Any] = ["version": 1, "action": "deleteSelection", "requestId": UUID().uuidString,
                                    "localIds": [String](), "meetingIds": [UUID().uuidString]]
        XCTAssertNotNil(EmbeddedCabinetDeletionSelection.parse(valid, rows: []))
        var invalid = valid; invalid["version"] = 999
        XCTAssertNil(EmbeddedCabinetDeletionSelection.parse(invalid, rows: []))
        invalid = valid; invalid["meetingIds"] = Array(repeating: UUID().uuidString, count: 101)
        XCTAssertNil(EmbeddedCabinetDeletionSelection.parse(invalid, rows: []))
        invalid = valid; invalid["localIds"] = ["not-in-projection"]
        XCTAssertNil(EmbeddedCabinetDeletionSelection.parse(invalid, rows: []))
    }

    func testTypedDeleteRetriesSameOperationAfterRestartAndRejectsAnotherSession() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let scope = try RecordingDeletionScope(serverOrigin: "https://graf.invalid", workspaceID: UUID().uuidString.lowercased(), actorUserID: UUID().uuidString.lowercased())
        let calls = DeletionCallCounter()
        let receiptID = UUID().uuidString
        let client = DesktopUploadClient(baseURL: URL(string: scope.serverOrigin)!, headers: [:], partSizeBytes: 65536,
            authSessionTokenProvider: { _ in "synthetic-session" }, requestExecutor: { request in
                let context = request.url!.path.hasSuffix("notification-context")
                let attempt = context ? 0 : await calls.increment()
                let status = attempt == 1 ? 503 : 200
                let body: [String: Any]
                if context {
                    body = ["workspace_id":scope.workspaceID, "user_id":scope.actorUserID]
                } else {
                    XCTAssertEqual(request.value(forHTTPHeaderField: "X-Graf-Expected-Actor"), scope.actorUserID)
                    XCTAssertEqual(request.value(forHTTPHeaderField: "X-Graf-Expected-Workspace"), scope.workspaceID)
                    body = attempt == 1 ? ["code":"network_unavailable"] : [
                        "receipt_type":"origin_cancellation", "request_id":receiptID, "local_recording_id":"synthetic-origin"
                    ]
                }
                return (try JSONSerialization.data(withJSONObject: body), HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!)
            })
        let file = root.appendingPathComponent("queue.json")
        let service = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: client, clock: { Date(timeIntervalSince1970: 100) })
        try await service.refreshDeletionScope()
        let operation = try RecordingDeletionOperation(scope: scope, target: .ownOrigin("synthetic-origin"), requestedAt: Date(timeIntervalSince1970: 1))
        try service.persistDeletionRequests([operation])
        do { try await service.processDeletionRequests(); XCTFail("Missing response must remain unresolved") } catch {}
        XCTAssertEqual(try service.currentDeletionOperations().first?.phase, .resolving)
        XCTAssertNotNil(try service.currentDeletionOperations().first?.nextAttemptAt)
        let restarted = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: client, clock: { Date(timeIntervalSince1970: 200) })
        _ = try restarted.loadItems() // Same native session restores its verified offline context.
        try await restarted.processDeletionRequests()
        let accepted = try XCTUnwrap(restarted.currentDeletionOperations().first)
        XCTAssertEqual(accepted.id, operation.id)
        XCTAssertEqual(accepted.receipt?.requestID.uuidString, receiptID.uppercased())
        XCTAssertEqual(accepted.phase, .accepted) // No local package is not evidence of physical cleanup.
        try await restarted.processDeletionRequests()
        let count = await calls.count
        XCTAssertEqual(count, 2)
        let changed = DesktopUploadClient(baseURL: URL(string: scope.serverOrigin)!, headers: [:], partSizeBytes: 65536,
            authSessionTokenProvider: { _ in "another-synthetic-session" }, requestExecutor: { _ in XCTFail("Another session must not execute this operation"); throw RecordingDeletionError.invalidIdentity })
        let other = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: changed)
        _ = try other.loadItems()
        XCTAssertTrue(try other.currentDeletionOperations().isEmpty)
        try await other.processDeletionRequests()
    }

    func testTypedReceiptForAnotherTargetIsRejected() throws {
        let receipt = try JSONDecoder().decode(RecordingDeletionReceipt.self, from: Data(#"{"receipt_type":"origin_cancellation","request_id":"00000000-0000-0000-0000-000000000001","local_recording_id":"different"}"#.utf8))
        let operation = try makeOperation()
        XCTAssertThrowsError(try operation.accepting(receipt, at: Date()))
    }

    private func makeOperation() throws -> RecordingDeletionOperation {
        try RecordingDeletionOperation(
            scope: RecordingDeletionScope(
                serverOrigin: "https://graf.invalid", workspaceID: "workspace", actorUserID: "actor"
            ),
            target: .meeting("meeting"),
            requestedAt: Date(timeIntervalSince1970: 1)
        )
    }
}

private actor DeletionCallCounter {
    var count = 0
    func increment() -> Int { count += 1; return count }
}
