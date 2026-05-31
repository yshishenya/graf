import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class GuidedDeviceManagementTests: XCTestCase {
    func testGuidedManagementRequiresExplicitUserApproval() {
        let decision = GuidedDeviceManagementService().prepareRoute(
            physicalInput: physicalDevice(id: "built-in-input", direction: .input),
            physicalOutput: physicalDevice(id: "built-in-output", direction: .output),
            previousInputId: nil,
            previousOutputId: nil,
            userApproved: false
        )

        XCTAssertEqual(decision, .requiresExplicitApproval)
    }

    func testGuidedManagementRejectsSelfRouting() {
        let decision = GuidedDeviceManagementService().prepareRoute(
            physicalInput: physicalDevice(id: SelfRoutingGuard.microphoneUID, name: "2brain Rec Microphone", direction: .input),
            physicalOutput: physicalDevice(id: "built-in-output", direction: .output),
            previousInputId: nil,
            previousOutputId: nil,
            userApproved: true
        )

        guard case .rejected = decision else {
            XCTFail("self-routed physical input must be rejected")
            return
        }
    }

    func testGuidedManagementProducesReversibleRouteChange() {
        let decision = GuidedDeviceManagementService().prepareRoute(
            physicalInput: physicalDevice(id: "built-in-input", direction: .input),
            physicalOutput: physicalDevice(id: "built-in-output", direction: .output),
            previousInputId: "old-input",
            previousOutputId: "old-output",
            userApproved: true
        )

        guard case let .applied(change) = decision else {
            XCTFail("approved physical devices should produce a route change")
            return
        }
        XCTAssertTrue(change.reversible)
        XCTAssertEqual(change.previousInputId, "old-input")
        XCTAssertEqual(change.virtualInputId, SelfRoutingGuard.microphoneUID)
    }

    private func physicalDevice(
        id: String,
        name: String? = nil,
        direction: AudioDirection
    ) -> PhysicalAudioDevice {
        PhysicalAudioDevice(
            id: id,
            displayName: name ?? id,
            direction: direction,
            deviceClass: .builtIn,
            availabilityState: .available
        )
    }
}
#endif
