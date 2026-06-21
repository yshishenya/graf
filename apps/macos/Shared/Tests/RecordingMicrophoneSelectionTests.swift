import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class RecordingMicrophoneSelectionTests: XCTestCase {
    func testRejectsTwoBrainVirtualMicrophoneBeforeCaptureStarts() {
        let virtualInput = PhysicalAudioDevice(
            id: SelfRoutingGuard.microphoneUID,
            displayName: SelfRoutingGuard.microphoneDisplayName,
            direction: .input,
            deviceClass: .otherVirtual,
            availabilityState: .available
        )
        let service = MicrophoneCaptureService(
            authorizer: FakeMicrophoneAuthorizer(current: .granted, requested: .granted),
            inputProvider: FakeRecordingMicrophoneInputProvider(defaultInput: virtualInput, devices: [virtualInput]),
            clock: { Date(timeIntervalSince1970: 300) }
        )

        let selection = service.resolveRecordingMicrophoneSelection(selectedInputDeviceId: virtualInput.id)

        XCTAssertEqual(selection.selectionResult, .rejected)
        XCTAssertEqual(selection.rejectionReason, .unsupportedSelfRoutingInput)
        XCTAssertEqual(selection.workingDeviceKind, .twoBrainVirtual)
        XCTAssertFalse(selection.isAccepted)
    }

    func testUnavailableSelectedMicrophoneFailsClosedWithoutDefaultMutation() {
        let defaultInput = PhysicalAudioDevice(
            id: "default-input",
            displayName: "MacBook Pro Microphone",
            direction: .input,
            deviceClass: .builtIn,
            availabilityState: .available
        )
        let service = MicrophoneCaptureService(
            authorizer: FakeMicrophoneAuthorizer(current: .granted, requested: .granted),
            inputProvider: FakeRecordingMicrophoneInputProvider(defaultInput: defaultInput, devices: [defaultInput]),
            clock: { Date(timeIntervalSince1970: 301) }
        )

        let selection = service.resolveRecordingMicrophoneSelection(selectedInputDeviceId: "missing-usb-mic")

        XCTAssertEqual(selection.mode, .userSelected)
        XCTAssertEqual(selection.inputDeviceId, "missing-usb-mic")
        XCTAssertEqual(selection.selectionResult, .unavailable)
        XCTAssertEqual(selection.rejectionReason, .deviceUnavailable)
        XCTAssertFalse(selection.isAccepted)
    }

    func testDisconnectedSelectedMicrophoneIsUnavailableNotAccepted() {
        let disconnected = PhysicalAudioDevice(
            id: "usb-mic",
            displayName: "USB Microphone",
            direction: .input,
            deviceClass: .usb,
            availabilityState: .disconnected
        )
        let service = MicrophoneCaptureService(
            authorizer: FakeMicrophoneAuthorizer(current: .granted, requested: .granted),
            inputProvider: FakeRecordingMicrophoneInputProvider(defaultInput: disconnected, devices: [disconnected]),
            clock: { Date(timeIntervalSince1970: 302) }
        )

        let selection = service.resolveRecordingMicrophoneSelection(selectedInputDeviceId: "usb-mic")

        XCTAssertEqual(selection.selectionResult, .unavailable)
        XCTAssertEqual(selection.rejectionReason, .deviceUnavailable)
        XCTAssertEqual(selection.workingDeviceKind, .physical)
        XCTAssertFalse(selection.isAccepted)
    }
}

private struct FakeMicrophoneAuthorizer: MicrophonePermissionAuthorizing {
    let current: CapturePermissionState
    let requested: CapturePermissionState

    func currentPermissionState() -> CapturePermissionState {
        current
    }

    func requestPermission() async -> CapturePermissionState {
        requested
    }
}

private struct FakeRecordingMicrophoneInputProvider: RecordingMicrophoneInputProviding {
    let defaultInput: PhysicalAudioDevice?
    let devices: [PhysicalAudioDevice]

    func availableInputs() -> [PhysicalAudioDevice] {
        devices
    }

    func defaultInputDevice() -> PhysicalAudioDevice? {
        defaultInput
    }

    func inputDevice(id: String) -> PhysicalAudioDevice? {
        devices.first { $0.id == id }
    }
}
#endif
