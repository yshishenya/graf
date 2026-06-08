import Foundation
import TwoBrainRecShared
#if canImport(CoreMedia)
import CoreMedia
#endif
#if canImport(AudioToolbox)
import AudioToolbox
#endif
#if canImport(ScreenCaptureKit)
import ScreenCaptureKit
#endif

public enum SystemAudioCaptureServiceError: Error, Equatable {
    case alreadyRunning
    case notRunning
    case permissionDenied
    case scopeNotApproved
    case runtimeStartFailed
    case screenCaptureKitUnavailable
    case noShareableDisplay
}

public protocol SystemAudioCaptureRuntime: Sendable {
    func start() async throws
    func stop() async
}

public protocol SystemAudioPermissionAuthorizing: Sendable {
    func currentPermissionState() -> CapturePermissionState
}

public struct CoreGraphicsSystemAudioPermissionAuthorizer: SystemAudioPermissionAuthorizing {
    public init() {}

    public func currentPermissionState() -> CapturePermissionState {
        #if canImport(CoreGraphics)
        return CGPreflightScreenCaptureAccess() ? .granted : .unknown
        #else
        return .unknown
        #endif
    }
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
        runtime: SystemAudioCaptureRuntime? = nil,
        sampleSource: BufferedLocalRecordingSampleSource = BufferedLocalRecordingSampleSource()
    ) {
        self.bufferedSampleSource = sampleSource
        self.incomingSampleSource = sampleSource
        self.runtime = runtime ?? Self.makeDefaultRuntime(sampleSource: sampleSource)
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

    private nonisolated static func makeDefaultRuntime(
        sampleSource: BufferedLocalRecordingSampleSource
    ) -> SystemAudioCaptureRuntime {
        #if canImport(ScreenCaptureKit) && canImport(CoreMedia) && canImport(AudioToolbox)
        return ScreenCaptureKitSystemAudioRuntime { samples in
            sampleSource.append(samples)
        }
        #else
        return NoopSystemAudioCaptureRuntime()
        #endif
    }
}

#if canImport(ScreenCaptureKit) && canImport(CoreMedia) && canImport(AudioToolbox)
public final class ScreenCaptureKitSystemAudioRuntime: NSObject, SystemAudioCaptureRuntime, SCStreamOutput, SCStreamDelegate, @unchecked Sendable {
    private let sampleHandler: @Sendable ([Float]) -> Void
    private let outputQueue = DispatchQueue(label: "pro.2brain.rec.screencapturekit.audio", qos: .userInitiated)
    private var stream: SCStream?

    public init(sampleHandler: @escaping @Sendable ([Float]) -> Void) {
        self.sampleHandler = sampleHandler
        super.init()
    }

    public func start() async throws {
        let content = try await SCShareableContent.excludingDesktopWindows(
            false,
            onScreenWindowsOnly: true
        )
        guard let display = content.displays.first else {
            throw SystemAudioCaptureServiceError.noShareableDisplay
        }

        let filter = SCContentFilter(display: display, excludingWindows: [])
        let configuration = SCStreamConfiguration()
        configuration.capturesAudio = true
        configuration.excludesCurrentProcessAudio = true
        configuration.sampleRate = 48_000
        configuration.channelCount = 2
        configuration.width = 2
        configuration.height = 2
        configuration.minimumFrameInterval = CMTime(value: 1, timescale: 1)
        configuration.showsCursor = false

        let stream = SCStream(filter: filter, configuration: configuration, delegate: self)
        try stream.addStreamOutput(self, type: .audio, sampleHandlerQueue: outputQueue)
        try await stream.startCapture()
        self.stream = stream
    }

    public func stop() async {
        guard let stream else { return }
        try? await stream.stopCapture()
        self.stream = nil
    }

    public func stream(
        _ stream: SCStream,
        didOutputSampleBuffer sampleBuffer: CMSampleBuffer,
        of outputType: SCStreamOutputType
    ) {
        guard outputType == .audio else { return }
        let samples = Self.extractFloatSamples(from: sampleBuffer)
        guard !samples.isEmpty else { return }
        sampleHandler(samples)
    }

    private static func extractFloatSamples(from sampleBuffer: CMSampleBuffer) -> [Float] {
        guard CMSampleBufferDataIsReady(sampleBuffer),
              let format = CMSampleBufferGetFormatDescription(sampleBuffer),
              let streamDescription = CMAudioFormatDescriptionGetStreamBasicDescription(format)?.pointee,
              let blockBuffer = CMSampleBufferGetDataBuffer(sampleBuffer)
        else {
            return []
        }

        var lengthAtOffset = 0
        var totalLength = 0
        var dataPointer: UnsafeMutablePointer<Int8>?
        guard CMBlockBufferGetDataPointer(
            blockBuffer,
            atOffset: 0,
            lengthAtOffsetOut: &lengthAtOffset,
            totalLengthOut: &totalLength,
            dataPointerOut: &dataPointer
        ) == kCMBlockBufferNoErr,
            let dataPointer,
            totalLength > 0
        else {
            return []
        }

        let flags = streamDescription.mFormatFlags
        if streamDescription.mBitsPerChannel == 32 &&
            flags & kAudioFormatFlagIsFloat != 0 {
            let count = totalLength / MemoryLayout<Float>.stride
            let pointer = UnsafeRawPointer(dataPointer).assumingMemoryBound(to: Float.self)
            return (0..<count).map { pointer[$0] }
        }

        if streamDescription.mBitsPerChannel == 16 &&
            flags & kAudioFormatFlagIsSignedInteger != 0 {
            let count = totalLength / MemoryLayout<Int16>.stride
            let pointer = UnsafeRawPointer(dataPointer).assumingMemoryBound(to: Int16.self)
            return (0..<count).map { Float(Int16(littleEndian: pointer[$0])) / Float(Int16.max) }
        }

        return []
    }
}
#endif
