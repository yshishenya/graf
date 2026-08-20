import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioCaptureServiceTests: XCTestCase {
    func testGeneratedSystemRouteGenerationAdvancesAcrossSessions() async throws {
        let source = BufferedLocalRecordingSampleSource(channelCount: 1)
        let service = SystemAudioCaptureService(runtime: FakeSystemAudioRuntime(), sampleSource: source)
        _ = try await service.start(
            sessionId: "first",
            permissionState: .granted,
            scopeApproval: approvedScope()
        )
        await service.appendIncomingSamples(Array(repeating: 0.1, count: 480))
        let first = try XCTUnwrap(source.readTimestampedBatch(maximumFrameCount: 480))
        _ = try await service.stop()

        _ = try await service.start(
            sessionId: "second",
            permissionState: .granted,
            scopeApproval: approvedScope()
        )
        await service.appendIncomingSamples(Array(repeating: 0.1, count: 480))
        let second = try XCTUnwrap(source.readTimestampedBatch(maximumFrameCount: 480))
        _ = try await service.stop()

        XCTAssertGreaterThan(first.routeGeneration, 0)
        XCTAssertGreaterThan(second.routeGeneration, first.routeGeneration)
    }

    func testScreenCaptureKitRuntimeStartsWithScreenAndAudioOutputs() throws {
        let source = try String(
            contentsOf: repositoryRootForSystemAudioCaptureTests()
                .appendingPathComponent("apps/macos/RecApp/Sources/Capture/SystemAudioCaptureService.swift"),
            encoding: .utf8
        )

        XCTAssertTrue(source.contains("configuration.width = 16"))
        XCTAssertTrue(source.contains("configuration.height = 16"))
        XCTAssertTrue(source.contains("runtimeStartTimeoutSeconds: TimeInterval = 120"))
        XCTAssertTrue(source.contains("runtimeStopTimeoutSeconds: TimeInterval = 120"))
        XCTAssertTrue(source.contains("func verifyCurrentPermission() async -> CapturePermissionState"))
        XCTAssertTrue(source.contains("let observedState = currentPermissionState()"))
        XCTAssertTrue(source.contains("return observedState == .granted ? .stale : observedState"))
        XCTAssertFalse(source.contains("guard currentPermissionState() != .granted else { return .granted }"))
        XCTAssertTrue(source.contains("guard content.displays.first != nil else"))
        XCTAssertTrue(source.contains("SCShareableContent.excludingDesktopWindows"))
        XCTAssertTrue(source.contains("_ = CGRequestScreenCaptureAccess()"))
        XCTAssertTrue(source.contains("return await verifyCurrentPermission()"))
        XCTAssertFalse(source.contains("if CGRequestScreenCaptureAccess() {\n            return .granted"))
        XCTAssertTrue(source.contains("stream.addStreamOutput(self, type: .audio"))
        XCTAssertTrue(source.contains("stream.addStreamOutput(self, type: .screen"))
        XCTAssertTrue(source.contains("stream.removeStreamOutput(self, type: .screen"))
        XCTAssertTrue(source.contains("outputQueue.sync {}"))
        XCTAssertTrue(source.contains("kAudioHardwarePropertyDefaultOutputDevice"))
        XCTAssertTrue(source.contains("discontinuity: .routeChanged"))
    }

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
            let running = await service.isRunning
            XCTAssertFalse(running)
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
        XCTAssertEqual(started.sampleRate, 48_000)
        XCTAssertEqual(started.channelCount, 1)
        XCTAssertEqual(stopped.frameCount, 480)
        XCTAssertEqual(stopped.failureReason, LocalRecordingFailureReason.none)
    }

    func testIncomingSampleSourceFeedsCurrentWriter() async throws {
        let service = SystemAudioCaptureService(runtime: FakeSystemAudioRuntime())
        _ = try await service.start(
            sessionId: "session",
            permissionState: .granted,
            scopeApproval: approvedScope()
        )
        await service.appendIncomingSamples(Array(repeating: 0.4, count: 256))

        let batch = service.incomingSampleSource.readTimestampedBatch(maximumFrameCount: 512)

        XCTAssertEqual(batch?.samples.count, 256)
        XCTAssertEqual(batch?.samples.first ?? 0, 0.4, accuracy: 0.0001)
        _ = try await service.stop()
    }

    func testIncomingBatchPreservesPTSFormatAndRouteGenerationForTimeline() async throws {
        let service = SystemAudioCaptureService(runtime: FakeSystemAudioRuntime())
        _ = try await service.start(
            sessionId: "timestamped-system-audio",
            permissionState: .granted,
            scopeApproval: approvedScope()
        )
        let original = RecordingAudioBatch(
            samples: Array(repeating: 0.25, count: 480),
            format: RecordingAudioFormat(sampleRate: 48_000, channelCount: 1),
            presentationTime: RecordingAudioPresentationTimestamp(seconds: 321.25, clockDomain: .hostTime),
            discontinuity: .none,
            routeGeneration: 7
        )

        await service.appendIncomingBatch(original, observedAt: Date(timeIntervalSince1970: 11))
        let restored = try XCTUnwrap(service.incomingSampleSource.readTimestampedBatch(maximumFrameCount: 480))

        XCTAssertEqual(restored.presentationTime, original.presentationTime)
        XCTAssertEqual(restored.format, original.format)
        XCTAssertEqual(restored.discontinuity, .none)
        XCTAssertEqual(restored.routeGeneration, 7)
        XCTAssertEqual(restored.samples, original.samples)
        _ = try await service.stop()
    }

    func testSplitIncomingBatchPreservesPTSAndCallbackObservation() async throws {
        let service = SystemAudioCaptureService(runtime: FakeSystemAudioRuntime())
        _ = try await service.start(
            sessionId: "timestamped-system-audio-split",
            permissionState: .granted,
            scopeApproval: approvedScope()
        )
        let original = RecordingAudioBatch(
            samples: Array(repeating: 0.25, count: 960),
            format: RecordingAudioFormat(sampleRate: 48_000, channelCount: 1),
            presentationTime: RecordingAudioPresentationTimestamp(
                seconds: 321.25,
                clockDomain: .sourcePresentationTime,
                observedHostTimeSeconds: 321.75
            ),
            discontinuity: .none,
            routeGeneration: 7
        )

        await service.appendIncomingBatch(original, observedAt: Date(timeIntervalSince1970: 11))
        let first = try XCTUnwrap(service.incomingSampleSource.readTimestampedBatch(maximumFrameCount: 480))
        let remainder = try XCTUnwrap(service.incomingSampleSource.readTimestampedBatch(maximumFrameCount: 480))

        XCTAssertEqual(first.presentationTime, original.presentationTime)
        XCTAssertEqual(remainder.presentationTime.seconds, 321.26, accuracy: 0.000001)
        XCTAssertEqual(remainder.presentationTime.clockDomain, .sourcePresentationTime)
        XCTAssertEqual(remainder.presentationTime.observedHostTimeSeconds, 321.75)
        XCTAssertEqual(remainder.format, original.format)
        XCTAssertEqual(remainder.routeGeneration, 7)
        XCTAssertEqual(first.samples.count, 480)
        XCTAssertEqual(remainder.samples.count, 480)
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

        XCTAssertEqual(stopped.frameCount, 256)
        XCTAssertEqual(stopped.lastFrameAt, Date(timeIntervalSince1970: 11))
        XCTAssertEqual(stopped.failureReason, LocalRecordingFailureReason.none)
        XCTAssertTrue(stopped.canBeAccepted)
    }

    func testBufferedRuntimeStatsTreatStereoSamplesAsFramesOnce() async throws {
        let sampleSource = BufferedLocalRecordingSampleSource(channelCount: 2)
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

        XCTAssertEqual(stopped.frameCount, 256)
        XCTAssertEqual(stopped.lastFrameAt, Date(timeIntervalSince1970: 11))
    }

    func testStartResetsBufferedSamplesAndStatsBetweenSessions() async throws {
        let sampleSource = BufferedLocalRecordingSampleSource()
        let service = SystemAudioCaptureService(
            runtime: FakeSystemAudioRuntime(),
            sampleSource: sampleSource
        )

        _ = try await service.start(
            sessionId: "first",
            permissionState: .granted,
            scopeApproval: approvedScope(),
            startedAt: Date(timeIntervalSince1970: 10)
        )
        sampleSource.append(
            Array(repeating: 0.8, count: 512),
            at: Date(timeIntervalSince1970: 11)
        )
        _ = try await service.stop(stoppedAt: Date(timeIntervalSince1970: 12))

        _ = try await service.start(
            sessionId: "second",
            permissionState: .granted,
            scopeApproval: approvedScope(),
            startedAt: Date(timeIntervalSince1970: 20)
        )
        XCTAssertNil(service.incomingSampleSource.readTimestampedBatch(maximumFrameCount: 512))

        let stopped = try await service.stop(stoppedAt: Date(timeIntervalSince1970: 21))
        XCTAssertEqual(stopped.sessionId, "second")
        XCTAssertEqual(stopped.frameCount, 0)
        XCTAssertEqual(stopped.lastFrameAt, nil)
        XCTAssertEqual(stopped.failureReason, .noFrames)
    }

    func testStartTimeoutFailsFastAndDoesNotLeaveServiceRunning() async throws {
        let runtime = SlowStartingSystemAudioRuntime(startDelaySeconds: 0.2)
        let service = SystemAudioCaptureService(
            runtime: runtime,
            runtimeStartTimeoutSeconds: 0.05
        )

        let startedAt = Date()
        do {
            _ = try await service.start(
                sessionId: "session",
                permissionState: .granted,
                scopeApproval: approvedScope()
            )
            XCTFail("Slow runtime start should fail with runtimeStartFailed")
        } catch SystemAudioCaptureServiceError.runtimeStartFailed {
            let elapsed = Date().timeIntervalSince(startedAt)
            XCTAssertLessThan(elapsed, 1)
            let running = await service.isRunning
            XCTAssertFalse(running)
        }

        try? await Task.sleep(nanoseconds: 350_000_000)
        XCTAssertEqual(runtime.startCount, 1)
        XCTAssertEqual(runtime.stopCount, 3)
    }

    func testImmediateRuntimeStartFailureDoesNotBecomeAcceptedStart() async throws {
        let service = SystemAudioCaptureService(
            runtime: FailingSystemAudioRuntime(),
            runtimeStartTimeoutSeconds: 1
        )

        do {
            _ = try await service.start(
                sessionId: "session",
                permissionState: .granted,
                scopeApproval: approvedScope()
            )
            XCTFail("Failing runtime start should fail with runtimeStartFailed")
        } catch SystemAudioCaptureServiceError.runtimeStartFailed {
            let running = await service.isRunning
            XCTAssertFalse(running)
        }
    }

    func testImmediateRuntimeStartFailureLogsDiagnosticDetail() async throws {
        let logger = RuntimeStartFailureRecorder()
        let service = SystemAudioCaptureService(
            runtime: FailingSystemAudioRuntime(),
            runtimeStartTimeoutSeconds: 1,
            runtimeStartFailureLogger: { detail in
                logger.record(detail)
            }
        )

        do {
            _ = try await service.start(
                sessionId: "session",
                permissionState: .granted,
                scopeApproval: approvedScope()
            )
            XCTFail("Failing runtime start should fail with runtimeStartFailed")
        } catch SystemAudioCaptureServiceError.runtimeStartFailed {
            XCTAssertEqual(logger.details.count, 1)
            XCTAssertTrue(logger.details[0].contains("reason=error"))
            XCTAssertTrue(logger.details[0].contains("description="))
        }
    }

    func testRuntimeStartFailureStopsPartiallyStartedRuntime() async throws {
        let runtime = PartiallyStartingThenFailingSystemAudioRuntime()
        let service = SystemAudioCaptureService(
            runtime: runtime,
            runtimeStartTimeoutSeconds: 1
        )

        do {
            _ = try await service.start(
                sessionId: "session",
                permissionState: .granted,
                scopeApproval: approvedScope()
            )
            XCTFail("Partially started runtime must fail closed")
        } catch SystemAudioCaptureServiceError.runtimeStartFailed {
            let running = await service.isRunning
            XCTAssertFalse(running)
        }

        XCTAssertEqual(runtime.startCount, 1)
        // The service reports the failed start before its detached cleanup finishes.
        // Wait only for that bounded cleanup instead of depending on task scheduling.
        for _ in 0..<50 {
            if runtime.stopCount == 1 {
                break
            }
            try? await Task.sleep(nanoseconds: 10_000_000)
        }
        XCTAssertEqual(runtime.stopCount, 1)
    }

    func testRetryWaitsForTimedOutRuntimeStartCleanup() async throws {
        let firstStartGate = RecoveringRuntimeStartGate()
        let runtime = RecoveringSlowStartingSystemAudioRuntime(firstStartGate: firstStartGate)
        let service = SystemAudioCaptureService(
            runtime: runtime,
            runtimeStartTimeoutSeconds: 0.05
        )

        do {
            _ = try await service.start(
                sessionId: "first",
                permissionState: .granted,
                scopeApproval: approvedScope()
            )
            XCTFail("First slow runtime start should fail with runtimeStartFailed")
        } catch SystemAudioCaptureServiceError.runtimeStartFailed {
            let running = await service.isRunning
            XCTAssertFalse(running)
        }

        // Wait until the cleanup has stopped the timed-out runtime and is now
        // blocked on its first start. This is a deterministic boundary: a retry
        // must not create a second runtime start until the gate is released.
        await firstStartGate.waitUntilFirstStop()
        let retry = Task {
            try await service.start(
                sessionId: "second",
                permissionState: .granted,
                scopeApproval: approvedScope()
            )
        }
        for _ in 0..<10 {
            await Task.yield()
        }

        XCTAssertEqual(runtime.startCount, 1)
        let runningWhileRetryWaits = await service.isRunning
        XCTAssertFalse(runningWhileRetryWaits)

        await firstStartGate.releaseFirstStart()
        let second = try await retry.value
        XCTAssertEqual(second.sessionId, "second")
        XCTAssertEqual(runtime.startCount, 2)
        XCTAssertGreaterThanOrEqual(runtime.stopCount, 2)
        let runningAfterRetry = await service.isRunning
        XCTAssertTrue(runningAfterRetry)

        let stopCountBeforeAcceptedStop = runtime.stopCount
        _ = try await service.stop()
        XCTAssertEqual(runtime.stopCount, stopCountBeforeAcceptedStop + 1)
    }

    func testRetryCanUseFreshRuntimeAfterTimedOutStartCleanup() async throws {
        let firstRuntime = CancellableSlowStartingSystemAudioRuntime()
        let secondRuntime = FakeSystemAudioRuntime()
        let runtimeFactory = SequencedSystemAudioRuntimeFactory([firstRuntime, secondRuntime])
        let service = SystemAudioCaptureService(
            runtimeFactory: { runtimeFactory.next() },
            runtimeStartTimeoutSeconds: 0.05,
            runtimeStartCleanupTimeoutSeconds: 0.05,
            waitForTimedOutRuntimeStartCleanup: false
        )

        do {
            _ = try await service.start(
                sessionId: "first",
                permissionState: .granted,
                scopeApproval: approvedScope()
            )
            XCTFail("First runtime should time out")
        } catch SystemAudioCaptureServiceError.runtimeStartFailed {
            let running = await service.isRunning
            XCTAssertFalse(running)
        }

        let startedAt = Date()
        let second = try await service.start(
            sessionId: "second",
            permissionState: .granted,
            scopeApproval: approvedScope()
        )
        let elapsed = Date().timeIntervalSince(startedAt)

        XCTAssertEqual(second.sessionId, "second")
        XCTAssertLessThan(elapsed, 1)
        XCTAssertEqual(firstRuntime.startCount, 1)
        XCTAssertGreaterThanOrEqual(firstRuntime.stopCount, 1)
        XCTAssertTrue(secondRuntime.didStart)

        _ = try await service.stop()
        XCTAssertTrue(secondRuntime.didStop)
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

private func repositoryRootForSystemAudioCaptureTests() throws -> URL {
    var candidate = URL(fileURLWithPath: #filePath)
    while candidate.path != "/" {
        let package = candidate.appendingPathComponent("apps/macos/Package.swift")
        if FileManager.default.fileExists(atPath: package.path) {
            return candidate
        }
        candidate.deleteLastPathComponent()
    }
    throw CocoaError(.fileNoSuchFile)
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

private final class FailingSystemAudioRuntime: SystemAudioCaptureRuntime, @unchecked Sendable {
    func start() async throws {
        throw SystemAudioCaptureServiceError.runtimeStartFailed
    }

    func stop() async {}
}

private final class RuntimeStartFailureRecorder: @unchecked Sendable {
    private let lock = NSLock()
    private var protectedDetails: [String] = []

    var details: [String] {
        lock.withLock { protectedDetails }
    }

    func record(_ detail: String) {
        lock.withLock {
            protectedDetails.append(detail)
        }
    }
}

private final class PartiallyStartingThenFailingSystemAudioRuntime: SystemAudioCaptureRuntime, @unchecked Sendable {
    private let lock = NSLock()
    private var protectedStartCount = 0
    private var protectedStopCount = 0

    var startCount: Int {
        lock.withLock { protectedStartCount }
    }

    var stopCount: Int {
        lock.withLock { protectedStopCount }
    }

    func start() async throws {
        lock.withLock {
            protectedStartCount += 1
        }
        throw SystemAudioCaptureServiceError.runtimeStartFailed
    }

    func stop() async {
        lock.withLock {
            protectedStopCount += 1
        }
    }
}

private final class SlowStartingSystemAudioRuntime: SystemAudioCaptureRuntime, @unchecked Sendable {
    private let startDelaySeconds: TimeInterval
    private let lock = NSLock()
    private var protectedStartCount = 0
    private var protectedStopCount = 0

    init(startDelaySeconds: TimeInterval) {
        self.startDelaySeconds = startDelaySeconds
    }

    var startCount: Int {
        lock.withLock { protectedStartCount }
    }

    var stopCount: Int {
        lock.withLock { protectedStopCount }
    }

    func start() async throws {
        lock.withLock {
            protectedStartCount += 1
        }
        try? await Task.sleep(nanoseconds: UInt64(startDelaySeconds * 1_000_000_000))
    }

    func stop() async {
        lock.withLock {
            protectedStopCount += 1
        }
    }
}

private final class RecoveringSlowStartingSystemAudioRuntime: SystemAudioCaptureRuntime, @unchecked Sendable {
    private let firstStartGate: RecoveringRuntimeStartGate
    private let lock = NSLock()
    private var protectedStartCount = 0
    private var protectedStopCount = 0

    init(firstStartGate: RecoveringRuntimeStartGate) {
        self.firstStartGate = firstStartGate
    }

    var startCount: Int {
        lock.withLock { protectedStartCount }
    }

    var stopCount: Int {
        lock.withLock { protectedStopCount }
    }

    func start() async throws {
        let currentStart = lock.withLock {
            protectedStartCount += 1
            return protectedStartCount
        }

        if currentStart == 1 {
            await firstStartGate.waitForRelease()
        }
    }

    func stop() async {
        lock.withLock {
            protectedStopCount += 1
        }
        await firstStartGate.recordStop()
    }
}

private actor RecoveringRuntimeStartGate {
    private var firstStopObserved = false
    private var firstStopWaiters: [CheckedContinuation<Void, Never>] = []
    private var released = false
    private var releaseContinuation: CheckedContinuation<Void, Never>?

    func waitForRelease() async {
        guard !released else {
            return
        }
        await withCheckedContinuation { continuation in
            if released {
                continuation.resume()
            } else {
                releaseContinuation = continuation
            }
        }
    }

    func recordStop() {
        guard !firstStopObserved else {
            return
        }
        firstStopObserved = true
        let waiters = firstStopWaiters
        firstStopWaiters.removeAll()
        waiters.forEach { $0.resume() }
    }

    func waitUntilFirstStop() async {
        guard !firstStopObserved else {
            return
        }
        await withCheckedContinuation { continuation in
            if firstStopObserved {
                continuation.resume()
            } else {
                firstStopWaiters.append(continuation)
            }
        }
    }

    func releaseFirstStart() {
        guard !released else {
            return
        }
        released = true
        releaseContinuation?.resume()
        releaseContinuation = nil
    }
}

private final class CancellableSlowStartingSystemAudioRuntime: SystemAudioCaptureRuntime, @unchecked Sendable {
    private let lock = NSLock()
    private var protectedStartCount = 0
    private var protectedStopCount = 0

    var startCount: Int {
        lock.withLock { protectedStartCount }
    }

    var stopCount: Int {
        lock.withLock { protectedStopCount }
    }

    func start() async throws {
        lock.withLock {
            protectedStartCount += 1
        }
        try await Task.sleep(nanoseconds: 10_000_000_000)
    }

    func stop() async {
        lock.withLock {
            protectedStopCount += 1
        }
    }
}

private final class SequencedSystemAudioRuntimeFactory: @unchecked Sendable {
    private let lock = NSLock()
    private var runtimes: [SystemAudioCaptureRuntime]

    init(_ runtimes: [SystemAudioCaptureRuntime]) {
        self.runtimes = runtimes
    }

    func next() -> SystemAudioCaptureRuntime {
        lock.withLock {
            guard !runtimes.isEmpty else {
                return FakeSystemAudioRuntime()
            }
            return runtimes.removeFirst()
        }
    }
}
#endif
