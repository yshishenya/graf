import Foundation
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LocalRecordingWriterSystemAudioTests: XCTestCase {
    func testShortRecordingThresholdUsesFramesAndOnlyNormalStops() throws {
        let root = makeSystemWriterRoot("short-threshold")
        defer { try? FileManager.default.removeItem(at: root) }
        let microphone = BufferedLocalRecordingSampleSource(channelCount: 1)
        let system = BufferedLocalRecordingSampleSource(channelCount: 1)
        let writer = makeSystemV5Writer(root: root, microphone: microphone, system: system)
        let directory = try writer.start(sessionId: "short", startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: systemScopeApproval(), permissions: systemGrantedPermissions())
        microphone.append(systemBatch(samples: Array(repeating: 0, count: 4_800), seconds: 100))
        system.append(systemBatch(samples: Array(repeating: 0.2, count: 4_800), seconds: 100))
        // Ten minutes of wall time still represents only 100 ms of audio.
        let original = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 610))
        XCTAssertTrue(original.isComplete)
        XCTAssertNil(original.shortRecordingDiscarded)
        for reason in [RecordingStopReason.userRequested, .meetingEnded] {
            for frames: Int64 in [479_999, 480_000, 480_001] {
                var manifest = original
                let index = try XCTUnwrap(manifest.tracks.firstIndex { $0.role == .mixedMeetingAudio })
                manifest.tracks[index].frameCount = frames
                manifest.applyShortRecordingPolicy(stopReason: reason)
                XCTAssertEqual(manifest.shortRecordingDiscarded == true, frames < 480_000)
            }
        }
        for reason: RecordingStopReason? in [nil, .failed, .appRestarted, .indicatorLost, .storageUnsafe] {
            var manifest = original
            manifest.applyShortRecordingPolicy(stopReason: reason)
            XCTAssertNil(manifest.shortRecordingDiscarded)
        }
        for invalidRate in [0.0, -1, Double.nan, Double.infinity, 48_000] {
            var manifest = original
            manifest.tracks[0].sampleRate = invalidRate
            manifest.applyShortRecordingPolicy(stopReason: .userRequested)
            XCTAssertNil(manifest.shortRecordingDiscarded)
        }
        var damaged = original
        damaged.captureFailureCode = "recording_recovered_after_interruption"
        damaged.applyShortRecordingPolicy(stopReason: .userRequested)
        XCTAssertNil(damaged.shortRecordingDiscarded)
        var missingFrames = original
        missingFrames.tracks[0].frameCount = 0
        missingFrames.applyShortRecordingPolicy(stopReason: .userRequested)
        XCTAssertNil(missingFrames.shortRecordingDiscarded)
        XCTAssertNil(try LocalRecordingManifestService().read(from: directory.manifestURL).shortRecordingDiscarded)
    }

    func testShortRecordingDecisionIsPublishedWithFinalManifest() async throws {
        for reason in [RecordingStopReason.userRequested, .meetingEnded, .failed] {
            let root = makeSystemWriterRoot("short-final")
            defer { try? FileManager.default.removeItem(at: root) }
            let microphone = BufferedLocalRecordingSampleSource(channelCount: 1)
            let system = BufferedLocalRecordingSampleSource(channelCount: 1)
            let writer = makeSystemV5Writer(root: root, microphone: microphone, system: system)
            let directory = try writer.start(sessionId: "short", startedAt: Date(timeIntervalSince1970: 10),
                scopeApproval: systemScopeApproval(), permissions: systemGrantedPermissions())
            microphone.append(systemBatch(samples: Array(repeating: 0, count: 4_800), seconds: 100))
            system.append(systemBatch(samples: Array(repeating: 0.2, count: 4_800), seconds: 100))
            let manifest = try await writer.stopAsync(stopReason: reason)
            XCTAssertEqual(manifest.shortRecordingDiscarded == true, reason != .failed)
            let persisted = try LocalRecordingManifestService().read(from: directory.manifestURL)
            XCTAssertEqual(persisted.shortRecordingDiscarded, manifest.shortRecordingDiscarded)
            XCTAssertEqual(persisted.status, manifest.status)
            XCTAssertEqual(persisted.tracks, manifest.tracks)
            XCTAssertTrue(FileManager.default.fileExists(atPath: directory.transcriptionAudioURL.path))
            if reason != .failed { XCTAssertEqual(manifest.status, .blocked) }
        }
    }

    func testShortRecordingBoundaryKeepsThirtySecondsFromTheFirstFrame() async throws {
        let root = makeSystemWriterRoot("thirty-seconds")
        defer { try? FileManager.default.removeItem(at: root) }
        let frameCount = 1_440_000
        let microphone = BufferedLocalRecordingSampleSource(capacity: frameCount, channelCount: 1)
        let system = BufferedLocalRecordingSampleSource(capacity: frameCount, channelCount: 1)
        let writer = makeSystemV5Writer(root: root, microphone: microphone, system: system)
        let directory = try writer.start(sessionId: "thirty", startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: systemScopeApproval(), permissions: systemGrantedPermissions())
        for second in stride(from: 0, to: 30, by: 5) {
            microphone.append(systemBatch(samples: Array(repeating: 0, count: 240_000), seconds: Double(100 + second)))
            system.append(systemBatch(samples: Array(repeating: 0.2, count: 240_000), seconds: Double(100 + second)))
            try await Task.sleep(for: .milliseconds(200))
        }
        let manifest = try writer.stop(stopReason: .userRequested)
        XCTAssertTrue(manifest.isComplete)
        XCTAssertNil(manifest.shortRecordingDiscarded)
        let audio = try XCTUnwrap(manifest.tracks.first { $0.role == .mixedMeetingAudio })
        XCTAssertEqual(audio.frameCount, 480_000)
        XCTAssertEqual(audio.timelineStartMs, 0)
        let wav = try Data(contentsOf: directory.transcriptionAudioURL)
        XCTAssertEqual(wav.count, 44 + 480_000 * 2)
        XCTAssertTrue(wav.dropFirst(44).prefix(3_200).contains { $0 != 0 })
    }

    func testShortRecordingInterruptionDuringStopPreservesAudio() async throws {
        let root = makeSystemWriterRoot("short-interrupted-stop")
        defer { try? FileManager.default.removeItem(at: root) }
        let microphone = BufferedLocalRecordingSampleSource(channelCount: 1)
        let system = InterruptingShortRecordingSource()
        let writer = LocalRecordingWriter(store: LocalRecordingStore(rootURL: root),
            microphoneSampleSourceFactory: { microphone }, incomingSampleSourceFactory: { system }, recordMicrophone: true)
        let directory = try writer.start(sessionId: "interrupted-stop", startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: systemScopeApproval(), permissions: systemGrantedPermissions())
        microphone.append(systemBatch(samples: Array(repeating: 0, count: 4_800), seconds: 100))
        system.base.append(systemBatch(samples: Array(repeating: 0.2, count: 4_800), seconds: 100))
        system.writer = writer
        let manifest = try await writer.stopAsync(stopReason: .userRequested)
        XCTAssertTrue(manifest.isComplete)
        XCTAssertNil(manifest.shortRecordingDiscarded)
        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.transcriptionAudioURL.path))
    }

    func testWriterUsesPTSInsteadOfWallClockStopPadding() throws {
        let root = makeSystemWriterRoot("v5-pts-duration")
        defer { try? FileManager.default.removeItem(at: root) }
        let microphone = BufferedLocalRecordingSampleSource(channelCount: 1)
        let system = BufferedLocalRecordingSampleSource(channelCount: 1)
        let writer = makeSystemV5Writer(root: root, microphone: microphone, system: system)

        _ = try writer.start(
            sessionId: "pts-duration",
            startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: systemScopeApproval(),
            permissions: systemGrantedPermissions()
        )
        microphone.append(systemBatch(samples: Array(repeating: 0.4, count: 4_800), seconds: 100))
        system.append(systemBatch(samples: Array(repeating: 0.2, count: 4_800), seconds: 100))
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 20))

        let media = try XCTUnwrap(manifest.tracks.first { $0.role == .mixedMeetingAudio })
        let playback = try XCTUnwrap(manifest.tracks.first { $0.role == .reviewPlayback })
        XCTAssertEqual(media.durationMs, 100)
        XCTAssertLessThan(playback.durationMs, 250)
        XCTAssertLessThanOrEqual(manifest.durationDifferenceSeconds, 0.1)
        XCTAssertTrue(manifest.isComplete)
    }

    func testExternalFailurePreservesPublishedAudioBeforeWritingFailedManifest() throws {
        let root = makeSystemWriterRoot("v5-manual-failure")
        defer { try? FileManager.default.removeItem(at: root) }
        let microphone = BufferedLocalRecordingSampleSource(channelCount: 1)
        let system = BufferedLocalRecordingSampleSource(channelCount: 1)
        let writer = makeSystemV5Writer(root: root, microphone: microphone, system: system)

        let directory = try writer.start(
            sessionId: "manual-failure",
            startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: systemScopeApproval(),
            permissions: systemGrantedPermissions()
        )
        microphone.append(systemBatch(samples: Array(repeating: 0.4, count: 4_800), seconds: 100))
        system.append(systemBatch(samples: Array(repeating: 0.2, count: 4_800), seconds: 100))
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11), failureReason: .captureFailed, stopReason: .userRequested)

        XCTAssertEqual(manifest.status, .failed)
        XCTAssertEqual(manifest.failureReason, .captureFailed)
        XCTAssertFalse(manifest.isComplete)
        XCTAssertEqual(manifest.echoProcessingHealth?.state, .degraded)
        XCTAssertEqual(manifest.echoProcessingHealth?.reason, .sourceStopped)
        XCTAssertEqual(manifest.echoProcessingHealth?.processedFrameCount, 10)
        XCTAssertEqual(
            Set(try FileManager.default.contentsOfDirectory(atPath: directory.directoryURL.path)),
            Set(["manifest.json", "meeting-transcription.wav", "meeting-review.m4a"])
        )
        XCTAssertGreaterThan(try Data(contentsOf: directory.transcriptionAudioURL).count, 44)
        XCTAssertGreaterThan(try Data(contentsOf: directory.reviewAudioURL).count, 0)
    }

    func testLegacyTimelineFailureKeepsAudioLocalButBlocksUpload() throws {
        let root = makeSystemWriterRoot("v5-timeline-warning")
        defer { try? FileManager.default.removeItem(at: root) }
        let microphone = BufferedLocalRecordingSampleSource(channelCount: 1)
        let system = BufferedLocalRecordingSampleSource(channelCount: 1)
        let writer = makeSystemV5Writer(root: root, microphone: microphone, system: system)

        let directory = try writer.start(
            sessionId: "timeline-warning",
            startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: systemScopeApproval(),
            permissions: systemGrantedPermissions()
        )
        microphone.append(systemBatch(samples: Array(repeating: 0.4, count: 4_800), seconds: 100))
        system.append(systemBatch(samples: Array(repeating: 0.2, count: 4_800), seconds: 100))
        let manifest = try writer.stop(
            stoppedAt: Date(timeIntervalSince1970: 11),
            failureReason: .timelineMisaligned
        )

        let profile = DesktopUploadQueueService.artifactProfile(
            manifest: manifest,
            manifestURL: directory.manifestURL,
            microphoneURL: directory.directoryURL.appendingPathComponent("mic.wav"),
            systemAudioURL: directory.directoryURL.appendingPathComponent("incoming.wav"),
            reviewAudioURL: directory.reviewAudioURL,
            transcriptionURL: directory.transcriptionAudioURL
        )

        XCTAssertFalse(manifest.isComplete)
        XCTAssertEqual(manifest.failureReason, .captureFailed)
        XCTAssertNil(profile.qualityWarningReason)
        XCTAssertFalse(profile.isUploadable)
    }

    func testTimestampedQueueOverflowFailsWithoutPublishingPartialPackage() throws {
        let root = makeSystemWriterRoot("v5-overflow")
        defer { try? FileManager.default.removeItem(at: root) }
        let microphone = BufferedLocalRecordingSampleSource(channelCount: 1)
        let system = BufferedLocalRecordingSampleSource(capacity: 4_800, channelCount: 1)
        let writer = makeSystemV5Writer(root: root, microphone: microphone, system: system)

        let directory = try writer.start(
            sessionId: "overflow",
            startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: systemScopeApproval(),
            permissions: systemGrantedPermissions()
        )
        microphone.append(systemBatch(samples: Array(repeating: 0.4, count: 4_800), seconds: 100))
        system.append(systemBatch(samples: Array(repeating: 0.2, count: 9_600), seconds: 100))
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        XCTAssertEqual(manifest.status, .failed)
        XCTAssertEqual(manifest.failureReason, .writeFailed)
        XCTAssertFalse(manifest.isComplete)
        XCTAssertEqual(manifest.echoProcessingHealth?.state, .degraded)
        XCTAssertEqual(manifest.echoProcessingHealth?.reason, .sourceOverflow)
        XCTAssertEqual(manifest.echoProcessingHealth?.processedFrameCount, 0)
        XCTAssertEqual(
            Set(try FileManager.default.contentsOfDirectory(atPath: directory.directoryURL.path)),
            Set(["manifest.json"])
        )
        XCTAssertFalse(FileManager.default.fileExists(atPath: directory.transcriptionAudioURL.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: directory.reviewAudioURL.path))
    }

    func testStopBoundsAnUnboundedTimestampedSourceWithoutPublishingUnprocessedBuffers() throws {
        let root = makeSystemWriterRoot("v5-infinite")
        defer { try? FileManager.default.removeItem(at: root) }
        let microphone = BufferedLocalRecordingSampleSource(channelCount: 1)
        let system = InfiniteTimestampedSampleSource()
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            microphoneSampleSourceFactory: { microphone },
            incomingSampleSourceFactory: { system },
            recordMicrophone: true
        )

        let directory = try writer.start(
            sessionId: "infinite",
            startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: systemScopeApproval(),
            permissions: systemGrantedPermissions()
        )
        microphone.append(systemBatch(samples: Array(repeating: 0.4, count: 4_800), seconds: 100))
        let started = Date()
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        XCTAssertLessThan(Date().timeIntervalSince(started), 2)
        XCTAssertEqual(manifest.failureReason, .writeFailed)
        XCTAssertEqual(manifest.status, .failed)
        XCTAssertFalse(writer.isRecording)
        XCTAssertEqual(manifest.echoProcessingHealth?.state, .degraded)
        XCTAssertEqual(manifest.echoProcessingHealth?.reason, .sourceOverflow)
        XCTAssertEqual(manifest.echoProcessingHealth?.processedFrameCount, 0)
        XCTAssertEqual(
            Set(try FileManager.default.contentsOfDirectory(atPath: directory.directoryURL.path)),
            Set(["manifest.json"])
        )
        XCTAssertFalse(FileManager.default.fileExists(atPath: directory.transcriptionAudioURL.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: directory.reviewAudioURL.path))
    }

    func testBufferedSourceSplitsBatchesWithTheirOriginalPTS() throws {
        let source = BufferedLocalRecordingSampleSource(channelCount: 1)
        source.append(systemBatch(samples: Array(repeating: 0.2, count: 10), seconds: 100))

        let first = source.readTimestampedBatch(maximumFrameCount: 4)
        let second = source.readTimestampedBatch(maximumFrameCount: 4)
        let third = source.readTimestampedBatch(maximumFrameCount: 4)

        let firstBatch = try XCTUnwrap(first)
        let secondBatch = try XCTUnwrap(second)
        let thirdBatch = try XCTUnwrap(third)
        XCTAssertEqual(firstBatch.samples.count, 4)
        XCTAssertEqual(secondBatch.samples.count, 4)
        XCTAssertEqual(thirdBatch.samples.count, 2)
        XCTAssertEqual(firstBatch.presentationTime.seconds, 100)
        XCTAssertEqual(secondBatch.presentationTime.seconds, 100 + 4.0 / 48_000, accuracy: 0.000_000_001)
        XCTAssertEqual(thirdBatch.presentationTime.seconds, 100 + 8.0 / 48_000, accuracy: 0.000_000_001)
        XCTAssertFalse(source.hasTimestampedOverflow)
    }

    func testCanonicalWriterFlushKeepsDownsampledWavOnTheSameTimeline() throws {
        let root = makeSystemWriterRoot("canonical-flush")
        defer { try? FileManager.default.removeItem(at: root) }
        let directory = try LocalRecordingStore(rootURL: root).createDirectory(sessionId: "canonical-flush")
        let writer = try CanonicalRecordingWriter(directory: directory)

        try writer.append(RecordingAudioTimelineChunk(
            startFrameIndex: 0,
            samples: Array(repeating: 0.35, count: 4_800)
        ))
        let artifact = try writer.finish()

        XCTAssertEqual(artifact.canonicalFrameCount, 4_800)
        XCTAssertEqual(artifact.transcriptionFrameCount, 1_600)
        XCTAssertEqual(artifact.transcriptionDurationMs, 100)
        XCTAssertTrue(FileManager.default.fileExists(atPath: artifact.reviewAudioURL.path))
    }
}

private func makeSystemWriterRoot(_ name: String) -> URL {
    FileManager.default.temporaryDirectory.appendingPathComponent("\(name)-\(UUID().uuidString)", isDirectory: true)
}

private func makeSystemV5Writer(
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

private func systemBatch(samples: [Float], seconds: Double) -> RecordingAudioBatch {
    RecordingAudioBatch(
        samples: samples,
        format: RecordingAudioFormat(sampleRate: 48_000, channelCount: 1),
        presentationTime: RecordingAudioPresentationTimestamp(seconds: seconds, clockDomain: .hostTime),
        discontinuity: .none,
        routeGeneration: 0
    )
}

private func systemScopeApproval() -> CaptureScopeApproval {
    CaptureScopeApproval(
        scopeApprovalId: "system-writer-scope",
        scopeKind: .display,
        sourceDisplayName: "Current Display",
        approvedAt: Date(timeIntervalSince1970: 9),
        approvalMode: .userConfirmedSuggestedScope,
        eligibleReason: .manualMeetingScope
    )
}

private func systemGrantedPermissions() -> SystemAudioPermissionSnapshot {
    SystemAudioPermissionSnapshot(
        microphone: .granted,
        systemAudio: .granted,
        evaluatedAt: Date(timeIntervalSince1970: 9)
    )
}

private final class InterruptingShortRecordingSource: TimestampedLocalRecordingSampleSource, @unchecked Sendable {
    let base = BufferedLocalRecordingSampleSource(channelCount: 1)
    private let lock = NSLock()
    private weak var storedWriter: LocalRecordingWriter?
    var writer: LocalRecordingWriter? {
        get { lock.withLock { storedWriter } }
        set { lock.withLock { storedWriter = newValue } }
    }
    var hasTimestampedOverflow: Bool { base.hasTimestampedOverflow }
    func readTimestampedBatch(maximumFrameCount: Int) -> RecordingAudioBatch? {
        writer?.preserveRecordingForInterruption()
        return base.readTimestampedBatch(maximumFrameCount: maximumFrameCount)
    }
}

private final class InfiniteTimestampedSampleSource: TimestampedLocalRecordingSampleSource, @unchecked Sendable {
    private let lock = NSLock()
    private var nextTimestamp: Double = 100

    func readTimestampedBatch(maximumFrameCount: Int) -> RecordingAudioBatch? {
        lock.lock()
        defer { lock.unlock() }
        let timestamp = nextTimestamp
        nextTimestamp += 1.0 / 48_000
        return systemBatch(samples: [0.2], seconds: timestamp)
    }

    var hasTimestampedOverflow: Bool { false }
}
#endif
