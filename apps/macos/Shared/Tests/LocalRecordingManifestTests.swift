import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LocalRecordingManifestTests: XCTestCase {
    func testCompleteTracksProduceSavedManifest() {
        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .manifest(
                sessionId: "session",
                directoryId: "dir",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: [
                    completeTrack(role: .localMic),
                    completeTrack(role: .remoteSpeaker)
                ]
            )

        XCTAssertEqual(manifest.status, .saved)
        XCTAssertTrue(manifest.isComplete)
        XCTAssertFalse(manifest.externalEgressStarted)
        XCTAssertFalse(manifest.transcriptionStarted)
    }

    func testMissingRequiredTrackProducesDegradedManifest() {
        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .manifest(
                sessionId: "session",
                directoryId: "dir",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: [
                    completeTrack(role: .localMic),
                    LocalRecordingTrack(
                        trackId: "remote",
                        role: .remoteSpeaker,
                        status: .missing,
                        fileName: "remote-speaker.wav",
                        format: "wav-lpcm",
                        sampleRate: 48_000,
                        channelCount: 2,
                        durationMs: 0,
                        byteCount: 44,
                        frameCount: 0,
                        failureReason: .emptyRequiredTrack
                    )
                ]
            )

        XCTAssertEqual(manifest.status, .degraded)
        XCTAssertFalse(manifest.isComplete)
        XCTAssertEqual(manifest.failureReason, .emptyRequiredTrack)
    }

    func testManifestWritesJSON() throws {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-manifest-\(UUID().uuidString).json")
        defer { try? FileManager.default.removeItem(at: url) }
        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .manifest(
                sessionId: "session",
                directoryId: "dir",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: [completeTrack(role: .localMic), completeTrack(role: .remoteSpeaker)]
            )

        try LocalRecordingManifestService().write(manifest, to: url)

        let data = try Data(contentsOf: url)
        let object = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        XCTAssertEqual(object?["schemaVersion"] as? String, LocalRecordingManifest.schemaVersion)
    }
}

private func completeTrack(role: AudioTrackRole) -> LocalRecordingTrack {
    LocalRecordingTrack(
        trackId: role.rawValue,
        role: role,
        status: .saved,
        fileName: "\(role.rawValue).wav",
        format: "wav-lpcm",
        sampleRate: 48_000,
        channelCount: 2,
        durationMs: 1000,
        byteCount: 192_044,
        frameCount: 48_000
    )
}
#endif
