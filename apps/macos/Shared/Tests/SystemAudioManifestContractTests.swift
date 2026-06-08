import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioManifestContractTests: XCTestCase {
    func testIncomingSystemAudioPreservesRemoteSpeakerRoleAndSourceMetadata() {
        let track = LocalRecordingTrack(
            trackId: "incoming",
            role: .remoteSpeaker,
            status: .saved,
            fileName: "incoming.wav",
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

        XCTAssertEqual(track.role, .remoteSpeaker)
        XCTAssertEqual(track.sourceKind, .systemAudio)
        XCTAssertEqual(track.mediaScribeField, .incomingFile)
        XCTAssertTrue(track.isMediaScribeReady)
    }

    func testManifestCarriesScopePermissionsAndCpuEvidenceWithoutEgress() {
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
                scopeApproval: CaptureScopeApproval(
                    scopeApprovalId: "scope-1",
                    scopeKind: .application,
                    sourceDisplayName: "Telemost",
                    approvedAt: Date(timeIntervalSince1970: 9),
                    approvalMode: .manualSelection,
                    eligibleReason: .approvedMeetingApp
                ),
                permissions: SystemAudioPermissionSnapshot(
                    microphone: .granted,
                    systemAudio: .granted,
                    evaluatedAt: Date(timeIntervalSince1970: 9)
                ),
                captureHealth: CaptureHealthSnapshot(
                    recordingSessionId: "session",
                    phase: .activeRecording,
                    sampledAt: Date(timeIntervalSince1970: 15),
                    coreaudiodCpuPercent: 4,
                    appCpuPercent: 8,
                    helperCpuPercent: 1
                )
            )

        XCTAssertEqual(manifest.status, .saved)
        XCTAssertEqual(manifest.scopeApproval?.scopeApprovalId, "scope-1")
        XCTAssertEqual(manifest.permissions?.microphone, .granted)
        XCTAssertEqual(manifest.permissions?.systemAudio, .granted)
        XCTAssertEqual(manifest.captureHealth?.appHelperCpuPercent, 9)
        XCTAssertFalse(manifest.externalEgressStarted)
        XCTAssertFalse(manifest.transcriptionStarted)
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
