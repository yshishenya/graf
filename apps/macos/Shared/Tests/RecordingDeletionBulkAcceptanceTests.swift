import Foundation
import TwoBrainRecShared
@testable import TwoBrainRecAppCore
import XCTest

final class RecordingDeletionBulkAcceptanceTests: XCTestCase {
    func testHundredMixedOperationsKeepIndividualTruthAndResumeAfterRestart() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let scope = try RecordingDeletionScope(
            serverOrigin: "https://graf.invalid",
            workspaceID: UUID().uuidString.lowercased(), actorUserID: UUID().uuidString.lowercased()
        )
        let operations = try (0..<100).map { index in
            try RecordingDeletionOperation(
                scope: scope,
                target: index % 3 == 0 && index != 99
                    ? .ownOrigin("bulk-origin-\(index)") : .meeting(UUID().uuidString.lowercased()),
                requestedAt: Date(timeIntervalSince1970: 1)
            )
        }
        let server = BulkDeletionServer(scope: scope, operations: operations)
        let client = DesktopUploadClient(
            baseURL: URL(string: scope.serverOrigin)!, headers: [:], partSizeBytes: 65536,
            authSessionTokenProvider: { _ in "synthetic-bulk-session" },
            requestExecutor: { try await server.respond(to: $0) }
        )
        let file = root.appendingPathComponent("queue.json")
        let service = DesktopUploadQueueService(
            queueURL: file, recordingsRootURL: root, client: client,
            clock: { Date(timeIntervalSince1970: 100) }
        )
        try await service.refreshDeletionScope()
        XCTAssertEqual(try service.persistDeletionRequests(operations), operations)
        do {
            try await service.processDeletionRequests()
            XCTFail("Partial and unknown results must not become a bulk success")
        } catch {}

        let initial = try service.currentDeletionOperations()
        XCTAssertEqual(initial.count, 100)
        XCTAssertEqual(Set(initial.map(\.id)), Set(operations.map(\.id)))
        XCTAssertEqual(initial.filter { $0.phase == .accepted }.count, 33)
        XCTAssertEqual(initial.filter { $0.phase == .rejected }.count, 33)
        XCTAssertEqual(initial.filter { $0.phase == .resolving }.count, 34)
        let byID = Dictionary(uniqueKeysWithValues: initial.map { ($0.id, $0) })
        for (index, original) in operations.enumerated() {
            let result = try XCTUnwrap(byID[original.id])
            XCTAssertEqual(result.target, original.target)
            XCTAssertEqual(result.attemptCount, 1)
            if index != 99 && index % 3 == 0 {
                XCTAssertEqual(result.phase, .accepted)
                XCTAssertTrue(try XCTUnwrap(result.receipt).matches(original.target))
                XCTAssertTrue(result.blocksContent)
            } else if index % 3 == 1 {
                XCTAssertEqual(result.phase, .rejected)
                XCTAssertNil(result.receipt)
                XCTAssertFalse(result.blocksContent)
            } else {
                XCTAssertEqual(result.phase, .resolving)
                XCTAssertNil(result.receipt, "404 or a lost response cannot authorize cleanup")
                XCTAssertNotNil(result.nextAttemptAt)
                XCTAssertTrue(result.blocksContent)
            }
        }
        let firstAttempts = await server.attempts
        XCTAssertEqual(firstAttempts.count, 100, "Target 404 must not starve later operations")
        XCTAssertTrue(firstAttempts.values.allSatisfy { $0 == 1 })

        let restarted = DesktopUploadQueueService(
            queueURL: file, recordingsRootURL: root, client: client,
            clock: { Date(timeIntervalSince1970: 200) }
        )
        _ = try restarted.loadItems() // Restore the same verified session from the actual queue file.
        XCTAssertEqual(try restarted.currentDeletionOperations(), initial)
        await server.resolvePendingTargets()
        try await restarted.processDeletionRequests()
        let final = try restarted.currentDeletionOperations()
        XCTAssertEqual(final.count, 100)
        XCTAssertEqual(final.filter { $0.phase == .accepted }.count, 67)
        XCTAssertEqual(final.filter { $0.phase == .rejected }.count, 33)
        XCTAssertFalse(final.contains { $0.phase == .verified }, "No audio package is not physical cleanup proof")
        let finalByID = Dictionary(uniqueKeysWithValues: final.map { ($0.id, $0) })
        let finalAttempts = await server.attempts
        for previous in initial {
            let result = try XCTUnwrap(finalByID[previous.id])
            XCTAssertEqual(result.target, previous.target)
            if previous.phase == .resolving {
                XCTAssertEqual(result.phase, .accepted)
                XCTAssertTrue(try XCTUnwrap(result.receipt).matches(previous.target))
                XCTAssertNil(result.nextAttemptAt)
                XCTAssertEqual(finalAttempts[previous.target.identifier], 2)
            } else {
                XCTAssertEqual(result, previous, "Accepted receipts and rejected targets survive untouched")
                XCTAssertEqual(finalAttempts[previous.target.identifier], 1)
            }
        }
        let lostResponse = try XCTUnwrap(finalByID[operations[99].id]?.receipt)
        let serverReceipt = await server.receiptID(for: 99)
        XCTAssertEqual(lostResponse.requestID, serverReceipt, "Retry resolves the original server receipt")
        try await restarted.processDeletionRequests()
        let noExtraAttempts = await server.attempts
        XCTAssertEqual(noExtraAttempts, finalAttempts)
    }
}

private actor BulkDeletionServer {
    let scope: RecordingDeletionScope
    let operations: [RecordingDeletionOperation]
    let indexByTarget: [String: Int]
    let receiptIDs = (0..<100).map { _ in UUID() }
    var attempts: [String: Int] = [:]
    var pendingResolved = false

    init(scope: RecordingDeletionScope, operations: [RecordingDeletionOperation]) {
        self.scope = scope
        self.operations = operations
        self.indexByTarget = Dictionary(uniqueKeysWithValues: operations.enumerated().map { ($1.target.identifier, $0) })
    }

    func resolvePendingTargets() { pendingResolved = true }
    func receiptID(for index: Int) -> UUID { receiptIDs[index] }

    func respond(to request: URLRequest) throws -> (Data, HTTPURLResponse) {
        let url = try XCTUnwrap(request.url)
        var status = 200
        let body: Any
        if url.path.hasSuffix("notification-context") {
            body = ["workspace_id": scope.workspaceID, "user_id": scope.actorUserID,
                    "recording_deletion_protocol_version": 1] as [String: Any]
        } else {
            XCTAssertEqual(request.value(forHTTPHeaderField: "X-Graf-Expected-Actor"), scope.actorUserID)
            XCTAssertEqual(request.value(forHTTPHeaderField: "X-Graf-Expected-Workspace"), scope.workspaceID)
            XCTAssertEqual(request.httpMethod, "POST")
            if url.path.hasSuffix("/lifecycle") {
                let payload = try XCTUnwrap(JSONSerialization.jsonObject(with: XCTUnwrap(request.httpBody)) as? [String: [String]])
                let target = try XCTUnwrap(payload["meeting_ids"]?.first)
                let index = try XCTUnwrap(indexByTarget[target])
                body = [["target_type": "meeting", "target_id": target,
                         "state": index % 3 == 1 ? "unavailable" : "allowed"]]
            } else {
                XCTAssertTrue(url.path.hasSuffix("/deletion-requests"))
                let target = url.deletingLastPathComponent().lastPathComponent
                let index = try XCTUnwrap(indexByTarget[target])
                attempts[target, default: 0] += 1
                if index == 99 && attempts[target] == 1 {
                    // The server accepted this stable receipt, but its first response never arrived.
                    throw URLError(.timedOut)
                }
                if index % 3 == 1 || (index % 3 == 2 && !pendingResolved) {
                    status = 404
                    body = ["code": "meeting_not_found"]
                } else if case .ownOrigin = operations[index].target {
                    body = ["receipt_type": "origin_cancellation", "request_id": receiptIDs[index].uuidString,
                            "local_recording_id": target]
                } else {
                    body = ["receipt_type": "meeting_deletion", "request_id": receiptIDs[index].uuidString,
                            "meeting_id": target, "deletion_epoch": 1] as [String: Any]
                }
            }
        }
        return (try JSONSerialization.data(withJSONObject: body),
                try XCTUnwrap(HTTPURLResponse(url: url, statusCode: status, httpVersion: nil, headerFields: nil)))
    }
}
