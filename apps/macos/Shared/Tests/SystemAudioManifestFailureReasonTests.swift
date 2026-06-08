import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioManifestFailureReasonTests: XCTestCase {
    func testMissingIncomingAudioIsDegradedWithNoFramesReason() {
        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .manifest(
                sessionId: "session",
                directoryId: "dir",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: [
                    completeTrack(role: .localMic),
                    incomingTrack(status: .missing, durationMs: 0, frameCount: 0, failureReason: .noFrames)
                ]
            )

        XCTAssertEqual(manifest.status, .degraded)
        XCTAssertEqual(manifest.failureReason, .noFrames)
        XCTAssertFalse(manifest.isComplete)
    }

    func testSilentIncomingAudioIsDegradedWithSilentInputReason() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("silent-system-audio-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let micSource = BufferedLocalRecordingSampleSource()
        let incomingSource = BufferedLocalRecordingSampleSource()
        micSource.append(Array(repeating: 0.15, count: 48_000))
        incomingSource.append(Array(repeating: 0, count: 48_000))
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            microphoneSampleSourceFactory: { micSource },
            incomingSampleSourceFactory: { incomingSource },
            recordMicrophone: true
        )

        _ = try writer.start(sessionId: "session", startedAt: Date(timeIntervalSince1970: 10))
        Thread.sleep(forTimeInterval: 0.2)
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        let incoming = try XCTUnwrap(manifest.tracks.first { $0.role == .remoteSpeaker })
        XCTAssertEqual(incoming.status, .degraded)
        XCTAssertEqual(incoming.failureReason, .silentInput)
        XCTAssertEqual(manifest.status, .degraded)
        XCTAssertEqual(manifest.failureReason, .silentInput)
    }

    func testProtectedIncomingAudioIsBlockedNotSaved() {
        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .manifest(
                sessionId: "session",
                directoryId: "dir",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: [
                    completeTrack(role: .localMic),
                    incomingTrack(status: .blocked, failureReason: .protectedAudioBlocked)
                ]
            )

        XCTAssertEqual(manifest.status, .blocked)
        XCTAssertEqual(manifest.failureReason, .protectedAudioBlocked)
        XCTAssertFalse(manifest.isComplete)
    }

    func testDroppedIncomingAudioIsDegradedNotSaved() {
        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .manifest(
                sessionId: "session",
                directoryId: "dir",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: [
                    completeTrack(role: .localMic),
                    incomingTrack(status: .degraded, failureReason: .captureFailed)
                ]
            )

        XCTAssertEqual(manifest.status, .degraded)
        XCTAssertEqual(manifest.failureReason, .captureFailed)
    }
}

private func completeTrack(role: AudioTrackRole) -> LocalRecordingTrack {
    LocalRecordingTrack(
        trackId: role.rawValue,
        role: role,
        status: .saved,
        fileName: role == .localMic ? "mic.wav" : "incoming.wav",
        format: "wav-pcm-s16le",
        sampleRate: 16_000,
        channelCount: 1,
        bitsPerSample: 16,
        durationMs: 1000,
        byteCount: 32_044,
        frameCount: 16_000,
        timelineStartMs: 0,
        timelineAligned: true
    )
}

private func incomingTrack(
    status: LocalRecordingTrackStatus,
    durationMs: Int = 1000,
    frameCount: Int64 = 16_000,
    failureReason: LocalRecordingFailureReason
) -> LocalRecordingTrack {
    LocalRecordingTrack(
        trackId: "incoming",
        role: .remoteSpeaker,
        status: status,
        fileName: "incoming.wav",
        format: "wav-pcm-s16le",
        sampleRate: 16_000,
        channelCount: 1,
        bitsPerSample: 16,
        durationMs: durationMs,
        byteCount: frameCount > 0 ? 32_044 : 44,
        frameCount: frameCount,
        timelineStartMs: 0,
        timelineAligned: status == .saved,
        failureReason: failureReason
    )
}
#endif
