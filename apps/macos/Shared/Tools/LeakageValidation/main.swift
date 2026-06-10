import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

struct ValidationError: Error, CustomStringConvertible {
    let description: String
}

func require(_ condition: @autoclosure () -> Bool, _ message: String) throws {
    if !condition() {
        throw ValidationError(description: message)
    }
}

let start = Date()
try validateDelayedLeakage()
try validateLateLeakage()
try validateMalformedWAV()
try validateFormatMismatch()
try validateDeletionTruth()
try validateTwoHourSparseFixture()
let elapsed = Date().timeIntervalSince(start)
print(String(format: "LeakageValidation: PASS elapsed=%.2fs", elapsed))

func validateDelayedLeakage() throws {
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
    try require(
        decision.0 == .leakageDetected,
        "delayed leakage must not finalize clean; status=\(decision.0.rawValue) corr=\(measurement.correlationPeak ?? -1) lag=\(measurement.correlationLagMs ?? -999) leakageDb=\(measurement.leakageLevelDb ?? -999)"
    )
    try require(measurement.correlationPeak ?? 0 > LeakageThresholdVersion.v1.maximumCorrelationPeak, "delayed leakage correlation must exceed threshold")
}

func validateLateLeakage() throws {
    let sampleRate = 16_000
    let durationSeconds = 90
    let totalCount = sampleRate * durationSeconds
    let incoming = sineSamples(count: totalCount, amplitude: 0.5)
    let mic = (0..<totalCount).map { index -> Float in
        index >= sampleRate * 75 ? incoming[index] * 0.2 : lowNoiseSample(index: index, amplitude: 0.0005)
    }
    let directory = try makeDirectory(prefix: "leakage-validation-late")
    defer { try? FileManager.default.removeItem(at: directory) }
    try writeWAV(samples: mic, to: directory.appendingPathComponent("mic.wav"))
    try writeWAV(samples: incoming, to: directory.appendingPathComponent("incoming.wav"))

    let finalization = LeakageFinalizationService().finalize(
        micURL: directory.appendingPathComponent("mic.wav"),
        incomingURL: directory.appendingPathComponent("incoming.wav"),
        micTrack: completeTrack(role: .localMic, durationMs: durationSeconds * 1000),
        incomingTrack: completeTrack(role: .remoteSpeaker, durationMs: durationSeconds * 1000)
    )
    try require(finalization.status == .leakageDetected, "late leakage must not finalize clean")
}

func validateMalformedWAV() throws {
    let directory = try makeDirectory(prefix: "leakage-validation-malformed")
    defer { try? FileManager.default.removeItem(at: directory) }
    try writeWAV(samples: lowNoiseSamples(count: 16_000), sampleRate: 0, to: directory.appendingPathComponent("mic.wav"))
    try writeWAV(samples: sineSamples(count: 16_000, amplitude: 0.5), to: directory.appendingPathComponent("incoming.wav"))
    let finalization = LeakageFinalizationService().finalize(
        micURL: directory.appendingPathComponent("mic.wav"),
        incomingURL: directory.appendingPathComponent("incoming.wav"),
        micTrack: completeTrack(role: .localMic, durationMs: 1_000),
        incomingTrack: completeTrack(role: .remoteSpeaker, durationMs: 1_000)
    )
    try require(finalization.status == .notMeasured, "malformed WAV must fail closed")
    try require(finalization.transcriptionGate == .blockedNotMeasured, "malformed WAV must not be transcription-ready")
}

func validateFormatMismatch() throws {
    let directory = try makeDirectory(prefix: "leakage-validation-format")
    defer { try? FileManager.default.removeItem(at: directory) }
    try writeWAV(samples: lowNoiseSamples(count: 8_000 * 16), sampleRate: 8_000, to: directory.appendingPathComponent("mic.wav"))
    try writeWAV(samples: sineSamples(count: 16_000 * 16, amplitude: 0.5), to: directory.appendingPathComponent("incoming.wav"))
    let finalization = LeakageFinalizationService().finalize(
        micURL: directory.appendingPathComponent("mic.wav"),
        incomingURL: directory.appendingPathComponent("incoming.wav"),
        micTrack: completeTrack(role: .localMic, durationMs: 16_000),
        incomingTrack: completeTrack(role: .remoteSpeaker, durationMs: 16_000)
    )
    try require(finalization.status != .clean, "format mismatch must not finalize clean")
    try require(finalization.transcriptionGate != .eligibleOriginalDual, "format mismatch must not be transcription-ready")
}

func validateDeletionTruth() throws {
    let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) }).manifest(
        sessionId: "session",
        directoryId: "dir",
        startedAt: Date(timeIntervalSince1970: 10),
        stoppedAt: Date(timeIntervalSince1970: 20),
        tracks: [completeTrack(role: .localMic), completeTrack(role: .remoteSpeaker)],
        leakageFinalization: LeakageFinalization(
            status: .notMeasured,
            evaluatedAt: Date(timeIntervalSince1970: 20),
            measurementAttempted: false,
            measurementApplicable: false,
            alignmentStatus: .unknown,
            confidence: 0,
            failureReason: .leakageNotMeasured,
            originalEvidenceStatus: .notMeasured,
            transcriptionGate: .blockedNotMeasured
        )
    )
    try require(manifest.localDeletionRegistered == false, "manifest must not claim deletion registration without evidence")
}

func validateTwoHourSparseFixture() throws {
    let directory = try makeDirectory(prefix: "leakage-validation-2h")
    defer { try? FileManager.default.removeItem(at: directory) }
    let durationSeconds = 2 * 60 * 60
    let frameCount = 16_000 * durationSeconds
    try writeSparseWAV(
        frameCount: frameCount,
        windows: validationWindows(frameCount: frameCount),
        amplitude: 0.0005,
        to: directory.appendingPathComponent("mic.wav")
    )
    try writeSparseWAV(
        frameCount: frameCount,
        windows: validationWindows(frameCount: frameCount),
        amplitude: 0.5,
        to: directory.appendingPathComponent("incoming.wav")
    )

    let start = Date()
    let finalization = LeakageFinalizationService().finalize(
        micURL: directory.appendingPathComponent("mic.wav"),
        incomingURL: directory.appendingPathComponent("incoming.wav"),
        micTrack: completeTrack(role: .localMic, durationMs: durationSeconds * 1000),
        incomingTrack: completeTrack(role: .remoteSpeaker, durationMs: durationSeconds * 1000)
    )
    let elapsed = Date().timeIntervalSince(start)
    try require(elapsed < 60, "2-hour sparse finalization exceeded 60 seconds")
    try require(finalization.transcriptionGate != .eligibleOriginalDual || finalization.status == .clean, "ready package must be clean")
    print(String(format: "LeakageValidation: two_hour_sparse elapsed=%.2fs status=%@", elapsed, finalization.status.rawValue))
}

func validationWindows(frameCount: Int) -> [Int] {
    let windowLength = 960_000 / 3
    return [
        0,
        max(0, (frameCount - windowLength) / 2),
        max(0, frameCount - windowLength)
    ]
}

func makeDirectory(prefix: String) throws -> URL {
    let url = FileManager.default.temporaryDirectory
        .appendingPathComponent("\(prefix)-\(UUID().uuidString)", isDirectory: true)
    try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
    return url
}

func writeWAV(samples: [Float], sampleRate: UInt32 = 16_000, to url: URL) throws {
    var data = Data()
    let dataByteCount = UInt32(samples.count * MemoryLayout<Int16>.stride)
    appendWAVHeader(to: &data, dataByteCount: dataByteCount, sampleRate: sampleRate)
    for sample in samples {
        var intSample = Int16(max(-1, min(1, sample)) * Float(Int16.max)).littleEndian
        data.append(Data(bytes: &intSample, count: MemoryLayout<Int16>.size))
    }
    try data.write(to: url)
}

func writeSparseWAV(frameCount: Int, windows: [Int], amplitude: Float, to url: URL) throws {
    FileManager.default.createFile(atPath: url.path, contents: nil)
    let handle = try FileHandle(forWritingTo: url)
    defer { try? handle.close() }
    var header = Data()
    let dataByteCount = UInt32(frameCount * MemoryLayout<Int16>.stride)
    appendWAVHeader(to: &header, dataByteCount: dataByteCount, sampleRate: 16_000)
    try handle.write(contentsOf: header)
    for startFrame in windows {
        let samples = sineSamples(count: 16_000, amplitude: amplitude)
        var data = Data()
        data.reserveCapacity(samples.count * MemoryLayout<Int16>.size)
        for sample in samples {
            var intSample = Int16(max(-1, min(1, sample)) * Float(Int16.max)).littleEndian
            data.append(Data(bytes: &intSample, count: MemoryLayout<Int16>.size))
        }
        try handle.seek(toOffset: UInt64(44 + startFrame * MemoryLayout<Int16>.stride))
        try handle.write(contentsOf: data)
    }
    try handle.seek(toOffset: UInt64(44 + frameCount * MemoryLayout<Int16>.stride - 1))
    try handle.write(contentsOf: Data([0]))
}

func appendWAVHeader(to data: inout Data, dataByteCount: UInt32, sampleRate: UInt32) {
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
}

func completeTrack(role: AudioTrackRole, durationMs: Int = 1_000) -> LocalRecordingTrack {
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

func sineSamples(count: Int, amplitude: Float) -> [Float] {
    (0..<count).map { index in
        amplitude * sin(Float(index) / 64.0)
    }
}

func lowNoiseSamples(count: Int) -> [Float] {
    (0..<count).map { lowNoiseSample(index: $0, amplitude: 0.0005) }
}

func lowNoiseSample(index: Int, amplitude: Float) -> Float {
    let value = ((index * 1103515245 + 12345) & 0x7fffffff) % 997
    return (Float(value) / 997.0 - 0.5) * amplitude
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
