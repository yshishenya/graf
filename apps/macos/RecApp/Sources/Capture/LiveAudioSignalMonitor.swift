import Foundation
import TwoBrainRecShared

public protocol LiveAudioSignalSampleSource {
    func writeIndexSnapshot(checkedAt: Date) -> SharedAudioMemory.WriteIndexSnapshot
    func peekLatestMic(dst: UnsafeMutablePointer<Float>, count: Int) -> Int
    func peekLatestSpeaker(dst: UnsafeMutablePointer<Float>, count: Int) -> Int
    func peekLatestCapture(dst: UnsafeMutablePointer<Float>, count: Int) -> Int
}

extension SharedAudioMemory: LiveAudioSignalSampleSource {}

public final class LiveAudioSignalMonitor {
    private let sampleSource: LiveAudioSignalSampleSource?
    private let scratch: UnsafeMutablePointer<Float>
    private let scratchCapacity: Int
    private var lastMicReadIndex: UInt64 = 0
    private var lastMicWriteIndex: UInt64 = 0
    private var lastSpeakerWriteIndex: UInt64 = 0
    private var lastCaptureWriteIndex: UInt64 = 0
    private var lastMicrophoneLevel = 0.0
    private var lastIncomingLevel = 0.0
    private var lastMicrophoneFrameAt: Date?
    private var lastIncomingFrameAt: Date?

    public init(
        sampleSource: LiveAudioSignalSampleSource? = SharedAudioMemory(),
        scratchCapacity: Int = 2048
    ) {
        self.sampleSource = sampleSource
        self.scratchCapacity = scratchCapacity
        self.scratch = UnsafeMutablePointer<Float>.allocate(capacity: scratchCapacity)
        self.scratch.initialize(repeating: 0, count: scratchCapacity)
    }

    deinit {
        scratch.deinitialize(count: scratchCapacity)
        scratch.deallocate()
    }

    public func currentLevels(
        routeActive: Bool,
        now: Date = Date()
    ) -> LiveRouteSignalLevels {
        if let sampleSource {
            updateSharedMemoryLevels(sampleSource: sampleSource, now: now)
        }

        return LiveRouteSignalLevels(
            isActive: routeActive,
            microphoneLevel: lastMicrophoneLevel,
            speakerLevel: lastIncomingLevel,
            microphoneUpdatedAt: lastMicrophoneFrameAt,
            speakerUpdatedAt: lastIncomingFrameAt
        )
    }

    private func updateSharedMemoryLevels(sampleSource: LiveAudioSignalSampleSource, now: Date) {
        let indexes = sampleSource.writeIndexSnapshot(checkedAt: now)

        let micClientReadAdvanced = indexes.micReadIndex != lastMicReadIndex
        let micWriterAdvanced = indexes.micWriteIndex != lastMicWriteIndex
        if micClientReadAdvanced && micWriterAdvanced {
            let count = sampleSource.peekLatestMic(dst: scratch, count: scratchCapacity)
            if count > 0 {
                lastMicrophoneLevel = Self.rmsLevel(samples: scratch, count: count)
                lastMicrophoneFrameAt = now
            }
        }
        lastMicReadIndex = indexes.micReadIndex
        lastMicWriteIndex = indexes.micWriteIndex

        if indexes.captureWriteIndex != lastCaptureWriteIndex {
            let count = sampleSource.peekLatestCapture(dst: scratch, count: scratchCapacity)
            if count > 0 {
                lastIncomingLevel = Self.rmsLevel(samples: scratch, count: count)
                lastIncomingFrameAt = now
            }
        } else if indexes.speakerWriteIndex != lastSpeakerWriteIndex {
            let count = sampleSource.peekLatestSpeaker(dst: scratch, count: scratchCapacity)
            if count > 0 {
                lastIncomingLevel = Self.rmsLevel(samples: scratch, count: count)
                lastIncomingFrameAt = now
            }
        }
        lastCaptureWriteIndex = indexes.captureWriteIndex
        lastSpeakerWriteIndex = indexes.speakerWriteIndex
    }

    private static func rmsLevel(samples: UnsafePointer<Float>, count: Int) -> Double {
        guard count > 0 else { return 0 }
        var sum = 0.0
        for index in 0..<count {
            let sample = Double(samples[index])
            sum += sample * sample
        }
        return min(1, sqrt(sum / Double(count)))
    }
}
