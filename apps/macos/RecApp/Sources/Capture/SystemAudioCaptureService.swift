import Foundation
import TwoBrainRecShared
#if canImport(ScreenCaptureKit)
import ScreenCaptureKit
#endif

public enum SystemAudioCaptureServiceError: Error, Equatable {
    case alreadyRunning
    case notRunning
    case permissionDenied
    case scopeNotApproved
    case runtimeStartFailed
}

public protocol SystemAudioCaptureRuntime: Sendable {
    func start() async throws
    func stop() async
}

public final class NoopSystemAudioCaptureRuntime: SystemAudioCaptureRuntime {
    public init() {}

    public func start() async throws {}
    public func stop() async {}
}

public actor SystemAudioCaptureService {
    private let runtime: SystemAudioCaptureRuntime
    public nonisolated let incomingSampleSource: LocalRecordingSampleSource
    private let bufferedSampleSource: BufferedLocalRecordingSampleSource
    private var activeSession: SystemAudioCaptureSession?

    public init(
        runtime: SystemAudioCaptureRuntime = NoopSystemAudioCaptureRuntime(),
        sampleSource: BufferedLocalRecordingSampleSource = BufferedLocalRecordingSampleSource()
    ) {
        self.runtime = runtime
        self.bufferedSampleSource = sampleSource
        self.incomingSampleSource = sampleSource
    }

    public var isRunning: Bool {
        activeSession != nil
    }

    public func start(
        sessionId: String,
        permissionState: CapturePermissionState,
        scopeApproval: CaptureScopeApproval,
        startedAt: Date = Date()
    ) async throws -> SystemAudioCaptureSession {
        guard permissionState == .granted else {
            throw SystemAudioCaptureServiceError.permissionDenied
        }
        guard scopeApproval.isAcceptedForMeetingRecording else {
            throw SystemAudioCaptureServiceError.scopeNotApproved
        }
        if activeSession != nil {
            throw SystemAudioCaptureServiceError.alreadyRunning
        }

        do {
            try await runtime.start()
        } catch {
            throw SystemAudioCaptureServiceError.runtimeStartFailed
        }

        let session = SystemAudioCaptureSession(
            sessionId: sessionId,
            permissionState: permissionState,
            scopeApprovalId: scopeApproval.scopeApprovalId,
            scopeKind: scopeApproval.scopeKind,
            sourceDisplayName: scopeApproval.sourceDisplayName,
            startedAt: startedAt
        )
        activeSession = session
        return session
    }

    public func appendIncomingSamples(_ samples: [Float], at date: Date = Date()) {
        guard !samples.isEmpty else { return }
        bufferedSampleSource.append(samples)
        if var session = activeSession {
            session.frameCount += Int64(samples.count)
            session.lastFrameAt = date
            activeSession = session
        }
    }

    @discardableResult
    public func stop(stoppedAt: Date = Date()) async throws -> SystemAudioCaptureSession {
        guard var session = activeSession else {
            throw SystemAudioCaptureServiceError.notRunning
        }
        activeSession = nil

        await runtime.stop()
        session.stoppedAt = stoppedAt
        if session.frameCount == 0 {
            session.failureReason = .noFrames
        }
        return session
    }
}
