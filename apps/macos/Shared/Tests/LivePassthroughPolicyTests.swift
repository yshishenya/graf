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

    func testAutoIdlePolicyReleasesPhysicalRouteWhenVirtualClientCloses() {
        let policy = PassthroughAutoIdlePolicy(releaseAfterIdleTicks: 3)

        XCTAssertFalse(policy.shouldReleasePhysicalRoute(
            bridgeActive: true,
            virtualClientRunning: false,
            consecutiveIdleTicks: 2
        ))
        XCTAssertTrue(policy.shouldReleasePhysicalRoute(
            bridgeActive: true,
            virtualClientRunning: false,
            consecutiveIdleTicks: 3
        ))
        XCTAssertFalse(policy.shouldReleasePhysicalRoute(
            bridgeActive: true,
            virtualClientRunning: true,
            consecutiveIdleTicks: 3
        ))
        XCTAssertFalse(policy.shouldReleasePhysicalRoute(
            bridgeActive: false,
            virtualClientRunning: false,
            consecutiveIdleTicks: 3
        ))
    }

    func testAutoIdlePolicyPreservesNaturalSilenceWithFreshClientEvidence() {
        let policy = PassthroughAutoIdlePolicy(releaseAfterIdleTicks: 3)
        let snapshot = ClientActivitySnapshot(
            source: .validationFixture,
            microphoneOpen: false,
            microphoneRunning: false,
            speakerOpen: false,
            speakerRunning: false,
            stillUsesVirtualMicrophone: true,
            stillUsesVirtualSpeaker: true,
            freshnessMs: 200,
            naturalSilenceAllowed: true
        )

        XCTAssertFalse(policy.shouldReleasePhysicalRoute(
            bridgeActive: true,
            clientActivity: snapshot,
            consecutiveIdleTicks: 300
        ))
    }

    func testAutoIdlePolicyPreservesOneSidedActivity() {
        let policy = PassthroughAutoIdlePolicy(releaseAfterIdleTicks: 3)
        let snapshot = ClientActivitySnapshot(
            source: .validationFixture,
            microphoneOpen: false,
            microphoneRunning: false,
            speakerOpen: true,
            speakerRunning: true,
            stillUsesVirtualMicrophone: true,
            stillUsesVirtualSpeaker: true,
            freshnessMs: 200,
            naturalSilenceAllowed: true
        )

        XCTAssertFalse(policy.shouldReleasePhysicalRoute(
            bridgeActive: true,
            clientActivity: snapshot,
            consecutiveIdleTicks: 300
        ))
    }

    func testCoreAudioDetectorBuildsPerSideClientActivitySnapshots() {
        let detector = CoreAudioVirtualDeviceActivityDetector(snapshotProvider: {
            [
                .init(name: "2brain Rec Microphone", isRunning: true),
                .init(name: "2brain Rec Speaker", isRunning: false)
            ]
        })

        let snapshot = detector.expectedVirtualDeviceClientActivity()

        XCTAssertTrue(snapshot.microphoneOpen)
        XCTAssertTrue(snapshot.microphoneRunning)
        XCTAssertFalse(snapshot.speakerOpen)
        XCTAssertFalse(snapshot.speakerRunning)
        XCTAssertEqual(snapshot.stillUsesVirtualMicrophone, true)
        XCTAssertEqual(snapshot.stillUsesVirtualSpeaker, false)
        XCTAssertEqual(snapshot.source, .coreAudioClient)
    }

    func testCoreAudioDetectorDoesNotUseAggregateFallbackForMissingSide() {
        let detector = CoreAudioVirtualDeviceActivityDetector(snapshotProvider: {
            [.init(name: "2brain Rec Microphone", isRunning: true)]
        })

        let snapshot = detector.expectedVirtualDeviceClientActivity()

        XCTAssertTrue(snapshot.microphoneRunning)
        XCTAssertFalse(snapshot.speakerOpen)
        XCTAssertEqual(snapshot.stillUsesVirtualSpeaker, false)
        XCTAssertTrue(detector.anyExpectedVirtualDeviceRunning())
    }

    func testCoreAudioDetectorDoesNotTreatInstalledIdleDevicesAsOpenClients() {
        let detector = CoreAudioVirtualDeviceActivityDetector(snapshotProvider: {
            [
                .init(name: "2brain Rec Microphone", isRunning: false),
                .init(name: "2brain Rec Speaker", isRunning: false)
            ]
        })

        let snapshot = detector.expectedVirtualDeviceClientActivity()

        XCTAssertFalse(snapshot.microphoneOpen)
        XCTAssertFalse(snapshot.microphoneRunning)
        XCTAssertFalse(snapshot.speakerOpen)
        XCTAssertFalse(snapshot.speakerRunning)
        XCTAssertEqual(snapshot.stillUsesVirtualMicrophone, false)
        XCTAssertEqual(snapshot.stillUsesVirtualSpeaker, false)
        XCTAssertFalse(PassthroughAutoIdlePolicy().clientActivityPolicy.shouldPreserveRoute(for: snapshot))
    }

    func testCoreAudioDetectorReportsClosedWhenNeitherExpectedSideExists() {
        let detector = CoreAudioVirtualDeviceActivityDetector(snapshotProvider: {
            [.init(name: "External USB Microphone", isRunning: true)]
        })

        let snapshot = detector.expectedVirtualDeviceClientActivity()

        XCTAssertFalse(snapshot.microphoneOpen)
        XCTAssertFalse(snapshot.speakerOpen)
        XCTAssertEqual(snapshot.stillUsesVirtualMicrophone, false)
        XCTAssertEqual(snapshot.stillUsesVirtualSpeaker, false)
        XCTAssertFalse(detector.anyExpectedVirtualDeviceRunning())
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
