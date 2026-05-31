import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class RouteInvalidationTests: XCTestCase {
    func testRouteInvalidationMovesReadyToStaleWithRecoveryAction() {
        let event = RouteInvalidationEvent(
            source: .physicalDevice,
            previousReadinessStatus: .ready,
            newReadinessStatus: .stale,
            detectedAt: Date(timeIntervalSince1970: 1_779_887_120),
            recoveryAction: "rerun_readiness_check"
        )

        XCTAssertEqual(event.previousReadinessStatus, .ready)
        XCTAssertEqual(event.newReadinessStatus, .stale)
        XCTAssertEqual(event.recoveryAction, "rerun_readiness_check")
    }

    func testInvalidationSourcesMatchSpecContract() {
        XCTAssertEqual(RouteInvalidationSource.physicalDevice.rawValue, "physical_device")
        XCTAssertEqual(RouteInvalidationSource.outputRoute.rawValue, "output_route")
        XCTAssertEqual(RouteInvalidationSource.browserTarget.rawValue, "browser_target")
        XCTAssertEqual(RouteInvalidationSource.bluetoothProfile.rawValue, "bluetooth_profile")
        XCTAssertEqual(RouteInvalidationSource.appIO.rawValue, "app_io")
        XCTAssertEqual(RouteInvalidationSource.coreaudiod.rawValue, "coreaudiod")
    }
}
#endif
