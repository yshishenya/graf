import Foundation
@testable import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

final class RecordingAEC3QualityTests: XCTestCase {
    func testSyntheticFarEndNearEndAndDoubleTalkQuality() throws {
        let sampleCount = 12 * RecordingEchoProcessor.sampleRate
        let farEnd = speechLikeSignal(count: sampleCount, seed: 0x1234_5678, gain: 0.35)
        let nearEnd = voicedSignal(count: sampleCount, gain: 0.22)
        let convergenceStart = 5 * RecordingEchoProcessor.sampleRate

        for delayMs in [20, 80, 150, 300] {
            for rt60Seconds in [0.2, 0.5, 0.8] {
                let echo = roomEcho(farEnd, delayMs: delayMs, rt60Seconds: rt60Seconds)
                let farOnlyOutput = try process(render: farEnd, capture: echo)
                let farReductionDb = db(
                    rms(Array(echo[convergenceStart...])),
                    over: rms(Array(farOnlyOutput[convergenceStart...]))
                )
                XCTAssertGreaterThanOrEqual(
                    farReductionDb,
                    20,
                    "delay=\(delayMs)ms rt60=\(rt60Seconds)s"
                )
            }
        }

        let echo = roomEcho(farEnd, delayMs: 80, rt60Seconds: 0.5)

        let silence = [Float](repeating: 0, count: sampleCount)
        let nearOnlyOutput = try process(render: silence, capture: nearEnd)
        let nearInput = Array(nearEnd[RecordingEchoProcessor.sampleRate...])
        let nearOutput = Array(nearOnlyOutput[RecordingEchoProcessor.sampleRate...])
        let lag = bestLag(lhs: Array(nearInput.prefix(48_000)), rhs: Array(nearOutput.prefix(48_000)))
        let alignedNearOnly = aligned(lhs: nearInput, rhs: nearOutput, lag: lag)
        XCTAssertLessThanOrEqual(abs(lag), 480)
        XCTAssertLessThanOrEqual(abs(db(rms(alignedNearOnly.rhs), over: rms(alignedNearOnly.lhs))), 1)
        XCTAssertGreaterThanOrEqual(correlation(alignedNearOnly.lhs, alignedNearOnly.rhs), 0.98)

        let doubleTalkNear = nearEnd.enumerated().map { index, sample in
            index < convergenceStart ? 0 : sample
        }
        let doubleTalkCapture = zip(echo, doubleTalkNear).map { min(0.95, max(-0.95, $0 + $1)) }
        let doubleTalkOutput = try process(render: farEnd, capture: doubleTalkCapture)
        let alignedDoubleTalk = aligned(
            lhs: Array(doubleTalkNear[convergenceStart...]),
            rhs: Array(doubleTalkOutput[convergenceStart...]),
            lag: lag
        )
        let alignedEcho = aligned(
            lhs: Array(echo[convergenceStart...]),
            rhs: Array(doubleTalkOutput[convergenceStart...]),
            lag: lag
        )
        XCTAssertGreaterThanOrEqual(
            db(rms(alignedEcho.lhs), over: projectedRMS(alignedEcho.rhs, onto: alignedEcho.lhs)),
            10
        )
        XCTAssertLessThanOrEqual(
            abs(db(projectedRMS(alignedDoubleTalk.rhs, onto: alignedDoubleTalk.lhs), over: rms(alignedDoubleTalk.lhs))),
            3
        )
        XCTAssertFalse(hasSilentRun(alignedDoubleTalk.rhs, longerThan: 960))
    }

    func testSmoothAcousticDelayDriftKeepsProcessingAndReducesEcho() throws {
        let sampleCount = 12 * RecordingEchoProcessor.sampleRate
        let farEnd = speechLikeSignal(count: sampleCount, seed: 0x177_AEC3, gain: 0.35)
        let echo = farEnd.indices.map { index -> Float in
            let progress = Double(index) / Double(max(1, farEnd.count - 1))
            let delaySamples = Int((80 + 5 * progress) * Double(RecordingEchoProcessor.sampleRate) / 1_000)
            return index >= delaySamples ? farEnd[index - delaySamples] * 0.5 : 0
        }

        let output = try process(render: farEnd, capture: echo)
        let measuredStart = 7 * RecordingEchoProcessor.sampleRate

        XCTAssertTrue(output.allSatisfy(\.isFinite))
        XCTAssertGreaterThanOrEqual(
            db(rms(Array(echo[measuredStart...])), over: rms(Array(output[measuredStart...]))),
            10
        )
    }

    func testCanonicalMixUsesCleanedMicrophoneWithoutReintroducingEcho() throws {
        let sampleCount = 8 * RecordingEchoProcessor.sampleRate
        let farEnd = speechLikeSignal(count: sampleCount, seed: 0xCA11_AEC3, gain: 0.35)
        let echo = roomEcho(farEnd, delayMs: 80, rt60Seconds: 0.5)
        var mixed: [Float] = []
        let timeline = try RecordingAudioTimeline(
            configuration: .init(reorderWindowFrames: 0),
            echoProcessor: RecordingEchoProcessor()
        ) { chunk in
            mixed.append(contentsOf: chunk.samples)
        }
        let format = RecordingAudioFormat(sampleRate: 48_000, channelCount: 1)
        let timestamp = RecordingAudioPresentationTimestamp(seconds: 0, clockDomain: .hostTime)

        try timeline.append(source: .microphone, batch: RecordingAudioBatch(
            samples: echo,
            format: format,
            presentationTime: timestamp
        ))
        try timeline.append(source: .systemAudio, batch: RecordingAudioBatch(
            samples: farEnd,
            format: format,
            presentationTime: timestamp
        ))
        try timeline.finish()

        let measuredStart = 5 * RecordingEchoProcessor.sampleRate
        let rawEchoContribution = echo[measuredStart...].map { $0 * 0.5 }
        let residual = zip(mixed[measuredStart...], farEnd[measuredStart...]).map { output, system in
            output - system * 0.5
        }
        XCTAssertEqual(mixed.count, sampleCount)
        XCTAssertGreaterThanOrEqual(db(rms(rawEchoContribution), over: rms(residual)), 20)
    }

    private func process(render: [Float], capture: [Float]) throws -> [Float] {
        let processor = try RecordingEchoProcessor()
        var output: [Float] = []
        output.reserveCapacity(capture.count)
        for start in stride(from: 0, to: capture.count, by: RecordingEchoProcessor.frameSamples) {
            let end = start + RecordingEchoProcessor.frameSamples
            output.append(contentsOf: try processor.process(
                render: Array(render[start..<end]),
                capture: Array(capture[start..<end])
            ))
        }
        return output
    }

    private func speechLikeSignal(count: Int, seed: UInt64, gain: Float) -> [Float] {
        var state = seed
        var smoothed: Float = 0
        return (0..<count).map { index in
            state = state &* 6_364_136_223_846_793_005 &+ 1
            let noise = Float(Int32(truncatingIfNeeded: state >> 32)) / Float(Int32.max)
            smoothed = 0.92 * smoothed + 0.08 * noise
            let envelope = Float(0.35 + 0.65 * abs(sin(Double(index) * 2 * .pi / 19_200)))
            return min(0.95, max(-0.95, smoothed * envelope * gain * 4))
        }
    }

    private func roomEcho(_ render: [Float], delayMs: Int, rt60Seconds: Double) -> [Float] {
        let delaySamples = delayMs * RecordingEchoProcessor.sampleRate / 1_000
        let reflectionSpacing = RecordingEchoProcessor.sampleRate * 30 / 1_000
        return render.indices.map { index in
            var sample = index >= delaySamples ? render[index - delaySamples] * 0.5 : 0
            for reflection in 1...6 {
                let offset = delaySamples + reflection * reflectionSpacing
                guard index >= offset else { continue }
                let reflectionTime = Double(reflection * reflectionSpacing) /
                    Double(RecordingEchoProcessor.sampleRate)
                let decay = pow(10, -3 * reflectionTime / rt60Seconds)
                sample += render[index - offset] * Float(0.16 * decay)
            }
            return min(0.95, max(-0.95, sample))
        }
    }

    private func voicedSignal(count: Int, gain: Float) -> [Float] {
        (0..<count).map { index in
            let time = Double(index) / Double(RecordingEchoProcessor.sampleRate)
            let syllable = 0.25 + 0.75 * pow(abs(sin(2 * .pi * 1.7 * time)), 0.4)
            let sample = sin(2 * .pi * 137 * time) +
                0.55 * sin(2 * .pi * 293 * time + 0.4) +
                0.3 * sin(2 * .pi * 487 * time + 1.1) +
                0.15 * sin(2 * .pi * 941 * time + 0.7)
            return Float(sample * syllable) * gain
        }
    }

    private func rms(_ samples: [Float]) -> Double {
        sqrt(samples.reduce(0.0) { $0 + Double($1 * $1) } / Double(max(1, samples.count)))
    }

    private func db(_ numerator: Double, over denominator: Double) -> Double {
        20 * log10(max(numerator, 1e-12) / max(denominator, 1e-12))
    }

    private func correlation(_ lhs: [Float], _ rhs: [Float]) -> Double {
        let numerator = zip(lhs, rhs).reduce(0.0) { $0 + Double($1.0 * $1.1) }
        let lhsEnergy = lhs.reduce(0.0) { $0 + Double($1 * $1) }
        let rhsEnergy = rhs.reduce(0.0) { $0 + Double($1 * $1) }
        return numerator / max(1e-12, sqrt(lhsEnergy * rhsEnergy))
    }

    private func projectedRMS(_ signal: [Float], onto reference: [Float]) -> Double {
        let coefficient = zip(signal, reference).reduce(0.0) { $0 + Double($1.0 * $1.1) } /
            max(1e-12, reference.reduce(0.0) { $0 + Double($1 * $1) })
        return abs(coefficient) * rms(reference)
    }

    private func bestLag(lhs: [Float], rhs: [Float]) -> Int {
        var best = (lag: 0, correlation: -Double.infinity)
        for lag in stride(from: -4_800, through: 4_800, by: 48) {
            let pair = aligned(lhs: lhs, rhs: rhs, lag: lag)
            let value = correlation(pair.lhs, pair.rhs)
            if value > best.correlation { best = (lag, value) }
        }
        for lag in (best.lag - 47)...(best.lag + 47) {
            let pair = aligned(lhs: lhs, rhs: rhs, lag: lag)
            let value = correlation(pair.lhs, pair.rhs)
            if value > best.correlation { best = (lag, value) }
        }
        return best.lag
    }

    private func aligned(lhs: [Float], rhs: [Float], lag: Int) -> (lhs: [Float], rhs: [Float]) {
        if lag >= 0 {
            return (Array(lhs.dropLast(lag)), Array(rhs.dropFirst(lag)))
        }
        return (Array(lhs.dropFirst(-lag)), Array(rhs.dropLast(-lag)))
    }

    private func hasSilentRun(_ samples: [Float], longerThan maximum: Int) -> Bool {
        var run = 0
        for sample in samples {
            run = abs(sample) < 0.000_01 ? run + 1 : 0
            if run > maximum { return true }
        }
        return false
    }
}
#endif
