import Foundation
import TwoBrainRecShared

public final class PrivacySuppressingSampleSource: TimestampedLocalRecordingSampleSource, @unchecked Sendable {
    private let base: TimestampedLocalRecordingSampleSource
    private let lock = NSLock()
    private var state: ProductPrivacyControlState
    private var totalSuppressedSampleCount: Int64
    private var lastReadSuppressed: Bool

    public init(
        base: TimestampedLocalRecordingSampleSource,
        state: ProductPrivacyControlState = .capturing
    ) {
        self.base = base
        self.state = state
        self.totalSuppressedSampleCount = 0
        self.lastReadSuppressed = false
    }

    public var suppressedSampleCount: Int64 {
        lock.lock()
        defer { lock.unlock() }
        return totalSuppressedSampleCount
    }

    public var lastReadWasSuppressed: Bool {
        lock.lock()
        defer { lock.unlock() }
        return lastReadSuppressed
    }

    public func update(state: ProductPrivacyControlState) {
        lock.lock()
        self.state = state
        lock.unlock()
    }

    public func readTimestampedBatch(maximumFrameCount: Int) -> RecordingAudioBatch? {
        guard let batch = base.readTimestampedBatch(maximumFrameCount: maximumFrameCount) else {
            return nil
        }
        guard !batch.samples.isEmpty else { return batch }

        lock.lock()
        let shouldSuppress = state.suppressesLocalMicrophone
        if shouldSuppress {
            totalSuppressedSampleCount += Int64(batch.samples.count)
        }
        lastReadSuppressed = shouldSuppress
        lock.unlock()

        guard shouldSuppress else { return batch }
        return RecordingAudioBatch(
            samples: Array(repeating: 0, count: batch.samples.count),
            format: batch.format,
            presentationTime: batch.presentationTime,
            discontinuity: batch.discontinuity,
            routeGeneration: batch.routeGeneration
        )
    }

    public var hasTimestampedOverflow: Bool {
        base.hasTimestampedOverflow
    }
}
