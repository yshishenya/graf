import Foundation
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LocalRecordingWriterTests: XCTestCase {
    func testV5WriterFailsClosedWithoutFramesAndPublishesNoAudio() throws {
        let root = makeWriterTestRoot("v5-empty")
        defer { try? FileManager.default.removeItem(at: root) }
        let microphone = BufferedLocalRecordingSampleSource(channelCount: 1)
        let system = BufferedLocalRecordingSampleSource(channelCount: 1)
        let writer = makeV5Writer(root: root, microphone: microphone, system: system)

        let directory = try writer.start(
            sessionId: "empty",
            startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: writerScopeApproval(),
            permissions: writerGrantedPermissions()
        )
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        XCTAssertEqual(manifest.schemaVersion, LocalRecordingManifest.schemaVersion)
        XCTAssertEqual(manifest.mediaScribeSourceMode, "single_wav_v1")
        XCTAssertEqual(manifest.failureReason, .noFrames)
        XCTAssertFalse(manifest.isComplete)
        XCTAssertNotEqual(manifest.status, .saved)
        XCTAssertEqual(
            Set(try FileManager.default.contentsOfDirectory(atPath: directory.directoryURL.path)),
            Set(["manifest.json"])
        )
        XCTAssertEqual(Set(manifest.tracks.map(\.role)), Set([.mixedMeetingAudio, .reviewPlayback]))
    }

    func testV5WriterProtectsOnlyPublishedCanonicalArtifactsAtRest() throws {
        let root = makeWriterTestRoot("v5-custody")
        defer { try? FileManager.default.removeItem(at: root) }
        let microphone = BufferedLocalRecordingSampleSource(channelCount: 1)
        let system = BufferedLocalRecordingSampleSource(channelCount: 1)
        let writer = makeV5Writer(root: root, microphone: microphone, system: system)

        let directory = try writer.start(
            sessionId: "custody",
            startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: writerScopeApproval(),
            permissions: writerGrantedPermissions()
        )
        appendConversation(microphone: microphone, system: system, seconds: 100)
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        XCTAssertTrue(manifest.isComplete)
        XCTAssertTrue(LocalCustodyFileProtection.isProtected(directory.transcriptionAudioURL))
        XCTAssertTrue(LocalCustodyFileProtection.isProtected(directory.reviewAudioURL))
        XCTAssertTrue(LocalCustodyFileProtection.isProtected(directory.manifestURL))

        let header = try V5WAVHeader(url: directory.transcriptionAudioURL)
        XCTAssertEqual(header.audioFormat, 1)
        XCTAssertEqual(header.channelCount, 1)
        XCTAssertEqual(header.sampleRate, 16_000)
        XCTAssertEqual(header.bitsPerSample, 16)
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

    func testWriterReportsRecordingLevelsFromTimestampedSources() throws {
        let root = makeWriterTestRoot("v5-levels")
        defer { try? FileManager.default.removeItem(at: root) }
        let microphone = BufferedLocalRecordingSampleSource(channelCount: 1)
        let system = BufferedLocalRecordingSampleSource(channelCount: 1)
        let writer = makeV5Writer(root: root, microphone: microphone, system: system)

        _ = try writer.start(
            sessionId: "levels",
            startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: writerScopeApproval(),
            permissions: writerGrantedPermissions()
        )
        appendConversation(microphone: microphone, system: system, seconds: 100)
        Thread.sleep(forTimeInterval: 0.05)
        let now = Date()
        let levels = writer.currentLevels(now: now)
        _ = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        XCTAssertTrue(levels.isRecording)
        XCTAssertGreaterThan(levels.microphoneLevel, 0)
        XCTAssertGreaterThan(levels.incomingLevel, 0)
        XCTAssertTrue(levels.microphoneIsLive(now: now, staleAfter: 2))
        XCTAssertTrue(levels.incomingIsLive(now: now, staleAfter: 2))
    }

    func testPrivacySuppressingTimestampedSourceZerosPausedMicrophoneSamples() {
        let source = BufferedLocalRecordingSampleSource(channelCount: 1)
        source.append(writerBatch(samples: [0.4, -0.2], seconds: 100))
        let privacySource = PrivacySuppressingSampleSource(base: source, state: .paused)

        let batch = privacySource.readTimestampedBatch(maximumFrameCount: 8)

        XCTAssertEqual(batch?.samples, [0, 0])
        XCTAssertEqual(batch?.presentationTime.clockDomain, .hostTime)
        XCTAssertTrue(privacySource.lastReadWasSuppressed)
        XCTAssertEqual(privacySource.suppressedSampleCount, 2)
    }

    func testCanonicalWriterFansOutOneTimelineIntoOnlyFinalV5Artifacts() throws {
        XCTAssertEqual(CanonicalRecordingWriter.reviewBitRate, 64_000)
        let root = makeWriterTestRoot("canonical-fan-out")
        defer { try? FileManager.default.removeItem(at: root) }
        let directory = try LocalRecordingStore(rootURL: root).createDirectory(sessionId: "canonical-fan-out")
        let writer = try CanonicalRecordingWriter(directory: directory)

        try writer.append(RecordingAudioTimelineChunk(
            startFrameIndex: 0,
            samples: Array(repeating: 0.4, count: 480)
        ))
        try writer.append(RecordingAudioTimelineChunk(
            startFrameIndex: 480,
            samples: Array(repeating: 0.2, count: 480)
        ))
        let artifact = try writer.finish()

        XCTAssertEqual(artifact.canonicalFrameCount, 960)
        XCTAssertEqual(artifact.transcriptionFrameCount, 320)
        XCTAssertEqual(artifact.transcriptionAudioURL, directory.transcriptionAudioURL)
        XCTAssertEqual(artifact.reviewAudioURL, directory.reviewAudioURL)
        XCTAssertEqual(
            Set(try FileManager.default.contentsOfDirectory(atPath: directory.directoryURL.path)),
            Set(["meeting-transcription.wav", "meeting-review.m4a"])
        )

        let header = try V5WAVHeader(url: directory.transcriptionAudioURL)
        XCTAssertEqual(header.audioFormat, 1)
        XCTAssertEqual(header.channelCount, 1)
        XCTAssertEqual(header.sampleRate, 16_000)
        XCTAssertEqual(header.bitsPerSample, 16)
    }

    func testCanonicalWriterCleansPartialArtifactsWhenFinalizationHasNoFrames() throws {
        let root = makeWriterTestRoot("canonical-empty")
        defer { try? FileManager.default.removeItem(at: root) }
        let directory = try LocalRecordingStore(rootURL: root).createDirectory(sessionId: "canonical-empty")
        let writer = try CanonicalRecordingWriter(directory: directory)

        XCTAssertThrowsError(try writer.finish()) { error in
            XCTAssertEqual(error as? CanonicalRecordingWriterError, .noFrames)
        }
        XCTAssertFalse(FileManager.default.fileExists(atPath: directory.transcriptionAudioURL.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: directory.reviewAudioURL.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: directory.directoryURL.appendingPathComponent("meeting-transcription.partial.wav").path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: directory.directoryURL.appendingPathComponent("meeting-review.partial.m4a").path))
    }
}

private func makeWriterTestRoot(_ name: String) -> URL {
    FileManager.default.temporaryDirectory.appendingPathComponent("\(name)-\(UUID().uuidString)", isDirectory: true)
}

private func makeV5Writer(
    root: URL,
    microphone: BufferedLocalRecordingSampleSource,
    system: BufferedLocalRecordingSampleSource
) -> LocalRecordingWriter {
    LocalRecordingWriter(
        store: LocalRecordingStore(rootURL: root),
        microphoneSampleSourceFactory: { microphone },
        incomingSampleSourceFactory: { system },
        recordMicrophone: true
    )
}

private func appendConversation(
    microphone: BufferedLocalRecordingSampleSource,
    system: BufferedLocalRecordingSampleSource,
    seconds: Double
) {
    microphone.append(writerBatch(samples: Array(repeating: 0.4, count: 4_800), seconds: seconds))
    system.append(writerBatch(samples: Array(repeating: 0.2, count: 4_800), seconds: seconds))
}

private func writerBatch(samples: [Float], seconds: Double) -> RecordingAudioBatch {
    RecordingAudioBatch(
        samples: samples,
        format: RecordingAudioFormat(sampleRate: 48_000, channelCount: 1),
        presentationTime: RecordingAudioPresentationTimestamp(seconds: seconds, clockDomain: .hostTime),
        discontinuity: .none,
        routeGeneration: 0
    )
}

private func writerScopeApproval() -> CaptureScopeApproval {
    CaptureScopeApproval(
        scopeApprovalId: "writer-scope",
        scopeKind: .display,
        sourceDisplayName: "Current Display",
        approvedAt: Date(timeIntervalSince1970: 9),
        approvalMode: .userConfirmedSuggestedScope,
        eligibleReason: .manualMeetingScope
    )
}

private func writerGrantedPermissions() -> SystemAudioPermissionSnapshot {
    SystemAudioPermissionSnapshot(
        microphone: .granted,
        systemAudio: .granted,
        evaluatedAt: Date(timeIntervalSince1970: 9)
    )
}

private struct V5WAVHeader {
    let audioFormat: UInt16
    let channelCount: UInt16
    let sampleRate: UInt32
    let bitsPerSample: UInt16

    init(url: URL) throws {
        let data = try Data(contentsOf: url)
        guard data.count >= 44 else {
            throw NSError(domain: "V5WAVHeader", code: 1)
        }
        audioFormat = data.v5UInt16LE(at: 20)
        channelCount = data.v5UInt16LE(at: 22)
        sampleRate = data.v5UInt32LE(at: 24)
        bitsPerSample = data.v5UInt16LE(at: 34)
    }
}

private extension Data {
    func v5UInt16LE(at offset: Int) -> UInt16 {
        UInt16(self[offset]) | (UInt16(self[offset + 1]) << 8)
    }

    func v5UInt32LE(at offset: Int) -> UInt32 {
        UInt32(self[offset]) |
            (UInt32(self[offset + 1]) << 8) |
            (UInt32(self[offset + 2]) << 16) |
            (UInt32(self[offset + 3]) << 24)
    }
}
#endif
