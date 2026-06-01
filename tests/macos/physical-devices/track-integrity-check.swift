#!/usr/bin/env swift

import Foundation

struct TrackSample {
    let sequence: Int
    let timestampMs: Double
}

let durationMinutes = 60
let sampleRate = 48_000
let framesPerBuffer = 480
let expectedBuffers = durationMinutes * 60 * sampleRate / framesPerBuffer
let remoteOffsetMs = 42.0

let localTrack = makeTrack(bufferCount: expectedBuffers, droppedSequences: [])
let remoteTrack = makeTrack(bufferCount: expectedBuffers, droppedSequences: [], offsetMs: remoteOffsetMs)
let report = integrityReport(local: localTrack, remote: remoteTrack)

print("Track integrity synthetic check:")
print("- expected buffers: \(expectedBuffers)")
print("- local dropped frame rate: \(format(report.localDroppedRate))")
print("- remote dropped frame rate: \(format(report.remoteDroppedRate))")
print("- alignment drift ms: \(format(report.alignmentDriftMs))")

guard report.localDroppedRate < 0.001 else {
    fail("Local mic dropped frame rate exceeds wired threshold.")
}

guard report.remoteDroppedRate < 0.001 else {
    fail("Remote speaker dropped frame rate exceeds wired threshold.")
}

guard abs(report.alignmentDriftMs) <= 100 else {
    fail("Track alignment drift exceeds 100 ms threshold.")
}

print("Track integrity synthetic check: ACCEPTED")

func makeTrack(
    bufferCount: Int,
    droppedSequences: Set<Int>,
    offsetMs: Double = 0
) -> [TrackSample] {
    (0..<bufferCount).compactMap { sequence in
        guard !droppedSequences.contains(sequence) else {
            return nil
        }
        return TrackSample(
            sequence: sequence,
            timestampMs: Double(sequence * framesPerBuffer) / Double(sampleRate) * 1_000.0 + offsetMs
        )
    }
}

struct IntegrityReport {
    let localDroppedRate: Double
    let remoteDroppedRate: Double
    let alignmentDriftMs: Double
}

func integrityReport(local: [TrackSample], remote: [TrackSample]) -> IntegrityReport {
    let localDroppedRate = droppedRate(observed: local)
    let remoteDroppedRate = droppedRate(observed: remote)
    let firstDelta = alignedDeltaMs(local: local.first, remote: remote.first)
    let lastDelta = alignedDeltaMs(local: local.last, remote: remote.last)

    return IntegrityReport(
        localDroppedRate: localDroppedRate,
        remoteDroppedRate: remoteDroppedRate,
        alignmentDriftMs: lastDelta - firstDelta
    )
}

func droppedRate(observed: [TrackSample]) -> Double {
    guard let maxSequence = observed.map(\.sequence).max() else {
        return 1
    }
    let expected = maxSequence + 1
    let dropped = expected - observed.count
    return Double(dropped) / Double(expected)
}

func alignedDeltaMs(local: TrackSample?, remote: TrackSample?) -> Double {
    guard let local, let remote else {
        return .infinity
    }
    return remote.timestampMs - local.timestampMs
}

func format(_ value: Double) -> String {
    String(format: "%.6f", value)
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(2)
}
