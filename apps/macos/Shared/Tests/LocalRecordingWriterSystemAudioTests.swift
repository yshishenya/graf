import AVFoundation
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
            for frames: Int64 in [1_439_999, 1_440_000, 1_440_001] {
                var manifest = original
                let index = try XCTUnwrap(manifest.tracks.firstIndex { $0.role == .reviewPlayback })
                manifest.tracks[index].frameCount = frames + (try XCTUnwrap(manifest.tracks[index].aacPresentationFrameDelta))
                manifest.applyShortRecordingPolicy(stopReason: reason)
                XCTAssertEqual(manifest.shortRecordingDiscarded == true, frames < 1_440_000)
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
        let playbackIndex = try XCTUnwrap(original.tracks.firstIndex { $0.role == .reviewPlayback })
        for delta: Int64? in [nil, Int64.min, Int64.max, -4_801, 4_801] {
            var manifest = original
            manifest.tracks[playbackIndex].aacPresentationFrameDelta = delta
            manifest.applyShortRecordingPolicy(stopReason: .userRequested)
            XCTAssertNil(manifest.shortRecordingDiscarded)
        }
        for (frames, delta): (Int64, Int64) in [(Int64.max, -1), (1, 1), (1, 2)] {
            var manifest = original
            manifest.tracks[playbackIndex].frameCount = frames
            manifest.tracks[playbackIndex].aacPresentationFrameDelta = delta
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
        for reason in [RecordingStopReason.userRequested, .meetingEnded] {
            for frameCount in [1_439_999, 1_440_000, 1_440_001] {
                let root = makeSystemWriterRoot("thirty-seconds")
                defer { try? FileManager.default.removeItem(at: root) }
                let microphone = DrainAcknowledgedSampleSource()
                let system = DrainAcknowledgedSampleSource()
                let writer = makeSystemV5Writer(root: root, microphone: microphone, system: system)
                let directory = try writer.start(sessionId: "thirty", startedAt: Date(timeIntervalSince1970: 10),
                    scopeApproval: systemScopeApproval(), permissions: systemGrantedPermissions())
                for offset in stride(from: 0, to: frameCount, by: 240_000) {
                    let count = min(240_000, frameCount - offset)
                    let seconds = 100 + Double(offset) / 48_000
                    let drained = expectation(description: "Both synthetic source chunks were processed")
                    drained.expectedFulfillmentCount = 2
                    microphone.append(systemBatch(samples: Array(repeating: 0, count: count), seconds: seconds), drained: drained)
                    system.append(systemBatch(samples: Array(repeating: 0.2, count: count), seconds: seconds), drained: drained)
                    await fulfillment(of: [drained], timeout: 10)
                }
                let manifest = try writer.stop(stopReason: reason)
                XCTAssertNil(manifest.captureFailureCode)
                let discarded = frameCount < 1_440_000
                XCTAssertEqual(manifest.shortRecordingDiscarded == true, discarded, "frames=\(frameCount), reason=\(reason)")
                XCTAssertEqual(manifest.status, discarded ? .blocked : .saved)
                let persisted = try LocalRecordingManifestService().read(from: directory.manifestURL)
                XCTAssertEqual(persisted.shortRecordingDiscarded, manifest.shortRecordingDiscarded)
                let playback = try XCTUnwrap(manifest.tracks.first { $0.role == .reviewPlayback })
                XCTAssertEqual(playback.frameCount - (try XCTUnwrap(playback.aacPresentationFrameDelta)), Int64(frameCount))
                let audio = try XCTUnwrap(manifest.tracks.first { $0.role == .mixedMeetingAudio })
                XCTAssertEqual(audio.frameCount, 480_000) // All three round to the same 16 kHz count.
                XCTAssertEqual(audio.timelineStartMs, 0)
                let wav = try Data(contentsOf: directory.transcriptionAudioURL)
                XCTAssertEqual(wav.count, 44 + 480_000 * 2)
                XCTAssertTrue(wav.dropFirst(44).prefix(3_200).contains { $0 != 0 })
            }
        }
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

    func testLiveDrainOrdersUnequalNativeBatchesWithoutArtificialTimelineOverflow() async throws {
        try await verifyNativeBatchBacklog(microphoneBatchFrames: 512, systemBatchFrames: 4_096)
    }

    func testLiveDrainAlsoOrdersLargeMicrophoneAndSmallSystemBatches() async throws {
        try await verifyNativeBatchBacklog(microphoneBatchFrames: 4_096, systemBatchFrames: 512)
    }

    func testLiveWriterPauseAtRetainedBatchBoundaryKeepsFullTimeline() async throws {
        let control = PendingMicrophonePrivacyControl()
        try await verifyNativeBatchBacklog(microphoneBatchFrames: 512, systemBatchFrames: 4_096, privacyControl: control)
        XCTAssertTrue(control.didPauseAndResume)
        XCTAssertGreaterThan(control.pendingFrameCount, 0)
        XCTAssertLessThanOrEqual(control.pendingFrameCount, 8_192)
    }

    private func verifyNativeBatchBacklog(microphoneBatchFrames: Int, systemBatchFrames: Int,
                                         privacyControl: PendingMicrophonePrivacyControl? = nil) async throws {
        let root = makeSystemWriterRoot("v5-native-batch-backlog")
        defer { try? FileManager.default.removeItem(at: root) }
        // Physical microphone capacity is 30 seconds mono; system capacity is
        // 10 seconds stereo. The backlog models delayed callbacks, not loss.
        let microphone = BackloggedMicrophoneSource()
        let totalFrames = 48_000 * 25
        for offset in stride(from: 0, to: totalFrames, by: microphoneBatchFrames) {
            microphone.append(systemBatch(
                samples: Array(repeating: 0.05, count: min(microphoneBatchFrames, totalFrames - offset)),
                seconds: 100 + Double(offset) / 48_000
            ))
        }
        let system = DelayedContinuousSystemSource(totalFrames: totalFrames, batchFrames: systemBatchFrames)
        let writer = LocalRecordingWriter(store: LocalRecordingStore(rootURL: root),
            microphoneSampleSourceFactory: { microphone }, incomingSampleSourceFactory: { system },
            diagnosticLogger: { privacyControl?.observe($0) })
        privacyControl?.writer = writer
        let directory = try writer.start(sessionId: "native-backlog", startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: systemScopeApproval(), permissions: systemGrantedPermissions())

        let deadline = Date().addingTimeInterval(15)
        var failure: String?
        repeat {
            failure = await writer.currentLevelsAsync().integrityFailureCode
            if failure != nil || (system.isDrained && microphone.readableFrameCountForTest == 0) { break }
            try await Task.sleep(nanoseconds: 10_000_000)
        } while Date() < deadline
        XCTAssertNil(failure, "Continuous native batches must not overflow merely because their sizes differ")
        XCTAssertTrue(system.isDrained)
        XCTAssertFalse(microphone.hasTimestampedOverflow)
        XCTAssertFalse(system.hasTimestampedOverflow)
        let manifest = try await writer.stopAsync(stoppedAt: Date(timeIntervalSince1970: 35))
        XCTAssertTrue(manifest.isComplete)
        XCTAssertEqual(manifest.failureReason, .none)
        XCTAssertEqual(manifest.echoProcessingHealth?.hostOverrunCount, 0)
        if privacyControl != nil { XCTAssertEqual(manifest.privacySegments?.count, 1) }
        let transcription = try XCTUnwrap(manifest.tracks.first { $0.role == .mixedMeetingAudio })
        let playback = try XCTUnwrap(manifest.tracks.first { $0.role == .reviewPlayback })
        XCTAssertEqual(transcription.frameCount, 16_000 * 25)
        XCTAssertEqual(transcription.durationMs, 25_000)
        XCTAssertLessThanOrEqual(abs(playback.durationMs - 25_000), 100)
        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.transcriptionAudioURL.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.reviewAudioURL.path))
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

    func testStopKeepsFinitePerSourceLimitWhenBothSourcesProduceSmallBatchesForever() async throws {
        let root = makeSystemWriterRoot("v5-small-infinite")
        defer { try? FileManager.default.removeItem(at: root) }
        let writer = makeSystemV5Writer(root: root,
            microphone: InfiniteTimestampedSampleSource(), system: InfiniteTimestampedSampleSource())
        _ = try await writer.startAsync(sessionId: "small-infinite", startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: systemScopeApproval(), permissions: systemGrantedPermissions())
        let manifest = try await writer.stopAsync(stoppedAt: Date(timeIntervalSince1970: 11))
        XCTAssertEqual(manifest.status, .failed)
        XCTAssertEqual(manifest.captureFailureCode, "stop_drain_limit_exceeded")
        XCTAssertFalse(manifest.isComplete)
        XCTAssertFalse(writer.isRecording)
    }

    func testWriterRejectsIncomparableClocksBeforePendingBatchOrdering() async throws {
        for microphoneFirst in [true, false] {
            let root = makeSystemWriterRoot("v5-incomparable-clock")
            defer { try? FileManager.default.removeItem(at: root) }
            let microphone = BufferedLocalRecordingSampleSource(channelCount: 1)
            let system = BufferedLocalRecordingSampleSource(channelCount: 1)
            microphone.append(systemBatch(samples: Array(repeating: 0.1, count: 480), seconds: microphoneFirst ? 100 : 200))
            system.append(RecordingAudioBatch(samples: Array(repeating: 0.2, count: 480),
                format: RecordingAudioFormat(sampleRate: 48_000, channelCount: 1),
                presentationTime: RecordingAudioPresentationTimestamp(seconds: microphoneFirst ? 200 : 100, clockDomain: .wallClock)))
            let writer = makeSystemV5Writer(root: root, microphone: microphone, system: system)
            _ = try await writer.startAsync(sessionId: "clock", startedAt: Date(timeIntervalSince1970: 10),
                scopeApproval: systemScopeApproval(), permissions: systemGrantedPermissions())
            let manifest = try await writer.stopAsync(stoppedAt: Date(timeIntervalSince1970: 11))
            XCTAssertEqual(manifest.captureFailureCode, "uncomparable_presentation_times")
            XCTAssertFalse(manifest.isComplete)
            XCTAssertEqual(manifest.echoProcessingHealth?.reason, .timebaseChanged)
        }
    }

    func testInvalidPendingTimestampCannotWaitBehindValidSource() async throws {
        for invalidTime in [Double.nan, Double.infinity, -Double.infinity] {
            let root = makeSystemWriterRoot("v5-invalid-pending")
            defer { try? FileManager.default.removeItem(at: root) }
            let microphone = BufferedLocalRecordingSampleSource(channelCount: 1)
            microphone.append(systemBatch(samples: [0.1], seconds: invalidTime))
            let writer = makeSystemV5Writer(root: root, microphone: microphone, system: InfiniteTimestampedSampleSource())
            _ = try await writer.startAsync(sessionId: "invalid-time", startedAt: Date(timeIntervalSince1970: 10),
                scopeApproval: systemScopeApproval(), permissions: systemGrantedPermissions())
            let manifest = try await writer.stopAsync(stoppedAt: Date(timeIntervalSince1970: 11))
            XCTAssertEqual(manifest.captureFailureCode, "invalid_timestamp")
            XCTAssertFalse(manifest.isComplete)
        }
    }

    func testPauseSilencesPrefetchedMicrophoneOnceAndResumeKeepsItsTimeline() throws {
        let microphone = BufferedLocalRecordingSampleSource(channelCount: 1)
        let privacy = PrivacySuppressingSampleSource(base: microphone)
        var output: [Float] = []
        let timeline = RecordingAudioTimeline(configuration: .init(reorderWindowFrames: 0),
            processEchoFrame: { _, microphone in microphone }, frameSink: { output += $0.samples })
        for offset in 0..<3 {
            microphone.append(systemBatch(samples: Array(repeating: 0.1, count: 480), seconds: 100 + Double(offset) * 0.01))
        }
        let first = try XCTUnwrap(privacy.readTimestampedBatch(maximumFrameCount: 8_192))
        try timeline.append(source: .microphone, batch: first)
        try timeline.append(source: .systemAudio, batch: systemBatch(samples: Array(repeating: 0, count: 480), seconds: 100))
        // This is the same retained bounded batch consumed by the writer after
        // its next control operation, rather than another read from the source.
        let prefetched = try XCTUnwrap(privacy.readTimestampedBatch(maximumFrameCount: 8_192))
        privacy.update(state: .paused)
        let pending = privacy.suppressPrefetchedBatch(prefetched)
        XCTAssertEqual(pending.samples, Array(repeating: 0, count: 480))
        XCTAssertEqual(pending.presentationTime, prefetched.presentationTime)
        XCTAssertEqual(pending.format, prefetched.format)
        XCTAssertEqual(pending.discontinuity, prefetched.discontinuity)
        XCTAssertEqual(pending.routeGeneration, prefetched.routeGeneration)
        XCTAssertEqual(privacy.suppressPrefetchedBatch(pending).samples, pending.samples)
        XCTAssertEqual(privacy.suppressedSampleCount, 480)
        privacy.update(state: .capturing)
        try timeline.append(source: .microphone, batch: pending)
        try timeline.append(source: .systemAudio, batch: systemBatch(samples: Array(repeating: 0, count: 480), seconds: 100.01))
        let resumed = try XCTUnwrap(privacy.readTimestampedBatch(maximumFrameCount: 8_192))
        try timeline.append(source: .microphone, batch: resumed)
        try timeline.append(source: .systemAudio, batch: systemBatch(samples: Array(repeating: 0, count: 480), seconds: 100.02))
        try timeline.finish()
        XCTAssertEqual(output.count, 1_440)
        XCTAssertTrue(output[480..<960].allSatisfy { $0 == 0 })
        // The third batch was also already queued when resume ran.
        XCTAssertTrue(output[960...].allSatisfy { $0 == 0 })
        XCTAssertEqual(timeline.metrics.ptsGapCount, 0)
        XCTAssertEqual(timeline.metrics.hostOverrunCount, 0)
    }

    func testPrivacyResumeSilencesEveryQueuedBatchAndRestoresNewFrames() throws {
        let microphone = BufferedLocalRecordingSampleSource(channelCount: 1)
        let privacy = PrivacySuppressingSampleSource(base: microphone)
        privacy.update(state: .paused)
        for offset in 0..<3 {
            microphone.append(systemBatch(samples: [0.4, 0.5], seconds: 100 + Double(offset * 2) / 48_000))
        }
        privacy.update(state: .capturing)
        microphone.append(systemBatch(samples: [0.6, 0.7], seconds: 100 + 6.0 / 48_000))
        for offset in 0..<3 {
            let batch = try XCTUnwrap(privacy.readTimestampedBatch(maximumFrameCount: 8))
            XCTAssertEqual(batch.samples, [0, 0])
            XCTAssertEqual(batch.presentationTime.seconds, 100 + Double(offset * 2) / 48_000)
            XCTAssertEqual(batch.format.channelCount, 1)
        }
        XCTAssertEqual(privacy.readTimestampedBatch(maximumFrameCount: 8)?.samples, [0.6, 0.7])
        XCTAssertEqual(privacy.suppressedSampleCount, 6)
        XCTAssertFalse(privacy.lastReadWasSuppressed)
    }

    func testPrivacyResumeBoundarySplitsStereoBatchAndPrefetchCountsOnlyUnsilencedSamples() throws {
        let microphone = CoalescedPrivacySampleSource()
        let privacy = PrivacySuppressingSampleSource(base: microphone)
        microphone.append([0.1, 0.2, 0.3, 0.4])
        privacy.update(state: .paused)
        privacy.update(state: .resuming)
        privacy.update(state: .capturing)
        microphone.append([0.5, 0.6, 0.7, 0.8])
        let partial = try XCTUnwrap(privacy.readTimestampedBatch(maximumFrameCount: 3))
        XCTAssertEqual(partial.samples, [0, 0, 0, 0, 0.5, 0.6])
        XCTAssertTrue(privacy.lastReadWasSuppressed)
        XCTAssertEqual(privacy.suppressedSampleCount, 4)
        XCTAssertEqual(partial.presentationTime.observedHostTimeSeconds, 123)
        XCTAssertEqual(partial.routeGeneration, 7)
        privacy.update(state: .paused)
        let pending = privacy.suppressPrefetchedBatch(partial)
        XCTAssertEqual(pending.samples, Array(repeating: 0, count: 6))
        XCTAssertEqual(privacy.suppressedSampleCount, 6)
        _ = privacy.suppressPrefetchedBatch(pending)
        XCTAssertEqual(privacy.suppressedSampleCount, 6)
        privacy.update(state: .capturing)
        microphone.append([0.9, 1.0])
        let rest = try XCTUnwrap(privacy.readTimestampedBatch(maximumFrameCount: 8))
        XCTAssertEqual(rest.samples, [0, 0, 0.9, 1.0])
        XCTAssertEqual(rest.presentationTime.seconds, 100 + 3.0 / 48_000)
        XCTAssertEqual(rest.format, partial.format)
        XCTAssertEqual(privacy.suppressedSampleCount, 8)
    }

    func testRepeatedPrivacyPauseReplacesRemainingQueueBoundary() throws {
        let microphone = BufferedLocalRecordingSampleSource(channelCount: 1)
        let privacy = PrivacySuppressingSampleSource(base: microphone)
        privacy.update(state: .paused)
        microphone.append(systemBatch(samples: Array(repeating: 0.4, count: 6), seconds: 100))
        privacy.update(state: .capturing)
        XCTAssertEqual(privacy.readTimestampedBatch(maximumFrameCount: 2)?.samples, [0, 0])
        privacy.update(state: .paused)
        microphone.append(systemBatch(samples: [0.5, 0.6], seconds: 100 + 6.0 / 48_000))
        XCTAssertEqual(privacy.readTimestampedBatch(maximumFrameCount: 1)?.samples, [0])
        privacy.update(state: .capturing)
        microphone.append(systemBatch(samples: [0.7, 0.8], seconds: 100 + 8.0 / 48_000))
        XCTAssertEqual(privacy.readTimestampedBatch(maximumFrameCount: 8)?.samples, [0, 0, 0])
        XCTAssertEqual(privacy.readTimestampedBatch(maximumFrameCount: 8)?.samples, [0, 0])
        XCTAssertEqual(privacy.readTimestampedBatch(maximumFrameCount: 8)?.samples, [0.7, 0.8])
        XCTAssertEqual(privacy.suppressedSampleCount, 8)
    }

    func testConcurrentResumeCannotUnmuteAnInFlightPausedRead() throws {
        let microphone = BlockingPrivacySampleSource()
        let privacy = PrivacySuppressingSampleSource(base: microphone, state: .paused)
        let result = PrivacyReadResult()
        let readFinished = DispatchSemaphore(value: 0)
        let resumeStarted = DispatchSemaphore(value: 0)
        let resumeFinished = DispatchSemaphore(value: 0)
        DispatchQueue.global().async {
            result.set(privacy.readTimestampedBatch(maximumFrameCount: 4))
            readFinished.signal()
        }
        XCTAssertEqual(microphone.readEntered.wait(timeout: .now() + 2), .success)
        DispatchQueue.global().async {
            resumeStarted.signal()
            privacy.update(state: .capturing)
            resumeFinished.signal()
        }
        XCTAssertEqual(resumeStarted.wait(timeout: .now() + 2), .success)
        XCTAssertEqual(resumeFinished.wait(timeout: .now() + 0.05), .timedOut)
        microphone.releaseRead.signal()
        XCTAssertEqual(readFinished.wait(timeout: .now() + 2), .success)
        XCTAssertEqual(resumeFinished.wait(timeout: .now() + 2), .success)
        XCTAssertEqual(result.batch?.samples, [0, 0, 0, 0])
        microphone.base.append(systemBatch(samples: [0.6], seconds: 100 + 4.0 / 48_000))
        XCTAssertEqual(privacy.readTimestampedBatch(maximumFrameCount: 4)?.samples, [0.6])
        XCTAssertEqual(privacy.suppressedSampleCount, 4)
    }

    func testPrivacyWithoutExactQueueBoundaryRemainsMutedDespiteContinuousProducer() throws {
        for resumeState in [ProductPrivacyControlState.capturing, .resuming] {
            let privacy = PrivacySuppressingSampleSource(base: InfiniteTimestampedSampleSource())
            privacy.update(state: .paused)
            XCTAssertFalse(privacy.update(state: resumeState))
            for _ in 0..<256 {
                XCTAssertEqual(privacy.readTimestampedBatch(maximumFrameCount: 8)?.samples, [0])
            }
            XCTAssertEqual(privacy.suppressedSampleCount, 256)
        }
    }

    func testProducerAppendCannotCrossResumeSnapshotAndStateBoundary() throws {
        let microphone = ProducerResumeBoundarySource()
        let privacy = PrivacySuppressingSampleSource(base: microphone, state: .paused)
        let result = PrivacyResumeResult()
        let resumeFinished = DispatchSemaphore(value: 0)
        let appendStarted = DispatchSemaphore(value: 0)
        let appendFinished = DispatchSemaphore(value: 0)
        DispatchQueue.global().async {
            result.set(privacy.update(state: .capturing))
            resumeFinished.signal()
        }
        XCTAssertEqual(microphone.boundaryEntered.wait(timeout: .now() + 2), .success)
        DispatchQueue.global().async {
            appendStarted.signal()
            microphone.appendFromProducer([0.5, 0.5], at: 100 + 2.0 / 48_000)
            appendFinished.signal()
        }
        XCTAssertEqual(appendStarted.wait(timeout: .now() + 2), .success)
        // The old getter releases the production FIFO lock before this gate.
        // Force that append to finish before permitting the old state change.
        // The atomic callback must instead hold the FIFO lock until release.
        let appendedBeforeFlip: Bool
        if microphone.usedAtomicBoundary {
            appendedBeforeFlip = appendFinished.wait(timeout: .now() + 0.05) == .success
        } else {
            appendedBeforeFlip = appendFinished.wait(timeout: .now() + 2) == .success
            XCTAssertTrue(appendedBeforeFlip, "Old-path append must precede the state change")
        }
        XCTAssertFalse(appendedBeforeFlip, "Producer must share the resume boundary lock")
        microphone.releaseBoundary.signal()
        XCTAssertEqual(resumeFinished.wait(timeout: .now() + 2), .success)
        if !appendedBeforeFlip {
            XCTAssertEqual(appendFinished.wait(timeout: .now() + 2), .success)
        }
        XCTAssertEqual(result.value, true)
        XCTAssertEqual(privacy.readTimestampedBatch(maximumFrameCount: 8)?.samples, [0, 0])
        XCTAssertEqual(privacy.readTimestampedBatch(maximumFrameCount: 8)?.samples,
            appendedBeforeFlip ? [0, 0] : [0.5, 0.5])
        microphone.appendFromProducer([0.6, 0.6], at: 100 + 4.0 / 48_000)
        XCTAssertEqual(privacy.readTimestampedBatch(maximumFrameCount: 8)?.samples, [0.6, 0.6])
        XCTAssertEqual(privacy.suppressedSampleCount, appendedBeforeFlip ? 4 : 2)
    }

    func testProductionAtomicBoundaryExcludesReadsAndAppendsDuringCallback() throws {
        let microphone = AppOwnedMicrophoneSampleSource()
        microphone.appendCapturedBatch(systemBatch(samples: [0.4, 0.4], seconds: 100))
        let result = PrivacyResumeResult()
        let readResult = PrivacyReadResult()
        let callbackEntered = DispatchSemaphore(value: 0)
        let releaseCallback = DispatchSemaphore(value: 0)
        let callbackFinished = DispatchSemaphore(value: 0)
        let readStarted = DispatchSemaphore(value: 0)
        let readFinished = DispatchSemaphore(value: 0)
        let appendStarted = DispatchSemaphore(value: 0)
        let appendFinished = DispatchSemaphore(value: 0)
        DispatchQueue.global().async {
            let applied = microphone.withQueuedFrameCountSnapshot { count in
                XCTAssertEqual(count, 2)
                callbackEntered.signal()
                guard releaseCallback.wait(timeout: .now() + 2) == .success else { return false }
                return true
            }
            result.set(applied)
            callbackFinished.signal()
        }
        XCTAssertEqual(callbackEntered.wait(timeout: .now() + 2), .success)
        DispatchQueue.global().async {
            readStarted.signal()
            readResult.set(microphone.readTimestampedBatch(maximumFrameCount: 2))
            readFinished.signal()
        }
        DispatchQueue.global().async {
            appendStarted.signal()
            microphone.appendCapturedBatch(systemBatch(samples: [0.5, 0.5], seconds: 100 + 2.0 / 48_000))
            appendFinished.signal()
        }
        XCTAssertEqual(readStarted.wait(timeout: .now() + 2), .success)
        XCTAssertEqual(appendStarted.wait(timeout: .now() + 2), .success)
        let earlyRead = readFinished.wait(timeout: .now() + 0.05)
        let earlyAppend = appendFinished.wait(timeout: .now() + 0.05)
        XCTAssertEqual(earlyRead, .timedOut)
        XCTAssertEqual(earlyAppend, .timedOut)
        releaseCallback.signal()
        XCTAssertEqual(callbackFinished.wait(timeout: .now() + 2), .success)
        if earlyRead != .success { XCTAssertEqual(readFinished.wait(timeout: .now() + 2), .success) }
        if earlyAppend != .success { XCTAssertEqual(appendFinished.wait(timeout: .now() + 2), .success) }
        XCTAssertEqual(result.value, true)
        XCTAssertEqual(readResult.batch?.samples, [0.4, 0.4])
        XCTAssertEqual(microphone.readTimestampedBatch(maximumFrameCount: 2)?.samples, [0.5, 0.5])
        XCTAssertEqual(microphone.timestampedDiagnostics?.queuedFrameCount, 0)
    }

    func testDiagnosticsAloneCannotAuthorizePrivacyResume() throws {
        let microphone = DiagnosticsOnlyPrivacySource()
        XCTAssertFalse(microphone.withQueuedFrameCountSnapshot { _ in
            XCTFail("Unsupported source must not invoke the callback")
            return true
        })
        let privacy = PrivacySuppressingSampleSource(base: microphone, state: .paused)
        microphone.append(systemBatch(samples: [0.4, 0.5], seconds: 100))
        XCTAssertFalse(privacy.update(state: .capturing))
        microphone.append(systemBatch(samples: [0.6, 0.7], seconds: 100 + 2.0 / 48_000))
        XCTAssertEqual(privacy.readTimestampedBatch(maximumFrameCount: 8)?.samples, [0, 0])
        XCTAssertEqual(privacy.readTimestampedBatch(maximumFrameCount: 8)?.samples, [0, 0])
        XCTAssertEqual(privacy.suppressedSampleCount, 4)
    }

    func testNegativePrivacyBoundaryLeavesSourcePaused() throws {
        let microphone = NegativePrivacyBoundarySource()
        let privacy = PrivacySuppressingSampleSource(base: microphone, state: .paused)
        XCTAssertFalse(privacy.update(state: .resuming))
        XCTAssertEqual(privacy.readTimestampedBatch(maximumFrameCount: 8)?.samples, [0])
        XCTAssertEqual(privacy.suppressedSampleCount, 1)
    }

    func testWriterFastResumeKeepsAllPausedMicrophoneBatchesSilentInBothFiles() async throws {
        _ = try await verifyWriterPrivacyQueueFiles(includeSystemAudio: false)
    }

    func testWriterPrivacyPausePreservesSystemAudioAndFinalFiles() async throws {
        let queuedSignal = try await verifyWriterPrivacyQueueFiles(includeSystemAudio: true)
        let zeroMicrophone = try await verifyWriterPrivacyQueueFiles(includeSystemAudio: true, queuedMicrophoneLevel: 0)
        for (index, pair) in zip(queuedSignal, zeroMicrophone).enumerated() {
            XCTAssertEqual(pair.0.samples.count, pair.1.samples.count)
            XCTAssertEqual(pair.0.sampleRate, pair.1.sampleRate)
            let pausedFrames = 0..<Int(pair.0.sampleRate * 0.27)
            let maximumDifference = pausedFrames.map { abs(pair.0.samples[$0] - pair.1.samples[$0]) }.max() ?? 0
            // The reference contains literal zero microphone samples through
            // the same system/AEC/codec path. A queue leak would differ here.
            XCTAssertEqual(maximumDifference, 0, accuracy: 0.000001)
            let tailFrames = Int(pair.0.sampleRate * 0.22)..<Int(pair.0.sampleRate * 0.27)
            let zeroMicTailPeak = tailFrames.map { abs(pair.1.samples[$0]) }.max() ?? 0
            print("T012 synthetic system-reference track=\(index) paused_mic_delta=\(maximumDifference) zero_mic_tail_peak=\(zeroMicTailPeak)")
        }
    }

    private func verifyWriterPrivacyQueueFiles(includeSystemAudio: Bool, queuedMicrophoneLevel: Float = 0.4) async throws
        -> [(samples: [Float], sampleRate: Double)] {
        let root = makeSystemWriterRoot("v5-privacy-queued")
        defer { try? FileManager.default.removeItem(at: root) }
        let microphone = BufferedLocalRecordingSampleSource(channelCount: 1)
        microphone.append(systemBatch(samples: Array(repeating: queuedMicrophoneLevel, count: 4_800), seconds: 100))
        let control = QueueBoundaryPrivacyControl(microphone: microphone, queuedMicrophoneLevel: queuedMicrophoneLevel)
        let system = PrivacyControlSystemSource(control: control, includeSystemAudio: includeSystemAudio)
        let writer = makeSystemV5Writer(root: root, microphone: microphone, system: system)
        control.writer = writer
        let directory = try await writer.startAsync(sessionId: "queued-privacy", startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: systemScopeApproval(), permissions: systemGrantedPermissions())
        let manifest = try await writer.stopAsync(stoppedAt: Date(timeIntervalSince1970: 13))
        XCTAssertTrue(control.didResume)
        XCTAssertTrue(manifest.isComplete)
        XCTAssertEqual(manifest.failureReason, .none)
        let segment = try XCTUnwrap(manifest.privacySegments?.first)
        XCTAssertEqual(manifest.privacySegments?.count, 1)
        XCTAssertEqual(segment.startedAt, Date(timeIntervalSince1970: 11))
        XCTAssertEqual(segment.endedAt, Date(timeIntervalSince1970: 12))
        XCTAssertEqual(segment.localMicTreatment, .silenced)
        let checkpoint = try LocalRecordingManifestService().read(from: directory.manifestURL)
        XCTAssertEqual(checkpoint.privacySegments, manifest.privacySegments)
        var decodedFiles: [(samples: [Float], sampleRate: Double)] = []
        for url in [directory.transcriptionAudioURL, directory.reviewAudioURL] {
            let file = try AVAudioFile(forReading: url)
            let buffer = try XCTUnwrap(AVAudioPCMBuffer(pcmFormat: file.processingFormat, frameCapacity: AVAudioFrameCount(file.length)))
            try file.read(into: buffer)
            let samples = try XCTUnwrap(buffer.floatChannelData).pointee
            let rate = file.processingFormat.sampleRate
            XCTAssertGreaterThanOrEqual(Double(buffer.frameLength) / rate, 0.39)
            XCTAssertLessThan(Double(buffer.frameLength) / rate, 0.55)
            if includeSystemAudio {
                let incomingFrames = Int(rate * 0.13)..<Int(rate * 0.17)
                XCTAssertTrue(incomingFrames.contains { abs(samples[$0]) > 0.01 }, "System audio must continue through microphone pause")
            } else {
                // Zero render reference isolates microphone leakage from AEC
                // and codec tails caused by the separate system-audio signal.
                let quietFrames = 0..<Int(rate * 0.27)
                XCTAssertTrue(quietFrames.allSatisfy { abs(samples[$0]) < 0.0001 }, "Paused queue leaked to \(url.lastPathComponent)")
            }
            let liveStart = Int(rate * 0.34)
            XCTAssertTrue((liveStart..<Int(buffer.frameLength)).contains { abs(samples[$0]) > 0.01 }, "New frames must become audible")
            decodedFiles.append((Array(UnsafeBufferPointer(start: samples, count: Int(buffer.frameLength))), rate))
        }
        return decodedFiles
    }

    func testWriterMissingQueueBoundaryRejectsResumeAndKeepsOpenCheckpointUntilBoundedStop() async throws {
        let root = makeSystemWriterRoot("v5-privacy-no-boundary")
        defer { try? FileManager.default.removeItem(at: root) }
        let microphone = InfiniteTimestampedSampleSource()
        let writer = makeSystemV5Writer(root: root, microphone: microphone, system: InfiniteTimestampedSampleSource())
        let directory = try await writer.startAsync(sessionId: "missing-boundary", startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: systemScopeApproval(), permissions: systemGrantedPermissions())
        try await writer.pausePrivacyAsync(startedAt: Date(timeIntervalSince1970: 11))
        var rejected = false
        do { try await writer.resumePrivacyAsync(endedAt: Date(timeIntervalSince1970: 12)) }
        catch LocalRecordingPrivacyError.resumeBoundaryUnavailable { rejected = true }
        catch { XCTFail("Unexpected resume error: \(error)") }
        XCTAssertTrue(rejected)
        let checkpoint = try LocalRecordingManifestService().read(from: directory.manifestURL)
        let openSegment = try XCTUnwrap(checkpoint.privacySegments?.first)
        XCTAssertNil(openSegment.endedAt)
        XCTAssertNil(openSegment.endMonotonicMs)
        XCTAssertEqual(openSegment.localMicTreatment, .silenced)
        let stillRecording = await writer.isRecordingAsync()
        XCTAssertTrue(stillRecording)
        let stopStart = Date()
        let stopped = try await writer.stopAsync(stoppedAt: Date(timeIntervalSince1970: 13))
        XCTAssertLessThan(Date().timeIntervalSince(stopStart), 2)
        XCTAssertEqual(stopped.captureFailureCode, "stop_drain_limit_exceeded")
        XCTAssertEqual(stopped.privacySegments?.count, 1)
        XCTAssertEqual(stopped.privacySegments?.first?.endedAt, Date(timeIntervalSince1970: 13))
    }

    func testOptionalSourceDiagnosticsTrackQueueAndFrontierThroughWrappers() throws {
        XCTAssertNil(InfiniteTimestampedSampleSource().timestampedDiagnostics)
        let microphone = AppOwnedMicrophoneSampleSource()
        let source = PrivacySuppressingSampleSource(base: microphone)
        let batch = systemBatch(samples: Array(repeating: 0.1, count: 4_800), seconds: 100)
        microphone.appendCapturedBatch(batch)
        let captured = try XCTUnwrap(source.timestampedDiagnostics)
        XCTAssertEqual(captured.queuedFrameCount, 4_800)
        XCTAssertEqual(captured.capturedFrontier?.seconds, 100.1)
        XCTAssertEqual(captured.lastBatchFrameCount, 4_800)
        XCTAssertEqual(captured.lastBatchFormat, batch.format)
        XCTAssertNotNil(captured.lastCapturedUptime)
        _ = source.readTimestampedBatch(maximumFrameCount: 512)
        let drained = try XCTUnwrap(source.timestampedDiagnostics)
        XCTAssertEqual(drained.queuedFrameCount, 4_288)
        XCTAssertEqual(drained.capturedFrontier?.seconds, captured.capturedFrontier?.seconds)
        XCTAssertEqual(drained.lastBatchFrameCount, captured.lastBatchFrameCount)
        source.update(state: .paused)
        microphone.appendCapturedBatch(systemBatch(samples: [0.4, 0.4], seconds: 100.1))
        XCTAssertTrue(source.update(state: .capturing))
        microphone.appendCapturedBatch(systemBatch(samples: [0.6, 0.6], seconds: 100.1 + 2.0 / 48_000))
        let queuedBeforePause = try XCTUnwrap(source.readTimestampedBatch(maximumFrameCount: 8_192))
        XCTAssertTrue(queuedBeforePause.samples.allSatisfy { $0 == 0 })
        let admittedDuringPause = try XCTUnwrap(source.readTimestampedBatch(maximumFrameCount: 8_192))
        XCTAssertEqual(admittedDuringPause.samples, [0, 0])
        XCTAssertEqual(admittedDuringPause.presentationTime.seconds, 100.1)
        XCTAssertEqual(source.readTimestampedBatch(maximumFrameCount: 8_192)?.samples, [0.6, 0.6])
        XCTAssertEqual(source.suppressedSampleCount, 4_290)
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
    microphone: any TimestampedLocalRecordingSampleSource,
    system: any TimestampedLocalRecordingSampleSource
) -> LocalRecordingWriter {
    LocalRecordingWriter(
        store: LocalRecordingStore(rootURL: root),
        microphoneSampleSourceFactory: { microphone },
        incomingSampleSourceFactory: { system },
        recordMicrophone: true
    )
}

/// Bound synthetic input by processing progress instead of the host's speed.
/// The empty read follows processing of the previous batch on the writer queue.
private final class DrainAcknowledgedSampleSource: TimestampedLocalRecordingSampleSource, @unchecked Sendable {
    private let base = BufferedLocalRecordingSampleSource(channelCount: 1)
    private let lock = NSLock()
    private var drained: XCTestExpectation?

    var hasTimestampedOverflow: Bool { base.hasTimestampedOverflow }

    func append(_ batch: RecordingAudioBatch, drained: XCTestExpectation) {
        lock.lock()
        defer { lock.unlock() }
        base.append(batch)
        self.drained = drained
    }

    func readTimestampedBatch(maximumFrameCount: Int) -> RecordingAudioBatch? {
        lock.lock()
        let batch = base.readTimestampedBatch(maximumFrameCount: maximumFrameCount)
        let completion = batch == nil ? drained : nil
        if batch == nil { drained = nil }
        lock.unlock()
        completion?.fulfill()
        return batch
    }
}

/// Exercise the actual writer queue exactly after its bounded live pass,
/// when diagnostics report a retained microphone batch. No timer sleeps or
/// production scheduling hooks are required to place the privacy transition.
private final class PendingMicrophonePrivacyControl: @unchecked Sendable {
    weak var writer: LocalRecordingWriter?
    private(set) var didPauseAndResume = false
    private(set) var pendingFrameCount = 0
    func observe(_ message: String) {
        guard !didPauseAndResume, message.contains("source=microphone"),
              let field = message.split(separator: " ").first(where: { $0.hasPrefix("pending_frames=") }),
              let count = Int(field.dropFirst("pending_frames=".count)), count > 0,
              let writer else { return }
        pendingFrameCount = count
        do {
            try writer.pausePrivacyOnQueue(startedAt: Date(timeIntervalSince1970: 11))
            try writer.resumePrivacyOnQueue(endedAt: Date(timeIntervalSince1970: 12))
            didPauseAndResume = true
        } catch { XCTFail("Privacy control at retained-batch boundary failed: \(error)") }
    }
}

/// Bounded real microphone queue with a read counter for completion only.
private final class BackloggedMicrophoneSource: TimestampedLocalRecordingSampleSource, @unchecked Sendable {
    private let base = BufferedLocalRecordingSampleSource(capacity: 48_000 * 30, channelCount: 1)
    private let lock = NSLock()
    private var unreadFrames = 0
    var hasTimestampedOverflow: Bool { base.hasTimestampedOverflow }
    var timestampedDiagnostics: RecordingSampleSourceDiagnostics? { base.timestampedDiagnostics }
    func withQueuedFrameCountSnapshot(_ body: (Int64) -> Bool) -> Bool {
        base.withQueuedFrameCountSnapshot(body)
    }
    var readableFrameCountForTest: Int { lock.withLock { unreadFrames } }
    func append(_ batch: RecordingAudioBatch) {
        base.append(batch)
        lock.withLock { unreadFrames += batch.samples.count }
    }
    func readTimestampedBatch(maximumFrameCount: Int) -> RecordingAudioBatch? {
        let batch = base.readTimestampedBatch(maximumFrameCount: maximumFrameCount)
        if let batch { lock.withLock { unreadFrames -= batch.samples.count } }
        return batch
    }
}

/// Deliver delayed, continuous system callbacks only as the preceding callback
/// is consumed. Every callback passes through the actual 10-second stereo ring.
private final class DelayedContinuousSystemSource: TimestampedLocalRecordingSampleSource, @unchecked Sendable {
    private let base = BufferedLocalRecordingSampleSource(capacity: 48_000 * 20, channelCount: 2)
    private let lock = NSLock()
    private let totalFrames: Int
    private let batchFrames: Int
    private var deliveredFrames = 0
    init(totalFrames: Int, batchFrames: Int) {
        self.totalFrames = totalFrames
        self.batchFrames = batchFrames
    }
    var hasTimestampedOverflow: Bool { base.hasTimestampedOverflow }
    var isDrained: Bool { lock.withLock { deliveredFrames == totalFrames } }
    func readTimestampedBatch(maximumFrameCount: Int) -> RecordingAudioBatch? {
        lock.withLock {
            if let existing = base.readTimestampedBatch(maximumFrameCount: maximumFrameCount) { return existing }
            guard deliveredFrames < totalFrames else { return nil }
            let frameCount = min(batchFrames, totalFrames - deliveredFrames)
            base.append(RecordingAudioBatch(samples: Array(repeating: 0.02, count: frameCount * 2),
                format: RecordingAudioFormat(sampleRate: 48_000, channelCount: 2),
                presentationTime: RecordingAudioPresentationTimestamp(
                    seconds: 100 + Double(deliveredFrames) / 48_000, clockDomain: .hostTime)))
            deliveredFrames += frameCount
            return base.readTimestampedBatch(maximumFrameCount: maximumFrameCount)
        }
    }
}

private final class PrivacyResumeResult: @unchecked Sendable {
    private let lock = NSLock()
    private var stored: Bool?
    var value: Bool? { lock.withLock { stored } }
    func set(_ value: Bool) { lock.withLock { stored = value } }
}

/// Gate the real production microphone path between snapshot and state flip.
private final class ProducerResumeBoundarySource: TimestampedLocalRecordingSampleSource, @unchecked Sendable {
    private let base = AppOwnedMicrophoneSampleSource()
    private let flagLock = NSLock()
    private var atomicBoundary = false
    let boundaryEntered = DispatchSemaphore(value: 0)
    let releaseBoundary = DispatchSemaphore(value: 0)
    var usedAtomicBoundary: Bool { flagLock.withLock { atomicBoundary } }
    init() { appendFromProducer([0.4, 0.4], at: 100) }
    func appendFromProducer(_ samples: [Float], at seconds: Double) {
        base.appendCapturedBatch(systemBatch(samples: samples, seconds: seconds))
    }
    var hasTimestampedOverflow: Bool { base.hasTimestampedOverflow }
    var timestampedDiagnostics: RecordingSampleSourceDiagnostics? {
        let snapshot = base.timestampedDiagnostics
        boundaryEntered.signal()
        _ = releaseBoundary.wait(timeout: .now() + 2)
        return snapshot
    }
    func withQueuedFrameCountSnapshot(_ body: (Int64) -> Bool) -> Bool {
        base.withQueuedFrameCountSnapshot { count in
            flagLock.withLock { atomicBoundary = true }
            boundaryEntered.signal()
            guard releaseBoundary.wait(timeout: .now() + 2) == .success else { return false }
            return body(count)
        }
    }
    func readTimestampedBatch(maximumFrameCount: Int) -> RecordingAudioBatch? {
        base.readTimestampedBatch(maximumFrameCount: maximumFrameCount)
    }
}

private final class DiagnosticsOnlyPrivacySource: TimestampedLocalRecordingSampleSource, @unchecked Sendable {
    private let base = BufferedLocalRecordingSampleSource(channelCount: 1)
    func append(_ batch: RecordingAudioBatch) { base.append(batch) }
    var hasTimestampedOverflow: Bool { base.hasTimestampedOverflow }
    var timestampedDiagnostics: RecordingSampleSourceDiagnostics? { base.timestampedDiagnostics }
    func readTimestampedBatch(maximumFrameCount: Int) -> RecordingAudioBatch? {
        base.readTimestampedBatch(maximumFrameCount: maximumFrameCount)
    }
}

private final class NegativePrivacyBoundarySource: TimestampedLocalRecordingSampleSource, @unchecked Sendable {
    var hasTimestampedOverflow: Bool { false }
    var timestampedDiagnostics: RecordingSampleSourceDiagnostics? {
        RecordingSampleSourceDiagnostics(queuedFrameCount: -1, capturedFrontier: nil,
            lastBatchFrameCount: 0, lastBatchFormat: nil, lastCapturedUptime: nil)
    }
    func readTimestampedBatch(maximumFrameCount: Int) -> RecordingAudioBatch? {
        systemBatch(samples: [0.4], seconds: 100)
    }
    func withQueuedFrameCountSnapshot(_ body: (Int64) -> Bool) -> Bool { body(-1) }
}

private final class PrivacyReadResult: @unchecked Sendable {
    private let lock = NSLock()
    private var storedBatch: RecordingAudioBatch?
    var batch: RecordingAudioBatch? { lock.withLock { storedBatch } }
    func set(_ batch: RecordingAudioBatch?) { lock.withLock { storedBatch = batch } }
}

private final class BlockingPrivacySampleSource: TimestampedLocalRecordingSampleSource, @unchecked Sendable {
    let base = BufferedLocalRecordingSampleSource(channelCount: 1)
    let readEntered = DispatchSemaphore(value: 0)
    let releaseRead = DispatchSemaphore(value: 0)
    private var blockNextRead = true
    init() { base.append(systemBatch(samples: Array(repeating: 0.4, count: 4), seconds: 100)) }
    var hasTimestampedOverflow: Bool { base.hasTimestampedOverflow }
    var timestampedDiagnostics: RecordingSampleSourceDiagnostics? { base.timestampedDiagnostics }
    func withQueuedFrameCountSnapshot(_ body: (Int64) -> Bool) -> Bool {
        base.withQueuedFrameCountSnapshot(body)
    }
    func readTimestampedBatch(maximumFrameCount: Int) -> RecordingAudioBatch? {
        if blockNextRead {
            blockNextRead = false
            readEntered.signal()
            guard releaseRead.wait(timeout: .now() + 2) == .success else { return nil }
        }
        return base.readTimestampedBatch(maximumFrameCount: maximumFrameCount)
    }
}

/// Models a producer that combines old and new stereo frames in one FIFO read.
private final class CoalescedPrivacySampleSource: TimestampedLocalRecordingSampleSource, @unchecked Sendable {
    private let lock = NSLock()
    private var samples: [Float] = []
    private var readFrames = 0
    func append(_ values: [Float]) { lock.withLock { samples += values } }
    var hasTimestampedOverflow: Bool { false }
    func withQueuedFrameCountSnapshot(_ body: (Int64) -> Bool) -> Bool {
        lock.withLock { body(Int64(samples.count / 2)) }
    }
    var timestampedDiagnostics: RecordingSampleSourceDiagnostics? {
        lock.withLock { RecordingSampleSourceDiagnostics(queuedFrameCount: Int64(samples.count / 2),
            capturedFrontier: nil, lastBatchFrameCount: 0, lastBatchFormat: nil, lastCapturedUptime: nil) }
    }
    func readTimestampedBatch(maximumFrameCount: Int) -> RecordingAudioBatch? {
        lock.withLock {
            guard !samples.isEmpty else { return nil }
            let count = min(samples.count, maximumFrameCount * 2)
            let values = Array(samples.prefix(count))
            samples.removeFirst(count)
            let timestamp = 100 + Double(readFrames) / 48_000
            readFrames += count / 2
            return RecordingAudioBatch(samples: values, format: RecordingAudioFormat(sampleRate: 48_000, channelCount: 2),
                presentationTime: RecordingAudioPresentationTimestamp(seconds: timestamp, clockDomain: .hostTime,
                    observedHostTimeSeconds: 123), discontinuity: .none, routeGeneration: 7)
        }
    }
}

/// Called on the actual writer queue after it prefetched microphone audio.
private final class QueueBoundaryPrivacyControl: @unchecked Sendable {
    weak var writer: LocalRecordingWriter?
    let microphone: BufferedLocalRecordingSampleSource
    private(set) var didResume = false
    private let queuedMicrophoneLevel: Float
    init(microphone: BufferedLocalRecordingSampleSource, queuedMicrophoneLevel: Float) {
        self.microphone = microphone
        self.queuedMicrophoneLevel = queuedMicrophoneLevel
    }
    func run() {
        guard let writer else { return XCTFail("Missing writer") }
        do {
            try writer.pausePrivacyOnQueue(startedAt: Date(timeIntervalSince1970: 11))
            for offset in 1...2 {
                microphone.append(systemBatch(samples: Array(repeating: queuedMicrophoneLevel, count: 4_800), seconds: 100 + Double(offset) * 0.1))
            }
            try writer.resumePrivacyOnQueue(endedAt: Date(timeIntervalSince1970: 12))
            microphone.append(systemBatch(samples: Array(repeating: 0.4, count: 4_800), seconds: 100.3))
            didResume = true
        } catch { XCTFail("Writer privacy controls failed: \(error)") }
    }
}

private final class PrivacyControlSystemSource: TimestampedLocalRecordingSampleSource, @unchecked Sendable {
    private let base = BufferedLocalRecordingSampleSource(channelCount: 1)
    private var control: QueueBoundaryPrivacyControl?
    init(control: QueueBoundaryPrivacyControl, includeSystemAudio: Bool) {
        self.control = control
        var samples = Array(repeating: Float.zero, count: 19_200)
        if includeSystemAudio {
            samples.replaceSubrange(4_800..<9_600, with: repeatElement(Float(0.1), count: 4_800))
        }
        base.append(systemBatch(samples: samples, seconds: 100))
    }
    var hasTimestampedOverflow: Bool { base.hasTimestampedOverflow }
    var timestampedDiagnostics: RecordingSampleSourceDiagnostics? { base.timestampedDiagnostics }
    func readTimestampedBatch(maximumFrameCount: Int) -> RecordingAudioBatch? {
        let pending = control
        control = nil
        pending?.run()
        return base.readTimestampedBatch(maximumFrameCount: maximumFrameCount)
    }
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
