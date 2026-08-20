import AVFoundation
import Foundation
import TwoBrainRecShared

public enum LocalRecordingWriterError: Error {
    case alreadyRecording
    case notRecording
    case directoryUnavailable
    case echoProcessorUnavailable
}

public struct LiveRecordingLevels: Equatable, Sendable {
    public var isRecording: Bool
    public var microphoneLevel: Double
    public var incomingLevel: Double
    public var microphoneUpdatedAt: Date?
    public var incomingUpdatedAt: Date?
    public var integrityFailureCode: String?

    public init(
        isRecording: Bool,
        microphoneLevel: Double,
        incomingLevel: Double,
        microphoneUpdatedAt: Date?,
        incomingUpdatedAt: Date?,
        integrityFailureCode: String? = nil
    ) {
        self.isRecording = isRecording
        self.microphoneLevel = Self.clamp(microphoneLevel)
        self.incomingLevel = Self.clamp(incomingLevel)
        self.microphoneUpdatedAt = microphoneUpdatedAt
        self.incomingUpdatedAt = incomingUpdatedAt
        self.integrityFailureCode = integrityFailureCode
    }

    public static let inactive = LiveRecordingLevels(
        isRecording: false,
        microphoneLevel: 0,
        incomingLevel: 0,
        microphoneUpdatedAt: nil,
        incomingUpdatedAt: nil,
        integrityFailureCode: nil
    )

    public func microphoneIsLive(now: Date = Date(), staleAfter: TimeInterval = 2) -> Bool {
        isFresh(microphoneUpdatedAt, now: now, staleAfter: staleAfter)
    }

    public func incomingIsLive(now: Date = Date(), staleAfter: TimeInterval = 2) -> Bool {
        isFresh(incomingUpdatedAt, now: now, staleAfter: staleAfter)
    }

    private func isFresh(_ date: Date?, now: Date, staleAfter: TimeInterval) -> Bool {
        guard isRecording, let date else { return false }
        let age = now.timeIntervalSince(date)
        return age >= 0 && age <= staleAfter
    }

    private static func clamp(_ value: Double) -> Double {
        min(1, max(0, value.isFinite ? value : 0))
    }
}

public protocol LocalRecordingSampleSource: Sendable {
    func readSamples(into destination: UnsafeMutablePointer<Float>, capacity: Int) -> Int
}

/// New capture writes PTS-bearing batches. `LocalRecordingSampleSource` remains
/// temporarily for isolated historic-package reading only; it is not a valid
/// input to the v5 writer.
public protocol TimestampedLocalRecordingSampleSource: LocalRecordingSampleSource {
    func readTimestampedBatch(maximumFrameCount: Int) -> RecordingAudioBatch?
    var hasTimestampedOverflow: Bool { get }
}

public final class BufferedLocalRecordingSampleSource: TimestampedLocalRecordingSampleSource, @unchecked Sendable {
    private let lock = NSLock()
    private var buffer: [Float] = []
    private var readOffset = 0
    private let capacity: Int
    public let channelCount: Int
    public let sampleRate: Double
    private var totalAppendedFrameCount: Int64 = 0
    private var lastAppendAt: Date?
    private var timestampedBatches: [RecordingAudioBatch] = []
    private var timestampedQueuedFrameCount: Int64 = 0
    private var timestampedOverflowed = false

    public init(
        capacity: Int = 48_000 * 20,
        channelCount: Int = 2,
        sampleRate: Double = RecordingAudioTimeline.canonicalSampleRate
    ) {
        self.capacity = capacity
        self.channelCount = max(1, channelCount)
        self.sampleRate = sampleRate
    }

    public convenience init(capacity: Int) {
        self.init(capacity: capacity, channelCount: 2)
    }

    public func append(_ samples: [Float], at date: Date = Date()) {
        append(
            RecordingAudioBatch(
                samples: samples,
                format: RecordingAudioFormat(sampleRate: sampleRate, channelCount: channelCount),
                presentationTime: RecordingAudioPresentationTimestamp(
                    seconds: date.timeIntervalSinceReferenceDate,
                    clockDomain: .wallClock
                ),
                discontinuity: .none,
                routeGeneration: 0
            ),
            observedAt: date
        )
    }

    public func append(_ batch: RecordingAudioBatch, observedAt date: Date = Date()) {
        guard !batch.samples.isEmpty || batch.discontinuity != .none else { return }
        lock.lock()
        if !batch.samples.isEmpty {
            buffer.append(contentsOf: batch.samples)
            trimUnreadSamplesToCapacity()
            compactIfNeeded()
            totalAppendedFrameCount += Int64(batch.samples.count / max(1, batch.format.channelCount))
        }
        enqueueTimestampedBatch(batch)
        lastAppendAt = date
        lock.unlock()
    }

    public func stats() -> (frameCount: Int64, lastFrameAt: Date?) {
        lock.lock()
        defer { lock.unlock() }
        return (totalAppendedFrameCount, lastAppendAt)
    }

    public func reset() {
        lock.lock()
        buffer.removeAll(keepingCapacity: true)
        readOffset = 0
        totalAppendedFrameCount = 0
        lastAppendAt = nil
        timestampedBatches.removeAll(keepingCapacity: true)
        timestampedQueuedFrameCount = 0
        timestampedOverflowed = false
        lock.unlock()
    }

    public func readSamples(into destination: UnsafeMutablePointer<Float>, capacity: Int) -> Int {
        lock.lock()
        defer { lock.unlock() }
        let count = min(capacity, unreadCount)
        guard count > 0 else {
            compactIfNeeded()
            return 0
        }
        for index in 0..<count {
            destination[index] = buffer[readOffset + index]
        }
        readOffset += count
        compactIfNeeded()
        return count
    }

    public func readTimestampedBatch(maximumFrameCount: Int) -> RecordingAudioBatch? {
        lock.lock()
        defer { lock.unlock() }
        guard !timestampedBatches.isEmpty else { return nil }

        let batch = timestampedBatches.removeFirst()
        let sourceFrameCount = batch.samples.count / max(1, batch.format.channelCount)
        guard maximumFrameCount > 0,
              sourceFrameCount > maximumFrameCount,
              batch.discontinuity == .none
        else {
            timestampedQueuedFrameCount -= Int64(sourceFrameCount)
            return batch
        }

        let emittedFrameCount = maximumFrameCount
        let emittedSampleCount = emittedFrameCount * batch.format.channelCount
        let remainder = RecordingAudioBatch(
            samples: Array(batch.samples.dropFirst(emittedSampleCount)),
            format: batch.format,
            presentationTime: RecordingAudioPresentationTimestamp(
                seconds: batch.presentationTime.seconds + Double(emittedFrameCount) / batch.format.sampleRate,
                clockDomain: batch.presentationTime.clockDomain,
                observedHostTimeSeconds: batch.presentationTime.observedHostTimeSeconds
            ),
            discontinuity: .none,
            routeGeneration: batch.routeGeneration
        )
        timestampedBatches.insert(remainder, at: 0)
        timestampedQueuedFrameCount -= Int64(emittedFrameCount)
        return RecordingAudioBatch(
            samples: Array(batch.samples.prefix(emittedSampleCount)),
            format: batch.format,
            presentationTime: batch.presentationTime,
            discontinuity: batch.discontinuity,
            routeGeneration: batch.routeGeneration
        )
    }

    public var hasTimestampedOverflow: Bool {
        lock.lock()
        defer { lock.unlock() }
        return timestampedOverflowed
    }

    private var unreadCount: Int {
        buffer.count - readOffset
    }

    private func trimUnreadSamplesToCapacity() {
        let overflow = unreadCount - capacity
        if overflow > 0 {
            readOffset += overflow
        }
    }

    private func compactIfNeeded() {
        guard readOffset > 0 else { return }
        if readOffset == buffer.count {
            buffer.removeAll(keepingCapacity: true)
            readOffset = 0
            return
        }
        if readOffset >= 16_384 || readOffset > buffer.count / 2 {
            buffer.removeFirst(readOffset)
            readOffset = 0
        }
    }

    private func enqueueTimestampedBatch(_ batch: RecordingAudioBatch) {
        let frameCount = Int64(batch.samples.count / max(1, batch.format.channelCount))
        let frameCapacity = Int64(max(1, capacity / channelCount))
        guard batch.discontinuity != .dropped,
              timestampedQueuedFrameCount + frameCount <= frameCapacity
        else {
            timestampedBatches.removeAll(keepingCapacity: true)
            timestampedQueuedFrameCount = 0
            timestampedOverflowed = true
            timestampedBatches.append(RecordingAudioBatch(
                samples: [],
                format: batch.format,
                presentationTime: batch.presentationTime,
                discontinuity: .dropped,
                routeGeneration: batch.routeGeneration
            ))
            return
        }
        timestampedBatches.append(batch)
        timestampedQueuedFrameCount += frameCount
    }
}
