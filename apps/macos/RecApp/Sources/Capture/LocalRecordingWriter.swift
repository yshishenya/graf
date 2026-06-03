import AVFoundation
import Foundation
import TwoBrainRecShared

public enum LocalRecordingWriterError: Error {
    case alreadyRecording
    case notRecording
    case directoryUnavailable
}

public final class LocalRecordingWriter {
    private let store: LocalRecordingStore
    private let manifestService: LocalRecordingManifestService
    private let sharedMemoryFactory: @Sendable () -> SharedAudioMemory?
    private let recordMicrophone: Bool
    private let queue = DispatchQueue(label: "pro.2brain.rec.local-recording-writer", qos: .utility)
    private var active: ActiveRecording?

    public init(
        store: LocalRecordingStore = LocalRecordingStore(),
        manifestService: LocalRecordingManifestService = LocalRecordingManifestService(),
        sharedMemoryFactory: @escaping @Sendable () -> SharedAudioMemory? = { SharedAudioMemory() },
        recordMicrophone: Bool = true
    ) {
        self.store = store
        self.manifestService = manifestService
        self.sharedMemoryFactory = sharedMemoryFactory
        self.recordMicrophone = recordMicrophone
    }

    public var isRecording: Bool {
        queue.sync { active != nil }
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

            let microphone = try Self.makeMicrophoneRecorder(url: directory.localMicURL)
            if recordMicrophone {
                microphone?.record()
            } else {
                FileManager.default.createFile(atPath: directory.localMicURL.path, contents: nil)
            }

            let remoteWriter = try PCM16MonoWAVFileWriter(url: directory.remoteSpeakerURL)
            let sharedMemory = sharedMemoryFactory()
            let timer = DispatchSource.makeTimerSource(queue: queue)
            let scratch = UnsafeMutablePointer<Float>.allocate(capacity: 8192)
            timer.schedule(deadline: .now(), repeating: .milliseconds(50))
            timer.setEventHandler { [weak self] in
                guard let self, let active = self.active, let sharedMemory = active.sharedMemory else { return }
                let available = min(Int(sharedMemory.captureAvailable()), active.scratchCapacity)
                guard available > 0 else { return }
                let read = sharedMemory.readCapture(dst: active.scratch, count: available)
                if read > 0 {
                    try? active.remoteWriter.write(samples: active.scratch, count: read)
                }
            }

            let activeRecording = ActiveRecording(
                sessionId: sessionId,
                startedAt: startedAt,
                directory: directory,
                microphoneRecorder: microphone,
                remoteWriter: remoteWriter,
                sharedMemory: sharedMemory,
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
            try active.remoteWriter.close()
            active.scratch.deallocate()
            self.active = nil

            let micTrack = track(
                role: .localMic,
                url: active.directory.localMicURL,
                durationMs: Int(max(0, stoppedAt.timeIntervalSince(active.startedAt) * 1000)),
                frameCount: Int64(max(0, stoppedAt.timeIntervalSince(active.startedAt) * 16_000)),
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
                timelineAligned: remoteTimelineAligned
            )

            let manifest = manifestService.manifest(
                sessionId: active.sessionId,
                directoryId: active.directory.directoryId,
                startedAt: active.startedAt,
                stoppedAt: stoppedAt,
                tracks: [micTrack, remoteTrack]
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
        timelineAligned: Bool
    ) -> LocalRecordingTrack {
        let byteCount = (try? FileManager.default.attributesOfItem(atPath: url.path)[.size] as? NSNumber)?
            .int64Value ?? 0
        let complete = byteCount > 44 && frameCount > 0 && durationMs > 0
        let failureReason: LocalRecordingFailureReason
        if complete {
            failureReason = timelineAligned ? .none : .timelineMisaligned
        } else {
            failureReason = .emptyRequiredTrack
        }
        return LocalRecordingTrack(
            trackId: "\(role.rawValue)-track",
            role: role,
            status: complete ? .saved : .missing,
            fileName: fileName,
            format: "wav-pcm-s16le",
            sampleRate: 16_000,
            channelCount: 1,
            bitsPerSample: 16,
            durationMs: complete ? durationMs : 0,
            byteCount: byteCount,
            frameCount: complete ? frameCount : 0,
            timelineStartMs: 0,
            timelineAligned: complete && timelineAligned,
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
        recorder.prepareToRecord()
        return recorder
    }
}

private final class ActiveRecording {
    let sessionId: String
    let startedAt: Date
    let directory: LocalRecordingDirectory
    let microphoneRecorder: AVAudioRecorder?
    let remoteWriter: PCM16MonoWAVFileWriter
    let sharedMemory: SharedAudioMemory?
    let timer: DispatchSourceTimer
    let scratch: UnsafeMutablePointer<Float>
    let scratchCapacity: Int

    init(
        sessionId: String,
        startedAt: Date,
        directory: LocalRecordingDirectory,
        microphoneRecorder: AVAudioRecorder?,
        remoteWriter: PCM16MonoWAVFileWriter,
        sharedMemory: SharedAudioMemory?,
        timer: DispatchSourceTimer,
        scratch: UnsafeMutablePointer<Float>,
        scratchCapacity: Int
    ) {
        self.sessionId = sessionId
        self.startedAt = startedAt
        self.directory = directory
        self.microphoneRecorder = microphoneRecorder
        self.remoteWriter = remoteWriter
        self.sharedMemory = sharedMemory
        self.timer = timer
        self.scratch = scratch
        self.scratchCapacity = scratchCapacity
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
