import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class AppIOHealthTests: XCTestCase {
    func testMissingHeartbeatFailsClosedWhileKeepingPublicDevicesVisible() {
        let health = AppIOHealthPolicy().evaluate(lastHeartbeatAt: nil, now: Date(timeIntervalSince1970: 10))

        XCTAssertEqual(health.state, .waitingForApp)
        XCTAssertEqual(health.publicDeviceAvailability, .available)
        XCTAssertEqual(health.recoveryAction, "restart_desktop_audio_engine")
    }

    func testExpiredHeartbeatFailsClosed() {
        let policy = AppIOHealthPolicy(heartbeatTimeoutMs: 3000)
        let health = policy.evaluate(
            lastHeartbeatAt: Date(timeIntervalSince1970: 1),
            now: Date(timeIntervalSince1970: 5)
        )

        XCTAssertEqual(health.state, .heartbeatLost)
        XCTAssertEqual(health.publicDeviceAvailability, .available)
        XCTAssertEqual(health.missedHeartbeatCount, 1)
    }

    func testFreshHeartbeatKeepsPublicDevicesAvailable() {
        let policy = AppIOHealthPolicy(heartbeatTimeoutMs: 3000)
        let health = policy.evaluate(
            lastHeartbeatAt: Date(timeIntervalSince1970: 4),
            now: Date(timeIntervalSince1970: 5)
        )

        XCTAssertEqual(health.state, .connected)
        XCTAssertEqual(health.publicDeviceAvailability, .available)
        XCTAssertNil(health.recoveryAction)
    }

    func testActivePassthroughUsesSameFailClosedHeartbeatPolicy() {
        let policy = AppIOHealthPolicy(heartbeatTimeoutMs: 5000)
        let health = policy.evaluate(
            lastHeartbeatAt: Date(timeIntervalSince1970: 10),
            now: Date(timeIntervalSince1970: 16)
        )

        XCTAssertEqual(health.state, .heartbeatLost)
        XCTAssertEqual(health.publicDeviceAvailability, .available)
        XCTAssertEqual(health.recoveryAction, "restart_desktop_audio_engine")
    }

    func testLegacyPolicyCanStillHidePublicDevicesWhenExplicitlyConfigured() {
        let health = AppIOHealthPolicy(keepsPublicDevicesVisibleOnFailure: false)
            .evaluate(lastHeartbeatAt: nil, now: Date(timeIntervalSince1970: 10))

        XCTAssertEqual(health.publicDeviceAvailability, .hidden)
    }
}
#endif
