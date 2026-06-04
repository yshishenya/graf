import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LiveRouteDefaultRouteTests: XCTestCase {
    func testAcceptedMacOSDefaultRoutesAreBuiltInWiredAndUSBOnly() {
        XCTAssertTrue(LiveRouteStabilityFixtures.defaultRoute(input: .builtIn, output: .wired).isAcceptedForAutomaticRouting)
        XCTAssertTrue(LiveRouteStabilityFixtures.defaultRoute(input: .usb, output: .builtIn).isAcceptedForAutomaticRouting)
        XCTAssertFalse(LiveRouteStabilityFixtures.defaultRoute(input: .bluetooth, output: .wired).isAcceptedForAutomaticRouting)
        XCTAssertFalse(LiveRouteStabilityFixtures.defaultRoute(input: .airpodsClass, output: .builtIn).isAcceptedForAutomaticRouting)
    }

    func testRouteVerificationServiceBuildsDefaultRouteSnapshot() {
        let input = PhysicalAudioDevice(
            id: "built-in-input",
            displayName: "MacBook Pro Microphone",
            direction: .input,
            deviceClass: .builtIn,
            availabilityState: .available
        )
        let output = PhysicalAudioDevice(
            id: "usb-output",
            displayName: "USB Speaker",
            direction: .output,
            deviceClass: .usb,
            availabilityState: .available
        )

        let snapshot = RouteVerificationService.defaultRouteSnapshot(
            input: input,
            output: output,
            observedAt: LiveRouteStabilityFixtures.now
        )

        XCTAssertTrue(snapshot.isAcceptedForAutomaticRouting)
        XCTAssertEqual(snapshot.inputDeviceClass, .builtIn)
        XCTAssertEqual(snapshot.outputDeviceClass, .usb)
    }
}
#endif
