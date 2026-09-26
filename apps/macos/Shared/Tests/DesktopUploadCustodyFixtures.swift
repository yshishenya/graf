import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

func custodyFixtureProfile(
    uploadable: Bool = true,
    durationSeconds: Int = 60
) -> ArtifactCompletenessProfile {
    ArtifactCompletenessProfile(
        schemaVersion: LocalRecordingManifest.schemaVersion,
        manifestPresent: true,
        microphonePresent: false,
        systemAudioPresent: false,
        manifestSha256: String(repeating: "a", count: 64),
        microphoneSha256: nil,
        systemAudioSha256: nil,
        manifestSizeBytes: 128,
        microphoneSizeBytes: 0,
        systemAudioSizeBytes: 0,
        durationSeconds: durationSeconds,
        trackCompleteness: [
            UploadTrackCompleteness(transportRole: .manifest, fileName: "manifest.json", present: true, byteCount: 128, sha256: String(repeating: "a", count: 64)),
            UploadTrackCompleteness(transportRole: .media, fileName: "meeting-transcription.wav", present: true, byteCount: 256, sha256: String(repeating: "b", count: 64)),
            UploadTrackCompleteness(transportRole: .playback, fileName: "meeting-review.m4a", present: true, byteCount: 512, sha256: String(repeating: "c", count: 64))
        ],
        isUploadable: uploadable
    )
}

func custodyFixtureQueueItem(
    id: String = "custody-item",
    state: UploadItemState = .queued,
    retryMode: UploadRetryMode = .automatic,
    meetingId: String? = nil,
    serverTruth: ServerTruthFingerprint = ServerTruthFingerprint(),
    failureCategory: UploadFailureCategory = .none,
    failureReason: String? = nil,
    syncConflictState: DesktopSyncConflictState = .none,
    retentionDeadline: Date = Date(timeIntervalSince1970: 1_800_000_000),
    updatedAt: Date = Date(timeIntervalSince1970: 100)
) -> DesktopUploadQueueItem {
    DesktopUploadQueueItem(
        id: id,
        sessionId: "\(id)-session",
        directoryId: "\(id)-directory",
        localMediaRevisionId: "\(id)-directory--initial",
        directoryPath: "/redacted/\(id)",
        manifestPath: "/redacted/\(id)/manifest.json",
        microphonePath: "/redacted/\(id)/meeting-transcription.wav",
        systemAudioPath: "/redacted/\(id)/meeting-review.m4a",
        state: state,
        failureCategory: failureCategory,
        failureReason: failureReason,
        retryMode: retryMode,
        retentionDeadline: retentionDeadline,
        createdAt: Date(timeIntervalSince1970: 1),
        updatedAt: updatedAt,
        meetingId: meetingId,
        syncConflictState: syncConflictState,
        artifactProfile: custodyFixtureProfile(),
        serverTruth: serverTruth,
        retentionDecision: RetentionDecision(
            decision: .retain,
            decidedAt: updatedAt,
            reason: "fixture",
            localArtifactsRetained: true,
            policyReference: "fixture"
        )
    )
}
