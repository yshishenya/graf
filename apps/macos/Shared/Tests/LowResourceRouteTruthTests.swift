import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LowResourceRouteTruthTests: XCTestCase {
    func testReadinessUsesSeparateEvidencePlanes() {
        let active = LowResourceTestFixtures.readySnapshot(clientOpen: true)

        XCTAssertEqual(LowResourceRouteTruthEvaluator.readinessState(for: active), .active)
    }

    func testVisiblePublicationDoesNotImplyReadyWithoutBridgeHealth() {
        var snapshot = LowResourceTestFixtures.readySnapshot(clientOpen: false)
        snapshot.appBridgeHealth = AppBridgeHealthEvidence(
            heartbeatState: .heartbeatLost,
            driverFailClosed: true
        )

        XCTAssertEqual(LowResourceRouteTruthEvaluator.readinessState(for: snapshot), .stale)
    }

    func testClientActivityDoesNotOverrideHiddenPublication() {
        var snapshot = LowResourceTestFixtures.readySnapshot(clientOpen: true)
        snapshot.publication.hidden = true
        snapshot.publication.microphoneVisible = false

        XCTAssertEqual(LowResourceRouteTruthEvaluator.readinessState(for: snapshot), .blocked)
    }

    func testInvalidWorkingDeviceBlocksOtherwiseHealthyRoute() {
        var snapshot = LowResourceTestFixtures.readySnapshot(clientOpen: true)
        snapshot.physicalDevices = PhysicalWorkingDeviceSelection(
            inputDeviceId: SelfRoutingGuard.microphoneUID,
            inputDeviceName: "2brain Rec Microphone",
            outputDeviceId: "built-in-output",
            outputDeviceName: "MacBook Speakers",
            inputKind: .twoBrainVirtual,
            outputKind: .physical,
            selectionResult: .rejected,
            rejectionReason: "input_must_be_physical_working_device"
        )

        XCTAssertEqual(LowResourceRouteTruthEvaluator.readinessState(for: snapshot), .blocked)
    }

    func testRecordingBoundaryBlocks006Readiness() {
        var snapshot = LowResourceTestFixtures.readySnapshot(clientOpen: true)
        snapshot.recordingTrigger = RecordingTriggerBoundary(
            recordingTriggerState: .activeFuture,
            driverRecordingOwner: true,
            appRecordingOwner: true,
            recordingArtifactsCreated: true,
            externalEgressStarted: false
        )

        XCTAssertEqual(LowResourceRouteTruthEvaluator.readinessState(for: snapshot), .blocked)
        XCTAssertFalse(LowResourceRouteTruthEvaluator.hasMetadataOnlyRecordingBoundary(snapshot))
    }
}
#endif
