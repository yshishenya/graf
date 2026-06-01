import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LowResourcePhysicalDevicePolicyTests: XCTestCase {
    func testRejectsTwoBrainVirtualDevicesAsWorkingDevices() {
        let selection = SelfRoutingGuard().physicalWorkingDeviceSelection(
            input: device(id: SelfRoutingGuard.microphoneUID, name: "2brain Rec Microphone", direction: .input),
            output: device(id: SelfRoutingGuard.speakerUID, name: "2brain Rec Speaker", direction: .output)
        )

        XCTAssertEqual(selection.selectionResult, .rejected)
        XCTAssertEqual(selection.inputKind, .twoBrainVirtual)
        XCTAssertEqual(selection.outputKind, .twoBrainVirtual)
    }

    func testRejectsOtherVirtualAggregateAndMultiOutputDevices() {
        let guardrail = SelfRoutingGuard()

        XCTAssertEqual(
            guardrail.physicalWorkingDeviceSelection(
                input: device(id: "blackhole-input", name: "BlackHole Virtual Input", direction: .input),
                output: device(id: "built-in-output", name: "MacBook Speakers", direction: .output)
            ).inputKind,
            .otherVirtual
        )
        XCTAssertEqual(
            guardrail.physicalWorkingDeviceSelection(
                input: device(id: "built-in-input", name: "MacBook Mic", direction: .input),
                output: device(id: "aggregate-output", name: "Aggregate Device", direction: .output)
            ).outputKind,
            .aggregate
        )
        XCTAssertEqual(
            guardrail.physicalWorkingDeviceSelection(
                input: device(id: "built-in-input", name: "MacBook Mic", direction: .input),
                output: device(id: "multi-output", name: "Multi-Output Device", direction: .output)
            ).outputKind,
            .multiOutput
        )
    }

    func testWorkingDeviceStoreExposesSelectionEvidence() {
        let store = WorkingDeviceStore()
        let selection = store.lowResourceSelectionEvidence(
            physicalInput: device(id: "built-in-input", name: "MacBook Mic", direction: .input),
            physicalOutput: device(id: "built-in-output", name: "MacBook Speakers", direction: .output)
        )

        XCTAssertTrue(selection.isReleaseReady)
        XCTAssertEqual(selection.selectionResult, .accepted)
    }

    private func device(id: String, name: String, direction: AudioDirection) -> PhysicalAudioDevice {
        PhysicalAudioDevice(
            id: id,
            displayName: name,
            direction: direction,
            deviceClass: id.contains("built-in") ? .builtIn : .unknown,
            availabilityState: .available
        )
    }
}
#endif
