import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LowResourceRecoveryTests: XCTestCase {
    func testHeartbeatLossKeepsDevicesVisibleAndMarksRouteStale() {
        let policy = AppIOHealthPolicy(heartbeatTimeoutMs: 3000)
        let health = policy.evaluate(
            lastHeartbeatAt: Date(timeIntervalSince1970: 1),
            now: Date(timeIntervalSince1970: 5)
        )
        let event = LowResourceRecoveryPolicy().event(
            for: .staleHeartbeat,
            previousState: .active,
            detectedAt: Date(timeIntervalSince1970: 5)
        )

        XCTAssertEqual(health.state, .heartbeatLost)
        XCTAssertEqual(health.publicDeviceAvailability, .available)
        XCTAssertEqual(event.newState, .stale)
        XCTAssertEqual(event.recoveryAction, "restart_desktop_audio_engine")
    }

    func testAudioEnvironmentMapsLowResourceRecoveryTriggers() {
        let monitor = AudioEnvironmentMonitor(now: { Date(timeIntervalSince1970: 10) })

        let events = monitor.lowResourceRecoveryEvents(
            for: [.passthroughChanged, .coreaudiodRestarted, .sleepWake, .deviceChanged, .browserTargetEvidenceChanged],
            previousState: .active
        )

        XCTAssertEqual(
            events.map(\.trigger),
            [.browserDeviceChanged, .coreaudiodRestart, .physicalDeviceChanged, .sleepWake, .staleHeartbeat]
        )
        XCTAssertTrue(events.allSatisfy { $0.newState == .stale })
        XCTAssertTrue(events.allSatisfy { $0.publicDeviceAvailability == .available })
    }

    func testWorkingDeviceStoreReportsPhysicalDeviceInvalidation() {
        let store = WorkingDeviceStore(
            snapshot: WorkingDeviceSnapshot(
                physicalInput: PhysicalAudioDevice(
                    id: "input-a",
                    displayName: "Built-in Mic",
                    direction: .input,
                    deviceClass: .builtIn,
                    availabilityState: .available
                ),
                physicalOutput: nil,
                updatedAt: Date(timeIntervalSince1970: 1)
            )
        )

        let event = store.lowResourceInvalidation(
            newPhysicalInput: PhysicalAudioDevice(
                id: "input-b",
                displayName: "USB Mic",
                direction: .input,
                deviceClass: .usb,
                availabilityState: .available
            ),
            newPhysicalOutput: nil,
            detectedAt: Date(timeIntervalSince1970: 2)
        )

        XCTAssertEqual(event?.trigger, .physicalDeviceChanged)
        XCTAssertEqual(event?.newState, .stale)
    }

    func testRecoveryDiagnosticsAreMetadataOnly() throws {
        let event = LowResourceRecoveryPolicy().event(
            for: .coreaudiodRestart,
            previousState: .active,
            detectedAt: Date(timeIntervalSince1970: 3)
        )

        let bundle = try DiagnosticBundleService().buildLowResourceRecoveryBundle(events: [event])

        XCTAssertEqual(bundle.redactionState, .redacted)
        XCTAssertNotNil(bundle.manifest["lowResourceRecoveryEvents"])
        XCTAssertNil(bundle.manifest["rawAudio"])
        XCTAssertNil(bundle.manifest["transcriptText"])
        XCTAssertNil(bundle.manifest["meetingContent"])
    }
}
#endif
