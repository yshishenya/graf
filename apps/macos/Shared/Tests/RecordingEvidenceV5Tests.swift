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
            schemaVersion: LocalRecordingManifest.schemaVersion,
            sessionId: "session",
            createdAt: Date(timeIntervalSince1970: 1),
            startedAt: Date(timeIntervalSince1970: 1),
            stoppedAt: Date(timeIntervalSince1970: 2),
            status: .saved,
            directoryId: "safe-dir",
            transcriptionReadiness: .ready,
            mediaScribeSourceMode: "single_wav_v1",
            canonicalMixProfile: LocalRecordingManifest.canonicalMixProfileVersion,
            tracks: canonicalEvidenceTracks(),
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
        )

        let evidence = RecordingEvidenceService().localRecordingEvidence(for: manifest)

        XCTAssertEqual(evidence["sessionId"], "session")
        XCTAssertEqual(evidence["status"], "saved")
        XCTAssertEqual(evidence["transcriptionReadiness"], "ready")
        XCTAssertEqual(evidence["mediaScribeSourceMode"], "single_wav_v1")
        XCTAssertEqual(evidence["mediaScribeFields"], "media_file,playback_file")
        XCTAssertEqual(evidence["trackFormats"], "wav-pcm-s16le,m4a-aac-lc")
        XCTAssertEqual(evidence["externalEgressStarted"], "false")
        XCTAssertEqual(evidence["recordingMicrophoneSelectionMode"], "macos_default_fallback")
        XCTAssertEqual(evidence["recordingMicrophoneSelectionResult"], "accepted")
        XCTAssertEqual(evidence["recordingMicrophoneInputDisplayName"], "Built-in Microphone")
        XCTAssertEqual(evidence["microphoneStreamKind"], "app_owned_sample_source")
        XCTAssertEqual(evidence["microphoneStreamGateStatus"], "passed")
        XCTAssertEqual(evidence["microphoneFutureProcessingReadiness"], "ready_for_future_processing")
        XCTAssertEqual(evidence["microphoneGraphDiagnosticSafe"], "true")
        XCTAssertNil(evidence["rawAudio"])
        XCTAssertNil(evidence["absolutePath"])
    }


    func testLocalRecordingDiagnosticBundlePreservesNoEgressTruth() throws {
        let manifest = LocalRecordingManifest(
            schemaVersion: LocalRecordingManifest.schemaVersion,
            sessionId: "session",
            createdAt: Date(timeIntervalSince1970: 1),
            startedAt: Date(timeIntervalSince1970: 1),
            stoppedAt: Date(timeIntervalSince1970: 2),
            status: .saved,
            directoryId: "safe-dir",
            transcriptionReadiness: .ready,
            mediaScribeSourceMode: "single_wav_v1",
            canonicalMixProfile: LocalRecordingManifest.canonicalMixProfileVersion,
            tracks: canonicalEvidenceTracks()
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

    private func canonicalEvidenceTracks() -> [LocalRecordingTrack] {
        [
            LocalRecordingTrack(
                trackId: "media",
                role: .mixedMeetingAudio,
                sourceKind: .canonicalMix,
                mediaScribeField: .mediaFile,
                status: .saved,
                fileName: "meeting-transcription.wav",
                format: "wav-pcm-s16le",
                sampleRate: 16_000,
                channelCount: 1,
                bitsPerSample: 16,
                durationMs: 1_000,
                byteCount: 32_044,
                sha256: String(repeating: "a", count: 64),
                frameCount: 16_000,
                timelineStartMs: 0,
                timelineAligned: true
            ),
            LocalRecordingTrack(
                trackId: "playback",
                role: .reviewPlayback,
                sourceKind: .canonicalMix,
                mediaScribeField: .playbackFile,
                status: .saved,
                fileName: "meeting-review.m4a",
                format: "m4a-aac-lc",
                sampleRate: 48_000,
                channelCount: 1,
                bitsPerSample: 0,
                durationMs: 1_000,
                byteCount: 12_000,
                sha256: String(repeating: "b", count: 64),
                frameCount: 48_000,
                aacPresentationFrameDelta: 0,
                timelineStartMs: 0,
                timelineAligned: true
            )
        ]
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

}
#endif
