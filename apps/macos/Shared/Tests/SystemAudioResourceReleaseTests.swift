import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioResourceReleaseTests: XCTestCase {
    func testStopReleasesSystemAudioRuntimeAndMarksServiceNotRunning() async throws {
        let runtime = CountingSystemAudioRuntime()
        let service = SystemAudioCaptureService(runtime: runtime)

        _ = try await service.start(
            sessionId: "session",
            permissionState: .granted,
            scopeApproval: resourceReleaseScope()
        )
        XCTAssertTrue(await service.isRunning)

        _ = try await service.stop(stoppedAt: Date(timeIntervalSince1970: 2))

        XCTAssertFalse(await service.isRunning)
        XCTAssertEqual(runtime.startCount, 1)
        XCTAssertEqual(runtime.stopCount, 1)
    }

    func testReleaseForTerminationStopsRuntimeAndReturnsStoppedBeforeFramesWhenEmpty() async throws {
        let runtime = CountingSystemAudioRuntime()
        let service = SystemAudioCaptureService(runtime: runtime)

        _ = try await service.start(
            sessionId: "session",
            permissionState: .granted,
            scopeApproval: resourceReleaseScope()
        )

        let released = await service.releaseForTermination(stoppedAt: Date(timeIntervalSince1970: 3))
        let secondRelease = await service.releaseForTermination(stoppedAt: Date(timeIntervalSince1970: 4))

        XCTAssertEqual(released?.failureReason, .stoppedBeforeFrames)
        XCTAssertNil(secondRelease)
        XCTAssertFalse(await service.isRunning)
        XCTAssertEqual(runtime.stopCount, 1)
    }

    func testReleaseForTerminationKeepsBufferedRuntimeFrameTruth() async throws {
        let runtime = CountingSystemAudioRuntime()
        let sampleSource = BufferedLocalRecordingSampleSource()
        let service = SystemAudioCaptureService(runtime: runtime, sampleSource: sampleSource)

        _ = try await service.start(
            sessionId: "session",
            permissionState: .granted,
            scopeApproval: resourceReleaseScope()
        )
        sampleSource.append(
            Array(repeating: 0.2, count: 320),
            at: Date(timeIntervalSince1970: 2)
        )

        let released = await service.releaseForTermination(stoppedAt: Date(timeIntervalSince1970: 3))

        XCTAssertEqual(released?.frameCount, 160)
        XCTAssertEqual(released?.lastFrameAt, Date(timeIntervalSince1970: 2))
        XCTAssertEqual(released?.failureReason, .none)
        XCTAssertEqual(runtime.stopCount, 1)
    }

    func testStopTimeoutReleasesServiceStateWithoutWaitingForever() async throws {
        let runtime = SlowStoppingSystemAudioRuntime(stopDelaySeconds: 2)
        let service = SystemAudioCaptureService(
            runtime: runtime,
            runtimeStopTimeoutSeconds: 0.05
        )

        _ = try await service.start(
            sessionId: "session",
            permissionState: .granted,
            scopeApproval: resourceReleaseScope()
        )
        let startedAt = Date()
        let stopped = try await service.stop(stoppedAt: Date(timeIntervalSince1970: 2))
        let elapsed = Date().timeIntervalSince(startedAt)

        XCTAssertLessThan(elapsed, 1)
        XCTAssertFalse(await service.isRunning)
        XCTAssertEqual(stopped.failureReason, .captureFailed)
        XCTAssertEqual(runtime.stopCount, 1)
    }

    func testTerminationReleaseTimeoutMarksCaptureFailedAndClearsServiceState() async throws {
        let runtime = SlowStoppingSystemAudioRuntime(stopDelaySeconds: 2)
        let service = SystemAudioCaptureService(
            runtime: runtime,
            runtimeStopTimeoutSeconds: 0.05
        )

        _ = try await service.start(
            sessionId: "session",
            permissionState: .granted,
            scopeApproval: resourceReleaseScope()
        )
        let released = await service.releaseForTermination(stoppedAt: Date(timeIntervalSince1970: 3))

        XCTAssertFalse(await service.isRunning)
        XCTAssertEqual(released?.failureReason, .captureFailed)
        XCTAssertEqual(runtime.stopCount, 1)
    }
}

private func resourceReleaseScope() -> CaptureScopeApproval {
    CaptureScopeApproval(
        scopeApprovalId: "scope-release",
        scopeKind: .display,
        sourceDisplayName: "Current Display",
        approvedAt: Date(timeIntervalSince1970: 1),
        approvalMode: .userConfirmedSuggestedScope,
        eligibleReason: .manualMeetingScope
    )
}

private final class CountingSystemAudioRuntime: SystemAudioCaptureRuntime, @unchecked Sendable {
    var startCount = 0
    var stopCount = 0

    func start() async throws {
        startCount += 1
    }

    func stop() async {
        stopCount += 1
    }
}

private final class SlowStoppingSystemAudioRuntime: SystemAudioCaptureRuntime, @unchecked Sendable {
    private let stopDelaySeconds: TimeInterval
    private let lock = NSLock()
    private var protectedStopCount = 0

    init(stopDelaySeconds: TimeInterval) {
        self.stopDelaySeconds = stopDelaySeconds
    }

    var stopCount: Int {
        lock.lock()
        defer { lock.unlock() }
        return protectedStopCount
    }

    func start() async throws {}

    func stop() async {
        lock.lock()
        protectedStopCount += 1
        lock.unlock()
        try? await Task.sleep(nanoseconds: UInt64(stopDelaySeconds * 1_000_000_000))
    }
}
#endif
