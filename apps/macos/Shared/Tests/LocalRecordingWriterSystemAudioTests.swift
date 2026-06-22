import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LocalRecordingWriterSystemAudioTests: XCTestCase {
    func testWriterAcceptsIndependentIncomingSampleSourceWithoutSharedMemory() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("system-audio-writer-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let source = FixtureSampleSource(samples: Array(repeating: 0.25, count: 48_000))
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            incomingSampleSourceFactory: { source },
            recordMicrophone: false
        )

        _ = try writer.start(
            sessionId: "session",
            startedAt: Date(timeIntervalSince1970: 10)
        )
        Thread.sleep(forTimeInterval: 0.15)
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        let incoming = try XCTUnwrap(manifest.tracks.first { $0.role == .remoteSpeaker })
        XCTAssertEqual(incoming.sourceKind, .systemAudio)
        XCTAssertEqual(incoming.fileName, "incoming.wav")
        XCTAssertEqual(incoming.mediaScribeField, .incomingFile)
        XCTAssertEqual(incoming.status, .saved)
        XCTAssertGreaterThan(incoming.frameCount, 0)
    }

    func testWriterReportsIncomingRecorderLevelFromSystemAudioSource() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("system-audio-writer-level-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let source = FixtureSampleSource(samples: Array(repeating: 0.5, count: 2_048))
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            incomingSampleSourceFactory: { source },
            recordMicrophone: false
        )

        _ = try writer.start(
            sessionId: "session",
            startedAt: Date(timeIntervalSince1970: 10)
        )
        Thread.sleep(forTimeInterval: 0.15)
        let now = Date()
        let levels = writer.currentLevels(now: now)
        _ = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        XCTAssertTrue(levels.isRecording)
        XCTAssertGreaterThan(levels.incomingLevel, 0)
        XCTAssertTrue(levels.incomingIsLive(now: now, staleAfter: 2))
    }

    func testStopDrainsPendingIncomingSamplesBeforeManifestFinalization() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("system-audio-writer-stop-drain-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let incomingSource = BufferedLocalRecordingSampleSource()
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            incomingSampleSourceFactory: { incomingSource },
            recordMicrophone: false
        )

        _ = try writer.start(
            sessionId: "session",
            startedAt: Date(timeIntervalSince1970: 10)
        )
        incomingSource.append(Array(repeating: 0.25, count: 48_000))

        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        let incoming = try XCTUnwrap(manifest.tracks.first { $0.role == .remoteSpeaker })
        XCTAssertGreaterThan(incoming.frameCount, 0)
        XCTAssertGreaterThan(incoming.durationMs, 0)
        XCTAssertNotEqual(incoming.failureReason, .noFrames)
    }

    func testStopBoundsInfiniteIncomingDrainAndFailsTruthfully() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("system-audio-writer-infinite-drain-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let incomingSource = InfiniteFixtureSampleSource()
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            incomingSampleSourceFactory: { incomingSource },
            recordMicrophone: false
        )

        _ = try writer.start(
            sessionId: "session-infinite-drain",
            startedAt: Date(timeIntervalSince1970: 10)
        )
        let startedAt = Date()
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))
        let elapsed = Date().timeIntervalSince(startedAt)

        let incoming = try XCTUnwrap(manifest.tracks.first { $0.role == .remoteSpeaker })
        XCTAssertLessThan(elapsed, 2)
        XCTAssertEqual(incoming.failureReason, .writeFailed)
        XCTAssertEqual(incoming.status, .failed)
        XCTAssertNotEqual(manifest.status, .saved)
        XCTAssertFalse(writer.isRecording)
    }

    func testForcedCaptureFailurePreventsCleanSavedManifest() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("system-audio-writer-forced-failure-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let microphoneSource = FixtureSampleSource(samples: Array(repeating: 0.35, count: 96_000))
        let incomingSource = FixtureSampleSource(samples: Array(repeating: 0.25, count: 96_000))
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            microphoneSampleSourceFactory: { microphoneSource },
            incomingSampleSourceFactory: { incomingSource },
            recordMicrophone: false
        )

        _ = try writer.start(
            sessionId: "session-forced-failure",
            startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: acceptedScope(),
            permissions: acceptedPermissions()
        )
        Thread.sleep(forTimeInterval: 0.15)
        let manifest = try writer.stop(
            stoppedAt: Date(timeIntervalSince1970: 11),
            failureReason: .captureFailed
        )

        let incoming = try XCTUnwrap(manifest.tracks.first { $0.role == .remoteSpeaker })
        let mic = try XCTUnwrap(manifest.tracks.first { $0.role == .localMic })
        XCTAssertGreaterThan(mic.frameCount, 0)
        XCTAssertGreaterThan(incoming.frameCount, 0)
        XCTAssertEqual(manifest.failureReason, .captureFailed)
        XCTAssertEqual(manifest.status, .failed)
        XCTAssertFalse(manifest.isComplete)
    }

    func testStopPadsIntermittentIncomingAudioToRecordingTimeline() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("system-audio-writer-padding-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let microphoneSource = FixtureSampleSource(samples: Array(repeating: 0.35, count: 48_000))
        let incomingSource = BufferedLocalRecordingSampleSource(channelCount: 1)
        incomingSource.append(Array(repeating: 0.25, count: 4_800))
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            microphoneSampleSourceFactory: { microphoneSource },
            incomingSampleSourceFactory: { incomingSource },
            recordMicrophone: true
        )

        _ = try writer.start(
            sessionId: "session",
            startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: acceptedScope(),
            permissions: acceptedPermissions()
        )

        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        let incoming = try XCTUnwrap(manifest.tracks.first { $0.role == .remoteSpeaker })
        XCTAssertGreaterThanOrEqual(incoming.durationMs, 990)
        XCTAssertLessThanOrEqual(manifest.durationDifferenceSeconds, 3)
        XCTAssertEqual(incoming.failureReason, .timelineMisaligned)
        XCTAssertEqual(incoming.status, .degraded)
        XCTAssertNotEqual(manifest.status, .saved)
        XCTAssertEqual(manifest.captureHealth?.failureReason, .timelineMisaligned)
        XCTAssertEqual(manifest.captureHealth?.gateStatus, .failed)
    }

    func testSmallIncomingStopTailPaddingDoesNotDegradeRecording() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("system-audio-writer-stop-tail-padding-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let microphoneSource = FixtureSampleSource(samples: Array(repeating: 0.35, count: 48_000))
        let incomingSource = BufferedLocalRecordingSampleSource(channelCount: 1)
        incomingSource.append(Array(repeating: 0.25, count: 46_080))
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            microphoneSampleSourceFactory: { microphoneSource },
            incomingSampleSourceFactory: { incomingSource },
            recordMicrophone: true
        )

        _ = try writer.start(
            sessionId: "session",
            startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: acceptedScope(),
            permissions: acceptedPermissions()
        )

        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        let incoming = try XCTUnwrap(manifest.tracks.first { $0.role == .remoteSpeaker })
        XCTAssertEqual(incoming.durationMs, 1000)
        XCTAssertEqual(incoming.failureReason, LocalRecordingFailureReason.none)
        XCTAssertEqual(incoming.status, .saved)
        XCTAssertTrue(incoming.timelineAligned)
        XCTAssertEqual(manifest.status, .degraded)
        XCTAssertEqual(manifest.failureReason, .leakageUnproven)
        XCTAssertEqual(manifest.leakageFinalization?.transcriptionGate, .blockedUnproven)
        XCTAssertFalse(manifest.isComplete)
        XCTAssertEqual(manifest.captureHealth?.failureReason, LocalRecordingFailureReason.none)
        XCTAssertEqual(manifest.captureHealth?.gateStatus, .passed)
    }

    func testBufferedIncomingSourceReadsInOrderAfterPartialReads() {
        let source = BufferedLocalRecordingSampleSource(capacity: 8)
        let scratch = UnsafeMutablePointer<Float>.allocate(capacity: 4)
        defer { scratch.deallocate() }

        source.append([1, 2, 3, 4])
        XCTAssertEqual(source.readSamples(into: scratch, capacity: 2), 2)
        XCTAssertEqual(Array(UnsafeBufferPointer(start: scratch, count: 2)), [1, 2])

        source.append([5, 6])
        XCTAssertEqual(source.readSamples(into: scratch, capacity: 4), 4)
        XCTAssertEqual(Array(UnsafeBufferPointer(start: scratch, count: 4)), [3, 4, 5, 6])
    }

    func testBufferedIncomingSourceDropsOldestUnreadSamplesWhenCapacityIsExceeded() {
        let source = BufferedLocalRecordingSampleSource(capacity: 4)
        let scratch = UnsafeMutablePointer<Float>.allocate(capacity: 4)
        defer { scratch.deallocate() }

        source.append([1, 2, 3])
        source.append([4, 5, 6])

        XCTAssertEqual(source.readSamples(into: scratch, capacity: 4), 4)
        XCTAssertEqual(Array(UnsafeBufferPointer(start: scratch, count: 4)), [3, 4, 5, 6])
        XCTAssertEqual(source.stats().frameCount, 4)
    }

    func testBufferedSourceStatsRespectConfiguredChannelCount() {
        let stereoSource = BufferedLocalRecordingSampleSource(channelCount: 2)
        stereoSource.append(Array(repeating: 0.25, count: 512))
        XCTAssertEqual(stereoSource.stats().frameCount, 256)

        let monoSource = BufferedLocalRecordingSampleSource(channelCount: 1)
        monoSource.append(Array(repeating: 0.25, count: 512))
        XCTAssertEqual(monoSource.stats().frameCount, 512)
    }

    func testWriterUsesInjectedAppOwnedMicrophoneSourceForMicTrackLevelsAndMetadata() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("system-audio-writer-app-owned-mic-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let microphoneSource = FixtureSampleSource(samples: Array(repeating: 0.45, count: 96_000))
        let incomingSource = FixtureSampleSource(samples: Array(repeating: 0.25, count: 96_000))
        let selection = writerRecordingMicrophoneSelection()
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            microphoneSampleSourceFactory: { microphoneSource },
            incomingSampleSourceFactory: { incomingSource },
            recordMicrophone: true
        )

        _ = try writer.start(
            sessionId: "session-app-owned-mic",
            startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: acceptedScope(),
            permissions: acceptedPermissions(),
            microphoneSelection: selection
        )
        Thread.sleep(forTimeInterval: 0.15)
        let levels = writer.currentLevels(now: Date())
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        let mic = try XCTUnwrap(manifest.tracks.first { $0.role == .localMic })
        let incoming = try XCTUnwrap(manifest.tracks.first { $0.role == .remoteSpeaker })
        XCTAssertGreaterThan(mic.frameCount, 0)
        XCTAssertGreaterThan(incoming.frameCount, 0)
        XCTAssertGreaterThan(levels.microphoneLevel, 0)
        XCTAssertTrue(levels.microphoneIsLive(staleAfter: 2))
        XCTAssertEqual(manifest.microphoneSelection, selection)
        XCTAssertEqual(manifest.microphoneStream?.streamKind, .appOwnedSampleSource)
        XCTAssertTrue(manifest.microphoneStream?.provesGraphReadiness == true)
        XCTAssertEqual(manifest.microphoneStreamHealth?.cleanupReadiness, .readyForFutureProcessing)
        XCTAssertGreaterThan(manifest.microphoneStreamHealth?.lastLevel ?? 0, 0)
        XCTAssertNotNil(manifest.microphoneStreamHealth?.lastLevelAt)
    }

    func testWriterAttachesAppleCandidateMetadataWithoutReplacingOriginalTracks() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("system-audio-writer-apple-candidate-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let microphoneSource = FixtureSampleSource(samples: Array(repeating: 0.35, count: 48_000))
        let incomingSource = FixtureSampleSource(samples: Array(repeating: 0.25, count: 48_000))
        let appleOutcome = AppleProcessingOutcome(
            candidateId: "apple-candidate-001",
            primaryOutcome: .acceptedForGuidanceOnly,
            validationRows: [
                AppleProcessingValidationRow(
                    candidateId: "apple-candidate-001",
                    candidateKind: .micModeGuidance,
                    routeClass: .builtInSpeakerphone,
                    scenario: .farEndOnly,
                    baselineStatus: .degraded,
                    candidateStatus: .unproven,
                    lineageStatus: .candidateMetadata,
                    speechPreservationStatus: .notMeasured,
                    alignmentStatus: .notMeasured,
                    stabilityStatus: .unproven,
                    diagnosticSafe: true
                )
            ],
            nextStepRecommendation: .deferToWebRTCAEC3
        )
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            microphoneSampleSourceFactory: { microphoneSource },
            incomingSampleSourceFactory: { incomingSource },
            recordMicrophone: true
        )

        _ = try writer.start(
            sessionId: "session-apple-candidate",
            startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: acceptedScope(),
            permissions: acceptedPermissions(),
            appleProcessingOutcome: appleOutcome
        )
        Thread.sleep(forTimeInterval: 0.15)
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        let mic = try XCTUnwrap(manifest.tracks.first { $0.role == .localMic })
        let incoming = try XCTUnwrap(manifest.tracks.first { $0.role == .remoteSpeaker })
        XCTAssertEqual(mic.fileName, "mic.wav")
        XCTAssertEqual(incoming.fileName, "incoming.wav")
        XCTAssertEqual(mic.evidenceRole, .original)
        XCTAssertEqual(incoming.evidenceRole, .original)
        XCTAssertEqual(manifest.appleProcessingOutcome, appleOutcome)
        XCTAssertFalse(manifest.appleProcessingOutcome?.canClaimCleanBuiltinSpeakerphone ?? true)
    }

    func testAppOwnedMicrophoneNoFramesProducesUnprovenStreamHealth() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("system-audio-writer-mic-no-frames-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let microphoneSource = FixtureSampleSource(samples: [])
        let incomingSource = FixtureSampleSource(samples: Array(repeating: 0.25, count: 96_000))
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            microphoneSampleSourceFactory: { microphoneSource },
            incomingSampleSourceFactory: { incomingSource },
            recordMicrophone: true
        )

        _ = try writer.start(
            sessionId: "session-mic-no-frames",
            startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: acceptedScope(),
            permissions: acceptedPermissions(),
            microphoneSelection: writerRecordingMicrophoneSelection()
        )
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        let mic = try XCTUnwrap(manifest.tracks.first { $0.role == .localMic })
        XCTAssertEqual(mic.failureReason, .noFrames)
        XCTAssertEqual(manifest.microphoneStreamHealth?.framesObserved, false)
        XCTAssertEqual(manifest.microphoneStreamHealth?.cleanupReadiness, .unproven)
        XCTAssertEqual(manifest.microphoneStreamHealth?.gateStatus, .failed)
        XCTAssertFalse(manifest.microphoneStream?.provesGraphReadiness == true)
    }

    func testAppOwnedMicrophoneSilenceProducesSilentStreamHealth() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("system-audio-writer-mic-silent-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let microphoneSource = FixtureSampleSource(samples: Array(repeating: 0, count: 96_000))
        let incomingSource = FixtureSampleSource(samples: Array(repeating: 0.25, count: 96_000))
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            microphoneSampleSourceFactory: { microphoneSource },
            incomingSampleSourceFactory: { incomingSource },
            recordMicrophone: true
        )

        _ = try writer.start(
            sessionId: "session-mic-silent",
            startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: acceptedScope(),
            permissions: acceptedPermissions(),
            microphoneSelection: writerRecordingMicrophoneSelection()
        )
        Thread.sleep(forTimeInterval: 0.15)
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        let mic = try XCTUnwrap(manifest.tracks.first { $0.role == .localMic })
        XCTAssertEqual(mic.failureReason, .silentInput)
        XCTAssertEqual(manifest.microphoneStreamHealth?.silenceStatus, .silent)
        XCTAssertEqual(manifest.microphoneStreamHealth?.cleanupReadiness, .unproven)
        XCTAssertFalse(manifest.microphoneStream?.provesGraphReadiness == true)
    }

    func testPausedMicrophoneSamplesDoNotProveAppOwnedGraphReadiness() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("system-audio-writer-mic-paused-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let microphoneSource = GateableFixtureSampleSource(samples: Array(repeating: 0.25, count: 96_000))
        let incomingSource = FixtureSampleSource(samples: Array(repeating: 0.25, count: 96_000))
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            microphoneSampleSourceFactory: { microphoneSource },
            incomingSampleSourceFactory: { incomingSource },
            recordMicrophone: true
        )

        _ = try writer.start(
            sessionId: "session-mic-paused",
            startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: acceptedScope(),
            permissions: acceptedPermissions(),
            microphoneSelection: writerRecordingMicrophoneSelection()
        )
        try writer.pausePrivacy(startedAt: Date(timeIntervalSince1970: 10.1))
        microphoneSource.release()
        Thread.sleep(forTimeInterval: 0.15)
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        XCTAssertEqual(manifest.microphoneStream?.frameCount, 0)
        XCTAssertEqual(manifest.microphoneStreamHealth?.framesObserved, false)
        XCTAssertEqual(manifest.microphoneStreamHealth?.cleanupReadiness, .unproven)
        XCTAssertFalse(manifest.microphoneStream?.provesGraphReadiness == true)
    }
}

private func acceptedScope() -> CaptureScopeApproval {
    CaptureScopeApproval(
        scopeApprovalId: "scope-system-audio",
        scopeKind: .display,
        sourceDisplayName: "Current Display",
        approvedAt: Date(timeIntervalSince1970: 9),
        approvalMode: .userConfirmedSuggestedScope,
        eligibleReason: .manualMeetingScope
    )
}

private func acceptedPermissions() -> SystemAudioPermissionSnapshot {
    SystemAudioPermissionSnapshot(
        microphone: .granted,
        systemAudio: .granted,
        evaluatedAt: Date(timeIntervalSince1970: 9)
    )
}

private func writerRecordingMicrophoneSelection() -> RecordingMicrophoneSelection {
    RecordingMicrophoneSelection(
        selectionId: "writer-selection",
        mode: .userSelected,
        inputDeviceId: "built-in",
        inputDisplayName: "Built-in Microphone",
        deviceClass: .builtIn,
        workingDeviceKind: .physical,
        selectionResult: .accepted,
        resolvedAt: Date(timeIntervalSince1970: 9)
    )
}

private final class FixtureSampleSource: LocalRecordingSampleSource, @unchecked Sendable {
    private var samples: [Float]

    init(samples: [Float]) {
        self.samples = samples
    }

    func readSamples(into destination: UnsafeMutablePointer<Float>, capacity: Int) -> Int {
        guard !samples.isEmpty else { return 0 }
        let count = min(capacity, samples.count)
        for index in 0..<count {
            destination[index] = samples[index]
        }
        samples.removeFirst(count)
        return count
    }
}

private final class InfiniteFixtureSampleSource: LocalRecordingSampleSource, @unchecked Sendable {
    func readSamples(into destination: UnsafeMutablePointer<Float>, capacity: Int) -> Int {
        guard capacity > 0 else { return 0 }
        for index in 0..<capacity {
            destination[index] = 0.25
        }
        return capacity
    }
}

private final class GateableFixtureSampleSource: LocalRecordingSampleSource, @unchecked Sendable {
    private let lock = NSLock()
    private var samples: [Float]
    private var released = false

    init(samples: [Float]) {
        self.samples = samples
    }

    func release() {
        lock.lock()
        released = true
        lock.unlock()
    }

    func readSamples(into destination: UnsafeMutablePointer<Float>, capacity: Int) -> Int {
        lock.lock()
        defer { lock.unlock() }
        guard released, !samples.isEmpty else { return 0 }
        let count = min(capacity, samples.count)
        for index in 0..<count {
            destination[index] = samples[index]
        }
        samples.removeFirst(count)
        return count
    }
}
#endif
