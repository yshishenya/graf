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
#endif
