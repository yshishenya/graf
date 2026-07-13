import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class RecordingEvidenceTests: XCTestCase {
    func testRecordingEvidenceEventIsMetadataOnlyAndDiagnosticSafe() {
        let service = RecordingEvidenceService(
            clock: { Date(timeIntervalSince1970: 1_777_777_777) },
            idFactory: { "event-1" }
        )
        let session = makeSession(state: .active, indicator: .active, stopAvailable: true)

        let event = service.event(
            for: session,
            type: .started,
            initiator: .user
        )

        XCTAssertEqual(event.eventId, "event-1")
        XCTAssertEqual(event.sessionId, session.id)
        XCTAssertEqual(event.eventType, .started)
        XCTAssertEqual(event.captureState, .active)
        XCTAssertEqual(event.indicatorState, .active)
        XCTAssertTrue(event.stopActionAvailable)
        XCTAssertTrue(event.diagnosticSafe)
    }

    func testBlockedStartEvidenceKeepsReasonAndRecoveryAction() {
        let service = RecordingEvidenceService(
            clock: { Date(timeIntervalSince1970: 1_777_777_777) },
            idFactory: { "blocked-event" }
        )
        let session = makeSession(state: .failed, indicator: .error, stopAvailable: false)
        let prerequisite = RecordingPrerequisiteSnapshot(
            policyAllowsRecording: true,
            microphonePermissionGranted: true,
            systemAudioPermissionGranted: false,
            storageRisk: .healthy,
            indicatorAvailable: true,
            sourceAppEligibility: .eligible,
            blockedReason: .permissionDenied,
            recoveryAction: "Grant Screen & System Audio permission in System Settings",
            evaluatedAt: Date(timeIntervalSince1970: 1_777_777_777)
        )

        let event = service.startBlocked(session: session, prerequisite: prerequisite)

        XCTAssertEqual(event.eventType, .startBlocked)
        XCTAssertEqual(event.blockedReason, .permissionDenied)
        XCTAssertEqual(event.recoveryAction, "Grant Screen & System Audio permission in System Settings")
    }

    func testRecordingEvidenceDiagnosticBundleRemovesForbiddenContent() throws {
        let event = RecordingEvidenceEvent(
            eventId: "event",
            sessionId: "session",
            eventType: .started,
            occurredAt: Date(timeIntervalSince1970: 1_777_777_777),
            initiator: .user,
            captureState: .active,
            indicatorState: .active,
            stopActionAvailable: true
        )

        let bundle = try DiagnosticBundleService().buildRecordingEvidenceBundle(
            events: [event],
            manifestOverrides: [
                "rawAudio": .string("not allowed"),
                "meetingContent": .string("not allowed")
            ]
        )

        XCTAssertNotNil(bundle.manifest["recordingEvidence"])
        XCTAssertEqual(bundle.manifest["captureState"], .string("active"))
        XCTAssertNil(bundle.manifest["rawAudio"])
        XCTAssertNil(bundle.manifest["meetingContent"])
        XCTAssertEqual(bundle.redactionState, .blockedSensitiveContent)
    }

    func testLocalRecordingEvidenceSummaryIsMetadataOnly() {
        let selection = RecordingMicrophoneSelection(
            selectionId: "selection-recording-evidence",
            mode: .macOSDefaultFallback,
            inputDeviceId: "built-in-mic",
            inputDisplayName: "Built-in Microphone",
            deviceClass: .builtIn,
            workingDeviceKind: .physical,
            selectionResult: .accepted,
            resolvedAt: Date(timeIntervalSince1970: 1)
        )
        let manifest = LocalRecordingManifest(
            sessionId: "session",
            createdAt: Date(timeIntervalSince1970: 1),
            startedAt: Date(timeIntervalSince1970: 1),
            stoppedAt: Date(timeIntervalSince1970: 2),
            status: .saved,
            directoryId: "safe-dir",
            transcriptionReadiness: .ready,
            mediaScribeSourceMode: "dual",
            tracks: [
                LocalRecordingTrack(
                    trackId: "mic",
                    role: .localMic,
                    status: .saved,
                    fileName: "mic.wav",
                    format: "wav-pcm-s16le",
                    sampleRate: 16_000,
                    channelCount: 1,
                    bitsPerSample: 16,
                    durationMs: 1000,
                    byteCount: 100,
                    frameCount: 16_000,
                    timelineStartMs: 0,
                    timelineAligned: true
                ),
                LocalRecordingTrack(
                    trackId: "remote",
                    role: .remoteSpeaker,
                    status: .saved,
                    fileName: "incoming.wav",
                    format: "wav-pcm-s16le",
                    sampleRate: 16_000,
                    channelCount: 1,
                    bitsPerSample: 16,
                    durationMs: 1000,
                    byteCount: 100,
                    frameCount: 16_000,
                    timelineStartMs: 0,
                    timelineAligned: true
                )
            ],
            microphoneSelection: selection,
            microphoneStream: AppOwnedMicrophoneStreamSession(
                sessionId: "session",
                selection: selection,
                permissionState: .granted,
                streamKind: .appOwnedSampleSource,
                stoppedAt: Date(timeIntervalSince1970: 2),
                sampleRate: 48_000,
                channelCount: 1,
                writerSampleRate: 16_000,
                writerChannelCount: 1,
                frameCount: 16_000,
                failureReason: .none
            ),
            microphoneStreamHealth: MicrophoneStreamHealth(
                gateStatus: .passed,
                failureReason: .none,
                framesObserved: true,
                timingConfidence: .usable,
                silenceStatus: .audible,
                cleanupReadiness: .readyForFutureProcessing,
                evidenceCodes: ["mic_graph_ready"]
            ),
            appleProcessingOutcome: AppleProcessingOutcome(
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
                        lineageStatus: .guidanceOnly,
                        speechPreservationStatus: .notMeasured,
                        alignmentStatus: .notMeasured,
                        stabilityStatus: .unproven,
                        diagnosticSafe: true
                    )
                ],
                nextStepRecommendation: .deferToWebRTCAEC3
            )
        )

        let evidence = RecordingEvidenceService().localRecordingEvidence(for: manifest)

        XCTAssertEqual(evidence["sessionId"], "session")
        XCTAssertEqual(evidence["status"], "saved")
        XCTAssertEqual(evidence["transcriptionReadiness"], "ready")
        XCTAssertEqual(evidence["mediaScribeSourceMode"], "dual")
        XCTAssertEqual(evidence["mediaScribeFields"], "mic_file,incoming_file")
        XCTAssertEqual(evidence["trackFormats"], "wav-pcm-s16le,wav-pcm-s16le")
        XCTAssertEqual(evidence["externalEgressStarted"], "false")
        XCTAssertEqual(evidence["recordingMicrophoneSelectionMode"], "macos_default_fallback")
        XCTAssertEqual(evidence["recordingMicrophoneSelectionResult"], "accepted")
        XCTAssertEqual(evidence["recordingMicrophoneInputDisplayName"], "Built-in Microphone")
        XCTAssertEqual(evidence["microphoneStreamKind"], "app_owned_sample_source")
        XCTAssertEqual(evidence["microphoneStreamGateStatus"], "passed")
        XCTAssertEqual(evidence["microphoneFutureProcessingReadiness"], "ready_for_future_processing")
        XCTAssertEqual(evidence["microphoneGraphDiagnosticSafe"], "true")
        XCTAssertEqual(evidence["appleProcessingPrimaryOutcome"], "accepted_for_guidance_only")
        XCTAssertEqual(evidence["appleProcessingNextStepRecommendation"], "defer_to_webrtc_aec3")
        XCTAssertEqual(evidence["appleProcessingValidationRowCount"], "1")
        XCTAssertEqual(evidence["appleProcessingCanClaimCleanBuiltinSpeakerphone"], "false")
        XCTAssertNil(evidence["rawAudio"])
        XCTAssertNil(evidence["absolutePath"])
    }

    func testLocalRecordingEvidenceIncludesWebRTCAEC3PackageTruthWithoutPrivateContent() {
        let manifest = LocalRecordingManifest(
            sessionId: "session-aec3",
            createdAt: Date(timeIntervalSince1970: 1),
            startedAt: Date(timeIntervalSince1970: 1),
            stoppedAt: Date(timeIntervalSince1970: 2),
            status: .degraded,
            directoryId: "safe-dir",
            transcriptionReadiness: .degraded,
            mediaScribeSourceMode: "dual",
            tracks: [
                LocalRecordingTrack(
                    trackId: "mic",
                    role: .localMic,
                    status: .saved,
                    fileName: "mic.wav",
                    format: "wav-pcm-s16le",
                    sampleRate: 16_000,
                    channelCount: 1,
                    bitsPerSample: 16,
                    durationMs: 1_000,
                    byteCount: 32_044,
                    frameCount: 16_000,
                    timelineAligned: true
                ),
                LocalRecordingTrack(
                    trackId: "incoming",
                    role: .remoteSpeaker,
                    status: .saved,
                    fileName: "incoming.wav",
                    format: "wav-pcm-s16le",
                    sampleRate: 16_000,
                    channelCount: 1,
                    bitsPerSample: 16,
                    durationMs: 1_000,
                    byteCount: 32_044,
                    frameCount: 16_000,
                    timelineAligned: true
                )
            ],
            webRTCAEC3Outcome: recordingEvidenceWebRTCAEC3GuidanceOutcome()
        )

        let evidence = RecordingEvidenceService().localRecordingEvidence(for: manifest)

        XCTAssertEqual(evidence["webRTCAEC3PrimaryOutcome"], "accepted_for_guidance_only")
        XCTAssertEqual(evidence["webRTCAEC3NextStepRecommendation"], "guidance_only")
        XCTAssertEqual(evidence["webRTCAEC3ValidationRowCount"], "1")
        XCTAssertEqual(evidence["webRTCAEC3ThresholdProfileId"], "aec3-threshold-profile-v1")
        XCTAssertEqual(evidence["webRTCAEC3CanClaimCleanBuiltInSpeakerphone"], "false")
        XCTAssertEqual(evidence["webRTCAEC3PackageTruth"], "original_microphone_truth")
        XCTAssertNil(evidence["rawAudio"])
        XCTAssertNil(evidence["transcriptText"])
        XCTAssertNil(evidence["privateLocalPath"])
    }

    func testLocalRecordingDiagnosticBundlePreservesNoEgressTruth() throws {
        let manifest = LocalRecordingManifest(
            sessionId: "session",
            createdAt: Date(timeIntervalSince1970: 1),
            startedAt: Date(timeIntervalSince1970: 1),
            stoppedAt: Date(timeIntervalSince1970: 2),
            status: .saved,
            directoryId: "safe-dir",
            transcriptionReadiness: .ready,
            mediaScribeSourceMode: "dual",
            tracks: [
                LocalRecordingTrack(
                    trackId: "mic",
                    role: .localMic,
                    status: .saved,
                    fileName: "mic.wav",
                    format: "wav-pcm-s16le",
                    sampleRate: 16_000,
                    channelCount: 1,
                    bitsPerSample: 16,
                    durationMs: 1000,
                    byteCount: 100,
                    frameCount: 16_000,
                    timelineStartMs: 0,
                    timelineAligned: true
                ),
                LocalRecordingTrack(
                    trackId: "remote",
                    role: .remoteSpeaker,
                    status: .saved,
                    fileName: "incoming.wav",
                    format: "wav-pcm-s16le",
                    sampleRate: 16_000,
                    channelCount: 1,
                    bitsPerSample: 16,
                    durationMs: 1000,
                    byteCount: 100,
                    frameCount: 16_000,
                    timelineStartMs: 0,
                    timelineAligned: true
                )
            ]
        )

        let bundle = try DiagnosticBundleService().buildLocalRecordingBundle(
            manifest: manifest,
            manifestOverrides: [
                "rawAudio": .string("not allowed"),
                "signedUrl": .string("not allowed")
            ]
        )

        guard case .object(let diagnosticManifest)? = bundle.manifest["localRecordingManifest"] else {
            XCTFail("Expected local recording manifest diagnostics")
            return
        }
        guard case .object(let summary)? = bundle.manifest["localRecordingEvidence"] else {
            XCTFail("Expected local recording evidence summary")
            return
        }

        XCTAssertEqual(diagnosticManifest["externalEgressStarted"], .bool(false))
        XCTAssertEqual(diagnosticManifest["transcriptionStarted"], .bool(false))
        XCTAssertEqual(diagnosticManifest["diagnosticSafe"], .bool(true))
        XCTAssertEqual(summary["diagnosticSafe"], .bool(true))
        XCTAssertEqual(bundle.redactionState, .blockedSensitiveContent)
        XCTAssertNil(bundle.manifest["rawAudio"])
        XCTAssertNil(bundle.manifest["signedUrl"])
    }

    private func makeSession(
        state: CaptureSessionState,
        indicator: VisibleIndicatorState,
        stopAvailable: Bool
    ) -> CaptureSession {
        CaptureSession(
            id: "recording-evidence-session",
            mode: .audioRecording,
            state: state,
            sourceAppEligibility: .eligible,
            policySnapshotRef: "policy",
            triggerEvidence: [:],
            visibleIndicatorState: indicator,
            stopActionAvailable: stopAvailable,
            bufferSummaryId: nil,
            startedAt: Date(timeIntervalSince1970: 1_777_777_700),
            stoppedAt: Date(timeIntervalSince1970: 1_777_777_777)
        )
    }

    private func recordingEvidenceWebRTCAEC3GuidanceOutcome() -> WebRTCAEC3DecisionRecord {
        WebRTCAEC3DecisionRecord(
            candidateId: "aec3-evidence-guidance",
            primaryOutcome: .acceptedForGuidanceOnly,
            validationRows: [
                WebRTCAEC3ValidationRow(
                    rowId: "aec3-evidence-row",
                    candidateId: "aec3-evidence-guidance",
                    scenarioFamily: .farEndOnlyLeakage,
                    validationKind: .fullFile,
                    routeClass: .builtInSpeakerphone,
                    baselineStatus: .leakageDetected,
                    candidateStatus: .unproven,
                    lineageStatus: .candidateMetadata,
                    speechPreservationStatus: .notMeasured,
                    residualLeakageStatus: .unproven,
                    timingConfidence: .notMeasured,
                    referenceStatus: .present,
                    stabilityStatus: .unproven,
                    thresholdProfileId: WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId,
                    thresholdSummary: "guidance_only",
                    appStatusState: .usingOriginalMicTruth,
                    diagnosticSafe: true
                )
            ],
            nextStepRecommendation: .guidanceOnly
        )
    }
}
#endif
