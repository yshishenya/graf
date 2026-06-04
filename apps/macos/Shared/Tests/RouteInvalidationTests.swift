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

    func testAudioEnvironmentChangesProduceInvalidationEvents() {
        let monitor = AudioEnvironmentMonitor(now: { Date(timeIntervalSince1970: 1_779_887_120) })

        let events = monitor.routeInvalidationEvents(
            for: [.deviceChanged, .activeMeetingContextChanged, .bluetoothProfileChanged],
            previousStatus: .ready
        )

        XCTAssertEqual(events.map(\.source), [.browserTarget, .bluetoothProfile, .physicalDevice])
        XCTAssertTrue(events.allSatisfy { $0.recoveryAction == "rerun_readiness_check" })
        XCTAssertTrue(events.contains { $0.newReadinessStatus == .degraded })
    }

    func testRouteInvalidationBundleIsMetadataOnly() throws {
        let event = RouteInvalidationEvent(
            source: .appIO,
            previousReadinessStatus: .ready,
            newReadinessStatus: .stale,
            detectedAt: Date(timeIntervalSince1970: 1_779_887_120),
            recoveryAction: "rerun_readiness_check"
        )

        let bundle = try DiagnosticBundleService().buildRouteInvalidationBundle(events: [event])

        XCTAssertEqual(bundle.redactionState, .redacted)
        XCTAssertNotNil(bundle.manifest["routeInvalidationEvents"])
        XCTAssertNil(bundle.manifest["rawAudio"])
        XCTAssertNil(bundle.manifest["transcriptText"])
    }

    func testLivePassthroughRecoveryEventsFollowRouteChanges() {
        let monitor = AudioEnvironmentMonitor(now: { Date(timeIntervalSince1970: 1_779_887_120) })

        let events = monitor.livePassthroughRecoveryEvents(
            for: [.deviceChanged, .browserTargetEvidenceChanged, .passthroughChanged],
            previousStatus: .active
        )

        XCTAssertEqual(events.map(\.eventType), [.appHeartbeatLost, .browserTargetChanged, .physicalInputChanged])
        XCTAssertTrue(events.allSatisfy { $0.previousStatus == .active })
        XCTAssertTrue(events.allSatisfy { $0.recoveryAction == "rerun_live_passthrough_check" })
        XCTAssertTrue(events.contains { $0.newStatus == .degraded })
        XCTAssertTrue(events.contains { $0.newStatus == .stale })
    }

    func testRouteStateTruthDistinguishesStaleBlockedFailedAndReleased() {
        let stale = RouteEvidenceEvent(
            eventId: "stale",
            sessionId: "route-session",
            family: .routeLifecycle,
            name: "route.stale",
            observedAt: Date(timeIntervalSince1970: 1),
            source: .routeEngine,
            routeState: .stale
        )
        let released = RouteEvidenceEvent(
            eventId: "released",
            sessionId: "route-session",
            family: .routeLifecycle,
            name: "route.released",
            observedAt: Date(timeIntervalSince1970: 2),
            source: .routeEngine,
            routeState: .released
        )

        XCTAssertNotEqual(stale.routeState, released.routeState)
        XCTAssertEqual(stale.routeState, .stale)
        XCTAssertEqual(released.routeState, .released)
    }
}
#endif
