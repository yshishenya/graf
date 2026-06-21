import Foundation
import TwoBrainRecShared

public final class PrivacySuppressingSampleSource: LocalRecordingSampleSource, @unchecked Sendable {
    private let base: LocalRecordingSampleSource
    private let lock = NSLock()
    private var state: ProductPrivacyControlState
    private var totalSuppressedSampleCount: Int64
    private var lastReadSuppressed: Bool

    public init(
        base: LocalRecordingSampleSource,
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

    public func readSamples(into destination: UnsafeMutablePointer<Float>, capacity: Int) -> Int {
        let read = base.readSamples(into: destination, capacity: capacity)
        guard read > 0 else {
            lock.lock()
            lastReadSuppressed = false
            lock.unlock()
            return read
        }

        lock.lock()
        let shouldSuppress = state.suppressesLocalMicrophone
        if shouldSuppress {
            totalSuppressedSampleCount += Int64(read)
        }
        lastReadSuppressed = shouldSuppress
        lock.unlock()

        guard shouldSuppress else { return read }
        for index in 0..<read {
            destination[index] = 0
        }
        return read
    }
}
