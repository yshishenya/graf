import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SharedAudioMemoryCompatibilityTests: XCTestCase {
    func testSharedMemoryLayoutSizeStaysOnAcceptedHeartbeatLayout() {
        let expected = 3 * kSharedRingCapacity * MemoryLayout<Float>.stride + 6 * MemoryLayout<UInt64>.stride + 16

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
}
#endif
