import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SharedAudioMemoryCompatibilityTests: XCTestCase {
    func testSharedMemoryLayoutSizeStaysOnAcceptedHeartbeatLayout() {
        let expected = 3 * kSharedRingCapacity * MemoryLayout<Float>.stride + 6 * MemoryLayout<UInt64>.stride + 16

        XCTAssertEqual(SharedAudioMemory.expectedSharedMemorySize, expected)
    }
}
#endif
