import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioCPUGateTests: XCTestCase {
    func testIdleStopAndQuitRequireReturnBelowIdleThresholds() {
        for phase in [CaptureHealthPhase.idle, .stop, .quit] {
            let evaluation = SystemAudioCPUGateEvaluator.evaluate(
                samples: [
                    cpuSample(phase: phase, coreaudiod: 2.1, app: 1.2, helper: 0.3),
                    cpuSample(phase: phase, coreaudiod: 4.9, app: 2.5, helper: 2.4)
                ],
                phase: phase
            )

            XCTAssertTrue(evaluation.passed, "Expected \(phase.rawValue) to pass below idle gates")
            XCTAssertEqual(evaluation.failureReason, .none)
        }
    }

    func testIdleFailsAtThresholdBecauseGateRequiresBelowFivePercent() {
        let evaluation = SystemAudioCPUGateEvaluator.evaluate(
            samples: [
                cpuSample(phase: .idle, coreaudiod: 5.0, app: 1.0),
                cpuSample(phase: .idle, coreaudiod: 3.0, app: 4.0)
            ],
            phase: .idle
        )

        XCTAssertFalse(evaluation.passed)
        XCTAssertEqual(evaluation.failureReason, .cpuGateFailed)
        XCTAssertEqual(evaluation.maxCoreaudiodCpuPercent, 5.0)
    }

    func testActiveRecordingAllowsTransientSpikeButFailsSustainedCoreaudiodOverage() {
        let transient = SystemAudioCPUGateEvaluator.evaluate(
            samples: [
                cpuSample(phase: .activeRecording, coreaudiod: 11.5, app: 4),
                cpuSample(phase: .activeRecording, coreaudiod: 4.0, app: 4),
                cpuSample(phase: .activeRecording, coreaudiod: 12.0, app: 4)
            ],
            phase: .activeRecording
        )
        XCTAssertTrue(transient.passed)

        let sustained = SystemAudioCPUGateEvaluator.evaluate(
            samples: [
                cpuSample(phase: .activeRecording, coreaudiod: 10.1, app: 4),
                cpuSample(phase: .activeRecording, coreaudiod: 11.0, app: 4),
                cpuSample(phase: .activeRecording, coreaudiod: 12.0, app: 4)
            ],
            phase: .activeRecording
        )

        XCTAssertFalse(sustained.passed)
        XCTAssertTrue(sustained.sustainedCoreaudiodExceeded)
        XCTAssertEqual(sustained.failureReason, .cpuGateFailed)
    }

    func testActiveRecordingFailsSustainedCombinedAppHelperOverage() {
        let evaluation = SystemAudioCPUGateEvaluator.evaluate(
            samples: [
                cpuSample(phase: .activeRecording, coreaudiod: 4, app: 20, helper: 6),
                cpuSample(phase: .activeRecording, coreaudiod: 4, app: 21, helper: 5.5),
                cpuSample(phase: .activeRecording, coreaudiod: 4, app: 19, helper: 7)
            ],
            phase: .activeRecording
        )

        XCTAssertFalse(evaluation.passed)
        XCTAssertTrue(evaluation.sustainedAppHelperExceeded)
        XCTAssertEqual(evaluation.maxAppHelperCpuPercent, 26.5)
    }

    func testHALProbeObservationFailsBeforeCpuThresholds() {
        let evaluation = SystemAudioCPUGateEvaluator.evaluate(
            samples: [
                cpuSample(phase: .activeRecording, coreaudiod: 2, app: 2, halProbeObserved: true)
            ],
            phase: .activeRecording
        )

        XCTAssertFalse(evaluation.passed)
        XCTAssertTrue(evaluation.halProbeObserved)
        XCTAssertEqual(evaluation.failureReason, .halProbeObserved)
    }

    private func cpuSample(
        phase: CaptureHealthPhase,
        coreaudiod: Double,
        app: Double,
        helper: Double = 0,
        halProbeObserved: Bool = false
    ) -> SystemAudioCPUSample {
        SystemAudioCPUSample(
            recordingSessionId: "session",
            phase: phase,
            sampledAt: Date(timeIntervalSince1970: 1),
            coreaudiodCpuPercent: coreaudiod,
            appCpuPercent: app,
            helperCpuPercent: helper,
            halProbeObserved: halProbeObserved
        )
    }
}
#endif
