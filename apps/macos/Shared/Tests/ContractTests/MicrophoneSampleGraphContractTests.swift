import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class MicrophoneSampleGraphContractTests: XCTestCase {
    func testMicrophoneSampleGraphManifestMetadataIsDiagnosticSafe() throws {
        let selection = contractRecordingMicrophoneSelection()
        let stream = AppOwnedMicrophoneStreamSession(
            sessionId: "session",
            selection: selection,
            permissionState: .granted,
            streamKind: .appOwnedSampleSource,
            stoppedAt: Date(timeIntervalSince1970: 20),
            sampleRate: 48_000,
            channelCount: 1,
            writerSampleRate: 16_000,
            writerChannelCount: 1,
            frameCount: 16_000,
            failureReason: .none
        )
        let health = MicrophoneStreamHealth(
            gateStatus: .passed,
            failureReason: .none,
            framesObserved: true,
            timingConfidence: .usable,
            silenceStatus: .audible,
            lastLevel: 0.42,
            lastLevelAt: Date(timeIntervalSince1970: 19),
            cleanupReadiness: .readyForFutureProcessing,
            evidenceCodes: ["mic_graph_ready", "incoming_reference_present"]
        )
        let manifest = LocalRecordingManifest(
            sessionId: "session",
            createdAt: Date(timeIntervalSince1970: 30),
            startedAt: Date(timeIntervalSince1970: 10),
            stoppedAt: Date(timeIntervalSince1970: 20),
            status: .saved,
            directoryId: "dir",
            transcriptionReadiness: .ready,
            tracks: [contractCompleteTrack(role: .localMic), contractCompleteTrack(role: .remoteSpeaker)],
            scopeApproval: contractAcceptedScopeApproval(),
            permissions: contractGrantedPermissions(),
            microphoneSelection: selection,
            microphoneStream: stream,
            microphoneStreamHealth: health
        )
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        let data = try encoder.encode(manifest)
        let object = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        let selectionObject = object?["microphoneSelection"] as? [String: Any]
        let streamObject = object?["microphoneStream"] as? [String: Any]
        let healthObject = object?["microphoneStreamHealth"] as? [String: Any]
        let json = String(decoding: data, as: UTF8.self)

        XCTAssertEqual(selectionObject?["diagnosticSafe"] as? Bool, true)
        XCTAssertEqual(streamObject?["streamKind"] as? String, MicrophoneStreamKind.appOwnedSampleSource.rawValue)
        XCTAssertEqual(streamObject?["diagnosticSafe"] as? Bool, true)
        XCTAssertEqual(healthObject?["cleanupReadiness"] as? String, FutureProcessingReadiness.readyForFutureProcessing.rawValue)
        XCTAssertEqual(healthObject?["lastLevel"] as? Double, 0.42)
        XCTAssertEqual(object?["externalEgressStarted"] as? Bool, false)
        XCTAssertFalse(json.contains("rawAudio"))
        XCTAssertFalse(json.contains("transcriptText"))
        XCTAssertFalse(json.contains("signedUrl"))
    }

    func testFutureReadinessVocabularyStaysWithinLocalCaptureModel() {
        let readinessVocabulary = [
            FutureProcessingReadiness.readyForFutureProcessing.rawValue,
            FutureProcessingReadiness.unproven.rawValue,
            FutureProcessingReadiness.historicalPackage.rawValue,
            FutureProcessingReadiness.blocked.rawValue,
            MicrophoneStreamKind.appOwnedSampleSource.rawValue,
            MicrophoneStreamKind.historicalSource.rawValue
        ].joined(separator: " ")

        for forbidden in ["external_processor", "cleaned", "speakerphone_clean"] {
            XCTAssertFalse(readinessVocabulary.contains(forbidden), "\(forbidden) must stay out of 037 claims")
        }
    }

    func testManifestFixtureWithMicrophoneStreamMetadataDecodesWithoutRawAudio() throws {
        fixtureProbe("before_fixture_lookup")
        let fixtureURL = try XCTUnwrap(contractFixtureURL(
            "apps/macos/Shared/Tests/Fixtures/MicrophoneSampleGraph/manifest-with-stream-metadata.json"
        ))
        fixtureProbe("after_fixture_lookup")
        let data = try Data(contentsOf: fixtureURL)
        fixtureProbe("after_fixture_read")
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601

        fixtureProbe("before_manifest_decode")
        let manifest = try decoder.decode(LocalRecordingManifest.self, from: data)
        fixtureProbe("after_manifest_decode")
        let json = String(decoding: data, as: UTF8.self)

        // The fixture documents a historical dual package. It remains decode-
        // compatible but cannot describe the active v5 writer contract.
        XCTAssertEqual(manifest.schemaVersion, LocalRecordingManifest.legacySchemaVersion)
        XCTAssertEqual(manifest.microphoneSelection?.selectionResult, .accepted)
        XCTAssertEqual(manifest.microphoneStream?.streamKind, .appOwnedSampleSource)
        XCTAssertEqual(manifest.microphoneStreamHealth?.cleanupReadiness, .readyForFutureProcessing)
        XCTAssertEqual(manifest.microphoneStreamHealth?.lastLevel, 0.42)
        XCTAssertNotNil(manifest.microphoneStreamHealth?.lastLevelAt)
        XCTAssertEqual(Set(manifest.tracks.map(\.role)), Set([.localMic, .remoteSpeaker]))
        XCTAssertFalse(json.contains("rawAudio"))
        XCTAssertFalse(json.contains("transcriptText"))
        XCTAssertFalse(json.contains("signedUrl"))
        XCTAssertFalse(json.contains("mediaScribeCredential"))
        fixtureProbe("after_assertions")
    }
}

private func fixtureProbe(_ phase: String) {
    FileHandle.standardError.write(Data("fixture_probe=\(phase)\n".utf8))
}

private func contractRecordingMicrophoneSelection() -> RecordingMicrophoneSelection {
    RecordingMicrophoneSelection(
        selectionId: "selection",
        mode: .userSelected,
        inputDeviceId: "built-in",
        inputDisplayName: "Built-in Microphone",
        deviceClass: .builtIn,
        workingDeviceKind: .physical,
        selectionResult: .accepted,
        resolvedAt: Date(timeIntervalSince1970: 9)
    )
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
#endif
