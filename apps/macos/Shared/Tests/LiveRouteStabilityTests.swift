import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LiveRouteStabilityTests: XCTestCase {
    func testThirtyMinuteSimulatedActiveClientWindowHasNoUnexpectedReleaseDecision() {
        let policy = PassthroughAutoIdlePolicy(releaseAfterIdleTicks: 300)
        let activity = LiveRouteStabilityFixtures.clientActivity(freshnessMs: 1_000)
        var releaseCount = 0

        for tick in 0..<(30 * 60) {
            if policy.shouldReleasePhysicalRoute(
                bridgeActive: true,
                clientActivity: activity,
                consecutiveIdleTicks: tick
            ) {
                releaseCount += 1
            }
        }

        XCTAssertEqual(releaseCount, 0)
    }

    func testEngineWritesRouteEvidenceJSONLinesWithRealSessionId() throws {
        let directoryURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("route-evidence-\(UUID().uuidString)")
        defer { try? FileManager.default.removeItem(at: directoryURL) }
        let ids = DeterministicIds(["route-session-1", "event-armed", "event-active"])
        let engine = PassthroughRouteEngine(
            sharedMemory: nil,
            activityDetector: FixedSnapshotActivityDetector(snapshot: LiveRouteStabilityFixtures.clientActivity()),
            bridgeFactory: { _, _ in NoopPassthroughBridge() },
            idFactory: ids.next,
            routeEvidenceStore: RouteEvidenceStore(directoryURL: directoryURL)
        )

        let state = engine.startAutomaticRoute { _, _ in }

        XCTAssertEqual(state, .active)
        XCTAssertEqual(engine.currentRouteSessionId, "route-session-1")
        let fileURL = directoryURL.appendingPathComponent("route-evidence.jsonl")
        let lines = try String(contentsOf: fileURL, encoding: .utf8)
            .split(separator: "\n")
            .map(String.init)
        XCTAssertTrue(lines.contains { $0.contains("\"sessionId\":\"route-session-1\"") })
        XCTAssertFalse(lines.contains { $0.contains("\"sessionId\":\"live-route\"") })
    }

    func testEngineDoesNotBlockRouteWhenEvidenceStoreWriteFails() throws {
        let fileURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("route-evidence-file-\(UUID().uuidString)")
        try Data("not-a-directory".utf8).write(to: fileURL)
        defer { try? FileManager.default.removeItem(at: fileURL) }
        let engine = PassthroughRouteEngine(
            sharedMemory: nil,
            activityDetector: FixedSnapshotActivityDetector(snapshot: LiveRouteStabilityFixtures.clientActivity()),
            bridgeFactory: { _, _ in NoopPassthroughBridge() },
            routeEvidenceStore: RouteEvidenceStore(directoryURL: fileURL)
        )

        let state = engine.startAutomaticRoute { _, _ in }

        XCTAssertEqual(state, .active)
        XCTAssertNotNil(engine.lastRouteEvidence())
    }

    func testEngineReleaseDecisionUsesSuppliedSnapshot() {
        let ids = DeterministicIds(["route-session-1", "event-active", "event-release"])
        let engine = PassthroughRouteEngine(
            sharedMemory: nil,
            activityDetector: FixedSnapshotActivityDetector(snapshot: LiveRouteStabilityFixtures.clientActivity()),
            bridgeFactory: { _, _ in NoopPassthroughBridge() },
            idFactory: ids.next
        )
        _ = engine.startAutomaticRoute { _, _ in }
        let closedSnapshot = ClientActivitySnapshot(
            source: .validationFixture,
            microphoneOpen: false,
            microphoneRunning: false,
            speakerOpen: false,
            speakerRunning: false,
            stillUsesVirtualMicrophone: false,
            stillUsesVirtualSpeaker: false,
            freshnessMs: 100,
            naturalSilenceAllowed: false
        )

        let state = engine.reconcileClientActivity(snapshot: closedSnapshot)
        let evidence = engine.lastRouteEvidence()

        XCTAssertEqual(state, .idleSafe)
        XCTAssertEqual(evidence?.releaseDecision?.outcome, .released)
        XCTAssertEqual(evidence?.clientActivity, closedSnapshot)
        XCTAssertEqual(evidence?.sessionId, "route-session-1")
    }

    func testEngineCreatesDifferentRouteSessionIdsAcrossSessions() {
        let ids = DeterministicIds(["route-session-1", "event-1", "route-session-2", "event-2"])
        let first = PassthroughRouteEngine(
            sharedMemory: nil,
            activityDetector: FixedSnapshotActivityDetector(snapshot: LiveRouteStabilityFixtures.clientActivity()),
            bridgeFactory: { _, _ in NoopPassthroughBridge() },
            idFactory: ids.next
        )
        let second = PassthroughRouteEngine(
            sharedMemory: nil,
            activityDetector: FixedSnapshotActivityDetector(snapshot: LiveRouteStabilityFixtures.clientActivity()),
            bridgeFactory: { _, _ in NoopPassthroughBridge() },
            idFactory: ids.next
        )

        _ = first.startAutomaticRoute { _, _ in }
        _ = second.startAutomaticRoute { _, _ in }

        XCTAssertEqual(first.currentRouteSessionId, "route-session-1")
        XCTAssertEqual(second.currentRouteSessionId, "route-session-2")
        XCTAssertNotEqual(first.currentRouteSessionId, second.currentRouteSessionId)
    }

    func testEngineEmitsFrameContinuityEvidence() {
        let ids = DeterministicIds(["route-session-1", "event-continuity"])
        let engine = PassthroughRouteEngine(
            sharedMemory: nil,
            activityDetector: FixedSnapshotActivityDetector(snapshot: LiveRouteStabilityFixtures.clientActivity()),
            bridgeFactory: { _, _ in NoopPassthroughBridge() },
            idFactory: ids.next
        )
        let continuity = FrameContinuitySnapshot(
            microphoneFramesObserved: 48_000,
            incomingFramesObserved: 48_000,
            missingFrameCount: 0,
            dropoutCount: 0,
            windowMs: 1_000
        )

        let event = engine.recordFrameContinuity(continuity)

        XCTAssertEqual(event.family, .frameContinuity)
        XCTAssertEqual(event.frameContinuity, continuity)
        XCTAssertEqual(event.sessionId, "route-session-1")
    }
}

private final class NoopPassthroughBridge: PassthroughBridgeControlling, @unchecked Sendable {
    private(set) var started = false

    func start() throws {
        started = true
    }

    func stop() {
        started = false
    }

    func refreshAppIOHeartbeat() {}
}

private struct FixedSnapshotActivityDetector: VirtualDeviceActivityDetecting {
    let snapshot: ClientActivitySnapshot

    func anyExpectedVirtualDeviceRunning() -> Bool {
        snapshot.microphoneRunning || snapshot.speakerRunning
    }

    func expectedVirtualDeviceClientActivity() -> ClientActivitySnapshot {
        snapshot
    }
}

private final class DeterministicIds: @unchecked Sendable {
    private var values: [String]
    private var index = 0

    init(_ values: [String]) {
        self.values = values
    }

    func next() -> String {
        defer { index += 1 }
        guard index < values.count else {
            return "extra-\(index)"
        }
        return values[index]
    }
}
#endif
