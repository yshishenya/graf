import Foundation
import TwoBrainRecShared

public struct LeakageMeasurementService: Sendable {
    public init() {}

    public func measure(
        micSamples: [Float],
        incomingSamples: [Float],
        sampleRate: Int,
        threshold: LeakageThresholdVersion = .v1,
        measuredAt: Date = Date()
    ) -> LeakageMeasurement {
        let sampleCount = min(micSamples.count, incomingSamples.count)
        guard sampleCount > 0 else {
            return Self.emptyMeasurement(measuredAt: measuredAt)
        }

        let windowCount = max(1, sampleCount / max(1, sampleRate))
        let farEndOnlyWindowMs = Int((Double(sampleCount) / Double(sampleRate)) * 1000)
        let micRMS = rms(micSamples.prefix(sampleCount))
        let incomingRMS = rms(incomingSamples.prefix(sampleCount))
        let leakageLevelDb = db(micRMS / max(incomingRMS, 0.000_001))
        let correlation = correlationPeak(micSamples: micSamples, incomingSamples: incomingSamples, count: sampleCount, sampleRate: sampleRate)
        let correlationPeak = correlation.value
        let clippingObserved = micSamples.prefix(sampleCount).contains { abs($0) >= 0.98 } ||
            incomingSamples.prefix(sampleCount).contains { abs($0) >= 0.98 }
        let dropoutObserved = micSamples.prefix(sampleCount).allSatisfy { abs($0) < 0.000_01 } ||
            incomingSamples.prefix(sampleCount).allSatisfy { abs($0) < 0.000_01 }
        let hasEnoughReference = farEndOnlyWindowMs >= threshold.minimumFarEndOnlyWindowMs && incomingRMS > 0.000_1
        let confidence = hasEnoughReference && !clippingObserved && !dropoutObserved ? 0.90 : 0.45
        let directLoopbackSuspicion = correlationPeak > threshold.maximumCorrelationPeak
        let acousticLeakageSuspicion = leakageLevelDb > threshold.maximumLeakageLevelDb
        let status: MeasurementStatus = if confidence < threshold.minimumConfidence {
            .degraded
        } else if acousticLeakageSuspicion || directLoopbackSuspicion {
            .blocked
        } else {
            .passed
        }

        return LeakageMeasurement(
            speakerReferenceDb: db(incomingRMS),
            virtualMicLeakageDb: db(micRMS),
            relativeLeakageDb: leakageLevelDb,
            intelligibilityStatus: acousticLeakageSuspicion ? .intelligible : .notIntelligible,
            status: status,
            measuredAt: measuredAt,
            measurementId: UUID().uuidString,
            windowCount: windowCount,
            farEndOnlyWindowMs: farEndOnlyWindowMs,
            doubleTalkExcludedWindowMs: 0,
            alignmentOffsetMs: 0,
            alignmentDriftMs: 0,
            leakageLevelDb: leakageLevelDb,
            correlationPeak: correlationPeak,
            correlationLagMs: correlation.lagMs,
            directLoopbackSuspicion: directLoopbackSuspicion,
            acousticLeakageSuspicion: acousticLeakageSuspicion,
            clippingObserved: clippingObserved,
            dropoutObserved: dropoutObserved,
            confidence: confidence
        )
    }

    public func finalizationStatus(
        measurement: LeakageMeasurement?,
        alignmentStatus: LeakageAlignmentStatus,
        measurementAttempted: Bool,
        measurementApplicable: Bool,
        threshold: LeakageThresholdVersion = .v1
    ) -> (LeakageStatus, LeakageTranscriptionGate, LocalRecordingFailureReason) {
        guard measurementApplicable else {
            return (.notMeasured, .blockedNotMeasured, .leakageNotMeasured)
        }
        guard measurementAttempted, let measurement else {
            return (.notMeasured, .blockedNotMeasured, .leakageNotMeasured)
        }
        guard alignmentStatus == .aligned else {
            return (.unproven, .blockedTimelineMisaligned, .timelineMisaligned)
        }
        guard (measurement.confidence ?? 0) >= threshold.minimumConfidence else {
            return (.unproven, .blockedUnproven, .leakageUnproven)
        }
        if (measurement.leakageLevelDb ?? 0) > threshold.maximumLeakageLevelDb ||
            (measurement.correlationPeak ?? 0) > threshold.maximumCorrelationPeak {
            return (.leakageDetected, .blockedLeakageDetected, .leakageDetected)
        }
        return (.clean, .eligibleOriginalDual, .none)
    }

    private static func emptyMeasurement(measuredAt: Date) -> LeakageMeasurement {
        LeakageMeasurement(
            speakerReferenceDb: -120,
            virtualMicLeakageDb: -120,
            relativeLeakageDb: -120,
            intelligibilityStatus: .unknown,
            status: .degraded,
            measuredAt: measuredAt,
            measurementId: UUID().uuidString,
            windowCount: 0,
            farEndOnlyWindowMs: 0,
            doubleTalkExcludedWindowMs: 0,
            alignmentOffsetMs: 0,
            alignmentDriftMs: 0,
            leakageLevelDb: -120,
            correlationPeak: 0,
            correlationLagMs: 0,
            directLoopbackSuspicion: false,
            acousticLeakageSuspicion: false,
            clippingObserved: false,
            dropoutObserved: true,
            confidence: 0
        )
    }

    private func rms<S: Sequence>(_ samples: S) -> Double where S.Element == Float {
        var sum = 0.0
        var count = 0.0
        for sample in samples {
            sum += Double(sample * sample)
            count += 1
        }
        guard count > 0 else { return 0 }
        return sqrt(sum / count)
    }

    private func db(_ value: Double) -> Double {
        guard value > 0 else { return -120 }
        return 20 * log10(value)
    }

    private func correlationPeak(micSamples: [Float], incomingSamples: [Float], count: Int, sampleRate: Int) -> (value: Double, lagMs: Int) {
        guard count > 1 else { return (0, 0) }
        let stride = max(1, count / 16_000)
        let sampledCount = max(1, count / stride)
        let sampledRate = max(1, sampleRate / stride)
        let maxLag = min(sampledCount - 1, sampledRate / 2)
        let lagStep = max(1, sampledRate / 200)
        var bestValue = 0.0
        var bestLag = 0

        var lag = -maxLag
        while lag <= maxLag {
            let value = abs(correlation(micSamples: micSamples, incomingSamples: incomingSamples, count: sampledCount, stride: stride, lag: lag))
            if value > bestValue {
                bestValue = value
                bestLag = lag
            }
            lag += lagStep
        }

        if bestLag != 0 {
            let zeroValue = abs(correlation(micSamples: micSamples, incomingSamples: incomingSamples, count: sampledCount, stride: stride, lag: 0))
            if zeroValue > bestValue {
                bestValue = zeroValue
                bestLag = 0
            }
        }

        let lagMs = Int((Double(bestLag * stride) / Double(max(1, sampleRate))) * 1000)
        return (bestValue, lagMs)
    }

    private func correlation(micSamples: [Float], incomingSamples: [Float], count: Int, stride: Int, lag: Int) -> Double {
        guard count > 1 else { return 0 }
        var dot = 0.0
        var micEnergy = 0.0
        var incomingEnergy = 0.0
        let start = max(0, lag)
        let end = min(count, count + lag)
        guard end - start > 1 else { return 0 }
        for sampledIndex in start..<end {
            let micIndex = sampledIndex * stride
            let incomingIndex = (sampledIndex - lag) * stride
            guard micIndex < micSamples.count, incomingIndex < incomingSamples.count else { continue }
            let mic = Double(micSamples[micIndex])
            let incoming = Double(incomingSamples[incomingIndex])
            dot += mic * incoming
            micEnergy += mic * mic
            incomingEnergy += incoming * incoming
        }
        guard micEnergy > 0, incomingEnergy > 0 else { return 0 }
        return dot / sqrt(micEnergy * incomingEnergy)
    }
}
