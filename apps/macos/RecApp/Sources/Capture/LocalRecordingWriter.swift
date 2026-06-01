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

            let remoteWriter = try FloatWAVFileWriter(url: directory.remoteSpeakerURL)
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
                frameCount: Int64(max(0, stoppedAt.timeIntervalSince(active.startedAt) * 48_000)),
                fileName: "local-mic.wav"
            )
            let remoteTrack = track(
                role: .remoteSpeaker,
                url: active.directory.remoteSpeakerURL,
                durationMs: active.remoteWriter.durationMs,
                frameCount: Int64(active.remoteWriter.frameCount),
                fileName: "remote-speaker.wav"
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
        fileName: String
    ) -> LocalRecordingTrack {
        let byteCount = (try? FileManager.default.attributesOfItem(atPath: url.path)[.size] as? NSNumber)?
            .int64Value ?? 0
        let complete = byteCount > 44 && frameCount > 0 && durationMs > 0
        return LocalRecordingTrack(
            trackId: "\(role.rawValue)-track",
            role: role,
            status: complete ? .saved : .missing,
            fileName: fileName,
            format: "wav-lpcm",
            sampleRate: 48_000,
            channelCount: 2,
            durationMs: complete ? durationMs : 0,
            byteCount: byteCount,
            frameCount: complete ? frameCount : 0,
            failureReason: complete ? .none : .emptyRequiredTrack
        )
    }

    private static func makeMicrophoneRecorder(url: URL) throws -> AVAudioRecorder? {
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatLinearPCM),
            AVSampleRateKey: 48_000,
            AVNumberOfChannelsKey: 2,
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
    let remoteWriter: FloatWAVFileWriter
    let sharedMemory: SharedAudioMemory?
    let timer: DispatchSourceTimer
    let scratch: UnsafeMutablePointer<Float>
    let scratchCapacity: Int

    init(
        sessionId: String,
        startedAt: Date,
        directory: LocalRecordingDirectory,
        microphoneRecorder: AVAudioRecorder?,
        remoteWriter: FloatWAVFileWriter,
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

private final class FloatWAVFileWriter {
    private let handle: FileHandle
    private(set) var sampleCount = 0
    private let sampleRate = 48_000
    private let channelCount = 2

    init(url: URL) throws {
        FileManager.default.createFile(atPath: url.path, contents: nil)
        handle = try FileHandle(forWritingTo: url)
        try handle.write(contentsOf: Data(repeating: 0, count: 44))
    }

    var frameCount: Int {
        sampleCount / channelCount
    }

    var durationMs: Int {
        Int((Double(frameCount) / Double(sampleRate)) * 1000)
    }

    func write(samples: UnsafePointer<Float>, count: Int) throws {
        guard count > 0 else { return }
        let byteCount = count * MemoryLayout<Float>.stride
        let data = Data(bytes: samples, count: byteCount)
        try handle.write(contentsOf: data)
        sampleCount += count
    }

    func close() throws {
        let dataByteCount = UInt32(sampleCount * MemoryLayout<Float>.stride)
        let riffByteCount = UInt32(36) + dataByteCount
        var header = Data()
        header.append(contentsOf: [0x52, 0x49, 0x46, 0x46])
        header.appendLE(riffByteCount)
        header.append(contentsOf: [0x57, 0x41, 0x56, 0x45])
        header.append(contentsOf: [0x66, 0x6d, 0x74, 0x20])
        header.appendLE(UInt32(16))
        header.appendLE(UInt16(3))
        header.appendLE(UInt16(channelCount))
        header.appendLE(UInt32(sampleRate))
        header.appendLE(UInt32(sampleRate * channelCount * MemoryLayout<Float>.stride))
        header.appendLE(UInt16(channelCount * MemoryLayout<Float>.stride))
        header.appendLE(UInt16(32))
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
