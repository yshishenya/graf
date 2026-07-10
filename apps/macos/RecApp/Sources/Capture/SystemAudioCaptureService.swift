import Foundation
import TwoBrainRecShared
#if canImport(CoreMedia)
import CoreMedia
#endif
#if canImport(AudioToolbox)
import AudioToolbox
#endif
#if canImport(CoreGraphics)
import CoreGraphics
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
    func requestPermission() async -> CapturePermissionState
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

    public func requestPermission() async -> CapturePermissionState {
        #if canImport(CoreGraphics)
        return CGRequestScreenCaptureAccess() ? .granted : currentPermissionState()
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
    private static let captureSampleRate: Double = 48_000
    private static let captureChannelCount = 1

    private let runtimeFactory: @Sendable () -> SystemAudioCaptureRuntime
    private let waitForTimedOutRuntimeStartCleanup: Bool
    private let runtimeStartTimeoutSeconds: TimeInterval
    private let runtimeStartCleanupTimeoutSeconds: TimeInterval
    private let runtimeStopTimeoutSeconds: TimeInterval
    private let runtimeStartFailureLogger: (@Sendable (String) -> Void)?
    public nonisolated let incomingSampleSource: LocalRecordingSampleSource
    private let bufferedSampleSource: BufferedLocalRecordingSampleSource
    private var activeSession: SystemAudioCaptureSession?
    private var activeRuntime: SystemAudioCaptureRuntime?
    private var pendingRuntimeStartCleanup: Task<Void, Never>?

    public init(
        runtime: SystemAudioCaptureRuntime? = nil,
        runtimeFactory: (@Sendable () -> SystemAudioCaptureRuntime)? = nil,
        sampleSource: BufferedLocalRecordingSampleSource? = nil,
        runtimeStartTimeoutSeconds: TimeInterval = 30,
        runtimeStartCleanupTimeoutSeconds: TimeInterval = 2,
        runtimeStopTimeoutSeconds: TimeInterval = 2,
        waitForTimedOutRuntimeStartCleanup: Bool? = nil,
        runtimeStartFailureLogger: (@Sendable (String) -> Void)? = nil
    ) {
        precondition(runtime == nil || runtimeFactory == nil, "Pass runtime or runtimeFactory, not both")
        let resolvedSampleSource = sampleSource ?? BufferedLocalRecordingSampleSource(
            channelCount: Self.captureChannelCount
        )
        let resolvedRuntimeFactory: @Sendable () -> SystemAudioCaptureRuntime
        if let runtimeFactory {
            resolvedRuntimeFactory = runtimeFactory
        } else if let runtime {
            resolvedRuntimeFactory = { runtime }
        } else {
            resolvedRuntimeFactory = {
                Self.makeDefaultRuntime(sampleSource: resolvedSampleSource)
            }
        }
        self.bufferedSampleSource = resolvedSampleSource
        self.incomingSampleSource = resolvedSampleSource
        self.runtimeStartTimeoutSeconds = runtimeStartTimeoutSeconds
        self.runtimeStartCleanupTimeoutSeconds = runtimeStartCleanupTimeoutSeconds
        self.runtimeStopTimeoutSeconds = runtimeStopTimeoutSeconds
        self.waitForTimedOutRuntimeStartCleanup = waitForTimedOutRuntimeStartCleanup ??
            (runtime != nil || runtimeFactory != nil)
        self.runtimeStartFailureLogger = runtimeStartFailureLogger
        self.runtimeFactory = resolvedRuntimeFactory
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
        if let pendingRuntimeStartCleanup {
            if waitForTimedOutRuntimeStartCleanup {
                await pendingRuntimeStartCleanup.value
            }
            self.pendingRuntimeStartCleanup = nil
        }
        guard permissionState == .granted else {
            throw SystemAudioCaptureServiceError.permissionDenied
        }
        guard scopeApproval.isAcceptedForMeetingRecording else {
            throw SystemAudioCaptureServiceError.scopeNotApproved
        }
        if activeSession != nil {
            throw SystemAudioCaptureServiceError.alreadyRunning
        }

        bufferedSampleSource.reset()
        let runtime = runtimeFactory()
        let startResult = await Self.startRuntime(
            runtime,
            timeoutSeconds: runtimeStartTimeoutSeconds,
            timeoutCleanupMode: waitForTimedOutRuntimeStartCleanup
                ? .waitForRuntimeStartTask
                : .bestEffort(timeoutSeconds: runtimeStartCleanupTimeoutSeconds)
        )
        pendingRuntimeStartCleanup = startResult.cleanupTask
        guard startResult.completed else {
            runtimeStartFailureLogger?(startResult.failureDetail ?? "reason=unknown")
            throw SystemAudioCaptureServiceError.runtimeStartFailed
        }

        let session = SystemAudioCaptureSession(
            sessionId: sessionId,
            permissionState: permissionState,
            scopeApprovalId: scopeApproval.scopeApprovalId,
            scopeKind: scopeApproval.scopeKind,
            sourceDisplayName: scopeApproval.sourceDisplayName,
            startedAt: startedAt,
            sampleRate: Self.captureSampleRate,
            channelCount: Self.captureChannelCount
        )
        activeSession = session
        activeRuntime = runtime
        return session
    }

    private nonisolated static func startRuntime(
        _ runtime: SystemAudioCaptureRuntime,
        timeoutSeconds: TimeInterval,
        timeoutCleanupMode: RuntimeStartTimeoutCleanupMode
    ) async -> RuntimeStartResult {
        guard timeoutSeconds > 0 else {
            do {
                try await runtime.start()
                return RuntimeStartResult(completed: true, cleanupTask: nil, failureDetail: nil)
            } catch {
                return RuntimeStartResult(
                    completed: false,
                    cleanupTask: nil,
                    failureDetail: runtimeStartFailureDetail(for: error)
                )
            }
        }

        let completion = RuntimeStartCompletion()
        let startTask = Task.detached {
            do {
                try await runtime.start()
                let accepted = completion.complete(
                    RuntimeStartResult(completed: true, cleanupTask: nil, failureDetail: nil)
                )
                if !accepted {
                    await runtime.stop()
                }
            } catch {
                _ = completion.complete(
                    RuntimeStartResult(
                        completed: false,
                        cleanupTask: nil,
                        failureDetail: runtimeStartFailureDetail(for: error)
                    )
                )
                await runtime.stop()
            }
        }
        let completed = await completion.wait(timeoutSeconds: timeoutSeconds)
        guard let result = completed else {
            let cleanupTask = Task.detached {
                switch timeoutCleanupMode {
                case .waitForRuntimeStartTask:
                    await runtime.stop()
                    _ = await startTask.result
                    await runtime.stop()
                case .bestEffort(let timeoutSeconds):
                    startTask.cancel()
                    _ = await Self.stopRuntime(runtime, timeoutSeconds: timeoutSeconds)
                }
            }
            return RuntimeStartResult(
                completed: false,
                cleanupTask: cleanupTask,
                failureDetail: runtimeStartTimeoutDetail(timeoutSeconds: timeoutSeconds)
            )
        }
        return result
    }

    public func appendIncomingSamples(_ samples: [Float], at date: Date = Date()) {
        guard !samples.isEmpty else { return }
        bufferedSampleSource.append(samples, at: date)
        if var session = activeSession {
            session.frameCount += Self.frameCount(forSampleCount: samples.count)
            session.lastFrameAt = date
            activeSession = session
        }
    }

    @discardableResult
    public func stop(stoppedAt: Date = Date()) async throws -> SystemAudioCaptureSession {
        guard var session = activeSession else {
            throw SystemAudioCaptureServiceError.notRunning
        }
        guard let runtime = activeRuntime else {
            activeSession = nil
            throw SystemAudioCaptureServiceError.notRunning
        }

        let stopCompleted = await Self.stopRuntime(
            runtime,
            timeoutSeconds: runtimeStopTimeoutSeconds
        )
        let stats = bufferedSampleSource.stats()
        let bufferedFrameCount = stats.frameCount
        if bufferedFrameCount > session.frameCount {
            session.frameCount = bufferedFrameCount
            session.lastFrameAt = stats.lastFrameAt
        }
        activeSession = nil
        activeRuntime = nil
        session.stoppedAt = stoppedAt
        if !stopCompleted {
            session.failureReason = .captureFailed
        } else if session.frameCount == 0 {
            session.failureReason = .noFrames
        }
        return session
    }

    @discardableResult
    public func releaseForTermination(stoppedAt: Date = Date()) async -> SystemAudioCaptureSession? {
        guard var session = activeSession else {
            return nil
        }
        guard let runtime = activeRuntime else {
            activeSession = nil
            return nil
        }

        let stopCompleted = await Self.stopRuntime(
            runtime,
            timeoutSeconds: runtimeStopTimeoutSeconds
        )
        let stats = bufferedSampleSource.stats()
        let bufferedFrameCount = stats.frameCount
        if bufferedFrameCount > session.frameCount {
            session.frameCount = bufferedFrameCount
            session.lastFrameAt = stats.lastFrameAt
        }
        activeSession = nil
        activeRuntime = nil
        session.stoppedAt = stoppedAt
        if !stopCompleted {
            session.failureReason = .captureFailed
        } else if session.frameCount == 0 {
            session.failureReason = .stoppedBeforeFrames
        }
        return session
    }

    private nonisolated static func stopRuntime(
        _ runtime: SystemAudioCaptureRuntime,
        timeoutSeconds: TimeInterval
    ) async -> Bool {
        guard timeoutSeconds > 0 else {
            await runtime.stop()
            return true
        }

        let completion = RuntimeStopCompletion()
        Task.detached {
            await runtime.stop()
            completion.complete(true)
        }
        return await completion.wait(timeoutSeconds: timeoutSeconds)
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

    private nonisolated static func frameCount(forSampleCount sampleCount: Int) -> Int64 {
        guard sampleCount > 0 else { return 0 }
        return Int64((sampleCount + captureChannelCount - 1) / captureChannelCount)
    }

    private nonisolated static func runtimeStartFailureDetail(for error: Error) -> String {
        let nsError = error as NSError
        return [
            "reason=error",
            "type=\(logToken(String(reflecting: Swift.type(of: error))))",
            "domain=\(logToken(nsError.domain))",
            "code=\(nsError.code)",
            "description=\(logToken(nsError.localizedDescription))"
        ].joined(separator: " ")
    }

    private nonisolated static func runtimeStartTimeoutDetail(timeoutSeconds: TimeInterval) -> String {
        let timeoutMs = Int((timeoutSeconds * 1000).rounded())
        return "reason=timeout timeoutMs=\(timeoutMs)"
    }

    private nonisolated static func logToken(_ value: String) -> String {
        value
            .replacingOccurrences(of: "\n", with: "_")
            .replacingOccurrences(of: "\r", with: "_")
            .replacingOccurrences(of: "\t", with: "_")
            .replacingOccurrences(of: " ", with: "_")
    }
}

private final class RuntimeStartCompletion: @unchecked Sendable {
    private let lock = NSLock()
    private var completed = false
    private var result: RuntimeStartResult?
    private var continuation: CheckedContinuation<RuntimeStartResult?, Never>?

    func wait(timeoutSeconds: TimeInterval) async -> RuntimeStartResult? {
        await withCheckedContinuation { continuation in
            lock.lock()
            if completed {
                let result = result
                lock.unlock()
                continuation.resume(returning: result)
                return
            }
            self.continuation = continuation
            lock.unlock()

            DispatchQueue.global(qos: .utility).asyncAfter(deadline: .now() + timeoutSeconds) {
                self.timeout()
            }
        }
    }

    @discardableResult
    func complete(_ result: RuntimeStartResult) -> Bool {
        lock.lock()
        guard !completed else {
            lock.unlock()
            return false
        }
        completed = true
        self.result = result
        let continuation = continuation
        self.continuation = nil
        lock.unlock()

        continuation?.resume(returning: result)
        return true
    }

    private func timeout() {
        lock.lock()
        guard !completed else {
            lock.unlock()
            return
        }
        completed = true
        result = nil
        let continuation = continuation
        self.continuation = nil
        lock.unlock()

        continuation?.resume(returning: nil)
    }
}

private struct RuntimeStartResult {
    let completed: Bool
    let cleanupTask: Task<Void, Never>?
    let failureDetail: String?
}

private enum RuntimeStartTimeoutCleanupMode: Sendable {
    case waitForRuntimeStartTask
    case bestEffort(timeoutSeconds: TimeInterval)
}

private final class RuntimeStopCompletion: @unchecked Sendable {
    private let lock = NSLock()
    private var completed = false
    private var continuation: CheckedContinuation<Bool, Never>?

    func wait(timeoutSeconds: TimeInterval) async -> Bool {
        await withCheckedContinuation { continuation in
            lock.lock()
            if completed {
                lock.unlock()
                continuation.resume(returning: true)
                return
            }
            self.continuation = continuation
            lock.unlock()

            DispatchQueue.global(qos: .utility).asyncAfter(deadline: .now() + timeoutSeconds) {
                self.complete(false)
            }
        }
    }

    func complete(_ result: Bool) {
        lock.lock()
        guard !completed else {
            lock.unlock()
            return
        }
        completed = true
        let continuation = continuation
        self.continuation = nil
        lock.unlock()

        continuation?.resume(returning: result)
    }
}

#if canImport(ScreenCaptureKit) && canImport(CoreMedia) && canImport(AudioToolbox)
public final class ScreenCaptureKitSystemAudioRuntime: NSObject, SystemAudioCaptureRuntime, SCStreamOutput, SCStreamDelegate, @unchecked Sendable {
    private let sampleHandler: @Sendable ([Float]) -> Void
    private let outputQueue = DispatchQueue(label: "pro.2brain.graf.screencapturekit.audio", qos: .userInitiated)
    private let streamLock = NSLock()
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
        configuration.channelCount = 1
        configuration.width = 16
        configuration.height = 16
        configuration.minimumFrameInterval = CMTime(value: 1, timescale: 1)
        configuration.showsCursor = false

        let stream = SCStream(filter: filter, configuration: configuration, delegate: self)
        try stream.addStreamOutput(self, type: .audio, sampleHandlerQueue: outputQueue)
        try stream.addStreamOutput(self, type: .screen, sampleHandlerQueue: outputQueue)
        setCurrentStream(stream)
        do {
            try await stream.startCapture()
        } catch {
            clearCurrentStreamIfSame(stream)
            try? await stream.stopCapture()
            throw error
        }
    }

    public func stop() async {
        guard let stream = currentStream() else { return }
        clearCurrentStreamIfSame(stream)
        try? stream.removeStreamOutput(self, type: .audio)
        try? stream.removeStreamOutput(self, type: .screen)
        try? await stream.stopCapture()
    }

    public func stream(
        _ stream: SCStream,
        didOutputSampleBuffer sampleBuffer: CMSampleBuffer,
        of outputType: SCStreamOutputType
    ) {
        guard outputType == .audio else { return }
        guard isCurrentStream(stream) else { return }
        let samples = SystemAudioSampleExtractor.extractMonoFloatSamples(from: sampleBuffer)
        guard !samples.isEmpty else { return }
        sampleHandler(samples)
    }

    private func currentStream() -> SCStream? {
        streamLock.lock()
        defer { streamLock.unlock() }
        return stream
    }

    private func setCurrentStream(_ stream: SCStream) {
        streamLock.lock()
        self.stream = stream
        streamLock.unlock()
    }

    private func clearCurrentStreamIfSame(_ stream: SCStream) {
        streamLock.lock()
        if self.stream === stream {
            self.stream = nil
        }
        streamLock.unlock()
    }

    private func isCurrentStream(_ stream: SCStream) -> Bool {
        streamLock.lock()
        defer { streamLock.unlock() }
        return self.stream === stream
    }
}
#endif

#if canImport(CoreMedia) && canImport(AudioToolbox)
enum SystemAudioSampleExtractor {
    static func extractMonoFloatSamples(from sampleBuffer: CMSampleBuffer) -> [Float] {
        guard CMSampleBufferDataIsReady(sampleBuffer),
              let format = CMSampleBufferGetFormatDescription(sampleBuffer),
              let streamDescription = CMAudioFormatDescriptionGetStreamBasicDescription(format)?.pointee
        else {
            return []
        }

        let samples = extractFloatSamples(from: sampleBuffer)
        return downmixInterleavedSamples(samples, channelCount: Int(streamDescription.mChannelsPerFrame))
    }

    static func extractFloatSamples(from sampleBuffer: CMSampleBuffer) -> [Float] {
        guard CMSampleBufferDataIsReady(sampleBuffer),
              let format = CMSampleBufferGetFormatDescription(sampleBuffer),
              let streamDescription = CMAudioFormatDescriptionGetStreamBasicDescription(format)?.pointee
        else {
            return []
        }

        if let blockSamples = extractFromContiguousBlockBuffer(
            sampleBuffer: sampleBuffer,
            streamDescription: streamDescription
        ) {
            return blockSamples
        }

        return extractFromAudioBufferList(
            sampleBuffer: sampleBuffer,
            streamDescription: streamDescription
        )
    }

    static func extractFloatSamples(
        streamDescription: AudioStreamBasicDescription,
        bufferData: [Data]
    ) -> [Float] {
        let bytesPerSample = Int(streamDescription.mBitsPerChannel / 8)
        guard bytesPerSample > 0 else { return [] }
        if bufferData.count == 1 {
            return bufferData[0].withUnsafeBytes { rawBuffer in
                guard let baseAddress = rawBuffer.baseAddress, rawBuffer.count > 0 else {
                    return []
                }
                return extractFloatSamples(
                    streamDescription: streamDescription,
                    buffers: [(baseAddress, rawBuffer.count)]
                )
            }
        }

        let decodedBuffers = bufferData.map { data -> [Float] in
            data.withUnsafeBytes { rawBuffer in
                guard let baseAddress = rawBuffer.baseAddress, rawBuffer.count > 0 else {
                    return []
                }
                return extractFloatSamples(
                    streamDescription: streamDescription,
                    buffers: [(baseAddress, rawBuffer.count)]
                )
            }
        }
        guard let frameCount = decodedBuffers.map(\.count).min(), frameCount > 0 else {
            return []
        }
        var samples: [Float] = []
        samples.reserveCapacity(frameCount * decodedBuffers.count)
        for frame in 0..<frameCount {
            for buffer in decodedBuffers {
                samples.append(buffer[frame])
            }
        }
        return samples
    }

    static func downmixInterleavedSamples(_ samples: [Float], channelCount: Int) -> [Float] {
        guard channelCount > 1 else { return samples }
        let frameCount = samples.count / channelCount
        guard frameCount > 0 else { return [] }
        var mono: [Float] = []
        mono.reserveCapacity(frameCount)
        for frame in 0..<frameCount {
            let frameOffset = frame * channelCount
            var sum: Float = 0
            for channel in 0..<channelCount {
                sum += samples[frameOffset + channel]
            }
            mono.append(sum / Float(channelCount))
        }
        return mono
    }

    private static func extractFromContiguousBlockBuffer(
        sampleBuffer: CMSampleBuffer,
        streamDescription: AudioStreamBasicDescription
    ) -> [Float]? {
        guard let blockBuffer = CMSampleBufferGetDataBuffer(sampleBuffer) else {
            return nil
        }

        var lengthAtOffset = 0
        var totalLength = 0
        var dataPointer: UnsafeMutablePointer<Int8>?
        let status = CMBlockBufferGetDataPointer(
            blockBuffer,
            atOffset: 0,
            lengthAtOffsetOut: &lengthAtOffset,
            totalLengthOut: &totalLength,
            dataPointerOut: &dataPointer
        )
        guard status == kCMBlockBufferNoErr, let dataPointer, totalLength > 0 else {
            return nil
        }

        return extractFloatSamples(
            streamDescription: streamDescription,
            buffers: [(UnsafeRawPointer(dataPointer), totalLength)]
        )
    }

    private static func extractFromAudioBufferList(
        sampleBuffer: CMSampleBuffer,
        streamDescription: AudioStreamBasicDescription
    ) -> [Float] {
        var bufferListSize = 0
        var retainedBlockBuffer: CMBlockBuffer?
        let sizeStatus = CMSampleBufferGetAudioBufferListWithRetainedBlockBuffer(
            sampleBuffer,
            bufferListSizeNeededOut: &bufferListSize,
            bufferListOut: nil,
            bufferListSize: 0,
            blockBufferAllocator: kCFAllocatorDefault,
            blockBufferMemoryAllocator: kCFAllocatorDefault,
            flags: 0,
            blockBufferOut: &retainedBlockBuffer
        )
        guard sizeStatus == noErr, bufferListSize > 0 else {
            return []
        }

        let rawBufferList = UnsafeMutableRawPointer.allocate(
            byteCount: bufferListSize,
            alignment: MemoryLayout<AudioBufferList>.alignment
        )
        defer { rawBufferList.deallocate() }

        let bufferListPointer = rawBufferList.bindMemory(to: AudioBufferList.self, capacity: 1)
        let dataStatus = CMSampleBufferGetAudioBufferListWithRetainedBlockBuffer(
            sampleBuffer,
            bufferListSizeNeededOut: nil,
            bufferListOut: bufferListPointer,
            bufferListSize: bufferListSize,
            blockBufferAllocator: kCFAllocatorDefault,
            blockBufferMemoryAllocator: kCFAllocatorDefault,
            flags: 0,
            blockBufferOut: &retainedBlockBuffer
        )
        guard dataStatus == noErr else {
            return []
        }

        let audioBuffers = UnsafeMutableAudioBufferListPointer(bufferListPointer)
        let buffers: [(UnsafeRawPointer, Int)] = audioBuffers.compactMap { audioBuffer in
            guard let data = audioBuffer.mData, audioBuffer.mDataByteSize > 0 else {
                return nil
            }
            return (UnsafeRawPointer(data), Int(audioBuffer.mDataByteSize))
        }
        return extractFloatSamples(streamDescription: streamDescription, buffers: buffers)
    }

    private static func extractFloatSamples(
        streamDescription: AudioStreamBasicDescription,
        buffers: [(UnsafeRawPointer, Int)]
    ) -> [Float] {
        guard !buffers.isEmpty else { return [] }
        let flags = streamDescription.mFormatFlags
        let isBigEndian = flags & kAudioFormatFlagIsBigEndian != 0
        if streamDescription.mBitsPerChannel == 32 &&
            flags & kAudioFormatFlagIsFloat != 0 {
            return extractSamples(
                buffers: buffers,
                sampleStride: MemoryLayout<Float>.stride
            ) { pointer, index in
                let bitPattern = pointer.assumingMemoryBound(to: UInt32.self)[index]
                let hostBits = isBigEndian ? UInt32(bigEndian: bitPattern) : UInt32(littleEndian: bitPattern)
                return Float(bitPattern: hostBits)
            }
        }

        if streamDescription.mBitsPerChannel == 16 &&
            flags & kAudioFormatFlagIsSignedInteger != 0 {
            return extractSamples(
                buffers: buffers,
                sampleStride: MemoryLayout<Int16>.stride
            ) { pointer, index in
                let sample = pointer.assumingMemoryBound(to: Int16.self)[index]
                let hostSample = isBigEndian ? Int16(bigEndian: sample) : Int16(littleEndian: sample)
                return max(-1, min(1, Float(hostSample) / Float(Int16.max)))
            }
        }

        return []
    }

    private static func extractSamples(
        buffers: [(UnsafeRawPointer, Int)],
        sampleStride: Int,
        read: (UnsafeRawPointer, Int) -> Float
    ) -> [Float] {
        if buffers.count == 1 {
            let (pointer, byteCount) = buffers[0]
            let sampleCount = byteCount / sampleStride
            guard sampleCount > 0 else { return [] }
            return (0..<sampleCount).map { read(pointer, $0) }
        }

        let sampleCounts = buffers.map { $0.1 / sampleStride }
        guard let frameCount = sampleCounts.min(), frameCount > 0 else {
            return []
        }
        var samples: [Float] = []
        samples.reserveCapacity(frameCount * buffers.count)
        for frame in 0..<frameCount {
            for (pointer, _) in buffers {
                samples.append(read(pointer, frame))
            }
        }
        return samples
    }
}
#endif
