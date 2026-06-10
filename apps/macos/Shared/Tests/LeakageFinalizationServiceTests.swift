import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LeakageFinalizationServiceTests: XCTestCase {
    func testFarEndOnlyCleanFixtureCanFinalizeClean() throws {
        let directory = try makePackage(mic: lowNoiseSamples(count: 16_000 * 16), incoming: sineSamples(count: 16_000 * 16, amplitude: 0.5))
        defer { try? FileManager.default.removeItem(at: directory) }

        let finalization = LeakageFinalizationService(clock: { Date(timeIntervalSince1970: 10) })
            .finalize(
                micURL: directory.appendingPathComponent("mic.wav"),
                incomingURL: directory.appendingPathComponent("incoming.wav"),
                micTrack: completeTrack(role: .localMic, durationMs: 16_000),
                incomingTrack: completeTrack(role: .remoteSpeaker, durationMs: 16_000)
            )

        XCTAssertEqual(finalization.status, LeakageStatus.clean)
        XCTAssertEqual(finalization.transcriptionGate, LeakageTranscriptionGate.eligibleOriginalDual)
    }

    func testFarEndOnlyContaminatedFixtureFinalizesLeakageDetected() throws {
        let incoming = sineSamples(count: 16_000 * 16, amplitude: 0.5)
        let directory = try makePackage(mic: incoming.map { $0 * 0.2 }, incoming: incoming)
        defer { try? FileManager.default.removeItem(at: directory) }

        let finalization = LeakageFinalizationService()
            .finalize(
                micURL: directory.appendingPathComponent("mic.wav"),
                incomingURL: directory.appendingPathComponent("incoming.wav"),
                micTrack: completeTrack(role: .localMic, durationMs: 16_000),
                incomingTrack: completeTrack(role: .remoteSpeaker, durationMs: 16_000)
            )

        XCTAssertEqual(finalization.status, LeakageStatus.leakageDetected)
        XCTAssertEqual(finalization.transcriptionGate, LeakageTranscriptionGate.blockedLeakageDetected)
    }

    func testLateLeakageAfterInitialWindowDoesNotFinalizeClean() throws {
        let sampleRate = 16_000
        let durationSeconds = 90
        let totalCount = sampleRate * durationSeconds
        let incoming = sineSamples(count: totalCount, amplitude: 0.5)
        let mic = (0..<totalCount).map { index -> Float in
            index >= sampleRate * 75 ? incoming[index] * 0.2 : lowNoiseSample(index: index, amplitude: 0.0005)
        }
        let directory = try makePackage(mic: mic, incoming: incoming)
        defer { try? FileManager.default.removeItem(at: directory) }

        let finalization = LeakageFinalizationService()
            .finalize(
                micURL: directory.appendingPathComponent("mic.wav"),
                incomingURL: directory.appendingPathComponent("incoming.wav"),
                micTrack: completeTrack(role: .localMic, durationMs: durationSeconds * 1000),
                incomingTrack: completeTrack(role: .remoteSpeaker, durationMs: durationSeconds * 1000)
            )

        XCTAssertEqual(finalization.status, LeakageStatus.leakageDetected)
        XCTAssertEqual(finalization.transcriptionGate, LeakageTranscriptionGate.blockedLeakageDetected)
    }

    func testMalformedZeroSampleRateDoesNotCrashOrFinalizeClean() throws {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("leakage-malformed-\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        try writeWAV(samples: lowNoiseSamples(count: 16_000), sampleRate: 0, to: directory.appendingPathComponent("mic.wav"))
        try writeWAV(samples: sineSamples(count: 16_000, amplitude: 0.5), sampleRate: 16_000, to: directory.appendingPathComponent("incoming.wav"))

        let finalization = LeakageFinalizationService()
            .finalize(
                micURL: directory.appendingPathComponent("mic.wav"),
                incomingURL: directory.appendingPathComponent("incoming.wav"),
                micTrack: completeTrack(role: .localMic, durationMs: 1_000),
                incomingTrack: completeTrack(role: .remoteSpeaker, durationMs: 1_000)
            )

        XCTAssertEqual(finalization.status, LeakageStatus.notMeasured)
        XCTAssertEqual(finalization.transcriptionGate, LeakageTranscriptionGate.blockedNotMeasured)
    }

    func testActualWAVFormatMismatchDoesNotFinalizeClean() throws {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("leakage-format-mismatch-\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        try writeWAV(samples: lowNoiseSamples(count: 8_000 * 16), sampleRate: 8_000, to: directory.appendingPathComponent("mic.wav"))
        try writeWAV(samples: sineSamples(count: 16_000 * 16, amplitude: 0.5), sampleRate: 16_000, to: directory.appendingPathComponent("incoming.wav"))

        let finalization = LeakageFinalizationService()
            .finalize(
                micURL: directory.appendingPathComponent("mic.wav"),
                incomingURL: directory.appendingPathComponent("incoming.wav"),
                micTrack: completeTrack(role: .localMic, durationMs: 16_000),
                incomingTrack: completeTrack(role: .remoteSpeaker, durationMs: 16_000)
            )

        XCTAssertNotEqual(finalization.status, LeakageStatus.clean)
        XCTAssertNotEqual(finalization.transcriptionGate, LeakageTranscriptionGate.eligibleOriginalDual)
    }

    func testTimelineMismatchIsUnprovenAndNotReady() throws {
        let directory = try makePackage(mic: lowNoiseSamples(count: 16_000 * 16), incoming: sineSamples(count: 16_000 * 16, amplitude: 0.5))
        defer { try? FileManager.default.removeItem(at: directory) }

        let finalization = LeakageFinalizationService()
            .finalize(
                micURL: directory.appendingPathComponent("mic.wav"),
                incomingURL: directory.appendingPathComponent("incoming.wav"),
                micTrack: completeTrack(role: .localMic, durationMs: 16_000),
                incomingTrack: completeTrack(role: .remoteSpeaker, durationMs: 12_000)
            )

        XCTAssertEqual(finalization.status, LeakageStatus.unproven)
        XCTAssertEqual(finalization.transcriptionGate, LeakageTranscriptionGate.blockedTimelineMisaligned)
    }

    func testMissingReferenceIsNotMeasured() throws {
        let directory = try makePackage(mic: lowNoiseSamples(count: 16_000 * 16), incoming: [])
        defer { try? FileManager.default.removeItem(at: directory) }

        let finalization = LeakageFinalizationService()
            .finalize(
                micURL: directory.appendingPathComponent("mic.wav"),
                incomingURL: directory.appendingPathComponent("incoming.wav"),
                micTrack: completeTrack(role: .localMic, durationMs: 16_000),
                incomingTrack: missingTrack(role: .remoteSpeaker)
            )

        XCTAssertEqual(finalization.status, LeakageStatus.notMeasured)
        XCTAssertEqual(finalization.transcriptionGate, LeakageTranscriptionGate.blockedNotMeasured)
    }
}

private func makePackage(mic: [Float], incoming: [Float]) throws -> URL {
    let directory = FileManager.default.temporaryDirectory
        .appendingPathComponent("leakage-fixture-\(UUID().uuidString)")
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    try writeWAV(samples: mic, to: directory.appendingPathComponent("mic.wav"))
    try writeWAV(samples: incoming, to: directory.appendingPathComponent("incoming.wav"))
    return directory
}

private func writeWAV(samples: [Float], to url: URL) throws {
    try writeWAV(samples: samples, sampleRate: 16_000, to: url)
}

private func writeWAV(samples: [Float], sampleRate: UInt32, to url: URL) throws {
    var data = Data()
    let dataByteCount = UInt32(samples.count * MemoryLayout<Int16>.stride)
    data.append(contentsOf: [0x52, 0x49, 0x46, 0x46])
    data.appendLE(UInt32(36) + dataByteCount)
    data.append(contentsOf: [0x57, 0x41, 0x56, 0x45])
    data.append(contentsOf: [0x66, 0x6d, 0x74, 0x20])
    data.appendLE(UInt32(16))
    data.appendLE(UInt16(1))
    data.appendLE(UInt16(1))
    data.appendLE(sampleRate)
    data.appendLE(sampleRate * UInt32(MemoryLayout<Int16>.stride))
    data.appendLE(UInt16(MemoryLayout<Int16>.stride))
    data.appendLE(UInt16(16))
    data.append(contentsOf: [0x64, 0x61, 0x74, 0x61])
    data.appendLE(dataByteCount)
    for sample in samples {
        var intSample = Int16(max(-1, min(1, sample)) * Float(Int16.max)).littleEndian
        data.append(Data(bytes: &intSample, count: MemoryLayout<Int16>.size))
    }
    try data.write(to: url)
}

private func lowNoiseSample(index: Int, amplitude: Float) -> Float {
    let value = ((index * 1103515245 + 12345) & 0x7fffffff) % 997
    return (Float(value) / 997.0 - 0.5) * amplitude
}

private func completeTrack(role: AudioTrackRole, durationMs: Int) -> LocalRecordingTrack {
    LocalRecordingTrack(
        trackId: role.rawValue,
        role: role,
        status: .saved,
        fileName: role == .localMic ? "mic.wav" : "incoming.wav",
        format: "wav-pcm-s16le",
        sampleRate: 16_000,
        channelCount: 1,
        bitsPerSample: 16,
        durationMs: durationMs,
        byteCount: Int64(44 + durationMs * 32),
        frameCount: Int64(durationMs * 16),
        timelineStartMs: 0,
        timelineAligned: true
    )
}

private func missingTrack(role: AudioTrackRole) -> LocalRecordingTrack {
    LocalRecordingTrack(
        trackId: role.rawValue,
        role: role,
        status: .missing,
        fileName: role == .localMic ? "mic.wav" : "incoming.wav",
        format: "wav-pcm-s16le",
        sampleRate: 16_000,
        channelCount: 1,
        durationMs: 0,
        byteCount: 0,
        frameCount: 0
    )
}

private extension Data {
    mutating func appendLE(_ value: UInt16) {
        var little = value.littleEndian
        append(Data(bytes: &little, count: MemoryLayout<UInt16>.size))
    }

    mutating func appendLE(_ value: UInt32) {
        var little = value.littleEndian
        append(Data(bytes: &little, count: MemoryLayout<UInt32>.size))
    }
}
#endif
