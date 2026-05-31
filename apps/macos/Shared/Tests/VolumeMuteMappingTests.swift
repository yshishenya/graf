import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

final class VolumeMuteMappingTests: XCTestCase {
    func testVolumeMuteMappingKeepsVisibleStateButNeverStartsCapture() {
        let mapping = VolumeMuteMapper().mapPhysicalToVirtual(
            VolumeMuteState(volume: 0.42, muted: true)
        )

        XCTAssertEqual(mapping.virtual.volume, 0.42)
        XCTAssertTrue(mapping.virtual.muted)
        XCTAssertFalse(mapping.captureSignalAllowed)
    }

    func testVolumeIsClampedToUserVisibleRange() {
        let mapping = VolumeMuteMapper().mapPhysicalToVirtual(
            VolumeMuteState(volume: 2, muted: false)
        )

        XCTAssertEqual(mapping.virtual.volume, 1)
    }
}
#endif
