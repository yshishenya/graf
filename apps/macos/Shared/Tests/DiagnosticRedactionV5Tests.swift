import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class DiagnosticRedactionTests: XCTestCase {
    func testCurrentCaptureDiagnosticsKeepMetadataAndRemoveSensitiveFields() {
        let manifest: [String: DiagnosticFieldValue] = [
            "capturePermissions": .object([
                "microphone": .string("granted"),
                "systemAudio": .string("granted"),
                "rawAudio": .string("forbidden")
            ]),
            "browserTargetEvidence": .array([
                .object([
                    "target": .string("chrome"),
                    "status": .string("blocked"),
                    "meetingContent": .string("forbidden")
                ])
            ]),
            "transcriptText": .string("forbidden"),
            "aecDump": .string("forbidden"),
            "captureState": .string("failed"),
            "recoveryActionId": .string("rerun_readiness_check")
        ]

        let result = DiagnosticRedactor().redact(manifest)

        XCTAssertNotNil(result.manifest["capturePermissions"])
        XCTAssertNotNil(result.manifest["browserTargetEvidence"])
        XCTAssertNotNil(result.manifest["captureState"])
        XCTAssertNil(result.manifest["transcriptText"])
        XCTAssertNil(result.manifest["aecDump"])
        XCTAssertTrue(result.removedFields.contains("capturePermissions.rawAudio"))
        XCTAssertTrue(result.removedFields.contains("browserTargetEvidence[0].meetingContent"))
    }

    func testMeetingDetectionDetectorBundleKeepsOnlyMetadata() throws {
        let bundle = try DiagnosticBundleService().buildMeetingDetectionDetectorBundle(
            evidence: MeetingDetectionDetectorEvidence(
                status: "observed",
                registryVersion: "2026.07.08.1",
                bundleID: "ru.yandex.desktop.telemost",
                targetID: "yandex_telemost",
                supportMode: .promptEnabled,
                decision: "prompt",
                reason: nil,
                observedAt: Date(timeIntervalSince1970: 1_783_440_000)
            )
        )

        XCTAssertNotNil(bundle.manifest["meetingDetectionDetector"])
        XCTAssertNil(bundle.manifest["rawAudio"])
        XCTAssertNil(bundle.manifest["transcriptText"])
        XCTAssertFalse(String(describing: bundle.manifest).localizedCaseInsensitiveContains("http"))
        XCTAssertFalse(String(describing: bundle.manifest).localizedCaseInsensitiveContains("passcode"))
    }

    func testRecordingEvidenceKeepsMetadataAndRemovesSensitiveFields() {
        let manifest: [String: DiagnosticFieldValue] = [
            "recordingEvidence": .array([
                .object([
                    "sessionId": .string("session"),
                    "eventType": .string("recording.started"),
                    "captureState": .string("active"),
                    "indicatorState": .string("active"),
                    "transcriptText": .string("forbidden")
                ])
            ]),
            "recordingPrerequisites": .array([
                .object([
                    "microphonePermissionGranted": .bool(true),
                    "systemAudioPermissionGranted": .bool(true),
                    "blockedReason": .string("none"),
                    "signedUrl": .string("forbidden")
                ])
            ]),
            "meetingContent": .string("forbidden")
        ]

        let result = DiagnosticRedactor().redact(manifest)

        XCTAssertNotNil(result.manifest["recordingEvidence"])
        XCTAssertNotNil(result.manifest["recordingPrerequisites"])
        XCTAssertNil(result.manifest["meetingContent"])
        XCTAssertTrue(result.removedFields.contains("recordingEvidence[0].transcriptText"))
        XCTAssertTrue(result.removedFields.contains("recordingPrerequisites[0].signedUrl"))
    }

    func testRecordingMetadataBundleKeepsProvenanceWithoutRawTitleOrBasename() throws {
        let metadata = RecordingDisplayMetadata(
            recordingStartedAt: Date(timeIntervalSince1970: 10),
            recordingStoppedAt: Date(timeIntervalSince1970: 20),
            title: "Private Customer Sync",
            titleStatus: .generated,
            titleSource: .appContext,
            titleConfidence: .high,
            titleGeneratedAt: Date(timeIntervalSince1970: 30),
            safeFileBasename: "1970-01-01_00-00_private-customer-sync_ab12cd",
            stableSuffix: "ab12cd"
        )
        let manifest = LocalRecordingManifest(
            sessionId: "session",
            createdAt: Date(timeIntervalSince1970: 30),
            startedAt: Date(timeIntervalSince1970: 10),
            stoppedAt: Date(timeIntervalSince1970: 20),
            status: .saved,
            directoryId: "dir",
            transcriptionReadiness: .ready,
            tracks: [],
            recordingMetadata: metadata
        )

        let bundle = try DiagnosticBundleService().buildLocalRecordingBundle(manifest: manifest)
        let rendered = String(describing: bundle.manifest)

        XCTAssertEqual(bundle.redactionState, .redacted)
        XCTAssertTrue(rendered.contains("titleSource"))
        XCTAssertTrue(rendered.contains("safeFileBasenameLength"))
        XCTAssertFalse(rendered.contains("stableSuffix"))
        XCTAssertFalse(rendered.contains("Private Customer Sync"))
        XCTAssertFalse(rendered.contains("private-customer-sync"))
    }

    func testRedactorRemovesUnsafeTitleLikeValues() {
        let unsafeURL = "https" + "://meet." + "example" + ".com/private"
        let unsafeEmail = "john" + "@example" + ".com"
        let unsafeToken = "token" + "=secret"
        let manifest: [String: DiagnosticFieldValue] = [
            "localRecordingManifest": .object([
                "visibleTitle": .string("\(unsafeURL) \(unsafeEmail) \(unsafeToken)"),
                "titleSource": .string("app_context")
            ])
        ]

        let result = DiagnosticRedactor().redact(manifest)

        XCTAssertNotNil(result.manifest["localRecordingManifest"])
        XCTAssertTrue(result.removedFields.contains("localRecordingManifest.visibleTitle"))
        XCTAssertFalse(String(describing: result.manifest).contains(unsafeEmail))
    }

    func testMuteTruthFieldsKeepMetadataAndRemoveNestedSensitiveFields() {
        let manifest: [String: DiagnosticFieldValue] = [
            "recordingEvidence": .array([
                .object([
                    "sessionId": .string("session"),
                    "eventType": .string("recording.paused"),
                    "participantSpeech": .string("forbidden")
                ])
            ]),
            "privacySegments": .array([
                .object([
                    "segmentId": .string("segment-1"),
                    "durationMs": .int(1000),
                    "audioSnippet": .string("forbidden")
                ])
            ]),
            "meetingMuteTruth": .object([
                "decision": .string("meeting_mute_unproven"),
                "meetingNotes": .string("forbidden")
            ])
        ]

        let result = DiagnosticRedactor().redact(manifest)

        XCTAssertNotNil(result.manifest["recordingEvidence"])
        XCTAssertNotNil(result.manifest["privacySegments"])
        XCTAssertNotNil(result.manifest["meetingMuteTruth"])
        XCTAssertTrue(result.removedFields.contains("recordingEvidence[0].participantSpeech"))
        XCTAssertTrue(result.removedFields.contains("privacySegments[0].audioSnippet"))
        XCTAssertTrue(result.removedFields.contains("meetingMuteTruth.meetingNotes"))
    }

    func testLocalRecordingEvidenceKeepsSafeMetadataAndRemovesSensitiveFields() {
        let manifest: [String: DiagnosticFieldValue] = [
            "localRecordingManifest": .object([
                "sessionId": .string("session"),
                "directoryId": .string("20260602-session"),
                "transcriptionReadiness": .string("ready"),
                "mediaScribeSourceMode": .string("single_wav_v1"),
                "absolutePath": .string("/Users/example/Recordings/session"),
                "rawAudio": .string("forbidden")
            ]),
            "localRecordingTracks": .array([
                .object([
                    "role": .string("mixed_meeting_audio"),
                    "mediaScribeField": .string("media_file"),
                    "fileName": .string("meeting-transcription.wav"),
                    "format": .string("wav-pcm-s16le"),
                    "byteCount": .int(100),
                    "meetingContent": .string("forbidden")
                ])
            ])
        ]

        let result = DiagnosticRedactor().redact(manifest)

        XCTAssertNotNil(result.manifest["localRecordingManifest"])
        XCTAssertNotNil(result.manifest["localRecordingTracks"])
        guard case .object(let localRecordingManifest)? = result.manifest["localRecordingManifest"] else {
            XCTFail("localRecordingManifest should be preserved as safe metadata")
            return
        }
        XCTAssertEqual(localRecordingManifest["transcriptionReadiness"], .string("ready"))
        XCTAssertEqual(localRecordingManifest["mediaScribeSourceMode"], .string("single_wav_v1"))
        XCTAssertTrue(result.removedFields.contains("localRecordingManifest.absolutePath"))
        XCTAssertTrue(result.removedFields.contains("localRecordingManifest.rawAudio"))
        XCTAssertTrue(result.removedFields.contains("localRecordingTracks[0].meetingContent"))
    }

    func testMicrophoneStreamDiagnosticsKeepSafeMetadataAndRemoveSensitiveFields() {
        let manifest: [String: DiagnosticFieldValue] = [
            "microphoneSelection": .object([
                "selectionResult": .string("accepted"),
                "mode": .string("user_selected"),
                "inputDisplayName": .string("Built-in Microphone"),
                "rawAudio": .string("forbidden")
            ]),
            "microphoneStream": .object([
                "streamKind": .string("app_owned_sample_source"),
                "permissionState": .string("granted"),
                "frameCount": .int(160_000),
                "absolutePath": .string("/Users/example/private/mic.wav")
            ]),
            "microphoneStreamHealth": .object([
                "gateStatus": .string("passed"),
                "failureReason": .string("none"),
                "cleanupReadiness": .string("ready_for_future_processing"),
                "transcriptText": .string("forbidden")
            ]),
            "rawAudio": .string("forbidden")
        ]

        let result = DiagnosticRedactor().redact(manifest)

        XCTAssertNotNil(result.manifest["microphoneSelection"])
        XCTAssertNotNil(result.manifest["microphoneStream"])
        XCTAssertNotNil(result.manifest["microphoneStreamHealth"])
        XCTAssertNil(result.manifest["rawAudio"])
        XCTAssertTrue(result.removedFields.contains("microphoneSelection.rawAudio"))
        XCTAssertTrue(result.removedFields.contains("microphoneStream.absolutePath"))
        XCTAssertTrue(result.removedFields.contains("microphoneStreamHealth.transcriptText"))
    }

    func testUploadQueueDiagnosticsKeepSafeMetadataAndRemoveSensitiveFields() {
        let manifest: [String: DiagnosticFieldValue] = [
            "uploadQueue": .object([
                "pendingCount": .int(1),
                "state": .string("retrying"),
                "absolutePath": .string("/Users/example/Recordings/session"),
                "uploadToken": .string("forbidden"),
                "uploadBearerToken": .string("forbidden")
            ]),
            "uploadQueueItems": .array([
                .object([
                    "id": .string("queue-id"),
                    "state": .string("blocked"),
                    "failureCategory": .string("auth_session"),
                    "failureReason": .string("Bearer leaked-token"),
                    "authorization": .string("Bearer forbidden"),
                    "signedUrl": .string("https://example.presigned/upload")
                ])
            ]),
            "serverTruth": .object([
                "acceptedBytesByTrack": .object([
                    "microphone": .int(128),
                    "system": .int(128),
                    "manifest": .int(64)
                ]),
                "mediaScribeCredentials": .string("forbidden")
            ]),
            "rawAudio": .string("forbidden")
        ]

        let result = DiagnosticRedactor().redact(manifest)

        XCTAssertNotNil(result.manifest["uploadQueue"])
        XCTAssertNotNil(result.manifest["uploadQueueItems"])
        XCTAssertNotNil(result.manifest["serverTruth"])
        XCTAssertNil(result.manifest["rawAudio"])
        XCTAssertTrue(result.removedFields.contains("uploadQueue.absolutePath"))
        XCTAssertTrue(result.removedFields.contains("uploadQueue.uploadToken"))
        XCTAssertTrue(result.removedFields.contains("uploadQueue.uploadBearerToken"))
        XCTAssertTrue(result.removedFields.contains("uploadQueueItems[0].failureReason"))
        XCTAssertTrue(result.removedFields.contains("uploadQueueItems[0].authorization"))
        XCTAssertTrue(result.removedFields.contains("uploadQueueItems[0].signedUrl"))
        XCTAssertTrue(result.removedFields.contains("serverTruth.mediaScribeCredentials"))
    }

    func testRecordingSyncDiagnosticsKeepRevisionMetadataAndRemoveSensitiveFields() {
        let manifest: [String: DiagnosticFieldValue] = [
            "localMediaRevisionId": .string("recording-sync-001--initial"),
            "mediaRevisionId": .string("019f-revision"),
            "syncGeneration": .int(2),
            "lastReconciledAt": .string("2026-06-18T01:00:00Z"),
            "syncConflictState": .string("server_ranges_inconsistent"),
            "mediaRevision": .object([
                "revisionNumber": .int(1),
                "sourceKind": .string("initial_recording"),
                "status": .string("accepted"),
                "manifestSha256": .string(String(repeating: "a", count: 64)),
                "storageObjectKey": .string("workspace/private/object-key"),
                "signedUrl": .string("https://example.presigned/download"),
                "rawTranscript": .string("forbidden transcript")
            ]),
            "recordingSyncState": .object([
                "meetingStatus": .string("uploading"),
                "acceptedBytesByTrack": .object([
                    "microphone": .int(128),
                    "system": .int(128),
                    "manifest": .int(64)
                ]),
                "temporaryUploadUrl": .string("https://example.presigned/upload")
            ]),
            "serverTruth": .object([
                "mediaRevisionId": .string("019f-revision"),
                "mediaScribeJobId": .string("private-job-id"),
                "objectStorageKey": .string("private/object")
            ]),
            "rawAudio": .string("forbidden")
        ]

        let result = DiagnosticRedactor().redact(manifest)

        XCTAssertEqual(result.manifest["localMediaRevisionId"], .string("recording-sync-001--initial"))
        XCTAssertEqual(result.manifest["mediaRevisionId"], .string("019f-revision"))
        XCTAssertEqual(result.manifest["syncGeneration"], .int(2))
        XCTAssertEqual(result.manifest["syncConflictState"], .string("server_ranges_inconsistent"))
        XCTAssertNotNil(result.manifest["mediaRevision"])
        XCTAssertNotNil(result.manifest["recordingSyncState"])
        XCTAssertNotNil(result.manifest["serverTruth"])
        XCTAssertNil(result.manifest["rawAudio"])
        XCTAssertTrue(result.removedFields.contains("mediaRevision.storageObjectKey"))
        XCTAssertTrue(result.removedFields.contains("mediaRevision.signedUrl"))
        XCTAssertTrue(result.removedFields.contains("mediaRevision.rawTranscript"))
        XCTAssertTrue(result.removedFields.contains("recordingSyncState.temporaryUploadUrl"))
        XCTAssertTrue(result.removedFields.contains("serverTruth.mediaScribeJobId"))
        XCTAssertTrue(result.removedFields.contains("serverTruth.objectStorageKey"))
    }

    func testDesktopSyncReviewDiagnosticsKeepResultMetadataOnly() {
        let manifest: [String: DiagnosticFieldValue] = [
            "desktopSyncState": .object([
                "reviewStatus": .string("ready"),
                "mediaRevisionId": .string("019f-revision"),
                "transcriptAvailable": .bool(true),
                "diarizationAvailable": .bool(true),
                "contentAvailable": .bool(true),
                "transcriptText": .string("forbidden transcript"),
                "audioDownloadUrl": .string("https://example.invalid/audio"),
                "signedUrl": .string("https://example.presigned/review")
            ]),
            "serverTruth": .object([
                "meetingId": .string("meeting-045"),
                "mediaRevisionId": .string("019f-revision"),
                "workflowId": .string("processing/019f-revision"),
                "mediaScribeApiKey": .string("forbidden"),
                "storageObjectKey": .string("private/object")
            ]),
            "uploadQueueItems": .array([
                .object([
                    "state": .string("uploaded"),
                    "qualityWarning": .string("leakage_detected"),
                    "failureReason": .string("Bearer forbidden")
                ])
            ]),
            "rawAudio": .string("forbidden")
        ]

        let result = DiagnosticRedactor().redact(manifest)

        XCTAssertNotNil(result.manifest["desktopSyncState"])
        XCTAssertNotNil(result.manifest["serverTruth"])
        XCTAssertNotNil(result.manifest["uploadQueueItems"])
        XCTAssertNil(result.manifest["rawAudio"])
        XCTAssertTrue(result.removedFields.contains("desktopSyncState.transcriptText"))
        XCTAssertTrue(result.removedFields.contains("desktopSyncState.audioDownloadUrl"))
        XCTAssertTrue(result.removedFields.contains("desktopSyncState.signedUrl"))
        XCTAssertTrue(result.removedFields.contains("serverTruth.mediaScribeApiKey"))
        XCTAssertTrue(result.removedFields.contains("serverTruth.storageObjectKey"))
        XCTAssertTrue(result.removedFields.contains("uploadQueueItems[0].failureReason"))
    }
}
#endif
