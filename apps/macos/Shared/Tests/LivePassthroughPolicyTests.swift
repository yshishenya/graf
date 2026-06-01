import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LivePassthroughPolicyTests: XCTestCase {
    func testSessionCanActivateOnlyWhenReadyAndNotRecording() {
        let session = makeSession(status: .ready, recordingState: "not_recording")

        XCTAssertTrue(session.canActivate)
    }

    func testSessionCannotActivateWhenRecordingStateIsRecording() {
        let session = makeSession(status: .ready, recordingState: "recording")

        XCTAssertFalse(session.canActivate)
    }

    func testSessionCannotActivateWithMissingHeartbeat() {
        var session = makeSession(status: .ready, recordingState: "not_recording")
        session.healthEvidence.appHeartbeatStatus = .heartbeatLost

        XCTAssertFalse(session.canActivate)
    }

    func testBuiltInWiredGateRequiresLatencyAndLeakageThresholds() {
        let passing = PassthroughHealthEvidence(
            appHeartbeatStatus: .connected,
            latencyMs: 24,
            leakageDbBelowReference: 48,
            notIntelligible: true
        )
        let highLatency = PassthroughHealthEvidence(
            appHeartbeatStatus: .connected,
            latencyMs: 34,
            leakageDbBelowReference: 48,
            notIntelligible: true
        )

        XCTAssertTrue(passing.passesBuiltInWiredGate)
        XCTAssertFalse(highLatency.passesBuiltInWiredGate)
    }

    func testDefaultLaunchStateIsNonRecordingAndInactiveUntilStarted() {
        let engine = PassthroughRouteEngine(sharedMemory: nil)
        var log: [(String, String)] = []

        let state = engine.recordLaunchState { event, detail in
            log.append((event, detail))
        }

        XCTAssertEqual(state, .inactive)
        XCTAssertTrue(log.contains { event, detail in
            event == "passthrough_bridge_launch_available" &&
                detail.contains("non-recording")
        })
    }

    func testAutomaticLaunchArmsWithoutOpeningPhysicalDevicesWhenNoVirtualClientRuns() {
        let engine = PassthroughRouteEngine(
            sharedMemory: nil,
            activityDetector: FixedVirtualDeviceActivityDetector(isRunning: false)
        )

        let state = engine.startAutomaticRoute { _, _ in }

        XCTAssertEqual(state, .armed)
    }

    private func makeSession(status: LivePassthroughStatus, recordingState: String) -> LivePassthroughSession {
        LivePassthroughSession(
            sessionId: "session-1",
            status: status,
            microphonePath: MicrophonePassthroughPath(
                physicalInputId: "built-in-input",
                physicalInputName: "MacBook Pro Microphone",
                status: .ready,
                validFrameObserved: true
            ),
            speakerPath: SpeakerPassthroughPath(
                physicalOutputId: "built-in-output",
                physicalOutputName: "MacBook Pro Speakers",
                status: .ready,
                stimulusObserved: true
            ),
            healthEvidence: PassthroughHealthEvidence(
                appHeartbeatStatus: .connected,
                latencyMs: 20,
                leakageDbBelowReference: 50
            ),
            recordingState: recordingState
        )
    }
}

private struct FixedVirtualDeviceActivityDetector: VirtualDeviceActivityDetecting {
    let isRunning: Bool

    func anyExpectedVirtualDeviceRunning() -> Bool {
        isRunning
    }
}
#endif
