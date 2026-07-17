import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

func custodyFixtureProfile(
    uploadable: Bool = true,
    durationSeconds: Int = 60
) -> ArtifactCompletenessProfile {
    ArtifactCompletenessProfile(
        schemaVersion: LocalRecordingManifest.legacySchemaVersion,
        manifestPresent: true,
        microphonePresent: true,
        systemAudioPresent: true,
        manifestSha256: String(repeating: "a", count: 64),
        microphoneSha256: String(repeating: "b", count: 64),
        systemAudioSha256: String(repeating: "c", count: 64),
        manifestSizeBytes: 128,
        microphoneSizeBytes: 256,
        systemAudioSizeBytes: 512,
        durationSeconds: durationSeconds,
        trackCompleteness: [],
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
        microphonePath: "/redacted/\(id)/mic.wav",
        systemAudioPath: "/redacted/\(id)/incoming.wav",
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
