import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

@MainActor
final class RouteVerificationTests: XCTestCase {
    func testRouteVerificationRawValuesMatchDesktopDriverContract() {
        XCTAssertEqual(RoutePath.micToVirtualInput.rawValue, "mic_to_virtual_input")
        XCTAssertEqual(RoutePath.remoteOutputToVirtualSpeaker.rawValue, "remote_output_to_virtual_speaker")
        XCTAssertEqual(RoutePath.speakerPassthrough.rawValue, "speaker_passthrough")
        XCTAssertEqual(RoutePath.captureMirror.rawValue, "capture_mirror")

        XCTAssertEqual(RouteVerificationStatus.notStarted.rawValue, "not_started")
        XCTAssertEqual(RouteVerificationStatus.running.rawValue, "running")
        XCTAssertEqual(RouteVerificationStatus.passed.rawValue, "passed")
        XCTAssertEqual(RouteVerificationStatus.failed.rawValue, "failed")
        XCTAssertEqual(RouteVerificationStatus.stale.rawValue, "stale")
    }

    func testRouteVerificationContractEncodesRequiredFields() throws {
        let startedAt = Date(timeIntervalSince1970: 1_779_887_120)
        let finishedAt = startedAt.addingTimeInterval(4)
        let verification = RouteVerification(
            id: "route-mic-001",
            path: .micToVirtualInput,
            validationType: .syntheticSignal,
            target: "2brain Rec Microphone",
            status: .passed,
            failureReason: nil,
            recoveryAction: nil,
            startedAt: startedAt,
            finishedAt: finishedAt
        )

        let encoded = try JSONEncoder().encode(verification)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: encoded) as? [String: Any])

        XCTAssertEqual(object["id"] as? String, "route-mic-001")
        XCTAssertEqual(object["path"] as? String, "mic_to_virtual_input")
        XCTAssertEqual(object["validationType"] as? String, "synthetic_signal")
        XCTAssertEqual(object["target"] as? String, "2brain Rec Microphone")
        XCTAssertEqual(object["status"] as? String, "passed")
        XCTAssertNotNil(object["startedAt"])
        XCTAssertNotNil(object["finishedAt"])
    }

    func testAllowedRouteVerificationStateTransitions() {
        XCTAssertTrue(allowsTransition(from: .notStarted, to: .running))
        XCTAssertTrue(allowsTransition(from: .running, to: .passed))
        XCTAssertTrue(allowsTransition(from: .running, to: .failed))
        XCTAssertTrue(allowsTransition(from: .passed, to: .stale))
        XCTAssertTrue(allowsTransition(from: .failed, to: .running))
        XCTAssertTrue(allowsTransition(from: .stale, to: .running))
    }

    func testBlockedRouteVerificationStateTransitions() {
        XCTAssertFalse(allowsTransition(from: .notStarted, to: .passed))
        XCTAssertFalse(allowsTransition(from: .notStarted, to: .failed))
        XCTAssertFalse(allowsTransition(from: .passed, to: .running))
        XCTAssertFalse(allowsTransition(from: .failed, to: .passed))
        XCTAssertFalse(allowsTransition(from: .stale, to: .passed))
    }

    func testReadyRequiresBothMicAndSpeakerSyntheticRoutesPassed() {
        let now = Date(timeIntervalSince1970: 1_779_887_120)
        let mic = verification(path: .micToVirtualInput, status: .passed, startedAt: now)
        let speaker = verification(path: .remoteOutputToVirtualSpeaker, status: .passed, startedAt: now)

        XCTAssertTrue(isReadyAllowed(mic: mic, speaker: speaker))
        XCTAssertFalse(isReadyAllowed(
            mic: mic,
            speaker: verification(path: .remoteOutputToVirtualSpeaker, status: .stale, startedAt: now)
        ))
        XCTAssertFalse(isReadyAllowed(
            mic: verification(path: .micToVirtualInput, status: .failed, startedAt: now),
            speaker: speaker
        ))
    }

    func testSelfRoutingRejectsVirtualInputAsPhysicalInput() {
        let decision = SelfRoutingGuard().evaluate(
            physicalInput: physicalDevice(
                id: SelfRoutingGuard.microphoneUID,
                displayName: "2brain Rec Microphone",
                direction: .input
            ),
            physicalOutput: physicalDevice(
                id: "built-in-output",
                displayName: "MacBook Pro Speakers",
                direction: .output
            )
        )

        guard case let .rejected(violation) = decision else {
            XCTFail("self-routing guard must reject virtual microphone as physical input")
            return
        }
        XCTAssertEqual(violation.code, .virtualInputSelectedAsPhysicalInput)
        XCTAssertEqual(violation.recoveryAction, "select_physical_microphone")
    }

    func testSelfRoutingRejectsVirtualOutputAsPhysicalOutput() {
        let decision = SelfRoutingGuard().evaluate(
            physicalInput: physicalDevice(
                id: "built-in-input",
                displayName: "MacBook Pro Microphone",
                direction: .input
            ),
            physicalOutput: physicalDevice(
                id: SelfRoutingGuard.speakerUID,
                displayName: "2brain Rec Speaker",
                direction: .output
            )
        )

        guard case let .rejected(violation) = decision else {
            XCTFail("self-routing guard must reject virtual speaker as physical output")
            return
        }
        XCTAssertEqual(violation.code, .virtualOutputSelectedAsPhysicalOutput)
        XCTAssertEqual(violation.recoveryAction, "select_physical_speaker")
    }

    func testSelfRoutingAllowsRealPhysicalDevices() {
        let decision = SelfRoutingGuard().evaluate(
            physicalInput: physicalDevice(
                id: "built-in-input",
                displayName: "MacBook Pro Microphone",
                direction: .input
            ),
            physicalOutput: physicalDevice(
                id: "built-in-output",
                displayName: "MacBook Pro Speakers",
                direction: .output
            )
        )

        XCTAssertEqual(decision, .allowed)
    }

    @MainActor
    func testPhysicalDeviceSelectionBlocksVirtualInput() {
        let model = PhysicalDeviceSelectionViewModel(
            availableInputs: [
                physicalDevice(
                    id: SelfRoutingGuard.microphoneUID,
                    displayName: "2brain Rec Microphone",
                    direction: .input
                )
            ],
            availableOutputs: [
                physicalDevice(
                    id: "built-in-output",
                    displayName: "MacBook Pro Speakers",
                    direction: .output
                )
            ]
        )

        let result = model.selectInput(id: SelfRoutingGuard.microphoneUID)

        guard case let .rejected(violation) = result else {
            XCTFail("virtual mic selection must be rejected")
            return
        }
        XCTAssertEqual(violation.code, .virtualInputSelectedAsPhysicalInput)
        XCTAssertNil(model.selectedInput)
        XCTAssertFalse(model.canAttemptRouteVerification)
    }

    @MainActor
    func testPhysicalDeviceSelectionAllowsRealInputAndOutput() {
        let input = physicalDevice(id: "built-in-input", displayName: "MacBook Pro Microphone", direction: .input)
        let output = physicalDevice(id: "built-in-output", displayName: "MacBook Pro Speakers", direction: .output)
        let model = PhysicalDeviceSelectionViewModel(
            availableInputs: [input],
            availableOutputs: [output]
        )

        XCTAssertEqual(model.selectInput(id: input.id), .accepted)
        XCTAssertEqual(model.selectOutput(id: output.id), .accepted)
        XCTAssertTrue(model.canAttemptRouteVerification)
    }

    func testRouteVerificationServiceBlocksMissingSelection() async {
        let service = RouteVerificationService(
            clock: fixedClock,
            idFactory: fixedID,
            probe: { _, _ in .passed }
        )

        let snapshot = await service.verify(physicalInput: nil, physicalOutput: nil)

        XCTAssertFalse(snapshot.canShowReady)
        XCTAssertEqual(snapshot.mic.status, .failed)
        XCTAssertEqual(snapshot.speaker.status, .failed)
        XCTAssertEqual(snapshot.mic.failureReason, "physical_input_missing")
    }

    func testRouteVerificationServiceAllowsReadyOnlyWhenBothRoutesPass() async {
        let input = physicalDevice(id: "built-in-input", displayName: "MacBook Pro Microphone", direction: .input)
        let output = physicalDevice(id: "built-in-output", displayName: "MacBook Pro Speakers", direction: .output)
        let service = RouteVerificationService(
            clock: fixedClock,
            idFactory: fixedID,
            probe: { path, _ in path == .micToVirtualInput ? .passed : .failed }
        )

        let partialSnapshot = await service.verify(physicalInput: input, physicalOutput: output)
        XCTAssertFalse(partialSnapshot.canShowReady)

        let passingService = RouteVerificationService(
            clock: fixedClock,
            idFactory: fixedID,
            probe: { _, _ in .passed }
        )
        let passingSnapshot = await passingService.verify(physicalInput: input, physicalOutput: output)
        XCTAssertTrue(passingSnapshot.canShowReady)
    }

    func testStreamHealthDoesNotTreatNaturalSilenceAsFailureWhenFramesAreValid() {
        let snapshot = SharedAudioMemory.StreamCounterSnapshot(
            capturedFrameCount: 48000,
            storedFrameCount: 48000,
            retrievedOrProcessedFrameCount: 48000,
            droppedFrameCount: 0,
            emptyBufferCount: 0,
            lastValidFrameAt: fixedClock(),
            latencyTimestampNanos: nil
        )

        let evidence = SharedAudioMemory.streamHealthEvidence(
            track: .localMic,
            snapshot: snapshot,
            checkedAt: fixedClock()
        )

        XCTAssertEqual(evidence.capturabilityStatus, .capturable)
        XCTAssertFalse(evidence.hardFailure)
    }

    func testStreamHealthFailsWhenNoValidFramesArrive() {
        let snapshot = SharedAudioMemory.StreamCounterSnapshot(
            capturedFrameCount: 0,
            storedFrameCount: 0,
            retrievedOrProcessedFrameCount: 0,
            droppedFrameCount: 0,
            emptyBufferCount: 1,
            lastValidFrameAt: nil,
            latencyTimestampNanos: nil
        )

        let evidence = SharedAudioMemory.streamHealthEvidence(
            track: .remoteSpeaker,
            snapshot: snapshot,
            checkedAt: fixedClock()
        )

        XCTAssertEqual(evidence.capturabilityStatus, .notCapturable)
        XCTAssertTrue(evidence.hardFailure)
    }

    private func allowsTransition(from: RouteVerificationStatus, to: RouteVerificationStatus) -> Bool {
        switch (from, to) {
        case (.notStarted, .running),
             (.running, .passed),
             (.running, .failed),
             (.passed, .stale),
             (.failed, .running),
             (.stale, .running):
            true
        default:
            false
        }
    }

    private func isReadyAllowed(mic: RouteVerification, speaker: RouteVerification) -> Bool {
        mic.path == .micToVirtualInput
            && speaker.path == .remoteOutputToVirtualSpeaker
            && mic.validationType == .syntheticSignal
            && speaker.validationType == .syntheticSignal
            && mic.status == .passed
            && speaker.status == .passed
    }

    private func verification(
        path: RoutePath,
        status: RouteVerificationStatus,
        startedAt: Date
    ) -> RouteVerification {
        RouteVerification(
            id: "\(path.rawValue)-\(status.rawValue)",
            path: path,
            validationType: .syntheticSignal,
            target: nil,
            status: status,
            failureReason: status == .failed ? "synthetic_signal_missing" : nil,
            recoveryAction: status == .failed ? "retry_route_verification" : nil,
            startedAt: startedAt,
            finishedAt: status == .running ? nil : startedAt.addingTimeInterval(1)
        )
    }

    private func physicalDevice(
        id: String,
        displayName: String,
        direction: AudioDirection
    ) -> PhysicalAudioDevice {
        PhysicalAudioDevice(
            id: id,
            displayName: displayName,
            direction: direction,
            deviceClass: .builtIn,
            availabilityState: .available
        )
    }

    private func fixedClock() -> Date {
        Date(timeIntervalSince1970: 1_779_887_120)
    }

    private func fixedID() -> String {
        "route-verification-test-id"
    }
}
#endif
