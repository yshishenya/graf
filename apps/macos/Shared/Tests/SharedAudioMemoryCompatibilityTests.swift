import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SharedAudioMemoryCompatibilityTests: XCTestCase {
    func testSharedMemoryLayoutSizeStaysOnAcceptedHeartbeatLayout() {
        let expected = 3 * kSharedRingCapacity * MemoryLayout<Float>.stride + 6 * MemoryLayout<UInt64>.stride + 24

        XCTAssertEqual(SharedAudioMemory.expectedSharedMemorySize, expected)
    }

    func testRingPolicyAllowsWriteWhenCapacityIsAvailable() {
        XCTAssertTrue(SharedRingPolicy.canWrite(writeIndex: 8, readIndex: 4, sampleCount: 4, capacity: 8))
    }

    func testRingPolicyRejectsOverflowWithoutConsumerIndexMutation() {
        XCTAssertFalse(SharedRingPolicy.canWrite(writeIndex: 8, readIndex: 4, sampleCount: 5, capacity: 8))
    }

    func testRingPolicyRejectsOversizedWrites() {
        XCTAssertFalse(SharedRingPolicy.canWrite(writeIndex: 0, readIndex: 0, sampleCount: kSharedRingCapacity + 1))
    }

    func testRingPolicyAcceptsZeroLengthWriteAsNoop() {
        XCTAssertTrue(SharedRingPolicy.canWrite(writeIndex: 8, readIndex: 8, sampleCount: 0, capacity: 8))
    }

    func testRingWritableSampleCountTracksUnreadDistance() {
        XCTAssertEqual(SharedRingPolicy.writableSampleCount(writeIndex: 10, readIndex: 6, capacity: 8), 4)
    }

    func testAvailableSampleCountClampsImpossibleSharedMemoryDistance() {
        XCTAssertEqual(
            SharedAudioMemory.clampedAvailable(writeIndex: UInt64.max, readIndex: 0, capacity: 8),
            8
        )
    }

    func testCopyLatestSamplesReadsTailWithoutRuntimeSharedMemory() {
        let samples: [Float] = [0.1, 0.2, 0.3, 0.4]
        let scratch = UnsafeMutablePointer<Float>.allocate(capacity: 2)
        defer { scratch.deallocate() }

        let read = samples.withUnsafeBufferPointer { buffer in
            SharedAudioMemory.copyLatestSamples(
                from: buffer.baseAddress!,
                writeIndex: UInt64(samples.count),
                dst: scratch,
                count: 2,
                capacity: samples.count
            )
        }

        XCTAssertEqual(read, 2)
        XCTAssertEqual(Array(UnsafeBufferPointer(start: scratch, count: 2)), [0.3, 0.4])
    }
}
#endif
