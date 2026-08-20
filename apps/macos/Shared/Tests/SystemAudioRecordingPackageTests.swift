import AVFoundation
import Foundation
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioRecordingPackageTests: XCTestCase {
    func testV5WriterCreatesOnlyCanonicalArtifactsFromTimestampedSources() throws {
        let root = makeRoot("v5-system-audio-package")
        defer { try? FileManager.default.removeItem(at: root) }
        let micSource = BufferedLocalRecordingSampleSource(channelCount: 1)
        let incomingSource = BufferedLocalRecordingSampleSource(channelCount: 1)
        let writer = makeWriter(root: root, microphone: micSource, incoming: incomingSource)

        let directory = try writer.start(
            sessionId: "v5-canonical-package",
            startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: scopeApproval(id: "scope-v5-canonical-package"),
            permissions: grantedPermissions()
        )
        appendStereoConversation(microphone: micSource, incoming: incomingSource, at: 100)

        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))
        let packageNames = Set(try FileManager.default.contentsOfDirectory(atPath: directory.directoryURL.path))

        XCTAssertEqual(packageNames, Set(["manifest.json", "meeting-transcription.wav", "meeting-review.m4a"]))
        XCTAssertTrue(manifest.isV5Package)
        XCTAssertTrue(manifest.isComplete)
        XCTAssertEqual(manifest.mediaScribeSourceMode, "single_wav_v1")
        XCTAssertEqual(manifest.canonicalMixProfile, "canonical-mix.v1")
        XCTAssertEqual(Set(manifest.tracks.map(\.role)), Set([.mixedMeetingAudio, .reviewPlayback]))
        XCTAssertTrue(manifest.tracks.first(where: { $0.role == .mixedMeetingAudio })?.isCanonicalTranscriptionArtifact == true)
        XCTAssertTrue(manifest.tracks.first(where: { $0.role == .reviewPlayback })?.isReviewPlaybackArtifact == true)
    }

    func testV5WriterIgnoresCallbackDeliveryJitterForValidPTS() throws {
        let root = makeRoot("v5-system-audio-callback-jitter")
        defer { try? FileManager.default.removeItem(at: root) }
        let microphone = BufferedLocalRecordingSampleSource(channelCount: 1)
        let incoming = BufferedLocalRecordingSampleSource(channelCount: 1)
        let writer = makeWriter(root: root, microphone: microphone, incoming: incoming)

        let directory = try writer.start(
            sessionId: "v5-callback-jitter",
            startedAt: Date(timeIntervalSince1970: 12),
            scopeApproval: scopeApproval(id: "scope-v5-callback-jitter"),
            permissions: grantedPermissions()
        )
        microphone.append(batch(
            samples: Array(repeating: 0.4, count: 4_800),
            seconds: 100,
            clock: .sourcePresentationTime,
            observedHostTimeSeconds: 100.01
        ))
        incoming.append(batch(
            samples: Array(repeating: 0.2, count: 4_800),
            seconds: 100,
            clock: .sourcePresentationTime,
            observedHostTimeSeconds: 100.50
        ))
        microphone.append(batch(
            samples: Array(repeating: 0.4, count: 4_800),
            seconds: 100.10,
            clock: .sourcePresentationTime,
            observedHostTimeSeconds: 100.60
        ))
        incoming.append(batch(
            samples: Array(repeating: 0.2, count: 4_800),
            seconds: 100.10,
            clock: .sourcePresentationTime,
            observedHostTimeSeconds: 100.11
        ))

        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 13))

        XCTAssertTrue(manifest.isComplete)
        XCTAssertEqual(manifest.failureReason, .none)
        XCTAssertEqual(
            Set(try FileManager.default.contentsOfDirectory(atPath: directory.directoryURL.path)),
            Set(["manifest.json", "meeting-transcription.wav", "meeting-review.m4a"])
        )
    }

    func testRepeatedStopReturnsTheAlreadyFinalizedManifest() throws {
        let root = makeRoot("v5-system-audio-repeated-stop")
        defer { try? FileManager.default.removeItem(at: root) }
        let microphone = BufferedLocalRecordingSampleSource(channelCount: 1)
        let incoming = BufferedLocalRecordingSampleSource(channelCount: 1)
        let writer = makeWriter(root: root, microphone: microphone, incoming: incoming)

        let directory = try writer.start(
            sessionId: "v5-repeated-stop",
            startedAt: Date(timeIntervalSince1970: 14),
            scopeApproval: scopeApproval(id: "scope-v5-repeated-stop"),
            permissions: grantedPermissions()
        )
        appendStereoConversation(microphone: microphone, incoming: incoming, at: 140)

        let first = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 15))
        let second = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 16))

        XCTAssertEqual(second.sessionId, first.sessionId)
        XCTAssertEqual(second.directoryId, first.directoryId)
        XCTAssertEqual(second.finalizedAt, first.finalizedAt)
        XCTAssertEqual(
            Set(try FileManager.default.contentsOfDirectory(atPath: directory.directoryURL.path)),
            Set(["manifest.json", "meeting-transcription.wav", "meeting-review.m4a"])
        )
    }

    func testV5WriterDoesNotPublishUnprocessedAudioForUncomparableSourceClocks() throws {
        let root = makeRoot("v5-system-audio-clock-mismatch")
        defer { try? FileManager.default.removeItem(at: root) }
        let micSource = BufferedLocalRecordingSampleSource(channelCount: 1)
        let incomingSource = BufferedLocalRecordingSampleSource(channelCount: 1)
        let writer = makeWriter(root: root, microphone: micSource, incoming: incomingSource)

        let directory = try writer.start(
            sessionId: "v5-clock-mismatch",
            startedAt: Date(timeIntervalSince1970: 20),
            scopeApproval: scopeApproval(id: "scope-v5-clock-mismatch"),
            permissions: grantedPermissions()
        )
        micSource.append(batch(samples: Array(repeating: 0.4, count: 4_800), seconds: 200, clock: .hostTime))
        incomingSource.append(batch(samples: Array(repeating: 0.2, count: 4_800), seconds: 200, clock: .wallClock))

        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 21))
        let packageNames = Set(try FileManager.default.contentsOfDirectory(atPath: directory.directoryURL.path))

        XCTAssertEqual(packageNames, Set(["manifest.json"]))
        XCTAssertEqual(manifest.status, .failed)
        XCTAssertEqual(manifest.failureReason, .captureFailed)
        XCTAssertEqual(manifest.captureFailureCode, "uncomparable_presentation_times")
        XCTAssertEqual(manifest.transcriptionReadiness, .failed)
        XCTAssertFalse(manifest.isComplete)
        XCTAssertFalse(FileManager.default.fileExists(atPath: directory.transcriptionAudioURL.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: directory.reviewAudioURL.path))
    }

    func testV5WriterDoesNotPublishSingleSourceAudioWhenEitherRequiredSourceHasNoFrames() throws {
        for microphoneOnly in [true, false] {
            let root = makeRoot("v5-required-source-\(microphoneOnly)")
            defer { try? FileManager.default.removeItem(at: root) }
            let microphone = BufferedLocalRecordingSampleSource(channelCount: 1)
            let incoming = BufferedLocalRecordingSampleSource(channelCount: 1)
            let writer = makeWriter(root: root, microphone: microphone, incoming: incoming)

            let directory = try writer.start(
                sessionId: "v5-required-source-\(microphoneOnly)",
                startedAt: Date(timeIntervalSince1970: 20),
                scopeApproval: scopeApproval(id: "scope-v5-required-source-\(microphoneOnly)"),
                permissions: grantedPermissions()
            )
            if microphoneOnly {
                microphone.append(batch(samples: Array(repeating: 0.4, count: 4_800), seconds: 200, clock: .hostTime))
            } else {
                incoming.append(batch(samples: Array(repeating: 0.2, count: 4_800), seconds: 200, clock: .hostTime))
            }

            let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 21))

            XCTAssertEqual(manifest.failureReason, .noFrames)
            XCTAssertFalse(manifest.isComplete)
            XCTAssertEqual(
                Set(try FileManager.default.contentsOfDirectory(atPath: directory.directoryURL.path)),
                Set(["manifest.json"])
            )
            XCTAssertFalse(FileManager.default.fileExists(atPath: directory.transcriptionAudioURL.path))
            XCTAssertFalse(FileManager.default.fileExists(atPath: directory.reviewAudioURL.path))
        }
    }

    func testV5ReviewM4AIsValidPlaybackOnlyAndNeverChangesASRDescriptor() throws {
        let root = makeRoot("v5-system-audio-review")
        defer { try? FileManager.default.removeItem(at: root) }
        let micSource = BufferedLocalRecordingSampleSource(channelCount: 1)
        let incomingSource = BufferedLocalRecordingSampleSource(channelCount: 1)
        let writer = makeWriter(root: root, microphone: micSource, incoming: incomingSource)

        let directory = try writer.start(
            sessionId: "v5-review-playback",
            startedAt: Date(timeIntervalSince1970: 30),
            scopeApproval: scopeApproval(id: "scope-v5-review-playback"),
            permissions: grantedPermissions()
        )
        appendStereoConversation(microphone: micSource, incoming: incomingSource, at: 300)

        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 31))
        let transcription = try AVAudioFile(forReading: directory.transcriptionAudioURL)
        let review = try AVAudioFile(forReading: directory.reviewAudioURL)
        let media = try XCTUnwrap(manifest.tracks.first(where: { $0.role == .mixedMeetingAudio }))
        let playback = try XCTUnwrap(manifest.tracks.first(where: { $0.role == .reviewPlayback }))

        XCTAssertEqual(Int(transcription.fileFormat.sampleRate), 16_000)
        XCTAssertEqual(Int(transcription.fileFormat.channelCount), 1)
        XCTAssertGreaterThan(transcription.length, 0)
        XCTAssertEqual(Int(review.fileFormat.sampleRate), 48_000)
        XCTAssertEqual(Int(review.fileFormat.channelCount), 1)
        XCTAssertGreaterThan(review.length, 0)
        XCTAssertLessThanOrEqual(
            abs(Double(transcription.length) / transcription.fileFormat.sampleRate - Double(review.length) / review.fileFormat.sampleRate),
            0.1
        )
        XCTAssertEqual(media.mediaScribeField, .mediaFile)
        XCTAssertEqual(media.fileName, "meeting-transcription.wav")
        XCTAssertEqual(playback.mediaScribeField, .playbackFile)
        XCTAssertEqual(playback.fileName, "meeting-review.m4a")
        XCTAssertNotEqual(media.sha256, playback.sha256)
        XCTAssertEqual(
            playback.aacPresentationFrameDelta,
            playback.frameCount - (media.frameCount * 3),
            "AAC presentation compensation must be recorded separately from the shared timeline"
        )
        XCTAssertLessThanOrEqual(abs(playback.aacPresentationFrameDelta ?? .max), 4_800)
    }

    func testV5AsyncStartAndStopUsesSameSinglePackagePath() async throws {
        let root = makeRoot("v5-system-audio-async")
        defer { try? FileManager.default.removeItem(at: root) }
        let micSource = BufferedLocalRecordingSampleSource(channelCount: 1)
        let incomingSource = BufferedLocalRecordingSampleSource(channelCount: 1)
        let writer = makeWriter(root: root, microphone: micSource, incoming: incomingSource)

        let directory = try await writer.startAsync(
            sessionId: "v5-async",
            startedAt: Date(timeIntervalSince1970: 40),
            scopeApproval: scopeApproval(id: "scope-v5-async"),
            permissions: grantedPermissions()
        )
        appendStereoConversation(microphone: micSource, incoming: incomingSource, at: 400)
        let manifest = try await writer.stopAsync(stoppedAt: Date(timeIntervalSince1970: 41))

        XCTAssertTrue(manifest.isComplete)
        XCTAssertEqual(
            Set(try FileManager.default.contentsOfDirectory(atPath: directory.directoryURL.path)),
            Set(["manifest.json", "meeting-transcription.wav", "meeting-review.m4a"])
        )
    }

    func testAsyncStartFailureDoesNotLeaveWriterRecording() async throws {
        let blockedRoot = FileManager.default.temporaryDirectory
            .appendingPathComponent("v5-system-audio-blocked-root-\(UUID().uuidString)")
        FileManager.default.createFile(atPath: blockedRoot.path, contents: Data())
        defer { try? FileManager.default.removeItem(at: blockedRoot) }

        let writer = makeWriter(
            root: blockedRoot,
            microphone: BufferedLocalRecordingSampleSource(),
            incoming: BufferedLocalRecordingSampleSource()
        )

        do {
            _ = try await writer.startAsync(
                sessionId: "v5-blocked-start",
                startedAt: Date(timeIntervalSince1970: 50),
                scopeApproval: scopeApproval(id: "scope-v5-blocked-start"),
                permissions: grantedPermissions()
            )
            XCTFail("Start should fail when the recording root is a file")
        } catch LocalRecordingWriterError.directoryUnavailable {
            XCTAssertFalse(writer.isRecording)
        }
    }

    private func makeRoot(_ prefix: String) -> URL {
        FileManager.default.temporaryDirectory.appendingPathComponent("\(prefix)-\(UUID().uuidString)", isDirectory: true)
    }

    private func makeWriter(
        root: URL,
        microphone: BufferedLocalRecordingSampleSource,
        incoming: BufferedLocalRecordingSampleSource
    ) -> LocalRecordingWriter {
        LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            microphoneSampleSourceFactory: { microphone },
            incomingSampleSourceFactory: { incoming },
            recordMicrophone: true
        )
    }

    private func appendStereoConversation(
        microphone: BufferedLocalRecordingSampleSource,
        incoming: BufferedLocalRecordingSampleSource,
        at seconds: Double
    ) {
        microphone.append(batch(samples: Array(repeating: 0.4, count: 4_800), seconds: seconds, clock: .hostTime))
        incoming.append(batch(samples: Array(repeating: 0.2, count: 4_800), seconds: seconds, clock: .hostTime))
    }

    private func batch(
        samples: [Float],
        seconds: Double,
        clock: RecordingAudioClockDomain,
        observedHostTimeSeconds: Double? = nil
    ) -> RecordingAudioBatch {
        RecordingAudioBatch(
            samples: samples,
            format: RecordingAudioFormat(sampleRate: 48_000, channelCount: 1),
            presentationTime: RecordingAudioPresentationTimestamp(
                seconds: seconds,
                clockDomain: clock,
                observedHostTimeSeconds: observedHostTimeSeconds
            ),
            discontinuity: .none,
            routeGeneration: 0
        )
    }
}

private func scopeApproval(id: String) -> CaptureScopeApproval {
    CaptureScopeApproval(
        scopeApprovalId: id,
        scopeKind: .display,
        sourceDisplayName: "Current Display",
        approvedAt: Date(timeIntervalSince1970: 39),
        approvalMode: .userConfirmedSuggestedScope,
        eligibleReason: .manualMeetingScope
    )
}

private func grantedPermissions() -> SystemAudioPermissionSnapshot {
    SystemAudioPermissionSnapshot(
        microphone: .granted,
        systemAudio: .granted,
        evaluatedAt: Date(timeIntervalSince1970: 39)
    )
}
#endif
