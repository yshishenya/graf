import Foundation
import TwoBrainRecShared
@testable import TwoBrainRecAppCore
import XCTest

final class RecordingDeletionLifecycleTests: XCTestCase {
    func testLifecycleBackgroundPagesAreBoundedAndVisitWholeHistory() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let scope = try RecordingDeletionScope(serverOrigin: "https://graf.invalid",
            workspaceID: UUID().uuidString.lowercased(), actorUserID: UUID().uuidString.lowercased())
        let probe = LifecycleLookupProbe()
        let client = DesktopUploadClient(baseURL: URL(string: scope.serverOrigin)!, headers: [:], partSizeBytes: 65536,
            authSessionTokenProvider: { _ in "synthetic-session" }, requestExecutor: { request in
                let body: Any
                if request.url!.path.hasSuffix("notification-context") {
                    body = ["workspace_id": scope.workspaceID, "user_id": scope.actorUserID, "recording_deletion_protocol_version": 1]
                } else {
                    let payload = try XCTUnwrap(JSONSerialization.jsonObject(with: request.httpBody!) as? [String: [String]])
                    let origins = try XCTUnwrap(payload["origins"])
                    await probe.record(origins)
                    body = origins.map { ["target_type": "own_origin", "target_id": $0, "state": "allowed"] }
                }
                return (try JSONSerialization.data(withJSONObject: body), HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
            })
        let items = (0..<250).map { number in
            var item = custodyFixtureQueueItem(id: String(format: "item-%03d", number))
            item.directoryId = item.id; item.ownerScope = scope; item.isLocalUnbound = false
            item.serverCreationAttempted = true; item.meetingId = nil
            return item
        }
        let file = root.appendingPathComponent("queue.json")
        let encoder = JSONEncoder(); encoder.dateEncodingStrategy = .iso8601
        try encoder.encode(DesktopUploadQueueDocument(updatedAt: Date(), items: items)).write(to: file)
        let service = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: client)
        for page in 1...3 {
            try await service.synchronizeRecordingLifecycle()
            let batches = await probe.batches
            XCTAssertEqual(batches.count, page, "Each trigger must check only one background page")
        }
        let batches = await probe.batches
        XCTAssertEqual(batches.map(\.count), [100, 100, 50])
        XCTAssertEqual(Set(batches.flatMap { $0 }), Set(items.map(\.directoryId)))
    }

    func testInvalidLifecycleResponseDoesNotCompleteOpenOrSkipBackgroundPage() async throws {
        for state in ["missing", "duplicate", "future", "deletion_accepted", "canceled_before_creation", "wrong-receipt"] {
            let probe = LifecycleLookupProbe()
            let fixture = try lifecycleFixture(probe: probe) { origins, attempt in
                if attempt > 1 { return origins.map { ["target_type": "own_origin", "target_id": $0, "state": "allowed"] } }
                if state == "missing" { return [] }
                if state == "duplicate" { return origins.map { _ in ["target_type": "own_origin", "target_id": origins[0], "state": "allowed"] } }
                return origins.map { origin -> [String: Any] in
                    var entry: [String: Any] = ["target_type": "own_origin", "target_id": origin,
                        "state": state == "wrong-receipt" ? "deletion_accepted" : state]
                    if state == "wrong-receipt" {
                        entry["receipt"] = ["receipt_type": "origin_cancellation", "phase": "accepted",
                            "request_id": UUID().uuidString, "local_recording_id": "another-origin"]
                    }
                    return entry
                }
            }
            defer { try? FileManager.default.removeItem(at: fixture.root) }
            do { try await fixture.service.synchronizeRecordingLifecycle(); XCTFail("Invalid response completed: \(state)") } catch {}
            XCTAssertTrue(try fixture.service.currentDeletionOperations().isEmpty)
            try await fixture.service.synchronizeRecordingLifecycle()
            let batches = await probe.batches
            XCTAssertEqual(batches.count, 2)
            XCTAssertEqual(batches.first, batches.last, "A failed page must be retried: \(state)")
        }
    }

    func testVisibleAndOpenPriorityLeaveRoomForBackgroundHistory() async throws {
        let probe = LifecycleLookupProbe()
        let fixture = try lifecycleFixture(probe: probe)
        defer { try? FileManager.default.removeItem(at: fixture.root) }
        fixture.service.setVisibleRecordingItemIDs(["item-249"])
        try await fixture.service.synchronizeRecordingLifecycle(priorityItemIDs: ["item-248"])
        try await fixture.service.synchronizeRecordingLifecycle()
        let batches = await probe.batches
        XCTAssertEqual(batches[0], ["item-248", "item-249"])
        XCTAssertEqual(batches[1], Array(fixture.items.prefix(100).map(\.directoryId)))
        XCTAssertEqual(batches[2], ["item-249"])
        XCTAssertEqual(batches[3], Array(fixture.items.dropFirst(100).prefix(100).map(\.directoryId)))
    }

    func testConcurrentOpenJoinsCycleAndScopeChangeRejectsOldResponse() async throws {
        for changeScope in [false, true] {
            let arrived = expectation(description: "First lookup suspended")
            let gate = LifecycleLookupGate(arrived: arrived)
            let probe = LifecycleLookupProbe()
            let fixture = try lifecycleFixture(probe: probe, gate: gate)
            defer { try? FileManager.default.removeItem(at: fixture.root) }
            let background = Task { try await fixture.service.synchronizeRecordingLifecycle(priorityItemIDs: ["item-249"]) }
            await fulfillment(of: [arrived], timeout: 5)
            let completed = DeletionCallCounter()
            let opening = Task {
                try await fixture.service.synchronizeRecordingLifecycle(priorityItemIDs: ["item-248"])
                _ = await completed.increment()
            }
            try await Task.sleep(for: .milliseconds(100))
            let completedBeforeReply = await completed.count
            XCTAssertEqual(completedBeforeReply, 0, "Open waits for its own lookup")
            if changeScope { fixture.service.setDeletionScope(nil) }
            else { background.cancel() } // One cancelled waiter must not cancel the shared lookup.
            await gate.release()
            if changeScope {
                do { try await background.value; XCTFail("Old scope accepted") } catch {}
                do { try await opening.value; XCTFail("Old open accepted") } catch {}
                XCTAssertTrue(try fixture.service.loadItems().allSatisfy { !$0.lifecycleAccessAvailable })
                try await fixture.service.synchronizeRecordingLifecycle(priorityItemIDs: ["item-247"])
                let batches = await probe.batches
                XCTAssertEqual(batches[1], ["item-247"], "Old priority must not leak into the new cycle")
            } else {
                try await background.value
                try await opening.value
                let batches = await probe.batches
                XCTAssertEqual(batches.map(\.count), [1, 1, 100])
                XCTAssertEqual(batches[1], ["item-248"], "Late open has priority over background history")
            }
        }
    }

    func testMixedLegacyRecoveryDoesNotDelayKnownOpenAndAdvancesPastFailure() async throws {
        let probe = LifecycleLookupProbe()
        let arrived = expectation(description: "Legacy lookup suspended")
        let gate = LifecycleLookupGate(arrived: arrived)
        let fixture = try lifecycleFixture(probe: probe, legacyGate: gate, legacyCount: 3)
        defer { try? FileManager.default.removeItem(at: fixture.root) }
        try await fixture.service.synchronizeRecordingLifecycle(priorityItemIDs: ["item-249"])
        await fulfillment(of: [arrived], timeout: 5)
        let batches = await probe.batches
        XCTAssertEqual(batches.first, ["item-249"], "Known open must finish while legacy HTTP is suspended")
        try await fixture.service.synchronizeRecordingLifecycle(priorityItemIDs: ["item-248"])
        let suspended = await probe.legacyOrigins
        XCTAssertEqual(suspended, ["item-000"], "Concurrent triggers share the pending legacy lookup")
        await gate.release()
        for _ in 0..<4 {
            try await fixture.service.synchronizeRecordingLifecycle()
            // Join the bounded recovery before asserting its persisted result.
            try? await fixture.service.refreshDeletionScope()
        }
        let recovered = try fixture.service.loadItems()
        XCTAssertNil(recovered.first { $0.id == "item-000" }?.ownerScope)
        XCTAssertNil(recovered.first { $0.id == "item-001" }?.ownerScope)
        XCTAssertEqual(recovered.first { $0.id == "item-002" }?.ownerScope, fixture.items.last?.ownerScope)
        let visited = await probe.legacyOrigins
        XCTAssertEqual(Set(visited), Set(["item-000", "item-001", "item-002"]))
        XCTAssertTrue(try fixture.service.currentDeletionOperations().isEmpty)
    }

    func testActivationRefreshSharesLifecycleNetworkBudget() async throws {
        let probe = LifecycleLookupProbe()
        let lookupArrived = expectation(description: "Origin lookup suspended")
        let legacyArrived = expectation(description: "Legacy lookup suspended")
        let lookup = LifecycleLookupGate(arrived: lookupArrived)
        let legacy = LifecycleLookupGate(arrived: legacyArrived)
        let fixture = try lifecycleFixture(probe: probe, gate: lookup, legacyGate: legacy, legacyCount: 3)
        defer { try? FileManager.default.removeItem(at: fixture.root) }
        let sync = Task { try await fixture.service.synchronizeRecordingLifecycle(priorityItemIDs: ["item-249"]) }
        await fulfillment(of: [lookupArrived, legacyArrived], timeout: 5)
        let refresh = Task { try? await fixture.service.refreshDeletionScope() }
        try await Task.sleep(for: .milliseconds(100))
        let contexts = await probe.contextRequests
        XCTAssertEqual(contexts, 1, "Activation must join the ongoing lifecycle instead of sending a third HTTP")
        await lookup.release()
        await legacy.release()
        try await sync.value
        await refresh.value
        let maximum = await probe.maxActiveRequests
        XCTAssertLessThanOrEqual(maximum, 2, "Count every HTTP, including notification-context")
    }

    func testDeletionAndPurgeShareLifecycleBudgetAndCancelWaiter() async throws {
        let probe = LifecycleLookupProbe()
        let lookupArrived = expectation(description: "Origin lookup suspended")
        let legacyArrived = expectation(description: "Legacy lookup suspended")
        let lookup = LifecycleLookupGate(arrived: lookupArrived)
        let legacy = LifecycleLookupGate(arrived: legacyArrived)
        let fixture = try lifecycleFixture(probe: probe, gate: lookup, legacyGate: legacy, legacyCount: 3)
        defer { try? FileManager.default.removeItem(at: fixture.root) }
        let sync = Task { try await fixture.service.synchronizeRecordingLifecycle(priorityItemIDs: ["item-249"]) }
        await fulfillment(of: [lookupArrived, legacyArrived], timeout: 5)
        let scope = try XCTUnwrap(fixture.items.last?.ownerScope)
        let operation = try RecordingDeletionOperation(scope: scope, target: .ownOrigin("synthetic-delete"), requestedAt: Date())
        let purge = try JSONDecoder().decode(DesktopLocalPurgeTask.self, from: Data("""
        {"task_id":"synthetic-task","meeting_id":"00000000-0000-4000-8000-000000000001",
         "task_type":"purge_local_buffers","state":"pending","safe_reason":"delete_requested","expires_at":0}
        """.utf8))
        let deletion = Task { try? await fixture.client.requestRecordingDeletion(operation) }
        let listing = Task { try? await fixture.client.listLocalPurgeTasks() }
        let ensure = Task { try? await fixture.client.ensureLocalPurgeTask(meetingID: purge.meetingId, scope: scope) }
        let ack = Task { try? await fixture.client.acknowledgeLocalPurgeTask(purge, state: .acknowledged, reasonCode: "local_buffers_purged") }
        let cancelledFinished = expectation(description: "Waiting request cancelled before HTTP slots are released")
        let cancelled = Task {
            defer { cancelledFinished.fulfill() }
            return try await fixture.client.recordingLifecycle(origins: ["cancelled-waiter"], scope: scope)
        }
        try await Task.sleep(for: .milliseconds(100))
        cancelled.cancel()
        await fulfillment(of: [cancelledFinished], timeout: 2)
        let contexts = await probe.contextRequests
        let maximumWhileHeld = await probe.maxActiveRequests
        XCTAssertEqual(contexts, 1, "Deletion preflight must wait for a shared HTTP slot")
        XCTAssertLessThanOrEqual(maximumWhileHeld, 2)
        await lookup.release()
        await legacy.release()
        try await sync.value
        _ = await (deletion.value, listing.value, ensure.value, ack.value)
        do { _ = try await cancelled.value; XCTFail("Cancelled waiter must not send HTTP") }
        catch is CancellationError {} catch { XCTFail("Unexpected cancellation error: \(error)") }
        let batches = await probe.batches
        XCTAssertFalse(batches.contains(["cancelled-waiter"]))
        let maximum = await probe.maxActiveRequests
        XCTAssertLessThanOrEqual(maximum, 2, "Lifecycle, recovery, deletion and purge share two HTTP slots")
        let paths = await probe.paths
        for suffix in ["deletion-requests", "local-purge-tasks", "local-purge-task", "ack"] {
            XCTAssertTrue(paths.contains { $0.hasSuffix(suffix) }, "Missing exercised HTTP: \(suffix)")
        }
        // Failures and cancellation must return their slots for later requests.
        _ = try await fixture.client.recordingLifecycle(origins: ["after-failure"], scope: scope)
    }

    @MainActor
    func testQueuedDeletionAndPurgeRejectScopeOrSessionChangeBeforeHTTP() async throws {
        for changeSession in [false, true] {
            let probe = LifecycleLookupProbe()
            let lookupArrived = expectation(description: "Origin lookup suspended")
            let legacyArrived = expectation(description: "Legacy lookup suspended")
            let lookup = LifecycleLookupGate(arrived: lookupArrived)
            let legacy = LifecycleLookupGate(arrived: legacyArrived)
            let fixture = try lifecycleFixture(probe: probe, gate: lookup, legacyGate: legacy, legacyCount: 3)
            defer { try? FileManager.default.removeItem(at: fixture.root) }
            let scope = try XCTUnwrap(fixture.items.last?.ownerScope)
            fixture.service.setDeletionScope(scope)
            let operation = try RecordingDeletionOperation(scope: scope, target: .ownOrigin("queued-delete"), requestedAt: Date())
            try fixture.service.persistDeletionRequests([operation])
            let sync = Task { try? await fixture.service.synchronizeRecordingLifecycle(priorityItemIDs: ["item-249"]) }
            await fulfillment(of: [lookupArrived, legacyArrived], timeout: 5)
            let deletion = Task { try? await fixture.service.processDeletionRequests() }
            let purge = Task { try? await fixture.service.acknowledgePendingLocalPurgeTasks() }
            try await Task.sleep(for: .milliseconds(100))
            let barrier: UUID?
            if changeSession { barrier = DesktopCabinetSessionBridge.beginNavigation() }
            else { barrier = nil; fixture.service.setDeletionScope(nil) }
            await lookup.release()
            await legacy.release()
            _ = await (sync.value, deletion.value, purge.value)
            if let barrier { DesktopCabinetSessionBridge.endNavigation(barrier) }
            let contexts = await probe.contextRequests
            let paths = await probe.paths
            XCTAssertEqual(contexts, 1, "Old deletion preflight must not leave after scope/session changes")
            XCTAssertFalse(paths.contains { $0.hasSuffix("deletion-requests") || $0.hasSuffix("local-purge-tasks") },
                           "Queued deletion/purge must recheck current scope/session immediately before HTTP")
            XCTAssertTrue(try fixture.service.currentDeletionOperations().allSatisfy { !$0.phase.isAccepted })
        }
    }

    private func lifecycleFixture(probe: LifecycleLookupProbe, gate: LifecycleLookupGate? = nil,
        legacyGate: LifecycleLookupGate? = nil, legacyCount: Int = 0,
        response: @escaping @Sendable ([String], Int) -> [[String: Any]] = { origins, _ in
            origins.map { ["target_type": "own_origin", "target_id": $0, "state": "allowed"] }
        }) throws -> (root: URL, service: DesktopUploadQueueService, items: [DesktopUploadQueueItem], client: DesktopUploadClient) {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let scope = try RecordingDeletionScope(serverOrigin: "https://graf.invalid",
            workspaceID: UUID().uuidString.lowercased(), actorUserID: UUID().uuidString.lowercased())
        let client = DesktopUploadClient(baseURL: URL(string: scope.serverOrigin)!, headers: [:], partSizeBytes: 65536,
            authSessionTokenProvider: { _ in "synthetic-session" }, requestExecutor: { request in
                await probe.beginRequest(path: request.url!.path)
                do {
                let body: Any
                if request.url!.path.hasSuffix("notification-context") {
                    body = ["workspace_id": scope.workspaceID, "user_id": scope.actorUserID, "recording_deletion_protocol_version": 1]
                } else if request.url!.path.hasSuffix("sync-state") {
                    let origin = request.url!.deletingLastPathComponent().lastPathComponent
                    let attempt = await probe.recordLegacy(origin)
                    if attempt == 1 { await legacyGate?.wait() }
                    if origin == "item-000" { throw URLError(.timedOut) }
                    body = ["local_recording_id": origin, "local_media_revision_id": "synthetic-revision",
                        "meeting": ["meeting_id": "meeting-\(origin)", "status": "ready",
                            "access_state": origin == "item-001" ? "denied" : "owner"],
                        "media_revision": ["track_sha256_by_role": [:]],
                        "upload_session": ["accepted_bytes_by_track": [:], "missing_ranges_by_track": [:]],
                        "processing": ["status": "not_submitted"], "conflict": ["state": "none"]]
                } else if !request.url!.path.hasSuffix("/recordings/lifecycle") {
                    await probe.endRequest()
                    return (Data("{}".utf8), HTTPURLResponse(url: request.url!, statusCode: 503, httpVersion: nil, headerFields: nil)!)
                } else {
                    let payload = try XCTUnwrap(JSONSerialization.jsonObject(with: request.httpBody!) as? [String: [String]])
                    let origins = try XCTUnwrap(payload["origins"])
                    let attempt = await probe.record(origins)
                    if attempt == 1 { await gate?.wait() }
                    body = response(origins, attempt)
                }
                let result = (try JSONSerialization.data(withJSONObject: body), HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
                await probe.endRequest()
                return result
                } catch { await probe.endRequest(); throw error }
            })
        let items = (0..<250).map { number in
            var item = custodyFixtureQueueItem(id: String(format: "item-%03d", number))
            item.directoryId = item.id; item.ownerScope = scope; item.isLocalUnbound = false
            item.serverCreationAttempted = true; item.meetingId = nil
            if number < legacyCount { item.ownerScope = nil; item.meetingId = "meeting-\(item.id)" }
            return item
        }
        let file = root.appendingPathComponent("queue.json")
        let encoder = JSONEncoder(); encoder.dateEncodingStrategy = .iso8601
        try encoder.encode(DesktopUploadQueueDocument(updatedAt: Date(), items: items)).write(to: file)
        return (root, DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: client), items, client)
    }

    func testVisibleRecordingHintsRequireBoundedNativeRowsAndCurrentRoute() throws {
        let meeting = "00000000-0000-0000-0000-000000000262"
        let rows = try JSONDecoder().decode([EmbeddedCabinetLocalRecordingRow].self, from: Data("""
        [{"id":"known","meetingId":"\(meeting)","title":"Synthetic","startedAt":0,"durationSeconds":1,
          "sessionDurationSeconds":1,"status":"Synthetic","canOpen":true,"showsPartialDuration":false,
          "canSend":false,"canDelete":true,"uploadComplete":true,"localDeletionPending":false,"deletionIsLocalOnly":false}]
        """.utf8))
        let policy = DesktopCabinetRoutePolicy(baseURL: URL(string: "https://graf.invalid")!)
        let list = policy.decision(for: URL(string: "https://graf.invalid/desktop/meetings")!).route
        let detail = policy.decision(for: URL(string: "https://graf.invalid/desktop/meetings/\(meeting)")!).route
        let wrongDetail = policy.decision(for: URL(string: "https://graf.invalid/desktop/meetings/00000000-0000-0000-0000-000000000263")!).route
        let settings = policy.decision(for: URL(string: "https://graf.invalid/desktop/settings")!).route
        let valid: [String: Any] = ["action": "visibleRecordings", "version": 1, "ids": ["known"]]
        for route in [list, detail] {
            XCTAssertEqual(EmbeddedCabinetLocalRecordingBridge.visibleItemIDs(from: valid, rows: rows, route: route), ["known"])
            var empty = valid; empty["ids"] = [String]()
            XCTAssertEqual(EmbeddedCabinetLocalRecordingBridge.visibleItemIDs(from: empty, rows: rows, route: route), [])
        }
        for route in [wrongDetail, settings] {
            XCTAssertNil(EmbeddedCabinetLocalRecordingBridge.visibleItemIDs(from: valid, rows: rows, route: route))
        }
        for invalid: [String: Any] in [
            ["action":"visibleRecordings", "version":2, "ids":["known"]],
            ["action":"visibleRecordings", "version":1, "ids":["forged"]],
            ["action":"visibleRecordings", "version":1, "ids":["known","known"]],
            ["action":"visibleRecordings", "version":1, "ids":Array(repeating:"known",count:101)],
            ["action":"visibleRecordings", "version":1, "ids":"known"],
        ] {
            XCTAssertNil(EmbeddedCabinetLocalRecordingBridge.visibleItemIDs(from: invalid, rows: rows, route: list))
        }
    }

    func testTypedRetryAndRejectionDeadlinesThroughServiceRestart() async throws {
        for target in [RecordingDeletionTarget.meeting(UUID().uuidString.lowercased()), .ownOrigin("synthetic-origin")] {
            for status in [503, 429, 403] {
                let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
                defer { try? FileManager.default.removeItem(at: root) }
                let scope = try RecordingDeletionScope(serverOrigin: "https://graf.invalid",
                    workspaceID: UUID().uuidString.lowercased(), actorUserID: UUID().uuidString.lowercased())
                let calls = DeletionCallCounter()
                let client = DesktopUploadClient(baseURL: URL(string: scope.serverOrigin)!, headers: [:], partSizeBytes: 65536,
                    authSessionTokenProvider: { _ in "synthetic-session" }, requestExecutor: { request in
                        let context = request.url!.path.hasSuffix("notification-context")
                        if !context { _ = await calls.increment() }
                        let body: [String: Any] = context
                            ? ["workspace_id": scope.workspaceID, "user_id": scope.actorUserID, "recording_deletion_protocol_version": 1]
                            : ["code":status == 403 ? "deletion_forbidden" : "server_unavailable"]
                        return (try JSONSerialization.data(withJSONObject: body),
                            HTTPURLResponse(url: request.url!, statusCode: context ? 200 : status, httpVersion: nil,
                                headerFields: status == 429 ? ["Retry-After":"120"] : [:])!)
                    })
                let file = root.appendingPathComponent("queue.json")
                let service = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: client,
                    clock: { Date(timeIntervalSince1970:100) })
                try await service.refreshDeletionScope()
                let operation = try RecordingDeletionOperation(id: UUID(uuidString:"00000000-0000-4000-8000-000000000001")!,
                    scope:scope,target:target,requestedAt:Date(timeIntervalSince1970:1))
                try service.persistDeletionRequests([operation])
                do { try await service.processDeletionRequests(); XCTFail("Network failure must be reported") } catch {}
                let stored = try XCTUnwrap(service.currentDeletionOperations().first)
                XCTAssertEqual(stored.phase,status == 403 ? .rejected : .resolving)
                if status != 403 {
                    XCTAssertEqual(stored.nextAttemptAt,Date(timeIntervalSince1970:status == 429 ? 220 : 104))
                }
                let restarted = DesktopUploadQueueService(queueURL:file,recordingsRootURL:root,client:client,
                    clock:{Date(timeIntervalSince1970:103)})
                _ = try restarted.loadItems()
                try await restarted.processDeletionRequests()
                XCTAssertEqual(try restarted.currentDeletionOperations(),[stored])
                let count = await calls.count
                XCTAssertEqual(count,1,"Restart must respect the deadline or final rejection for both targets")
            }
        }
    }

    func testRetryJitterIsBoundedStableAndPreservesServerDeadline() throws {
        let encoder = JSONEncoder(); encoder.dateEncodingStrategy = .iso8601
        let decoder = JSONDecoder(); decoder.dateDecodingStrategy = .iso8601
        for target in [RecordingDeletionTarget.meeting("meeting"), .ownOrigin("origin")] {
            for (prefix, multiplier) in [("00", 0.8), ("ff", 1.2), ("83", 0.8 + 0.4 * 131 / 255)] {
                for fractionalClock in [0.0, 0.25, 0.99] {
                    let id = try XCTUnwrap(UUID(uuidString: "\(prefix)000000-0000-4000-8000-000000000001"))
                    var operation = try RecordingDeletionOperation(id: id, scope: makeOperation().scope,
                        target: target, requestedAt: Date(timeIntervalSince1970: 1))
                    for (index, nominal) in [5.0, 15, 30, 60, 60].enumerated() {
                        let now = Date(timeIntervalSince1970: Double(100 + index * 200) + fractionalClock)
                        operation = operation.applying(.sending, at: now).applying(.resolving, at: now)
                        let deadline = try XCTUnwrap(operation.nextAttemptAt)
                        let calculated = now.addingTimeInterval(nominal * multiplier)
                        XCTAssertGreaterThanOrEqual(deadline, calculated)
                        XCTAssertLessThan(deadline.timeIntervalSince(calculated), 1)
                        XCTAssertEqual(operation.applying(.resolving, at: now), operation)
                        let restored = try decoder.decode(RecordingDeletionOperation.self, from: encoder.encode(operation))
                        XCTAssertEqual(restored.nextAttemptAt, deadline, "Use the queue's actual second-precision date format")
                        XCTAssertEqual(restored.applying(.resolving, at: now).nextAttemptAt, deadline)
                        let serverDeadline = now.addingTimeInterval(120.5)
                        let waiting = operation.waiting(until: serverDeadline)
                        let savedWait = try decoder.decode(RecordingDeletionOperation.self, from: encoder.encode(waiting))
                        XCTAssertEqual(savedWait.nextAttemptAt, waiting.nextAttemptAt)
                        XCTAssertGreaterThanOrEqual(try XCTUnwrap(savedWait.nextAttemptAt), serverDeadline)
                        XCTAssertLessThan(try XCTUnwrap(savedWait.nextAttemptAt).timeIntervalSince(serverDeadline), 1)
                        XCTAssertEqual(operation.waiting(until: now).nextAttemptAt, deadline)
                    }
                }
            }
        }
    }

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
                    body = ["workspace_id":scope.workspaceID, "user_id":scope.actorUserID, "recording_deletion_protocol_version": 1]
                } else {
                    XCTAssertEqual(request.value(forHTTPHeaderField: "X-Graf-Expected-Actor"), scope.actorUserID)
                    XCTAssertEqual(request.value(forHTTPHeaderField: "X-Graf-Expected-Workspace"), scope.workspaceID)
                    body = attempt == 1 ? ["code":"network_unavailable"] : [
                        "receipt_type":"origin_cancellation", "request_id":receiptID, "local_recording_id":"synthetic-origin", "phase": "accepted"
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

    func testOldServerCannotMutateDeletionBeforeCapabilityConfirmation() async throws {
        for version in [nil, 999] as [Int?] {
            let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
            defer { try? FileManager.default.removeItem(at: root) }
            let scope = try RecordingDeletionScope(serverOrigin: "https://graf.invalid", workspaceID: UUID().uuidString.lowercased(), actorUserID: UUID().uuidString.lowercased())
            let mutations = DeletionCallCounter()
            let client = DesktopUploadClient(baseURL: URL(string: scope.serverOrigin)!, headers: [:], partSizeBytes: 65536,
                authSessionTokenProvider: { _ in "synthetic-session" }, requestExecutor: { request in
                    if request.httpMethod != "GET" { _ = await mutations.increment(); XCTFail("Unsupported server must receive no deletion mutation") }
                    var body: [String: Any] = ["workspace_id": scope.workspaceID, "user_id": scope.actorUserID]
                    if let version { body["recording_deletion_protocol_version"] = version }
                    return (try JSONSerialization.data(withJSONObject: body), HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
                })
            let service = DesktopUploadQueueService(queueURL: root.appendingPathComponent("queue.json"), recordingsRootURL: root, client: client)
            service.setDeletionScope(scope)
            try service.persistDeletionRequests([RecordingDeletionOperation(scope: scope, target: .meeting(UUID().uuidString.lowercased()), requestedAt: Date())])
            do { try await service.processDeletionRequests(); XCTFail("Unsupported server must wait for update") } catch {}
            let operation = try XCTUnwrap(service.currentDeletionOperations().first)
            XCTAssertEqual(operation.phase, .resolving)
            XCTAssertEqual(operation.waitReason, .serverUpdate)
            XCTAssertNil(operation.receipt)
            let count = await mutations.count
            XCTAssertEqual(count, 0)
        }
    }

    func testUnavailableTargetDoesNotBlockNextDeletionAndNeverAuthorizesPurge() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let scope = try RecordingDeletionScope(serverOrigin: "https://graf.invalid", workspaceID: UUID().uuidString.lowercased(), actorUserID: UUID().uuidString.lowercased())
        let unavailableID = UUID().uuidString.lowercased()
        let allowedID = UUID().uuidString.lowercased()
        let mutations = DeletionCallCounter()
        let client = DesktopUploadClient(baseURL: URL(string: scope.serverOrigin)!, headers: [:], partSizeBytes: 65536,
            authSessionTokenProvider: { _ in "synthetic-session" }, requestExecutor: { request in
                XCTAssertEqual(request.value(forHTTPHeaderField: "X-Graf-Expected-Actor"), scope.actorUserID)
                XCTAssertEqual(request.value(forHTTPHeaderField: "X-Graf-Expected-Workspace"), scope.workspaceID)
                let path = request.url!.path
                var status = 200
                let body: Any
                if path.hasSuffix("notification-context") {
                    body = ["workspace_id": scope.workspaceID, "user_id": scope.actorUserID, "recording_deletion_protocol_version": 1]
                } else if path.hasSuffix("/lifecycle") {
                    let payload = try XCTUnwrap(JSONSerialization.jsonObject(with: request.httpBody!) as? [String: [String]])
                    XCTAssertEqual(payload["meeting_ids"], [unavailableID])
                    body = [["target_type": "meeting", "target_id": unavailableID, "state": "unavailable"]]
                } else {
                    _ = await mutations.increment()
                    if path.contains(unavailableID) {
                        status = 404
                        body = ["code": "meeting_not_found"]
                    } else {
                        XCTAssertTrue(path.contains(allowedID))
                        body = ["receipt_type": "meeting_deletion", "phase": "accepted", "request_id": UUID().uuidString,
                                "meeting_id": allowedID, "deletion_epoch": 1]
                    }
                }
                return (try JSONSerialization.data(withJSONObject: body), HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!)
            })
        let service = DesktopUploadQueueService(queueURL: root.appendingPathComponent("queue.json"), recordingsRootURL: root, client: client)
        service.setDeletionScope(scope)
        let operations = try [unavailableID, allowedID].map { try RecordingDeletionOperation(scope: scope, target: .meeting($0), requestedAt: Date()) }
        try service.persistDeletionRequests(operations)
        do { try await service.processDeletionRequests(); XCTFail("The unavailable target remains a reported failure") } catch {}
        let results = try service.currentDeletionOperations()
        XCTAssertEqual(results[0].phase, .rejected)
        XCTAssertNil(results[0].receipt)
        XCTAssertFalse(results[0].blocksContent)
        XCTAssertEqual(results[1].phase, .accepted)
        XCTAssertEqual(results[1].receipt?.meetingID, allowedID)
        let count = await mutations.count
        XCTAssertEqual(count, 2)
    }

    func testTypedReceiptForAnotherTargetIsRejected() throws {
        let receipt = try JSONDecoder().decode(RecordingDeletionReceipt.self, from: Data(#"{"receipt_type":"origin_cancellation","request_id":"00000000-0000-0000-0000-000000000001","local_recording_id":"different"}"#.utf8))
        let operation = try makeOperation()
        XCTAssertThrowsError(try operation.accepting(receipt, at: Date()))
    }

    func testNetworkReceiptPhaseControlsAcceptanceAndOriginCleanup() async throws {
        // Exercise each network entry point through the real queue and filesystem.
        for route in ["direct-origin", "direct-meeting", "origin-as-meeting", "origin-lookup", "meeting-fallback"] {
            for phase in ["\"accepted\"", "\"rejected\"", "\"future\"", "null", "1", "true", nil] as [String?] {
                let accepted = phase == "\"accepted\""
                let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
                try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
                defer { try? FileManager.default.removeItem(at: root) }
                let scope = try RecordingDeletionScope(serverOrigin: "https://graf.invalid", workspaceID: UUID().uuidString.lowercased(), actorUserID: UUID().uuidString.lowercased())
                let meetingID = UUID().uuidString.lowercased()
                let origin = "synthetic-origin"
                let originReceipt = ["direct-origin", "origin-lookup"].contains(route)
                let meetingTarget = ["direct-meeting", "meeting-fallback"].contains(route)
                let target: RecordingDeletionTarget = meetingTarget ? .meeting(meetingID) : .ownOrigin(origin)
                let phaseField = phase.map { ",\"phase\":\($0)" } ?? ""
                let meetingFields = originReceipt ? "" : ",\"meeting_id\":\"\(meetingID)\",\"deletion_epoch\":1"
                let receiptJSON = "{\"receipt_type\":\"\(originReceipt ? "origin_cancellation" : "meeting_deletion")\",\"request_id\":\"00000000-0000-0000-0000-000000000001\",\"local_recording_id\":\"\(origin)\"\(meetingFields)\(phaseField)}"
                let client = DesktopUploadClient(baseURL: URL(string: scope.serverOrigin)!, headers: [:], partSizeBytes: 65536,
                    authSessionTokenProvider: { _ in "synthetic-session" }, requestExecutor: { request in
                        let url = try XCTUnwrap(request.url)
                        let body: Data
                        var status = 200
                        if url.path.hasSuffix("notification-context") {
                            body = try JSONSerialization.data(withJSONObject: ["workspace_id": scope.workspaceID, "user_id": scope.actorUserID, "recording_deletion_protocol_version": 1])
                        } else if url.path.hasSuffix("/lifecycle") {
                            let state = originReceipt ? "canceled_before_creation" : "deletion_accepted"
                            body = Data("[{\"target_type\":\"\(meetingTarget ? "meeting" : "own_origin")\",\"target_id\":\"\(target.identifier)\",\"state\":\"\(state)\",\"receipt\":\(receiptJSON)}]".utf8)
                        } else if route == "meeting-fallback" {
                            status = 404; body = Data(#"{"code":"meeting_not_found"}"#.utf8)
                        } else {
                            XCTAssertTrue(url.path.hasSuffix("/deletion-requests"))
                            body = Data(receiptJSON.utf8)
                        }
                        return (body, try XCTUnwrap(HTTPURLResponse(url: url, statusCode: status, httpVersion: nil, headerFields: nil)))
                    })
                let directory = root.appendingPathComponent(origin)
                try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
                let manifest = directory.appendingPathComponent("manifest.json")
                let bytes = Data("synthetic-preserved-content".utf8)
                try bytes.write(to: manifest)
                var item = custodyFixtureQueueItem()
                item.directoryId = origin; item.directoryPath = directory.path; item.manifestPath = manifest.path
                item.microphonePath = directory.appendingPathComponent("mic.wav").path
                item.systemAudioPath = directory.appendingPathComponent("incoming.wav").path
                item.ownerScope = scope; item.isLocalUnbound = false; item.serverCreationAttempted = true
                item.meetingId = meetingTarget ? meetingID : nil
                let file = root.appendingPathComponent("queue.json")
                let encoder = JSONEncoder(); encoder.dateEncodingStrategy = .iso8601
                try encoder.encode(DesktopUploadQueueDocument(updatedAt: Date(), items: [item])).write(to: file)
                let service = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: client)
                try await service.refreshDeletionScope()
                let operation = try RecordingDeletionOperation(scope: scope, target: target, requestedAt: Date())
                if route != "origin-lookup" { try service.persistDeletionRequests([operation]) }
                do {
                    if route == "origin-lookup" { try await service.synchronizeRecordingLifecycle() }
                    try await service.processDeletionRequests()
                    if !accepted { XCTFail("Invalid network phase accepted: \(route)/\(phase ?? "missing")") }
                } catch {
                    if accepted { throw error }
                }
                let restarted = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: nil)
                restarted.setDeletionScope(scope)
                let stored = try restarted.currentDeletionOperations()
                if accepted {
                    XCTAssertEqual(stored.count, 1)
                    XCTAssertTrue(try XCTUnwrap(stored.first).phase.isAccepted)
                    XCTAssertEqual(FileManager.default.fileExists(atPath: manifest.path), !originReceipt)
                } else {
                    XCTAssertTrue(stored.allSatisfy { !$0.phase.isAccepted && $0.receipt == nil })
                    if route != "origin-lookup" {
                        XCTAssertEqual(stored.first?.id, operation.id)
                        XCTAssertEqual(stored.first?.target, target)
                        XCTAssertEqual(stored.first?.phase, .resolving)
                        XCTAssertNotNil(stored.first?.nextAttemptAt)
                    }
                    XCTAssertEqual(try Data(contentsOf: manifest), bytes)
                }
            }
        }
    }

    func testPersistedAcceptedReceiptsWithoutWirePhaseSurviveRestart() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let pending = try makeOperation()
        let receipt = try JSONDecoder().decode(RecordingDeletionReceipt.self, from: Data(#"{"receipt_type":"meeting_deletion","request_id":"00000000-0000-0000-0000-000000000001","meeting_id":"meeting","deletion_epoch":1}"#.utf8))
        let accepted = try pending.accepting(receipt, at: Date(timeIntervalSince1970: 2))
        let encoder = JSONEncoder(); encoder.dateEncodingStrategy = .iso8601
        let file = root.appendingPathComponent("queue.json")
        for operation in [accepted, accepted.applying(.verified, at: Date(timeIntervalSince1970: 3))] {
            let data = try encoder.encode(DesktopUploadQueueDocument(updatedAt: Date(), items: [], deletionOperations: [operation]))
            let raw = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
            let saved = try XCTUnwrap((raw["deletionOperations"] as? [[String: Any]])?.first?["receipt"] as? [String: Any])
            XCTAssertNil(saved["phase"], "The existing queue format is independent of the network response")
            try data.write(to: file)
            let restarted = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: nil)
            restarted.setDeletionScope(operation.scope)
            XCTAssertEqual(try restarted.currentDeletionOperations(), [operation])
            XCTAssertEqual(operation.applying(.rejected, at: Date()), operation)
        }
    }

    func testHundredLocalPackagesCleanWithinBudgetAndRemainDeletedAfterRestart() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let scope = try makeOperation().scope
        var items: [DesktopUploadQueueItem] = []
        // Real files: one MiB in CI; the acceptance run opts into the 100 MiB upper bound.
        let packageBytes = min(104_857_600, max(1_048_576, Int(ProcessInfo.processInfo.environment["GRAF_DELETION_TEST_PACKAGE_BYTES"] ?? "") ?? 1_048_576))
        let bytes = Data(repeating: 0x5a, count: packageBytes)
        for number in 0..<100 {
            let folder = root.appendingPathComponent("package-\(number)")
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
            try bytes.write(to: folder.appendingPathComponent("mic.wav"))
            try Data("{}".utf8).write(to: folder.appendingPathComponent("manifest.json"))
            var item = custodyFixtureQueueItem(id: "bulk-\(number)")
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
        let start = Date()
        XCTAssertTrue(try service.requestDeletion(itemIDs: items.map(\.id)).isEmpty)
        try service.finishLocalOnlyDeletions()
        let seconds = Date().timeIntervalSince(start)
        XCTAssertLessThan(seconds, 60)
        let restarted = DesktopUploadQueueService(queueURL: file, recordingsRootURL: root, client: nil)
        restarted.setDeletionScope(scope)
        for _ in 0..<100 {
            let saved = try restarted.loadItems()
            XCTAssertEqual(saved.count, 100)
            XCTAssertTrue(saved.allSatisfy { $0.hasConfirmedDeletion && !$0.retentionDecision.localArtifactsRetained })
            XCTAssertTrue(EmbeddedCabinetLocalRecordingRow.rows(for: saved, recordingsRootURL: root).isEmpty)
        }
        XCTAssertTrue(items.allSatisfy { !FileManager.default.fileExists(atPath: $0.directoryPath) })
        print("F262 local cleanup: packages=100 bytes=\(100 * packageBytes) elapsedSeconds=\(seconds) reloads=100")
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

private actor LifecycleLookupProbe {
    var batches: [[String]] = []
    var legacyOrigins: [String] = []
    private var activeRequests = 0
    var maxActiveRequests = 0
    var contextRequests = 0
    var paths: [String] = []
    func beginRequest(path: String) {
        paths.append(path)
        activeRequests += 1
        maxActiveRequests = max(maxActiveRequests, activeRequests)
        if path.hasSuffix("notification-context") { contextRequests += 1 }
    }
    func endRequest() { activeRequests -= 1 }
    func recordLegacy(_ origin: String) -> Int { legacyOrigins.append(origin); return legacyOrigins.count }
    @discardableResult
    func record(_ origins: [String]) -> Int { batches.append(origins); return batches.count }
}

private actor LifecycleLookupGate {
    let arrived: XCTestExpectation
    private var continuation: CheckedContinuation<Void, Never>?
    init(arrived: XCTestExpectation) { self.arrived = arrived }
    func wait() async {
        await withCheckedContinuation { continuation in self.continuation = continuation; arrived.fulfill() }
    }
    func release() { continuation?.resume(); continuation = nil }
}
