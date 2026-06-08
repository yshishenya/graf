import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioDegradedAttemptTests: XCTestCase {
    func testDeniedSystemAudioPermissionCannotProduceSavedManifest() {
        let permissions = SystemAudioPermissionSnapshot(
            microphone: .granted,
            systemAudio: .denied,
            evaluatedAt: Date(timeIntervalSince1970: 1)
        )

        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .manifest(
                sessionId: "session",
                directoryId: "dir",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: [
                    completeTrack(role: .localMic),
                    completeTrack(role: .remoteSpeaker)
                ],
                permissions: permissions
            )

        XCTAssertEqual(manifest.status, .degraded)
        XCTAssertEqual(manifest.transcriptionReadiness, .degraded)
        XCTAssertEqual(manifest.failureReason, .permissionDenied)
        XCTAssertFalse(manifest.isComplete)
    }

    func testGrantedPermissionsPreserveSavedManifestForCompleteTracks() {
        let permissions = SystemAudioPermissionSnapshot(
            microphone: .granted,
            systemAudio: .granted,
            evaluatedAt: Date(timeIntervalSince1970: 1)
        )

        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .manifest(
                sessionId: "session",
                directoryId: "dir",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: [
                    completeTrack(role: .localMic),
                    completeTrack(role: .remoteSpeaker)
                ],
                permissions: permissions
            )

        XCTAssertEqual(manifest.status, .saved)
        XCTAssertTrue(manifest.isComplete)
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
#endif
