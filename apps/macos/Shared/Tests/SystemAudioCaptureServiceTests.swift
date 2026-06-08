import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioCaptureServiceTests: XCTestCase {
    func testStartRequiresGrantedPermissionAndApprovedScope() async throws {
        let service = SystemAudioCaptureService(runtime: FakeSystemAudioRuntime())
        let approval = approvedScope()

        do {
            _ = try await service.start(
                sessionId: "session",
                permissionState: .denied,
                scopeApproval: approval
            )
            XCTFail("Denied permission must not start system-audio capture")
        } catch SystemAudioCaptureServiceError.permissionDenied {
            XCTAssertFalse(await service.isRunning)
        }
    }

    func testLifecycleRecordsIncomingFramesFromFakeSamples() async throws {
        let runtime = FakeSystemAudioRuntime()
        let service = SystemAudioCaptureService(runtime: runtime)
        let approval = approvedScope()

        let started = try await service.start(
            sessionId: "session",
            permissionState: .granted,
            scopeApproval: approval,
            startedAt: Date(timeIntervalSince1970: 10)
        )
        await service.appendIncomingSamples(Array(repeating: 0.2, count: 480), at: Date(timeIntervalSince1970: 11))
        let stopped = try await service.stop(stoppedAt: Date(timeIntervalSince1970: 12))

        XCTAssertTrue(runtime.didStart)
        XCTAssertTrue(runtime.didStop)
        XCTAssertEqual(started.scopeApprovalId, "scope-1")
        XCTAssertEqual(stopped.frameCount, 480)
        XCTAssertEqual(stopped.failureReason, .none)
    }

    func testIncomingSampleSourceFeedsWriterWithoutHAL() async throws {
        let service = SystemAudioCaptureService(runtime: FakeSystemAudioRuntime())
        _ = try await service.start(
            sessionId: "session",
            permissionState: .granted,
            scopeApproval: approvedScope()
        )
        await service.appendIncomingSamples(Array(repeating: 0.4, count: 256))

        let scratch = UnsafeMutablePointer<Float>.allocate(capacity: 512)
        defer { scratch.deallocate() }
        let read = service.incomingSampleSource.readSamples(into: scratch, capacity: 512)

        XCTAssertEqual(read, 256)
        XCTAssertEqual(scratch[0], 0.4, accuracy: 0.0001)
        _ = try await service.stop()
    }

    func testStopUsesBufferedRuntimeStatsWhenSamplesBypassActorAppend() async throws {
        let sampleSource = BufferedLocalRecordingSampleSource()
        let service = SystemAudioCaptureService(
            runtime: FakeSystemAudioRuntime(),
            sampleSource: sampleSource
        )
        _ = try await service.start(
            sessionId: "session",
            permissionState: .granted,
            scopeApproval: approvedScope(),
            startedAt: Date(timeIntervalSince1970: 10)
        )

        sampleSource.append(
            Array(repeating: 0.3, count: 512),
            at: Date(timeIntervalSince1970: 11)
        )
        let stopped = try await service.stop(stoppedAt: Date(timeIntervalSince1970: 12))

        XCTAssertEqual(stopped.frameCount, 512)
        XCTAssertEqual(stopped.lastFrameAt, Date(timeIntervalSince1970: 11))
        XCTAssertEqual(stopped.failureReason, .none)
        XCTAssertTrue(stopped.canBeAccepted)
    }
}

private func approvedScope() -> CaptureScopeApproval {
    CaptureScopeApproval(
        scopeApprovalId: "scope-1",
        scopeKind: .application,
        sourceDisplayName: "Telemost",
        approvedAt: Date(timeIntervalSince1970: 1),
        approvalMode: .manualSelection,
        eligibleReason: .approvedMeetingApp
    )
}

private final class FakeSystemAudioRuntime: SystemAudioCaptureRuntime, @unchecked Sendable {
    var didStart = false
    var didStop = false

    func start() async throws {
        didStart = true
    }

    func stop() async {
        didStop = true
    }
}
#endif
