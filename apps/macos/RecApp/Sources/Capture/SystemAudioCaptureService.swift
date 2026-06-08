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
        bufferedSampleSource.append(samples, at: date)
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

        await runtime.stop()
        let stats = bufferedSampleSource.stats()
        if stats.frameCount > session.frameCount {
            session.frameCount = stats.frameCount
            session.lastFrameAt = stats.lastFrameAt
        }
        activeSession = nil
        session.stoppedAt = stoppedAt
        if session.frameCount == 0 {
            session.failureReason = .noFrames
        }
        return session
    }

    @discardableResult
    public func releaseForTermination(stoppedAt: Date = Date()) async -> SystemAudioCaptureSession? {
        guard var session = activeSession else {
            return nil
        }

        await runtime.stop()
        let stats = bufferedSampleSource.stats()
        if stats.frameCount > session.frameCount {
            session.frameCount = stats.frameCount
            session.lastFrameAt = stats.lastFrameAt
        }
        activeSession = nil
        session.stoppedAt = stoppedAt
        if session.frameCount == 0 {
            session.failureReason = .stoppedBeforeFrames
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
        let samples = SystemAudioSampleExtractor.extractFloatSamples(from: sampleBuffer)
        guard !samples.isEmpty else { return }
        sampleHandler(samples)
    }
}
#endif

#if canImport(CoreMedia) && canImport(AudioToolbox)
enum SystemAudioSampleExtractor {
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
                return Float(hostSample) / Float(Int16.max)
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
