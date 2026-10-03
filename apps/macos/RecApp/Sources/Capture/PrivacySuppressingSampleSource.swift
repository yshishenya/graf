import Foundation
import TwoBrainRecShared

public final class PrivacySuppressingSampleSource: TimestampedLocalRecordingSampleSource, @unchecked Sendable {
    private let base: TimestampedLocalRecordingSampleSource
    private let lock = NSLock()
    private var state: ProductPrivacyControlState
    private var totalSuppressedSampleCount: Int64
    private var lastReadSuppressedSampleCount: Int
    private var queuedFramesToSuppress: Int64

    public init(
        base: TimestampedLocalRecordingSampleSource,
        state: ProductPrivacyControlState = .capturing
    ) {
        self.base = base
        self.state = state
        self.totalSuppressedSampleCount = 0
        self.lastReadSuppressedSampleCount = 0
        self.queuedFramesToSuppress = 0
    }

    public var suppressedSampleCount: Int64 {
        lock.lock()
        defer { lock.unlock() }
        return totalSuppressedSampleCount
    }

    /// True when at least part of the last returned batch was silenced.
    public var lastReadWasSuppressed: Bool {
        lock.lock()
        defer { lock.unlock() }
        return lastReadSuppressedSampleCount > 0
    }

    /// A FIFO snapshot is the finite boundary between frames accepted during
    /// mute and frames accepted after resume. Snapshot and state change share
    /// the producer's FIFO lock; diagnostics alone cannot authorize resume.
    @discardableResult
    public func update(state: ProductPrivacyControlState) -> Bool {
        lock.withLock {
            if self.state.suppressesLocalMicrophone && !state.suppressesLocalMicrophone {
                return base.withQueuedFrameCountSnapshot { queuedFrameCount in
                    guard queuedFrameCount >= 0 else { return false }
                    // Replace, rather than add: a second pause also covers any
                    // remaining frames from the first pause already in FIFO.
                    queuedFramesToSuppress = queuedFrameCount
                    self.state = state
                    return true
                }
            }
            self.state = state
            return true
        }
    }

    public func readTimestampedBatch(maximumFrameCount: Int) -> RecordingAudioBatch? {
        // Hold this lock across the base read as well as state transitions so
        // the snapshot cannot race a read that removes old muted frames.
        lock.withLock {
            lastReadSuppressedSampleCount = 0
            guard let batch = base.readTimestampedBatch(maximumFrameCount: maximumFrameCount) else { return nil }
            guard !batch.samples.isEmpty else { return batch }
            let channelCount = max(1, batch.format.channelCount)
            let mutedFrameCount = min(queuedFramesToSuppress, Int64(batch.samples.count / channelCount))
            queuedFramesToSuppress -= mutedFrameCount
            let mutedSampleCount = state.suppressesLocalMicrophone
                ? batch.samples.count : Int(mutedFrameCount) * channelCount
            lastReadSuppressedSampleCount = mutedSampleCount
            totalSuppressedSampleCount += Int64(mutedSampleCount)
            guard mutedSampleCount > 0 else { return batch }
            var samples = batch.samples
            samples.replaceSubrange(0..<mutedSampleCount, with: repeatElement(Float.zero, count: mutedSampleCount))
            return RecordingAudioBatch(samples: samples,
                format: batch.format, presentationTime: batch.presentationTime,
                discontinuity: batch.discontinuity, routeGeneration: batch.routeGeneration)
        }
    }

    /// A live drain may retain one microphone batch across a user control.
    /// Silence it after the durable pause checkpoint, without changing its PTS
    /// or double-counting samples already suppressed at read time.
    func suppressPrefetchedBatch(_ batch: RecordingAudioBatch) -> RecordingAudioBatch {
        lock.withLock {
            guard state.suppressesLocalMicrophone, !batch.samples.isEmpty else { return batch }
            let remainingSampleCount = batch.samples.count - lastReadSuppressedSampleCount
            guard remainingSampleCount > 0 else { return batch }
            totalSuppressedSampleCount += Int64(remainingSampleCount)
            lastReadSuppressedSampleCount = batch.samples.count
            return RecordingAudioBatch(samples: Array(repeating: 0, count: batch.samples.count),
                format: batch.format, presentationTime: batch.presentationTime,
                discontinuity: batch.discontinuity, routeGeneration: batch.routeGeneration)
        }
    }

    public var timestampedDiagnostics: RecordingSampleSourceDiagnostics? {
        base.timestampedDiagnostics
    }

    public var hasTimestampedOverflow: Bool {
        base.hasTimestampedOverflow
    }
}
