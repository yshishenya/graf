import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class AppleVoiceProcessingSpikeContractTests: XCTestCase {
    func testAppleProcessingManifestMetadataIsDiagnosticSafeAndOptional() throws {
        let manifest = LocalRecordingManifest(
            sessionId: "session",
            createdAt: Date(timeIntervalSince1970: 30),
            startedAt: Date(timeIntervalSince1970: 10),
            stoppedAt: Date(timeIntervalSince1970: 20),
            status: .saved,
            directoryId: "dir",
            transcriptionReadiness: .ready,
            tracks: [
                contractCompleteTrack(role: .localMic),
                contractCompleteTrack(role: .remoteSpeaker)
            ],
            scopeApproval: contractAcceptedScopeApproval(),
            permissions: contractGrantedPermissions(),
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
                        diagnosticSafe: true,
                        failureReason: "system_controlled_mic_mode"
                    )
                ],
                nextStepRecommendation: .deferToWebRTCAEC3
            )
        )
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        let data = try encoder.encode(manifest)
        let object = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        let appleObject = object?["appleProcessingOutcome"] as? [String: Any]
        let json = String(decoding: data, as: UTF8.self)

        XCTAssertEqual(appleObject?["feature"] as? String, "038-apple-voice-processing-spike")
        XCTAssertEqual(appleObject?["diagnosticSafe"] as? Bool, true)
        XCTAssertEqual(appleObject?["primaryOutcome"] as? String, AppleProcessingOutcomeState.acceptedForGuidanceOnly.rawValue)
        XCTAssertFalse(json.contains("rawAudio"))
        XCTAssertFalse(json.contains("transcriptText"))
        XCTAssertFalse(json.contains("signedUrl"))
        XCTAssertFalse(manifest.appleProcessingOutcome?.canClaimCleanBuiltinSpeakerphone ?? true)
    }

    func testLegacyManifestDecodesWithoutAppleProcessingMetadata() throws {
        let json = """
        {
          "schemaVersion": "local-recording-manifest.v3",
          "sessionId": "legacy-session",
          "createdAt": "2026-06-22T00:00:30Z",
          "startedAt": "2026-06-22T00:00:10Z",
          "stoppedAt": "2026-06-22T00:00:20Z",
          "status": "saved",
          "directoryId": "dir",
          "manifestFileName": "manifest.json",
          "transcriptionReadiness": "ready",
          "mediaScribeSourceMode": "dual",
          "tracks": [],
          "externalEgressStarted": false,
          "transcriptionStarted": false,
          "diagnosticSafe": true,
          "localDeletionRegistered": false,
          "failureReason": "none",
          "durationDifferenceSeconds": 0
        }
        """
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601

        let manifest = try decoder.decode(LocalRecordingManifest.self, from: Data(json.utf8))

        XCTAssertNil(manifest.appleProcessingOutcome)
    }

    func testOutcomeVocabularyDoesNotContainCleanSpeakerphoneClaims() {
        let vocabulary = [
            AppleProcessingOutcomeState.acceptedForBuiltinSpeakerphone.rawValue,
            AppleProcessingOutcomeState.acceptedForGuidanceOnly.rawValue,
            AppleProcessingOutcomeState.acceptedForHeadsetRoutesOnly.rawValue,
            AppleProcessingOutcomeState.blockedRouteTopology.rawValue,
            AppleProcessingOutcomeState.blockedQuality.rawValue,
            AppleProcessingOutcomeState.blockedStability.rawValue,
            AppleProcessingOutcomeState.deferToWebRTCAEC3.rawValue
        ].joined(separator: " ")

        for forbidden in ["cleaned", "speakerphone_clean", "clean_speakerphone"] {
            XCTAssertFalse(vocabulary.contains(forbidden), "\(forbidden) must stay out of 038 outcome vocabulary")
        }
    }
}

private func contractCompleteTrack(role: AudioTrackRole) -> LocalRecordingTrack {
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

private func contractAcceptedScopeApproval() -> CaptureScopeApproval {
    CaptureScopeApproval(
        scopeApprovalId: "scope",
        scopeKind: .display,
        sourceDisplayName: "Current Display",
        approvedAt: Date(timeIntervalSince1970: 9),
        approvalMode: .userConfirmedSuggestedScope,
        eligibleReason: .manualMeetingScope
    )
}

private func contractGrantedPermissions() -> SystemAudioPermissionSnapshot {
    SystemAudioPermissionSnapshot(
        microphone: .granted,
        systemAudio: .granted,
        evaluatedAt: Date(timeIntervalSince1970: 9)
    )
}
#endif
