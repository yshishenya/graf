import AVFoundation
import Foundation
import TwoBrainRecShared

public enum LocalRecordingWriterError: Error {
    case alreadyRecording
    case notRecording
    case directoryUnavailable
    case echoProcessorUnavailable
}

public enum LocalRecordingPrivacyError: Error {
    case resumeBoundaryUnavailable
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

public struct RecordingSampleSourceDiagnostics: Sendable {
    /// Exact unread FIFO frame count, captured under the source read lock.
    public let queuedFrameCount: Int64
    public let capturedFrontier: RecordingAudioPresentationTimestamp?
    public let lastBatchFrameCount: Int
    public let lastBatchFormat: RecordingAudioFormat?
    public let lastCapturedUptime: TimeInterval?

    public init(queuedFrameCount: Int64, capturedFrontier: RecordingAudioPresentationTimestamp?,
                lastBatchFrameCount: Int, lastBatchFormat: RecordingAudioFormat?, lastCapturedUptime: TimeInterval?) {
        self.queuedFrameCount = queuedFrameCount
        self.capturedFrontier = capturedFrontier
        self.lastBatchFrameCount = lastBatchFrameCount
        self.lastBatchFormat = lastBatchFormat
        self.lastCapturedUptime = lastCapturedUptime
    }
}

public protocol TimestampedLocalRecordingSampleSource: Sendable {
    func readTimestampedBatch(maximumFrameCount: Int) -> RecordingAudioBatch?
    var hasTimestampedOverflow: Bool { get }
    var timestampedDiagnostics: RecordingSampleSourceDiagnostics? { get }
    /// Invoke body once, synchronously, with the exact unread FIFO frame count
    /// while excluding producer appends and reads. Return body's result; an
    /// unsupported source returns false without invoking body. The callback
    /// must only update bounded control state, without reentering this source.
    func withQueuedFrameCountSnapshot(_ body: (Int64) -> Bool) -> Bool
}

public extension TimestampedLocalRecordingSampleSource {
    var timestampedDiagnostics: RecordingSampleSourceDiagnostics? { nil }
    func withQueuedFrameCountSnapshot(_ body: (Int64) -> Bool) -> Bool { false }
}

public final class BufferedLocalRecordingSampleSource: TimestampedLocalRecordingSampleSource, @unchecked Sendable {
    private let lock = NSLock()
    private let capacity: Int
    public let channelCount: Int
    public let sampleRate: Double
    private var totalAppendedFrameCount: Int64 = 0
    private var lastAppendAt: Date?
    private var timestampedBatches: [RecordingAudioBatch] = []
    private var timestampedQueuedFrameCount: Int64 = 0
    private var timestampedOverflowed = false
    private var capturedFrontier: RecordingAudioPresentationTimestamp?
    private var lastBatchFrameCount = 0
    private var lastBatchFormat: RecordingAudioFormat?
    private var lastCapturedUptime: TimeInterval?

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
            totalAppendedFrameCount += Int64(batch.samples.count / max(1, batch.format.channelCount))
        }
        enqueueTimestampedBatch(batch)
        lastBatchFrameCount = batch.samples.count / max(1, batch.format.channelCount)
        lastBatchFormat = batch.format
        if batch.format.sampleRate.isFinite, batch.format.sampleRate > 0, batch.presentationTime.seconds.isFinite {
            capturedFrontier = RecordingAudioPresentationTimestamp(
                seconds: batch.presentationTime.seconds + Double(lastBatchFrameCount) / batch.format.sampleRate,
                clockDomain: batch.presentationTime.clockDomain)
        }
        lastAppendAt = date
        lastCapturedUptime = ProcessInfo.processInfo.systemUptime
        lock.unlock()
    }

    public func stats() -> (frameCount: Int64, lastFrameAt: Date?) {
        lock.lock()
        defer { lock.unlock() }
        return (totalAppendedFrameCount, lastAppendAt)
    }

    public func reset() {
        lock.lock()
        totalAppendedFrameCount = 0
        lastAppendAt = nil
        timestampedBatches.removeAll(keepingCapacity: true)
        timestampedQueuedFrameCount = 0
        timestampedOverflowed = false
        capturedFrontier = nil
        lastBatchFrameCount = 0
        lastBatchFormat = nil
        lastCapturedUptime = nil
        lock.unlock()
    }

    public func withQueuedFrameCountSnapshot(_ body: (Int64) -> Bool) -> Bool {
        lock.withLock { body(timestampedQueuedFrameCount) }
    }

    public var timestampedDiagnostics: RecordingSampleSourceDiagnostics? {
        lock.withLock {
            RecordingSampleSourceDiagnostics(queuedFrameCount: timestampedQueuedFrameCount,
                capturedFrontier: capturedFrontier, lastBatchFrameCount: lastBatchFrameCount,
                lastBatchFormat: lastBatchFormat, lastCapturedUptime: lastCapturedUptime)
        }
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
