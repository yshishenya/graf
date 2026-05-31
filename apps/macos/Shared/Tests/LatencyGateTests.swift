import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LatencyGateTests: XCTestCase {
    func testBuiltInRouteAtThirtyMsIsHealthy() {
        let evidence = RouteLatencyEvidence(
            routeClass: .builtIn,
            measuredLatencyMs: 30,
            measuredAt: Date(timeIntervalSince1970: 10)
        )

        XCTAssertTrue(evidence.isBuiltInOrWiredReleaseReady)
        XCTAssertEqual(LatencyMonitor().passthroughStatus(for: evidence), .healthy)
    }

    func testWiredRouteAboveThirtyMsIsDegraded() {
        let evidence = RouteLatencyEvidence(
            routeClass: .wired,
            measuredLatencyMs: 30.1,
            measuredAt: Date(timeIntervalSince1970: 10)
        )

        XCTAssertFalse(evidence.isBuiltInOrWiredReleaseReady)
        XCTAssertEqual(LatencyMonitor().passthroughStatus(for: evidence), .latencyExceeded)
    }

    func testBluetoothRouteIsManagedNotReleaseParity() {
        let evidence = RouteLatencyEvidence(
            routeClass: .bluetooth,
            measuredLatencyMs: 25,
            measuredAt: Date(timeIntervalSince1970: 10)
        )

        XCTAssertFalse(evidence.isBuiltInOrWiredReleaseReady)
        XCTAssertEqual(LatencyMonitor().passthroughStatus(for: evidence), .degraded)
    }

    func testLeakageMeasurementPassesAtNegativeFortyFiveDb() {
        let measurement = LeakageMeasurement(
            speakerReferenceDb: -10,
            virtualMicLeakageDb: -55,
            relativeLeakageDb: -45,
            intelligibilityStatus: .notIntelligible,
            status: .passed,
            measuredAt: Date(timeIntervalSince1970: 10)
        )

        XCTAssertEqual(measurement.status, .passed)
        XCTAssertEqual(measurement.relativeLeakageDb, -45)
        XCTAssertEqual(measurement.intelligibilityStatus, .notIntelligible)
    }

    func testLatencyMeasurementDegradesAboveThreshold() {
        let measurement = LatencyMeasurement(
            routeClass: .wired,
            addedLatencyMs: 30.1,
            status: .degraded,
            measuredAt: Date(timeIntervalSince1970: 10)
        )

        XCTAssertEqual(measurement.status, .degraded)
        XCTAssertEqual(measurement.thresholdMs, 30)
    }

    func testLatencyMonitorMapsMeasurementsToReleaseGateStatus() {
        let monitor = LatencyMonitor()
        let passed = LatencyMeasurement(
            routeClass: .builtIn,
            addedLatencyMs: 30,
            status: .passed,
            measuredAt: Date(timeIntervalSince1970: 10)
        )
        let degraded = LatencyMeasurement(
            routeClass: .wired,
            addedLatencyMs: 30.1,
            status: .degraded,
            measuredAt: Date(timeIntervalSince1970: 10)
        )
        let blocked = LatencyMeasurement(
            routeClass: .bluetooth,
            addedLatencyMs: 25,
            status: .blocked,
            measuredAt: Date(timeIntervalSince1970: 10)
        )

        XCTAssertEqual(monitor.measurementStatus(for: passed), .passed)
        XCTAssertEqual(monitor.measurementStatus(for: degraded), .degraded)
        XCTAssertEqual(monitor.measurementStatus(for: blocked), .blocked)
    }

    func testLeakagePolicyDegradesAboveThresholdOrWhenIntelligible() {
        let guardrail = SelfRoutingGuard()
        let passed = LeakageMeasurement(
            speakerReferenceDb: -10,
            virtualMicLeakageDb: -55,
            relativeLeakageDb: -45,
            intelligibilityStatus: .notIntelligible,
            status: .passed,
            measuredAt: Date(timeIntervalSince1970: 10)
        )
        let tooLoud = LeakageMeasurement(
            speakerReferenceDb: -10,
            virtualMicLeakageDb: -54.9,
            relativeLeakageDb: -44.9,
            intelligibilityStatus: .notIntelligible,
            status: .degraded,
            measuredAt: Date(timeIntervalSince1970: 10)
        )
        let intelligible = LeakageMeasurement(
            speakerReferenceDb: -10,
            virtualMicLeakageDb: -60,
            relativeLeakageDb: -50,
            intelligibilityStatus: .intelligible,
            status: .degraded,
            measuredAt: Date(timeIntervalSince1970: 10)
        )

        XCTAssertEqual(guardrail.leakageStatus(for: passed), .passed)
        XCTAssertEqual(guardrail.leakageStatus(for: tooLoud), .degraded)
        XCTAssertEqual(guardrail.leakageStatus(for: intelligible), .degraded)
    }
}
#endif
