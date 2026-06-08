import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioNoVirtualDeviceCopyTests: XCTestCase {
    func testDriverSetupBoundaryCopySaysVirtualDevicesAreNotRequired() {
        let copy = DriverSetupView.mvpBoundaryCopy

        XCTAssertTrue(copy.contains("does not require"))
        XCTAssertTrue(copy.localizedCaseInsensitiveContains("virtual devices"))
        XCTAssertFalse(copy.localizedCaseInsensitiveContains("before recording"))
        XCTAssertFalse(copy.localizedCaseInsensitiveContains("run check"))
    }

    func testMissingVirtualDeviceCopyDoesNotAskForRepairBeforeRecording() {
        let microphone = DriverSetupView.virtualDeviceText(.missing)
        let speaker = DriverSetupView.virtualDeviceText(.unavailable)
        let driver = DriverSetupView.driverText(.needsRepair)

        XCTAssertTrue(microphone.contains("Not required"))
        XCTAssertTrue(speaker.contains("not blocking recording"))
        XCTAssertFalse(driver.localizedCaseInsensitiveContains("needed"))
        XCTAssertFalse(driver.localizedCaseInsensitiveContains("before recording"))
    }
}
#endif
