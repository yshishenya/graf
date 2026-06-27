import Foundation
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LocalRecordingWriterTests: XCTestCase {
    func testWriterFinalizesTruthfulDegradedManifestWhenNoFramesAreAvailable() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-writer-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            sharedMemoryFactory: { nil },
            recordMicrophone: false
        )

        let directory = try writer.start(
            sessionId: "session",
            startedAt: Date(timeIntervalSince1970: 10)
        )
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.manifestURL.path))
        XCTAssertEqual(directory.localMicURL.lastPathComponent, "mic.wav")
        XCTAssertEqual(directory.remoteSpeakerURL.lastPathComponent, "incoming.wav")
        XCTAssertEqual(manifest.status, .degraded)
        XCTAssertEqual(manifest.transcriptionReadiness, .degraded)
        XCTAssertFalse(manifest.isComplete)
        XCTAssertEqual(Set(manifest.tracks.map(\.role)), Set([.localMic, .remoteSpeaker]))
    }

    func testWriterCreatesIncomingWavHeaderInMediaScribeReadyFormat() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-writer-format-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            sharedMemoryFactory: { nil },
            recordMicrophone: false
        )

        let directory = try writer.start(
            sessionId: "session",
            startedAt: Date(timeIntervalSince1970: 10)
        )
        _ = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        let header = try WAVHeader(url: directory.remoteSpeakerURL)
        XCTAssertEqual(header.audioFormat, 1)
        XCTAssertEqual(header.channelCount, 1)
        XCTAssertEqual(header.sampleRate, 16_000)
        XCTAssertEqual(header.bitsPerSample, 16)
    }

    func testWriterProtectsLocalCustodyArtifactsAtRest() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-writer-protection-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            sharedMemoryFactory: { nil },
            recordMicrophone: false
        )

        let directory = try writer.start(
            sessionId: "session",
            startedAt: Date(timeIntervalSince1970: 10)
        )
        _ = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        XCTAssertTrue(LocalCustodyFileProtection.isProtected(directory.localMicURL))
        XCTAssertTrue(LocalCustodyFileProtection.isProtected(directory.remoteSpeakerURL))
        XCTAssertTrue(LocalCustodyFileProtection.isProtected(directory.manifestURL))
    }

    func testWriterProtectsRecorderCreatedMicrophoneFileAtRest() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-writer-recorder-protection-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            sharedMemoryFactory: { nil },
            recordMicrophone: true
        )

        let directory = try writer.start(
            sessionId: "session",
            startedAt: Date(timeIntervalSince1970: 10)
        )
        _ = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        XCTAssertTrue(LocalCustodyFileProtection.isProtected(directory.localMicURL))
    }

    func testWriterReportsInactiveLevelsWhenIdle() {
        let writer = LocalRecordingWriter(recordMicrophone: false)

        let levels = writer.currentLevels(now: Date(timeIntervalSince1970: 10))

        XCTAssertFalse(levels.isRecording)
        XCTAssertEqual(levels.microphoneLevel, 0)
        XCTAssertEqual(levels.incomingLevel, 0)
        XCTAssertFalse(levels.microphoneIsLive(now: Date(timeIntervalSince1970: 10)))
        XCTAssertFalse(levels.incomingIsLive(now: Date(timeIntervalSince1970: 10)))
    }

    func testWriterReportsInactiveLevelsAsynchronouslyWhenIdle() async {
        let writer = LocalRecordingWriter(recordMicrophone: false)

        let isRecording = await writer.isRecordingAsync()
        let levels = await writer.currentLevelsAsync(now: Date(timeIntervalSince1970: 10))

        XCTAssertFalse(isRecording)
        XCTAssertFalse(levels.isRecording)
        XCTAssertEqual(levels.microphoneLevel, 0)
        XCTAssertEqual(levels.incomingLevel, 0)
    }

    func testFutureLevelTimestampIsNotTreatedAsLive() {
        let levels = LiveRecordingLevels(
            isRecording: true,
            microphoneLevel: 0.8,
            incomingLevel: 0.8,
            microphoneUpdatedAt: Date(timeIntervalSince1970: 11),
            incomingUpdatedAt: Date(timeIntervalSince1970: 11)
        )

        XCTAssertFalse(levels.microphoneIsLive(now: Date(timeIntervalSince1970: 10), staleAfter: 2))
        XCTAssertFalse(levels.incomingIsLive(now: Date(timeIntervalSince1970: 10), staleAfter: 2))
    }

    func testWriterReportsRecordingLevelsWithoutInventingIncomingFrames() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-writer-level-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            sharedMemoryFactory: { nil },
            recordMicrophone: false
        )

        _ = try writer.start(
            sessionId: "session",
            startedAt: Date(timeIntervalSince1970: 10)
        )
        let levels = writer.currentLevels(now: Date(timeIntervalSince1970: 11))
        _ = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        XCTAssertTrue(levels.isRecording)
        XCTAssertEqual(levels.microphoneLevel, 0)
        XCTAssertEqual(levels.incomingLevel, 0)
        XCTAssertFalse(levels.incomingIsLive(now: Date(timeIntervalSince1970: 11)))
    }

    func testWriterReportsRecordingLevelsAsynchronously() async throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-writer-async-level-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            sharedMemoryFactory: { nil },
            recordMicrophone: false
        )

        _ = try await writer.startAsync(
            sessionId: "session-async-levels",
            startedAt: Date(timeIntervalSince1970: 10)
        )
        let isRecording = await writer.isRecordingAsync()
        let levels = await writer.currentLevelsAsync(now: Date(timeIntervalSince1970: 11))
        _ = try await writer.stopAsync(stoppedAt: Date(timeIntervalSince1970: 11))

        XCTAssertTrue(isRecording)
        XCTAssertTrue(levels.isRecording)
        XCTAssertEqual(levels.microphoneLevel, 0)
        XCTAssertEqual(levels.incomingLevel, 0)
    }

    func testWriterReportsCurrentDirectoryAsynchronously() async throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-writer-async-directory-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            sharedMemoryFactory: { nil },
            recordMicrophone: false
        )

        let directory = try await writer.startAsync(
            sessionId: "session-async-directory",
            startedAt: Date(timeIntervalSince1970: 10)
        )
        let currentDirectory = await writer.currentDirectoryURLAsync()
        _ = try await writer.stopAsync(stoppedAt: Date(timeIntervalSince1970: 11))
        let stoppedDirectory = await writer.currentDirectoryURLAsync()

        XCTAssertEqual(currentDirectory, directory.directoryURL)
        XCTAssertNil(stoppedDirectory)
    }

    func testPrivacySuppressingSampleSourceZerosPausedMicSamples() {
        let source = BufferedLocalRecordingSampleSource(capacity: 16, channelCount: 1)
        let suppressing = PrivacySuppressingSampleSource(base: source)
        let scratch = UnsafeMutablePointer<Float>.allocate(capacity: 4)
        defer { scratch.deallocate() }

        XCTAssertFalse(suppressing.lastReadWasSuppressed)
        source.append([0.4, -0.4, 0.2, -0.2])
        suppressing.update(state: .paused)
        let read = suppressing.readSamples(into: scratch, capacity: 4)

        XCTAssertEqual(read, 4)
        XCTAssertEqual(Array(UnsafeBufferPointer(start: scratch, count: 4)), [0, 0, 0, 0])
        XCTAssertEqual(suppressing.suppressedSampleCount, 4)
        XCTAssertTrue(suppressing.lastReadWasSuppressed)

        source.append([0.1, -0.1])
        suppressing.update(state: .capturing)
        let resumedRead = suppressing.readSamples(into: scratch, capacity: 4)

        XCTAssertEqual(resumedRead, 2)
        XCTAssertEqual(Array(UnsafeBufferPointer(start: scratch, count: 2)), [0.1, -0.1])
        XCTAssertFalse(suppressing.lastReadWasSuppressed)
    }

    func testWriterPersistsPrivacySegmentWhenPausedAndResumed() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-writer-privacy-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let micSource = BufferedLocalRecordingSampleSource(capacity: 16, channelCount: 1)
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            sharedMemoryFactory: { nil },
            microphoneSampleSourceFactory: { micSource },
            recordMicrophone: true
        )

        _ = try writer.start(
            sessionId: "session-privacy",
            startedAt: Date(timeIntervalSince1970: 10),
            targetMuteCapability: .chromeTelemost,
            meetingMuteTruthEvidence: [
                MeetingMuteTruthEvidence(
                    evidenceId: "evidence-1",
                    sessionId: "session-privacy",
                    targetId: "chrome_telemost",
                    targetDisplayName: "Chrome + Telemost",
                    source: .productPause,
                    status: .meetingMuteUnproven,
                    freshness: .unavailable,
                    limitationCopyShown: true,
                    recordedAt: Date(timeIntervalSince1970: 10)
                )
            ],
            limitationCopyShownAt: Date(timeIntervalSince1970: 10)
        )
        try writer.pausePrivacy(startedAt: Date(timeIntervalSince1970: 12))
        try writer.resumePrivacy(endedAt: Date(timeIntervalSince1970: 15))
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 20))

        XCTAssertEqual(manifest.privacySegments?.count, 1)
        XCTAssertEqual(manifest.privacySegments?.first?.durationMs, 3_000)
        XCTAssertEqual(manifest.privacySegments?.first?.localMicTreatment, .silenced)
        XCTAssertEqual(manifest.meetingMuteTruth?.decision, .meetingMuteUnproven)
        XCTAssertEqual(manifest.meetingMuteTruthEvidence?.first?.evidenceId, "evidence-1")
    }

    func testWriterPersistsRedactedPrivacySegmentWithoutSuppressingMicSource() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-writer-redacted-privacy-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            sharedMemoryFactory: { nil },
            recordMicrophone: false
        )

        _ = try writer.start(
            sessionId: "session-redacted-privacy",
            startedAt: Date(timeIntervalSince1970: 10)
        )
        try writer.pausePrivacy(startedAt: Date(timeIntervalSince1970: 12))
        try writer.resumePrivacy(endedAt: Date(timeIntervalSince1970: 15))
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 20))

        XCTAssertEqual(manifest.privacySegments?.count, 1)
        XCTAssertEqual(manifest.privacySegments?.first?.localMicTreatment, .redacted)
    }

    func testWriterFinalizesActivePauseWithPrivacyTreatmentOnStop() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-writer-pause-stop-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let micSource = BufferedLocalRecordingSampleSource(capacity: 16, channelCount: 1)
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            sharedMemoryFactory: { nil },
            microphoneSampleSourceFactory: { micSource },
            recordMicrophone: true
        )

        _ = try writer.start(
            sessionId: "session-pause-stop",
            startedAt: Date(timeIntervalSince1970: 10)
        )
        try writer.pausePrivacy(startedAt: Date(timeIntervalSince1970: 12))
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 20))

        XCTAssertEqual(manifest.privacySegments?.count, 1)
        XCTAssertEqual(manifest.privacySegments?.first?.durationMs, 8_000)
        XCTAssertEqual(manifest.privacySegments?.first?.localMicTreatment, .silenced)
    }

    func testDownsamplerAveragesWindowBeforeReducingSystemAudioTo16k() {
        let samples: [Float] = [
            0.0, 0.0,
            0.9, 0.9,
            0.0, 0.0
        ]

        let result = samples.withUnsafeBufferPointer {
            PCM16MonoDownsampler.downsample(
                samples: $0.baseAddress!,
                count: samples.count,
                inputChannelCount: 2,
                inputSampleRate: 48_000,
                outputSampleRate: 16_000
            )
        }

        XCTAssertEqual(result.frameCount, 1)
        XCTAssertInt16AlmostEqual(result.data.int16LE(at: 0), Int16(0.3 * Float(Int16.max)))
    }

    func testDownsamplerTreatsMonoSystemAudioSamplesAsFrames() {
        let samples: [Float] = [0.3, 0.3, 0.3, -0.6]

        let result = samples.withUnsafeBufferPointer {
            PCM16MonoDownsampler.downsample(
                samples: $0.baseAddress!,
                count: samples.count,
                inputChannelCount: 1,
                inputSampleRate: 48_000,
                outputSampleRate: 16_000
            )
        }

        XCTAssertEqual(result.frameCount, 2)
        XCTAssertInt16AlmostEqual(result.data.int16LE(at: 0), Int16(0.3 * Float(Int16.max)))
        XCTAssertInt16AlmostEqual(result.data.int16LE(at: 2), Int16(-0.6 * Float(Int16.max)))
    }
}

private func XCTAssertInt16AlmostEqual(
    _ actual: Int16,
    _ expected: Int16,
    tolerance: Int = 2,
    file: StaticString = #filePath,
    line: UInt = #line
) {
    XCTAssertLessThanOrEqual(abs(Int(actual) - Int(expected)), tolerance, file: file, line: line)
}

private struct WAVHeader {
    let audioFormat: UInt16
    let channelCount: UInt16
    let sampleRate: UInt32
    let bitsPerSample: UInt16

    init(url: URL) throws {
        let data = try Data(contentsOf: url)
        XCTAssertGreaterThanOrEqual(data.count, 44)
        audioFormat = data.uint16LE(at: 20)
        channelCount = data.uint16LE(at: 22)
        sampleRate = data.uint32LE(at: 24)
        bitsPerSample = data.uint16LE(at: 34)
    }
}

private extension Data {
    func int16LE(at offset: Int) -> Int16 {
        Int16(bitPattern: uint16LE(at: offset))
    }

    func uint16LE(at offset: Int) -> UInt16 {
        UInt16(self[offset]) | (UInt16(self[offset + 1]) << 8)
    }

    func uint32LE(at offset: Int) -> UInt32 {
        UInt32(self[offset]) |
            (UInt32(self[offset + 1]) << 8) |
            (UInt32(self[offset + 2]) << 16) |
            (UInt32(self[offset + 3]) << 24)
    }
}
#endif
