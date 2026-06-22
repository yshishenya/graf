import Foundation
import TwoBrainRecAppCore
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

    func testManifestFixtureWithAppleCandidateMetadataDecodesWithoutRawAudio() throws {
        let fixtureURL = try XCTUnwrap(contractFixtureURL(
            "apps/macos/Shared/Tests/Fixtures/AppleVoiceProcessing/manifest-with-apple-candidate.json"
        ))
        let data = try Data(contentsOf: fixtureURL)
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601

        let manifest = try decoder.decode(LocalRecordingManifest.self, from: data)
        let json = String(decoding: data, as: UTF8.self)

        XCTAssertEqual(manifest.schemaVersion, LocalRecordingManifest.schemaVersion)
        XCTAssertEqual(manifest.appleProcessingOutcome?.feature, "038-apple-voice-processing-spike")
        XCTAssertEqual(manifest.appleProcessingOutcome?.primaryOutcome, .acceptedForGuidanceOnly)
        XCTAssertEqual(manifest.appleProcessingOutcome?.validationRows.first?.lineageStatus, .candidateMetadata)
        XCTAssertEqual(Set(manifest.tracks.map(\.role)), Set<AudioTrackRole>([.localMic, .remoteSpeaker]))
        XCTAssertEqual(Set(manifest.tracks.map(\.evidenceRole)), Set<LeakageEvidenceRole>([.original]))
        XCTAssertFalse(json.contains("rawAudio"))
        XCTAssertFalse(json.contains("transcriptText"))
        XCTAssertFalse(json.contains("signedUrl"))
        XCTAssertFalse(json.contains("mediaScribeCredential"))
    }

    func testSummariesCannotClaimCleanSpeakerphoneWithoutAcceptedBuiltinGates() {
        let service = AppleVoiceProcessingEvaluationService()
        let outcomes = [
            contractAppleOutcome(state: .acceptedForGuidanceOnly, nextStep: .guidanceOnly, failureReason: "system_controlled_mic_mode"),
            contractAppleOutcome(state: .blockedRouteTopology, nextStep: .deferToWebRTCAEC3, failureReason: "route_topology_blocked"),
            contractAppleOutcome(state: .deferToWebRTCAEC3, nextStep: .deferToWebRTCAEC3, failureReason: "required_rows_missing"),
            contractAppleOutcome(state: .acceptedForBuiltinSpeakerphone, nextStep: .promoteAppleProcessing, failureReason: nil)
        ]

        for outcome in outcomes {
            let summary = service.finalOutcomeSummary(outcome)

            XCTAssertFalse(summary.canClaimCleanBuiltinSpeakerphone)
            XCTAssertFalse(summary.containsCleanSpeakerphoneClaim)
            XCTAssertFalse(summary.userFacingSummary.localizedCaseInsensitiveContains("чист"))
            XCTAssertFalse(summary.releaseSummary.localizedCaseInsensitiveContains("clean"))
        }
    }
}

private func contractFixtureURL(_ relativePath: String) -> URL? {
    let current = URL(fileURLWithPath: #filePath)
    let candidates = sequence(first: current.deletingLastPathComponent()) { directory in
        let parent = directory.deletingLastPathComponent()
        return parent.path == directory.path ? nil : parent
    }
    return candidates
        .map { $0.appendingPathComponent(relativePath) }
        .first { FileManager.default.fileExists(atPath: $0.path) }
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

private func contractAppleOutcome(
    state: AppleProcessingOutcomeState,
    nextStep: AppleProcessingNextStepRecommendation,
    failureReason: String?
) -> AppleProcessingOutcome {
    AppleProcessingOutcome(
        candidateId: "apple-\(state.rawValue)",
        primaryOutcome: state,
        validationRows: [
            AppleProcessingValidationRow(
                candidateId: "apple-\(state.rawValue)",
                candidateKind: state == .acceptedForGuidanceOnly ? .micModeGuidance : .appOwnedGraphVoiceProcessing,
                routeClass: .builtInSpeakerphone,
                scenario: .farEndOnly,
                baselineStatus: .degraded,
                candidateStatus: state == .acceptedForBuiltinSpeakerphone ? .accepted : .unproven,
                lineageStatus: state == .acceptedForBuiltinSpeakerphone ? .liveAndPersisted : .unproven,
                speechPreservationStatus: state == .acceptedForBuiltinSpeakerphone ? .preserved : .notMeasured,
                alignmentStatus: state == .acceptedForBuiltinSpeakerphone ? .accepted : .notMeasured,
                stabilityStatus: state == .acceptedForBuiltinSpeakerphone ? .accepted : .unproven,
                diagnosticSafe: true,
                failureReason: failureReason
            )
        ],
        nextStepRecommendation: nextStep,
        failureReason: failureReason
    )
}
#endif
