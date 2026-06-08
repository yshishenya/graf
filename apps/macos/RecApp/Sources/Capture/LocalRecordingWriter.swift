import AVFoundation
import Foundation
import TwoBrainRecShared

public enum LocalRecordingWriterError: Error {
    case alreadyRecording
    case notRecording
    case directoryUnavailable
}

public struct LiveRecordingLevels: Equatable, Sendable {
    public var isRecording: Bool
    public var microphoneLevel: Double
    public var incomingLevel: Double
    public var microphoneUpdatedAt: Date?
    public var incomingUpdatedAt: Date?

    public init(
        isRecording: Bool,
        microphoneLevel: Double,
        incomingLevel: Double,
        microphoneUpdatedAt: Date?,
        incomingUpdatedAt: Date?
    ) {
        self.isRecording = isRecording
        self.microphoneLevel = Self.clamp(microphoneLevel)
        self.incomingLevel = Self.clamp(incomingLevel)
        self.microphoneUpdatedAt = microphoneUpdatedAt
        self.incomingUpdatedAt = incomingUpdatedAt
    }

    public static let inactive = LiveRecordingLevels(
        isRecording: false,
        microphoneLevel: 0,
        incomingLevel: 0,
        microphoneUpdatedAt: nil,
        incomingUpdatedAt: nil
    )

    public func microphoneIsLive(now: Date = Date(), staleAfter: TimeInterval = 2) -> Bool {
        isFresh(microphoneUpdatedAt, now: now, staleAfter: staleAfter)
    }

    public func incomingIsLive(now: Date = Date(), staleAfter: TimeInterval = 2) -> Bool {
        isFresh(incomingUpdatedAt, now: now, staleAfter: staleAfter)
    }

    private func isFresh(_ date: Date?, now: Date, staleAfter: TimeInterval) -> Bool {
        guard isRecording, let date else { return false }
        return now.timeIntervalSince(date) <= staleAfter
    }

    private static func clamp(_ value: Double) -> Double {
        min(1, max(0, value.isFinite ? value : 0))
    }
}

public protocol LocalRecordingSampleSource: Sendable {
    func readSamples(into destination: UnsafeMutablePointer<Float>, capacity: Int) -> Int
}

public final class BufferedLocalRecordingSampleSource: LocalRecordingSampleSource, @unchecked Sendable {
    private let lock = NSLock()
    private var buffer: [Float] = []
    private let capacity: Int

    public init(capacity: Int = 48_000 * 20) {
        self.capacity = capacity
    }

    public func append(_ samples: [Float]) {
        guard !samples.isEmpty else { return }
        lock.lock()
        buffer.append(contentsOf: samples)
        if buffer.count > capacity {
            buffer.removeFirst(buffer.count - capacity)
        }
        lock.unlock()
    }

    public func readSamples(into destination: UnsafeMutablePointer<Float>, capacity: Int) -> Int {
        lock.lock()
        defer { lock.unlock() }
        let count = min(capacity, buffer.count)
        guard count > 0 else { return 0 }
        for index in 0..<count {
            destination[index] = buffer[index]
        }
        buffer.removeFirst(count)
        return count
    }
}

public final class SharedMemoryRecordingSampleSource: LocalRecordingSampleSource, @unchecked Sendable {
    private let sharedMemory: SharedAudioMemory

    public init(sharedMemory: SharedAudioMemory) {
        self.sharedMemory = sharedMemory
    }

    public func readSamples(into destination: UnsafeMutablePointer<Float>, capacity: Int) -> Int {
        let available = min(Int(sharedMemory.captureAvailable()), capacity)
        guard available > 0 else { return 0 }
        return sharedMemory.readCapture(dst: destination, count: available)
    }
}

public final class LocalRecordingWriter {
    private let store: LocalRecordingStore
    private let manifestService: LocalRecordingManifestService
    private let microphoneSampleSourceFactory: @Sendable () -> LocalRecordingSampleSource?
    private let incomingSampleSourceFactory: @Sendable () -> LocalRecordingSampleSource?
    private let recordMicrophone: Bool
    private let queue = DispatchQueue(label: "pro.2brain.rec.local-recording-writer", qos: .utility)
    private var active: ActiveRecording?

    public init(
        store: LocalRecordingStore = LocalRecordingStore(),
        manifestService: LocalRecordingManifestService = LocalRecordingManifestService(),
        sharedMemoryFactory: @escaping @Sendable () -> SharedAudioMemory? = { SharedAudioMemory() },
        microphoneSampleSourceFactory: @escaping @Sendable () -> LocalRecordingSampleSource? = { nil },
        incomingSampleSourceFactory: (@Sendable () -> LocalRecordingSampleSource?)? = nil,
        recordMicrophone: Bool = true
    ) {
        self.store = store
        self.manifestService = manifestService
        self.microphoneSampleSourceFactory = microphoneSampleSourceFactory
        self.incomingSampleSourceFactory = incomingSampleSourceFactory ?? {
            sharedMemoryFactory().map { SharedMemoryRecordingSampleSource(sharedMemory: $0) }
        }
        self.recordMicrophone = recordMicrophone
    }

    public var isRecording: Bool {
        queue.sync { active != nil }
    }

    public func currentLevels(now: Date = Date()) -> LiveRecordingLevels {
        queue.sync {
            guard let active else { return .inactive }
            var microphoneLevel = active.lastMicrophoneLevel
            var microphoneUpdatedAt = active.lastMicrophoneFrameAt
            if let recorder = active.microphoneRecorder, recorder.isRecording {
                recorder.updateMeters()
                microphoneLevel = Self.normalizedPower(recorder.averagePower(forChannel: 0))
                microphoneUpdatedAt = now
                active.lastMicrophoneLevel = microphoneLevel
                active.lastMicrophoneFrameAt = now
            }
            return LiveRecordingLevels(
                isRecording: true,
                microphoneLevel: microphoneLevel,
                incomingLevel: active.lastIncomingLevel,
                microphoneUpdatedAt: microphoneUpdatedAt,
                incomingUpdatedAt: active.lastIncomingFrameAt
            )
        }
    }

    public func start(sessionId: String, startedAt: Date) throws -> LocalRecordingDirectory {
        try queue.sync {
            guard active == nil else { throw LocalRecordingWriterError.alreadyRecording }
            let directory: LocalRecordingDirectory
            do {
                directory = try store.createDirectory(sessionId: sessionId)
            } catch {
                throw LocalRecordingWriterError.directoryUnavailable
            }

            let microphoneSampleSource = microphoneSampleSourceFactory()
            let microphoneWriter: PCM16MonoWAVFileWriter?
            let microphone: AVAudioRecorder?
            if let microphoneSampleSource {
                microphone = nil
                microphoneWriter = try PCM16MonoWAVFileWriter(url: directory.localMicURL)
                _ = microphoneSampleSource
            } else {
                microphoneWriter = nil
                microphone = try Self.makeMicrophoneRecorder(url: directory.localMicURL)
            }
            if recordMicrophone, microphoneSampleSource == nil {
                microphone?.isMeteringEnabled = true
                microphone?.record()
            } else if microphoneSampleSource == nil {
                FileManager.default.createFile(atPath: directory.localMicURL.path, contents: nil)
            }

            let remoteWriter = try PCM16MonoWAVFileWriter(url: directory.remoteSpeakerURL)
            let incomingSampleSource = incomingSampleSourceFactory()
            let timer = DispatchSource.makeTimerSource(queue: queue)
            let scratch = UnsafeMutablePointer<Float>.allocate(capacity: 8192)
            timer.schedule(deadline: .now(), repeating: .milliseconds(50))
            timer.setEventHandler { [weak self] in
                guard let self, let active = self.active else { return }
                if let microphoneSampleSource = active.microphoneSampleSource,
                   let microphoneWriter = active.microphoneWriter {
                    let read = microphoneSampleSource.readSamples(into: active.scratch, capacity: active.scratchCapacity)
                    if read > 0 {
                        try? microphoneWriter.write(samples: active.scratch, count: read)
                        active.lastMicrophoneLevel = Self.rmsLevel(samples: active.scratch, count: read)
                        active.lastMicrophoneFrameAt = Date()
                    }
                }
                guard let incomingSampleSource = active.incomingSampleSource else { return }
                let incomingRead = incomingSampleSource.readSamples(into: active.scratch, capacity: active.scratchCapacity)
                if incomingRead > 0 {
                    try? active.remoteWriter.write(samples: active.scratch, count: incomingRead)
                    active.lastIncomingLevel = Self.rmsLevel(samples: active.scratch, count: incomingRead)
                    active.lastIncomingFrameAt = Date()
                }
            }

            let activeRecording = ActiveRecording(
                sessionId: sessionId,
                startedAt: startedAt,
                directory: directory,
                microphoneRecorder: microphone,
                microphoneWriter: microphoneWriter,
                microphoneSampleSource: microphoneSampleSource,
                remoteWriter: remoteWriter,
                incomingSampleSource: incomingSampleSource,
                timer: timer,
                scratch: scratch,
                scratchCapacity: 8192
            )
            active = activeRecording
            timer.resume()
            return directory
        }
    }

    public func stop(stoppedAt: Date = Date()) throws -> LocalRecordingManifest {
        try queue.sync {
            guard let active else { throw LocalRecordingWriterError.notRecording }
            active.timer.cancel()
            active.microphoneRecorder?.stop()
            try active.microphoneWriter?.close()
            try active.remoteWriter.close()
            active.scratch.deallocate()
            self.active = nil

            let elapsedDurationMs = Int(max(0, stoppedAt.timeIntervalSince(active.startedAt) * 1000))
            let elapsedFrameCount = Int64(max(0, stoppedAt.timeIntervalSince(active.startedAt) * 16_000))
            let micTrack = track(
                role: .localMic,
                url: active.directory.localMicURL,
                durationMs: active.microphoneWriter?.durationMs ?? elapsedDurationMs,
                frameCount: Int64(active.microphoneWriter?.frameCount ?? Int(elapsedFrameCount)),
                fileName: "mic.wav",
                timelineAligned: true
            )
            let timelineToleranceMs = 1_000
            let remoteTimelineAligned = abs(active.remoteWriter.durationMs - micTrack.durationMs) <= timelineToleranceMs
            let remoteTrack = track(
                role: .remoteSpeaker,
                url: active.directory.remoteSpeakerURL,
                durationMs: active.remoteWriter.durationMs,
                frameCount: Int64(active.remoteWriter.frameCount),
                fileName: "incoming.wav",
                timelineAligned: remoteTimelineAligned,
                observedLevel: active.lastIncomingLevel
            )
            let captureHealth = CaptureHealthMonitor().snapshot(
                sessionId: active.sessionId,
                phase: .stop,
                micDurationMs: micTrack.durationMs,
                incomingDurationMs: remoteTrack.durationMs,
                micFrameCount: micTrack.frameCount,
                incomingFrameCount: remoteTrack.frameCount,
                silentFrameCount: remoteTrack.failureReason == .silentInput ? remoteTrack.frameCount : 0
            )

            let manifest = manifestService.manifest(
                sessionId: active.sessionId,
                directoryId: active.directory.directoryId,
                startedAt: active.startedAt,
                stoppedAt: stoppedAt,
                tracks: [micTrack, remoteTrack],
                captureHealth: captureHealth
            )
            try manifestService.write(manifest, to: active.directory.manifestURL)
            return manifest
        }
    }

    public func currentDirectoryURL() -> URL? {
        queue.sync { active?.directory.directoryURL }
    }

    private func track(
        role: AudioTrackRole,
        url: URL,
        durationMs: Int,
        frameCount: Int64,
        fileName: String,
        timelineAligned: Bool,
        observedLevel: Double? = nil
    ) -> LocalRecordingTrack {
        let byteCount = (try? FileManager.default.attributesOfItem(atPath: url.path)[.size] as? NSNumber)?
            .int64Value ?? 0
        let complete = byteCount > 44 && frameCount > 0 && durationMs > 0
        let failureReason: LocalRecordingFailureReason
        if complete {
            if observedLevel == 0 {
                failureReason = .silentInput
            } else {
                failureReason = timelineAligned ? .none : .timelineMisaligned
            }
        } else {
            failureReason = .noFrames
        }
        let status: LocalRecordingTrackStatus = switch failureReason {
        case .none:
            .saved
        case .protectedAudioBlocked:
            .blocked
        case .directoryUnavailable, .captureFailed, .writeFailed, .finalizationFailed:
            .failed
        case .silentInput, .noFrames, .emptyRequiredTrack, .timelineMisaligned, .formatNotReady,
             .permissionDenied, .scopeUnavailable, .cpuGateFailed, .stoppedBeforeFrames,
             .halProbeObserved, .deviceUnavailable, .legacyNotReady, .appClosed, .unknown:
            complete ? .degraded : .missing
        }
        return LocalRecordingTrack(
            trackId: "\(role.rawValue)-track",
            role: role,
            status: status,
            fileName: fileName,
            format: "wav-pcm-s16le",
            sampleRate: 16_000,
            channelCount: 1,
            bitsPerSample: 16,
            durationMs: complete ? durationMs : 0,
            byteCount: byteCount,
            frameCount: complete ? frameCount : 0,
            timelineStartMs: 0,
            timelineAligned: complete && timelineAligned && failureReason == .none,
            failureReason: failureReason
        )
    }

    private static func makeMicrophoneRecorder(url: URL) throws -> AVAudioRecorder? {
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatLinearPCM),
            AVSampleRateKey: 16_000,
            AVNumberOfChannelsKey: 1,
            AVLinearPCMBitDepthKey: 16,
            AVLinearPCMIsFloatKey: false,
            AVLinearPCMIsBigEndianKey: false
        ]
        let recorder = try AVAudioRecorder(url: url, settings: settings)
        recorder.isMeteringEnabled = true
        recorder.prepareToRecord()
        return recorder
    }

    private static func normalizedPower(_ decibels: Float) -> Double {
        guard decibels.isFinite else { return 0 }
        let floor: Float = -60
        if decibels <= floor { return 0 }
        if decibels >= 0 { return 1 }
        return Double((decibels - floor) / -floor)
    }

    private static func rmsLevel(samples: UnsafePointer<Float>, count: Int) -> Double {
        guard count > 0 else { return 0 }
        var sum: Double = 0
        for index in 0..<count {
            let sample = Double(samples[index])
            sum += sample * sample
        }
        return min(1, sqrt(sum / Double(count)))
    }
}

private final class ActiveRecording {
    let sessionId: String
    let startedAt: Date
    let directory: LocalRecordingDirectory
    let microphoneRecorder: AVAudioRecorder?
    let microphoneWriter: PCM16MonoWAVFileWriter?
    let microphoneSampleSource: LocalRecordingSampleSource?
    let remoteWriter: PCM16MonoWAVFileWriter
    let incomingSampleSource: LocalRecordingSampleSource?
    let timer: DispatchSourceTimer
    let scratch: UnsafeMutablePointer<Float>
    let scratchCapacity: Int
    var lastMicrophoneLevel: Double
    var lastIncomingLevel: Double
    var lastMicrophoneFrameAt: Date?
    var lastIncomingFrameAt: Date?

    init(
        sessionId: String,
        startedAt: Date,
        directory: LocalRecordingDirectory,
        microphoneRecorder: AVAudioRecorder?,
        microphoneWriter: PCM16MonoWAVFileWriter?,
        microphoneSampleSource: LocalRecordingSampleSource?,
        remoteWriter: PCM16MonoWAVFileWriter,
        incomingSampleSource: LocalRecordingSampleSource?,
        timer: DispatchSourceTimer,
        scratch: UnsafeMutablePointer<Float>,
        scratchCapacity: Int
    ) {
        self.sessionId = sessionId
        self.startedAt = startedAt
        self.directory = directory
        self.microphoneRecorder = microphoneRecorder
        self.microphoneWriter = microphoneWriter
        self.microphoneSampleSource = microphoneSampleSource
        self.remoteWriter = remoteWriter
        self.incomingSampleSource = incomingSampleSource
        self.timer = timer
        self.scratch = scratch
        self.scratchCapacity = scratchCapacity
        self.lastMicrophoneLevel = 0
        self.lastIncomingLevel = 0
        self.lastMicrophoneFrameAt = nil
        self.lastIncomingFrameAt = nil
    }
}

private final class PCM16MonoWAVFileWriter {
    private let handle: FileHandle
    private(set) var frameCount = 0
    private let inputSampleRate = 48_000
    private let inputChannelCount = 2
    private let outputSampleRate = 16_000
    private let outputChannelCount = 1
    private let bitsPerSample = 16

    init(url: URL) throws {
        FileManager.default.createFile(atPath: url.path, contents: nil)
        handle = try FileHandle(forWritingTo: url)
        try handle.write(contentsOf: Data(repeating: 0, count: 44))
    }

    var durationMs: Int {
        Int((Double(frameCount) / Double(outputSampleRate)) * 1000)
    }

    func write(samples: UnsafePointer<Float>, count: Int) throws {
        guard count > 0 else { return }
        let inputFrameCount = count / inputChannelCount
        guard inputFrameCount > 0 else { return }
        let ratio = max(1, inputSampleRate / outputSampleRate)
        var data = Data()
        data.reserveCapacity((inputFrameCount / ratio) * MemoryLayout<Int16>.stride)
        var frameIndex = 0
        while frameIndex < inputFrameCount {
            let sampleIndex = frameIndex * inputChannelCount
            let left = samples[sampleIndex]
            let right = inputChannelCount > 1 ? samples[sampleIndex + 1] : left
            let mono = max(-1, min(1, (left + right) * 0.5))
            var intSample = Int16(mono * Float(Int16.max)).littleEndian
            data.append(Data(bytes: &intSample, count: MemoryLayout<Int16>.size))
            frameCount += 1
            frameIndex += ratio
        }
        guard !data.isEmpty else { return }
        try handle.write(contentsOf: data)
    }

    func close() throws {
        let dataByteCount = UInt32(frameCount * MemoryLayout<Int16>.stride)
        let riffByteCount = UInt32(36) + dataByteCount
        var header = Data()
        header.append(contentsOf: [0x52, 0x49, 0x46, 0x46])
        header.appendLE(riffByteCount)
        header.append(contentsOf: [0x57, 0x41, 0x56, 0x45])
        header.append(contentsOf: [0x66, 0x6d, 0x74, 0x20])
        header.appendLE(UInt32(16))
        header.appendLE(UInt16(1))
        header.appendLE(UInt16(outputChannelCount))
        header.appendLE(UInt32(outputSampleRate))
        header.appendLE(UInt32(outputSampleRate * outputChannelCount * MemoryLayout<Int16>.stride))
        header.appendLE(UInt16(outputChannelCount * MemoryLayout<Int16>.stride))
        header.appendLE(UInt16(bitsPerSample))
        header.append(contentsOf: [0x64, 0x61, 0x74, 0x61])
        header.appendLE(dataByteCount)
        try handle.seek(toOffset: 0)
        try handle.write(contentsOf: header)
        try handle.close()
    }
}

private extension Data {
    mutating func appendLE(_ value: UInt16) {
        var little = value.littleEndian
        append(Data(bytes: &little, count: MemoryLayout<UInt16>.size))
    }

    mutating func appendLE(_ value: UInt32) {
        var little = value.littleEndian
        append(Data(bytes: &little, count: MemoryLayout<UInt32>.size))
    }
}
