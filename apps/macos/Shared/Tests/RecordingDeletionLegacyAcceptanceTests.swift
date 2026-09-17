import Foundation
import TwoBrainRecShared
@testable import TwoBrainRecAppCore
import XCTest

final class RecordingDeletionLegacyAcceptanceTests: XCTestCase {
    func testFilledV2QueueDoesNotBindUnknownOwnerOrDeleteFiles() async throws {
        for evidence in ["missing", "different-meeting", "denied"] {
            let fixture = try LegacyDeletionFixture()
            defer { try? FileManager.default.removeItem(at: fixture.root) }
            let client = LegacyDeletionClient(scope: fixture.scope, meetingID: fixture.item.meetingId!, evidence: evidence)
            let service = DesktopUploadQueueService(queueURL: fixture.file, recordingsRootURL: fixture.root, client: client)
            try await service.synchronizeRecordingLifecycle()
            let item = try XCTUnwrap(service.loadItems().first)
            XCTAssertNil(item.ownerScope, evidence)
            XCTAssertFalse(item.lifecycleAccessAvailable, evidence)
            XCTAssertFalse(item.hasConfirmedDeletion, evidence)
            XCTAssertTrue(EmbeddedCabinetLocalRecordingRow.rows(for: [item], recordingsRootURL: fixture.root).isEmpty)
            XCTAssertThrowsError(try service.localPlaybackURL(itemId: item.id))
            XCTAssertThrowsError(try service.requestDeletion(itemIDs: [item.id]))
            try service.finishLocalOnlyDeletions()
            try fixture.assertFilesIntact()
            let restarted = DesktopUploadQueueService(queueURL: fixture.file, recordingsRootURL: fixture.root, client: client)
            XCTAssertNil(try restarted.loadItems().first?.ownerScope)
            try fixture.assertFilesIntact()
        }
    }

    func testFilledV2QueueBindsOnlyMatchingOwnerAndKeepsDeletionFenceAfterRestart() async throws {
        let fixture = try LegacyDeletionFixture()
        defer { try? FileManager.default.removeItem(at: fixture.root) }
        let client = LegacyDeletionClient(scope: fixture.scope, meetingID: fixture.item.meetingId!, evidence: "owner-deleted")
        let service = DesktopUploadQueueService(queueURL: fixture.file, recordingsRootURL: fixture.root, client: client)
        try await service.synchronizeRecordingLifecycle()
        let item = try XCTUnwrap(service.loadItems().first)
        XCTAssertEqual(item.ownerScope, fixture.scope)
        XCTAssertEqual(item.serverCreationAttempted, true)
        XCTAssertTrue(item.hasConfirmedDeletion)
        XCTAssertTrue(item.lifecycleBlocksContent)
        XCTAssertThrowsError(try service.localPlaybackURL(itemId: item.id))
        XCTAssertTrue(EmbeddedCabinetLocalRecordingRow.rows(for: [item], recordingsRootURL: fixture.root).isEmpty)
        try fixture.assertFilesIntact() // Reconciliation is not the separate verified purge operation.
        let restarted = DesktopUploadQueueService(queueURL: fixture.file, recordingsRootURL: fixture.root, client: nil)
        restarted.setDeletionScope(fixture.scope)
        let restored = try XCTUnwrap(restarted.loadItems().first)
        XCTAssertEqual(restored.ownerScope, fixture.scope)
        XCTAssertTrue(restored.hasConfirmedDeletion)
        XCTAssertThrowsError(try restarted.localPlaybackURL(itemId: restored.id))
        XCTAssertEqual(try restarted.retry(itemId: restored.id).state, restored.state)
        try fixture.assertFilesIntact()
    }
}

private struct LegacyDeletionFixture {
    let root: URL
    let file: URL
    let scope: RecordingDeletionScope
    let item: DesktopUploadQueueItem
    let bytes = Data("synthetic legacy package".utf8)

    init() throws {
        root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        file = root.appendingPathComponent("queue.json")
        scope = try RecordingDeletionScope(serverOrigin: "https://graf.invalid", workspaceID: "workspace", actorUserID: "owner")
        var value = custodyFixtureQueueItem(state: .uploaded, meetingId: UUID().uuidString.lowercased())
        let package = root.appendingPathComponent(value.directoryId)
        try FileManager.default.createDirectory(at: package, withIntermediateDirectories: true)
        value.directoryPath = package.path
        value.manifestPath = package.appendingPathComponent("manifest.json").path
        value.microphonePath = package.appendingPathComponent("mic.wav").path
        value.systemAudioPath = package.appendingPathComponent("incoming.wav").path
        value.artifactProfile.trackCompleteness = [UploadTrackCompleteness(
            transportRole: .playback, fileName: "meeting-review.m4a", present: true,
            byteCount: Int64(bytes.count), sha256: nil, durationSeconds: 1
        )]
        item = value
        for path in [item.manifestPath, item.microphonePath, item.systemAudioPath, item.reviewAudioPath] {
            try bytes.write(to: URL(fileURLWithPath: path))
        }
        let encoder = JSONEncoder(); encoder.dateEncodingStrategy = .iso8601
        var payload = try XCTUnwrap(JSONSerialization.jsonObject(with: encoder.encode(
            DesktopUploadQueueDocument(updatedAt: Date(), items: [item])
        )) as? [String: Any])
        payload["schemaVersion"] = "desktop-upload-queue.v2"
        payload.removeValue(forKey: "deletionOperations")
        payload.removeValue(forKey: "lastAuthenticatedContext")
        var records = try XCTUnwrap(payload["items"] as? [[String: Any]])
        for key in ["ownerScope", "isLocalUnbound", "serverCreationAttempted"] { records[0].removeValue(forKey: key) }
        payload["items"] = records
        try JSONSerialization.data(withJSONObject: payload).write(to: file)
    }

    func assertFilesIntact() throws {
        for path in [item.manifestPath, item.microphonePath, item.systemAudioPath, item.reviewAudioPath] {
            XCTAssertEqual(try Data(contentsOf: URL(fileURLWithPath: path)), bytes)
        }
    }
}

private struct LegacyDeletionClient: DesktopUploadClientProtocol {
    let scope: RecordingDeletionScope
    let meetingID: String
    let evidence: String

    func recordingDeletionScope() async throws -> RecordingDeletionScope? { scope }
    func reconcile(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadReconciliation? {
        if evidence == "missing" { return nil }
        return DesktopUploadReconciliation(serverTruth: ServerTruthFingerprint(
            meetingId: evidence == "different-meeting" ? UUID().uuidString : meetingID,
            deletionState: "deleting", accessState: evidence == "denied" ? "denied" : "owner"
        ), conflictState: .serverMeetingDeleted)
    }
    func upload(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadResult {
        XCTFail("Legacy recovery must not upload content")
        throw RecordingDeletionError.invalidIdentity
    }
    func listLocalPurgeTasks() async throws -> [DesktopLocalPurgeTask] { [] }
    func acknowledgeLocalPurgeTask(_ task: DesktopLocalPurgeTask, state: DesktopLocalPurgeTaskState, reasonCode: String, completedAt: Date?) async throws -> DesktopLocalPurgeTask {
        XCTFail("Ownership reconciliation is not proof of physical cleanup")
        throw RecordingDeletionError.invalidIdentity
    }
}
