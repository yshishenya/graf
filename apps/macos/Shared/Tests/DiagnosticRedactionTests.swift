import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class DiagnosticRedactionTests: XCTestCase {
    func testReadinessEvidenceDiagnosticsKeepMetadataAndRemoveSensitiveFields() {
        let manifest: [String: DiagnosticFieldValue] = [
            "liveRouteReadiness": .object([
                "status": .string("failed"),
                "failureReason": .string("missing_valid_frames"),
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
            "routeStatus": .string("failed"),
            "recoveryActionId": .string("rerun_readiness_check")
        ]

        let result = DiagnosticRedactor().redact(manifest)

        XCTAssertNotNil(result.manifest["liveRouteReadiness"])
        XCTAssertNotNil(result.manifest["browserTargetEvidence"])
        XCTAssertNotNil(result.manifest["routeStatus"])
        XCTAssertNil(result.manifest["transcriptText"])
        XCTAssertTrue(result.removedFields.contains("liveRouteReadiness.rawAudio"))
        XCTAssertTrue(result.removedFields.contains("browserTargetEvidence[0].meetingContent"))
    }

    func testLiveRouteReadinessBundleKeepsOnlyMetadata() throws {
        let now = Date(timeIntervalSince1970: 1_779_887_120)
        let result = LiveRouteReadinessResult(
            status: .failed,
            microphoneEvidence: MicrophonePathEvidence(
                selectedPhysicalDeviceId: "built-in-input",
                selectedPhysicalDeviceName: "MacBook Pro Microphone",
                status: .failed,
                validFrameCount: 0,
                emptyBufferCount: 1,
                capturabilityStatus: .notCapturable,
                selfRoutingRejected: false,
                failureReason: "missing_valid_frames",
                checkedAt: now
            ),
            speakerEvidence: SpeakerPathEvidence(
                selectedPhysicalOutputId: "built-in-output",
                selectedPhysicalOutputName: "MacBook Pro Speakers",
                status: .passed,
                stimulusObserved: true,
                validFrameCount: 1,
                emptyBufferCount: 0,
                selfRoutingRejected: false,
                checkedAt: now
            ),
            checkedAt: now,
            recoveryAction: "rerun_readiness_check"
        )

        let bundle = try DiagnosticBundleService().buildLiveRouteReadinessBundle(result: result)

        XCTAssertEqual(bundle.redactionState, .redacted)
        XCTAssertNotNil(bundle.manifest["liveRouteReadiness"])
        XCTAssertNotNil(bundle.manifest["microphonePathEvidence"])
        XCTAssertNotNil(bundle.manifest["speakerPathEvidence"])
        XCTAssertNil(bundle.manifest["rawAudio"])
        XCTAssertNil(bundle.manifest["transcriptText"])
    }

    func testLivePassthroughBundleKeepsOnlyMetadata() throws {
        let now = Date(timeIntervalSince1970: 1_779_887_120)
        let session = LivePassthroughSession(
            sessionId: "passthrough-1",
            status: .active,
            microphonePath: MicrophonePassthroughPath(
                physicalInputId: "built-in-input",
                physicalInputName: "MacBook Pro Microphone",
                status: .ready,
                validFrameObserved: true
            ),
            speakerPath: SpeakerPassthroughPath(
                physicalOutputId: "built-in-output",
                physicalOutputName: "MacBook Pro Speakers",
                status: .ready,
                stimulusObserved: true
            ),
            healthEvidence: PassthroughHealthEvidence(
                appHeartbeatStatus: .connected,
                latencyMs: 21,
                leakageDbBelowReference: 49
            ),
            browserEvidence: [
                PassthroughBrowserCallEvidence(
                    targetName: "Chrome",
                    targetVersion: "local",
                    selectedMicrophone: "2brain Rec Microphone",
                    selectedSpeaker: "2brain Rec Speaker",
                    localSpeechUsable: true,
                    remoteAudioUsable: true,
                    status: .passed,
                    checkedAt: now
                )
            ],
            startedAt: now
        )

        let bundle = try DiagnosticBundleService().buildLivePassthroughBundle(session: session)

        XCTAssertEqual(bundle.redactionState, .redacted)
        XCTAssertNotNil(bundle.manifest["livePassthrough"])
        XCTAssertNotNil(bundle.manifest["microphonePassthroughPath"])
        XCTAssertNotNil(bundle.manifest["speakerPassthroughPath"])
        XCTAssertNotNil(bundle.manifest["passthroughHealth"])
        XCTAssertNil(bundle.manifest["rawAudio"])
        XCTAssertNil(bundle.manifest["transcriptText"])
    }

    func testReleaseHardeningBundleKeepsOnlyMetadata() throws {
        let now = Date(timeIntervalSince1970: 1_780_284_000)
        let run = ReleaseHardeningRun(
            runId: "005-local",
            createdAt: now,
            macOSVersion: "14.5",
            appBuild: "local",
            driverBuild: "local",
            result: .blocked,
            notes: "No-hang gate pending",
            evidenceFamilies: [.installedRuntime, .noHang, .deferredRecordingAcceptance]
        )

        let bundle = try DiagnosticBundleService().buildReleaseHardeningBundle(
            run: run,
            shortSmokeEvidence: [
                ShortSmokeEvidence(
                    targetApp: "Chrome",
                    selectedInput: "2brain Rec Microphone",
                    selectedOutput: "2brain Rec Speaker",
                    localSpeechObserved: true,
                    remoteAudioObserved: true,
                    loopbackObserved: false,
                    recordingStarted: false,
                    result: .passed
                )
            ],
            noHangEvidence: [
                CoreAudioNoHangEvidence(
                    targetSurface: "macOS Sound settings",
                    openedWithinSeconds: 2.0,
                    coreaudiodCPUPeakPercent: 4.0,
                    coreaudiodCPUSustainedPercent: 1.0,
                    routeStateBefore: .ready,
                    routeStateAfter: .ready,
                    result: .passed
                )
            ],
            deferredRecordingAcceptance: DeferredRecordingAcceptanceState()
        )

        XCTAssertEqual(bundle.redactionState, .redacted)
        XCTAssertNotNil(bundle.manifest["releaseHardeningRun"])
        XCTAssertNotNil(bundle.manifest["shortSmokeEvidence"])
        XCTAssertNotNil(bundle.manifest["coreAudioNoHangEvidence"])
        XCTAssertNotNil(bundle.manifest["deferredRecordingAcceptance"])
        XCTAssertNil(bundle.manifest["rawAudio"])
        XCTAssertNil(bundle.manifest["transcriptText"])
        XCTAssertNil(bundle.manifest["meetingContent"])
    }

    func testLowResourceRouteTruthKeepsMetadataAndRemovesSensitiveFields() {
        let manifest: [String: DiagnosticFieldValue] = [
            "lowResourceRouteTruth": .object([
                "resourceState": .string("active"),
                "publication": .object([
                    "microphoneVisible": .bool(true),
                    "speakerVisible": .bool(true)
                ]),
                "recordingTrigger": .object([
                    "recordingTriggerState": .string("off"),
                    "transcriptText": .string("forbidden")
                ])
            ]),
            "lowResourceStartupAttempts": .array([
                .object([
                    "durationMs": .int(2500),
                    "outcome": .string("ready"),
                    "signedUrl": .string("forbidden")
                ])
            ]),
            "rawAudio": .string("forbidden")
        ]

        let result = DiagnosticRedactor().redact(manifest)

        XCTAssertNotNil(result.manifest["lowResourceRouteTruth"])
        XCTAssertNotNil(result.manifest["lowResourceStartupAttempts"])
        XCTAssertNil(result.manifest["rawAudio"])
        XCTAssertTrue(result.removedFields.contains("lowResourceRouteTruth.recordingTrigger.transcriptText"))
        XCTAssertTrue(result.removedFields.contains("lowResourceStartupAttempts[0].signedUrl"))
    }

    func testRecordingEvidenceKeepsMetadataAndRemovesSensitiveFields() {
        let manifest: [String: DiagnosticFieldValue] = [
            "recordingEvidence": .array([
                .object([
                    "sessionId": .string("session"),
                    "eventType": .string("recording.started"),
                    "routeState": .string("active"),
                    "indicatorState": .string("active"),
                    "transcriptText": .string("forbidden")
                ])
            ]),
            "recordingPrerequisites": .array([
                .object([
                    "routeState": .string("active"),
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

    func testRouteEvidenceKeepsMetadataAndRemovesForbiddenContent() {
        let manifest: [String: DiagnosticFieldValue] = [
            "routeEvidenceEvents": .array([
                .object([
                    "family": .string("client_activity"),
                    "name": .string("client_activity.fresh"),
                    "sessionId": .string("route-session-019"),
                    "participantSpeech": .string("forbidden meeting words")
                ])
            ]),
            "validationRunEvidence": .object([
                "runId": .string("019-dev-run"),
                "result": .string("accepted"),
                "rawTranscript": .string("forbidden transcript")
            ]),
            "routeEvidenceFile": .string("route-evidence.jsonl"),
            "credentialPath": .string("/tmp/secret")
        ]

        let result = DiagnosticRedactor().redact(manifest)

        XCTAssertNotNil(result.manifest["routeEvidenceEvents"])
        XCTAssertNotNil(result.manifest["validationRunEvidence"])
        XCTAssertNotNil(result.manifest["routeEvidenceFile"])
        XCTAssertNil(result.manifest["credentialPath"])
        XCTAssertTrue(result.removedFields.contains("routeEvidenceEvents[0].participantSpeech"))
        XCTAssertTrue(result.removedFields.contains("validationRunEvidence.rawTranscript"))
    }

    func testLocalRecordingEvidenceKeepsSafeMetadataAndRemovesSensitiveFields() {
        let manifest: [String: DiagnosticFieldValue] = [
            "localRecordingManifest": .object([
                "sessionId": .string("session"),
                "directoryId": .string("20260602-session"),
                "transcriptionReadiness": .string("ready"),
                "mediaScribeSourceMode": .string("dual"),
                "absolutePath": .string("/Users/example/Recordings/session"),
                "rawAudio": .string("forbidden")
            ]),
            "localRecordingTracks": .array([
                .object([
                    "role": .string("local_mic"),
                    "mediaScribeField": .string("mic_file"),
                    "fileName": .string("mic.wav"),
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
        XCTAssertEqual(localRecordingManifest["mediaScribeSourceMode"], .string("dual"))
        XCTAssertTrue(result.removedFields.contains("localRecordingManifest.absolutePath"))
        XCTAssertTrue(result.removedFields.contains("localRecordingManifest.rawAudio"))
        XCTAssertTrue(result.removedFields.contains("localRecordingTracks[0].meetingContent"))
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
}
#endif
