import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LeakageMeasurementTests: XCTestCase {
    func testCleanLowCorrelationFarEndWindowPasses() {
        let service = LeakageMeasurementService()
        let incoming = sineSamples(count: 16_000 * 16, amplitude: 0.5)
        let mic = lowNoiseSamples(count: 16_000 * 16, amplitude: 0.0005)

        let measurement = service.measure(
            micSamples: mic,
            incomingSamples: incoming,
            sampleRate: 16_000,
            measuredAt: Date(timeIntervalSince1970: 1)
        )
        let decision = service.finalizationStatus(
            measurement: measurement,
            alignmentStatus: .aligned,
            measurementAttempted: true,
            measurementApplicable: true
        )

        XCTAssertEqual(measurement.status, .passed)
        XCTAssertEqual(decision.0, .clean)
        XCTAssertEqual(decision.1, .eligibleOriginalDual)
    }

    func testContaminatedFarEndWindowBlocksReadiness() {
        let service = LeakageMeasurementService()
        let incoming = sineSamples(count: 16_000 * 16, amplitude: 0.5)
        let mic = incoming.map { $0 * 0.2 }

        let measurement = service.measure(micSamples: mic, incomingSamples: incoming, sampleRate: 16_000)
        let decision = service.finalizationStatus(
            measurement: measurement,
            alignmentStatus: .aligned,
            measurementAttempted: true,
            measurementApplicable: true
        )

        XCTAssertEqual(decision.0, .leakageDetected)
        XCTAssertEqual(decision.1, .blockedLeakageDetected)
        XCTAssertEqual(decision.2, .leakageDetected)
    }

    func testDelayedFarEndLeakageBlocksReadiness() {
        let service = LeakageMeasurementService()
        let incoming = deterministicNoiseSamples(count: 16_000 * 16)
        let delaySamples = 800
        let mic = (0..<incoming.count).map { index -> Float in
            guard index >= delaySamples else { return 0 }
            return incoming[index - delaySamples] * 0.004
        }

        let measurement = service.measure(micSamples: mic, incomingSamples: incoming, sampleRate: 16_000)
        let decision = service.finalizationStatus(
            measurement: measurement,
            alignmentStatus: .aligned,
            measurementAttempted: true,
            measurementApplicable: true
        )

        XCTAssertEqual(decision.0, .leakageDetected)
        XCTAssertEqual(decision.1, .blockedLeakageDetected)
        XCTAssertGreaterThan(measurement.correlationPeak ?? 0, LeakageThresholdVersion.v1.maximumCorrelationPeak)
        XCTAssertEqual(measurement.correlationLagMs, 50)
    }

    func testDoubleTalkInsufficientReferenceDowngradesConfidence() {
        let service = LeakageMeasurementService()
        let incoming = sineSamples(count: 16_000 * 2, amplitude: 0.5)
        let mic = sineSamples(count: 16_000 * 2, amplitude: 0.5, phase: .pi / 2)

        let measurement = service.measure(micSamples: mic, incomingSamples: incoming, sampleRate: 16_000)
        let decision = service.finalizationStatus(
            measurement: measurement,
            alignmentStatus: .aligned,
            measurementAttempted: true,
            measurementApplicable: true
        )

        XCTAssertEqual(measurement.confidence, 0.45)
        XCTAssertEqual(decision.0, .unproven)
        XCTAssertEqual(decision.1, .blockedUnproven)
    }

    func testSilenceNoiseEchoClippingAndDropoutAreNotCleanByDefault() {
        let service = LeakageMeasurementService()
        let silence = Array(repeating: Float(0), count: 16_000)
        let noise = (0..<16_000).map { Float($0 % 2 == 0 ? 0.001 : -0.001) }
        let clipped = Array(repeating: Float(1), count: 16_000 * 16)

        for mic in [silence, noise, clipped] {
            let measurement = service.measure(micSamples: mic, incomingSamples: silence, sampleRate: 16_000)
            let decision = service.finalizationStatus(
                measurement: measurement,
                alignmentStatus: .aligned,
                measurementAttempted: true,
                measurementApplicable: true
            )
            XCTAssertNotEqual(decision.0, .clean)
        }
    }
}

func sineSamples(count: Int, amplitude: Float, phase: Float = 0) -> [Float] {
    (0..<count).map { index in
        amplitude * sin((Float(index) / 64.0) + phase)
    }
}

func lowNoiseSamples(count: Int, amplitude: Float = 0.0005) -> [Float] {
    (0..<count).map { index in
        let value = ((index * 1103515245 + 12345) & 0x7fffffff) % 997
        return (Float(value) / 997.0 - 0.5) * amplitude
    }
}

func deterministicNoiseSamples(count: Int) -> [Float] {
    var state: UInt64 = 0x1234_5678_9abc_def0
    return (0..<count).map { _ in
        state ^= state << 13
        state ^= state >> 7
        state ^= state << 17
        return ((Float(state % 20_001) / 10_000.0) - 1.0) * 0.5
    }
}
#endif
