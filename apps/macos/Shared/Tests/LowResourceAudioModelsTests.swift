import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LowResourceAudioModelsTests: XCTestCase {
    func testStartupAttemptEnforcesThreeSecondWindow() {
        let fast = StartupAttemptEvidence(
            attemptId: "fast",
            trigger: .clientIOOpened,
            startedAt: Date(timeIntervalSince1970: 1),
            completedAt: Date(timeIntervalSince1970: 3),
            durationMs: 2999,
            outcome: .ready
        )
        let slow = StartupAttemptEvidence(
            attemptId: "slow",
            trigger: .recovery,
            startedAt: Date(timeIntervalSince1970: 1),
            completedAt: Date(timeIntervalSince1970: 5),
            durationMs: 3001,
            outcome: .blocked,
            blockedReason: "core_audio_slow"
        )

        XCTAssertTrue(fast.isWithinAcceptedWindow)
        XCTAssertFalse(slow.isWithinAcceptedWindow)
    }

    func testRouteTruthSnapshotEncodesMetadataOnlyFields() throws {
        let snapshot = LowResourceTestFixtures.readySnapshot(clientOpen: true)
        let object = try JSONSerialization.jsonObject(with: JSONEncoder().encode(snapshot)) as? [String: Any]

        XCTAssertEqual(object?["resourceState"] as? String, "ready")
        XCTAssertNotNil(object?["publication"])
        XCTAssertNotNil(object?["clientActivity"])
        XCTAssertNil(object?["rawAudio"])
        XCTAssertNil(object?["transcriptText"])
        XCTAssertNil(object?["meetingContent"])
    }

    func testValidationRunPreservesAcceptedBaselineName() {
        let run = LowResourceValidationRun(
            runId: "local",
            createdAt: Date(timeIntervalSince1970: 1),
            appBuild: "local",
            driverBuild: "local",
            routeTruthSnapshots: [LowResourceTestFixtures.readySnapshot(clientOpen: true)],
            startupAttempts: [
                StartupAttemptEvidence(
                    attemptId: "startup",
                    trigger: .clientIOOpened,
                    startedAt: Date(timeIntervalSince1970: 1),
                    completedAt: Date(timeIntervalSince1970: 2),
                    durationMs: 1000,
                    outcome: .ready
                )
            ],
            realtimeSafety: RealtimeSafetyEvidence(
                scanId: "scan",
                checkedPaths: ["apps/macos/AudioDriver/Sources/Plugin/GrafProofDriver.cpp"],
                result: .passed
            ),
            result: .passed
        )

        XCTAssertEqual(run.baseline, "005-macos-passthrough-release-hardening")
        XCTAssertEqual(run.result, .passed)
    }
}

enum LowResourceTestFixtures {
    static func readySnapshot(clientOpen: Bool) -> RouteTruthSnapshot {
        RouteTruthSnapshot(
            snapshotId: "snapshot",
            recordedAt: Date(timeIntervalSince1970: 1),
            publication: VirtualDevicePublicationEvidence(
                microphoneVisible: true,
                speakerVisible: true,
                microphoneAlive: true,
                speakerAlive: true,
                microphoneRunning: clientOpen,
                speakerRunning: clientOpen,
                hidden: false,
                runtimeProbeResult: .passed
            ),
            clientActivity: ClientActivityEvidence(
                microphoneClientCount: clientOpen ? 1 : 0,
                speakerClientCount: clientOpen ? 1 : 0,
                microphoneRunning: clientOpen,
                speakerRunning: clientOpen,
                source: .driverStartStop
            ),
            appBridgeHealth: AppBridgeHealthEvidence(
                heartbeatState: .connected,
                driverFailClosed: true
            ),
            physicalDevices: PhysicalWorkingDeviceSelection(
                inputDeviceId: "built-in-input",
                inputDeviceName: "MacBook Pro Microphone",
                outputDeviceId: "built-in-output",
                outputDeviceName: "MacBook Pro Speakers",
                inputKind: .physical,
                outputKind: .physical,
                selectionResult: .accepted
            ),
            recordingTrigger: RecordingTriggerBoundary(),
            resourceState: .ready,
            result: .passed
        )
    }
}
#endif
