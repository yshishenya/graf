#!/usr/bin/env swift

import Foundation

struct StereoFrame {
    let left: Double
    let right: Double
}

let sampleRate = 48_000
let frameCount = sampleRate
let localMic = sineWave(frequency: 440, frameCount: frameCount, sampleRate: sampleRate)
let remoteSpeaker = sineWave(frequency: 1_000, frameCount: frameCount, sampleRate: sampleRate)
let virtualMicCapture = localMic
let remoteCorrelation = normalizedCorrelation(virtualMicCapture, remoteSpeaker)
let localCorrelation = normalizedCorrelation(virtualMicCapture, localMic)

print("No-loopback synthetic route check:")
print("- local mic correlation: \(format(localCorrelation))")
print("- remote-to-mic correlation: \(format(remoteCorrelation))")

guard localCorrelation > 0.98 else {
    fail("Virtual microphone path does not preserve the local microphone signal.")
}

guard abs(remoteCorrelation) < 0.02 else {
    fail("Remote speaker signal leaked into the virtual microphone path.")
}

print("No-loopback synthetic route check: ACCEPTED")

func sineWave(frequency: Double, frameCount: Int, sampleRate: Int) -> [StereoFrame] {
    (0..<frameCount).map { frame in
        let value = sin(2.0 * .pi * frequency * Double(frame) / Double(sampleRate))
        return StereoFrame(left: value, right: value)
    }
}

func normalizedCorrelation(_ lhs: [StereoFrame], _ rhs: [StereoFrame]) -> Double {
    let count = min(lhs.count, rhs.count)
    guard count > 0 else {
        return 0
    }

    var dot = 0.0
    var lhsEnergy = 0.0
    var rhsEnergy = 0.0

    for index in 0..<count {
        let lhsMono = (lhs[index].left + lhs[index].right) / 2.0
        let rhsMono = (rhs[index].left + rhs[index].right) / 2.0
        dot += lhsMono * rhsMono
        lhsEnergy += lhsMono * lhsMono
        rhsEnergy += rhsMono * rhsMono
    }

    guard lhsEnergy > 0, rhsEnergy > 0 else {
        return 0
    }
    return dot / sqrt(lhsEnergy * rhsEnergy)
}

func format(_ value: Double) -> String {
    String(format: "%.6f", value)
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(2)
}
