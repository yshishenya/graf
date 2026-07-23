import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class MicrophoneCaptureServiceTests: XCTestCase {
    func testPreflightReportsCurrentPermissionState() {
        let service = MicrophoneCaptureService(
            authorizer: FakeMicrophoneAuthorizer(current: .denied, requested: .granted)
        )

        let session = service.preflight(
            sessionId: "session",
            inputDeviceId: "built-in",
            inputDisplayName: "Built-in Microphone"
        )

        XCTAssertEqual(session.permissionState, .denied)
        XCTAssertEqual(session.inputDeviceId, "built-in")
        XCTAssertFalse(session.canBeAccepted)
    }

    func testRequestPermissionAndPreflightUsesRequestedState() async {
        let service = MicrophoneCaptureService(
            authorizer: FakeMicrophoneAuthorizer(current: .unknown, requested: .granted)
        )

        let session = await service.requestPermissionAndPreflight(
            sessionId: "session",
            inputDisplayName: "Built-in Microphone"
        )

        XCTAssertEqual(session.permissionState, .granted)
        XCTAssertEqual(session.inputDisplayName, "Built-in Microphone")
    }

    func testRequestPermissionAndPreflightDoesNotReRequestAfterDenial() async {
        let service = MicrophoneCaptureService(
            authorizer: FakeMicrophoneAuthorizer(current: .denied, requested: .granted)
        )

        let session = await service.requestPermissionAndPreflight(
            sessionId: "session",
            inputDisplayName: "Built-in Microphone"
        )

        XCTAssertEqual(session.permissionState, .denied)
    }

    func testRecordingMicrophoneSelectionAcceptsDefaultFallbackAsDiagnosticSafe() {
        let selection = RecordingMicrophoneSelection(
            selectionId: "selection-default",
            mode: .macOSDefaultFallback,
            inputDeviceId: "default-input",
            inputDisplayName: "MacBook Pro Microphone",
            deviceClass: .builtIn,
            workingDeviceKind: .physical,
            selectionResult: .accepted,
            resolvedAt: Date(timeIntervalSince1970: 100)
        )

        XCTAssertTrue(selection.isAccepted)
        XCTAssertTrue(selection.diagnosticSafe)
        XCTAssertNil(selection.rejectionReason)
    }

    func testAppOwnedMicrophoneStreamSessionProvesGraphReadinessOnlyForAppOwnedFrames() {
        let selection = acceptedRecordingMicrophoneSelection()
        let appOwned = AppOwnedMicrophoneStreamSession(
            sessionId: "session",
            selection: selection,
            permissionState: .granted,
            streamKind: .appOwnedSampleSource,
            startedAt: Date(timeIntervalSince1970: 110),
            stoppedAt: Date(timeIntervalSince1970: 120),
            monotonicStartMs: 0,
            monotonicStopMs: 10_000,
            sampleRate: 48_000,
            channelCount: 1,
            writerSampleRate: 16_000,
            writerChannelCount: 1,
            frameCount: 16_000,
            droppedFrameCount: 0,
            silentFrameCount: 0,
            clippedFrameCount: 0,
            routeChangeCount: 0,
            lastFrameAt: Date(timeIntervalSince1970: 119),
            failureReason: .none
        )
        let historical = AppOwnedMicrophoneStreamSession(
            sessionId: "session",
            selection: selection,
            permissionState: .granted,
            streamKind: .historicalSource,
            frameCount: 16_000,
            failureReason: .none
        )

        XCTAssertTrue(appOwned.provesGraphReadiness)
        XCTAssertFalse(historical.provesGraphReadiness)
        XCTAssertTrue(appOwned.diagnosticSafe)
    }

    func testMicrophoneStreamHealthCarriesFutureProcessingReadinessWithoutRawContent() {
        let health = MicrophoneStreamHealth(
            gateStatus: .passed,
            failureReason: .none,
            framesObserved: true,
            timingConfidence: .usable,
            silenceStatus: .audible,
            lastLevel: 0.42,
            lastLevelAt: Date(timeIntervalSince1970: 119),
            cleanupReadiness: .readyForFutureProcessing,
            evidenceCodes: ["mic_frames_observed", "incoming_reference_present"]
        )

        XCTAssertEqual(health.cleanupReadiness, .readyForFutureProcessing)
        XCTAssertEqual(health.failureReason, .none)
        XCTAssertTrue(health.framesObserved)
        XCTAssertTrue(health.diagnosticSafe)
        XCTAssertFalse(health.evidenceCodes.contains("raw_audio"))
    }

    func testResolveRecordingMicrophoneUsesDefaultInputWhenNoSelectionExists() {
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
            clock: { Date(timeIntervalSince1970: 200) }
        )

        let selection = service.resolveRecordingMicrophoneSelection(selectedInputDeviceId: nil)

        XCTAssertEqual(selection.mode, .macOSDefaultFallback)
        XCTAssertEqual(selection.inputDeviceId, "default-input")
        XCTAssertEqual(selection.inputDisplayName, "MacBook Pro Microphone")
        XCTAssertEqual(selection.selectionResult, .accepted)
        XCTAssertEqual(selection.workingDeviceKind, .physical)
        XCTAssertTrue(selection.isAccepted)
    }

    func testResolveRecordingMicrophoneUsesSelectedNativeInput() {
        let selectedInput = PhysicalAudioDevice(
            id: "usb-mic",
            displayName: "USB Microphone",
            direction: .input,
            deviceClass: .usb,
            availabilityState: .available
        )
        let defaultInput = PhysicalAudioDevice(
            id: "default-input",
            displayName: "MacBook Pro Microphone",
            direction: .input,
            deviceClass: .builtIn,
            availabilityState: .available
        )
        let service = MicrophoneCaptureService(
            authorizer: FakeMicrophoneAuthorizer(current: .granted, requested: .granted),
            inputProvider: FakeRecordingMicrophoneInputProvider(defaultInput: defaultInput, devices: [defaultInput, selectedInput]),
            clock: { Date(timeIntervalSince1970: 201) }
        )

        let selection = service.resolveRecordingMicrophoneSelection(selectedInputDeviceId: "usb-mic")

        XCTAssertEqual(selection.mode, .userSelected)
        XCTAssertEqual(selection.inputDeviceId, "usb-mic")
        XCTAssertEqual(selection.inputDisplayName, "USB Microphone")
        XCTAssertEqual(selection.deviceClass, .usb)
        XCTAssertEqual(selection.selectionResult, .accepted)
        XCTAssertNil(selection.rejectionReason)
    }

    func testResolveRecordingMicrophoneFailsClosedForUnknownInputIdentity() {
        let unknownInput = PhysicalAudioDevice(
            id: "unclassified-input",
            displayName: "External Audio",
            direction: .input,
            deviceClass: .unknown,
            availabilityState: .available
        )
        let service = MicrophoneCaptureService(
            authorizer: FakeMicrophoneAuthorizer(current: .granted, requested: .granted),
            inputProvider: FakeRecordingMicrophoneInputProvider(defaultInput: unknownInput, devices: [unknownInput]),
            clock: { Date(timeIntervalSince1970: 204) }
        )

        let selection = service.resolveRecordingMicrophoneSelection(selectedInputDeviceId: nil)

        XCTAssertEqual(selection.selectionResult, .rejected)
        XCTAssertEqual(selection.workingDeviceKind, .unknown)
        XCTAssertEqual(selection.rejectionReason, .inputIdentityUnproven)
        XCTAssertFalse(selection.isAccepted)
    }

    func testAppOwnedMicrophoneSampleSourceBindsResolvedSelectedInputDevice() throws {
        let selectedInput = PhysicalAudioDevice(
            id: "usb-mic",
            displayName: "USB Microphone",
            direction: .input,
            deviceClass: .usb,
            availabilityState: .available
        )
        let defaultInput = PhysicalAudioDevice(
            id: "default-input",
            displayName: "MacBook Pro Microphone",
            direction: .input,
            deviceClass: .builtIn,
            availabilityState: .available
        )
        let service = MicrophoneCaptureService(
            authorizer: FakeMicrophoneAuthorizer(current: .granted, requested: .granted),
            inputProvider: FakeRecordingMicrophoneInputProvider(defaultInput: defaultInput, devices: [defaultInput, selectedInput]),
            clock: { Date(timeIntervalSince1970: 203) }
        )

        let selection = service.resolveRecordingMicrophoneSelection(selectedInputDeviceId: "usb-mic")
        let source = try service.makeAppOwnedMicrophoneSampleSource(for: selection)

        XCTAssertEqual(source.inputDeviceId, "usb-mic")
    }

    func testAppOwnedMicrophoneSourcePreservesTimestampedCaptureBatch() throws {
        let source = AppOwnedMicrophoneSampleSource(inputDeviceId: "built-in")
        let original = RecordingAudioBatch(
            samples: Array(repeating: 0.4, count: 480),
            format: RecordingAudioFormat(sampleRate: 48_000, channelCount: 1),
            presentationTime: RecordingAudioPresentationTimestamp(seconds: 654.5, clockDomain: .hostTime),
            discontinuity: .none,
            routeGeneration: 3
        )

        source.appendCapturedBatch(original)
        let restored = try XCTUnwrap(source.readTimestampedBatch(maximumFrameCount: 480))

        XCTAssertEqual(restored.presentationTime, original.presentationTime)
        XCTAssertEqual(restored.format, original.format)
        XCTAssertEqual(restored.routeGeneration, 3)
        XCTAssertEqual(restored.samples, original.samples)
    }

    func testBlockedPermissionStatesCreateBlockedMicrophoneStreamEvidence() {
        let service = MicrophoneCaptureService(
            authorizer: FakeMicrophoneAuthorizer(current: .denied, requested: .denied),
            inputProvider: FakeRecordingMicrophoneInputProvider(defaultInput: nil, devices: []),
            clock: { Date(timeIntervalSince1970: 202) }
        )
        let selection = acceptedRecordingMicrophoneSelection()

        for permissionState in [CapturePermissionState.denied, .restricted, .stale] {
            let evidence = service.blockedMicrophoneStreamEvidence(
                sessionId: "blocked-\(permissionState.rawValue)",
                selection: selection,
                permissionState: permissionState,
                failureReason: .permissionDenied
            )

            XCTAssertEqual(evidence.stream.permissionState, permissionState)
            XCTAssertEqual(evidence.stream.failureReason, .permissionDenied)
            XCTAssertFalse(evidence.stream.provesGraphReadiness)
            XCTAssertEqual(evidence.health.gateStatus, .blocked)
            XCTAssertEqual(evidence.health.cleanupReadiness, .blocked)
        }
    }
}

private func acceptedRecordingMicrophoneSelection() -> RecordingMicrophoneSelection {
    RecordingMicrophoneSelection(
        selectionId: "selection",
        mode: .userSelected,
        inputDeviceId: "built-in",
        inputDisplayName: "Built-in Microphone",
        deviceClass: .builtIn,
        workingDeviceKind: .physical,
        selectionResult: .accepted,
        resolvedAt: Date(timeIntervalSince1970: 100)
    )
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
