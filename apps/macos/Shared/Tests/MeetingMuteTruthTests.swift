import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class MeetingMuteTruthTests: XCTestCase {
    func testMuteTruthModelsRoundTripAsMetadataOnlyValues() throws {
        let startedAt = Date(timeIntervalSince1970: 100)
        let endedAt = Date(timeIntervalSince1970: 103)
        let segment = ProductPrivacySegment(
            segmentId: "segment-1",
            sessionId: "session-1",
            control: .pause,
            startedAt: startedAt,
            startMonotonicMs: 1_000
        ).finalized(endedAt: endedAt, endMonotonicMs: 4_000)
        let evidence = MeetingMuteTruthEvidence(
            evidenceId: "evidence-1",
            sessionId: "session-1",
            targetId: TargetMuteCapability.chromeTelemost.targetId,
            targetDisplayName: TargetMuteCapability.chromeTelemost.targetDisplayName,
            source: .productPause,
            status: .meetingMuteUnproven,
            freshness: .unavailable,
            limitationCopyShown: true,
            recordedAt: startedAt
        )
        let decision = MuteTruthDecision.mvpDecision(
            sessionId: "session-1",
            privacySegments: [segment],
            targetEvidence: [evidence],
            targetCapability: .chromeTelemost,
            decidedAt: endedAt
        )

        let payload = MuteTruthPayload(
            segment: segment,
            evidence: evidence,
            capability: .chromeTelemost,
            decision: decision
        )
        let data = try JSONEncoder().encode(payload)
        let decoded = try JSONDecoder().decode(MuteTruthPayload.self, from: data)

        XCTAssertEqual(decoded.segment.durationMs, 3_000)
        XCTAssertEqual(decoded.capability.firstMatrixStatus, .pauseValidated)
        XCTAssertEqual(decoded.decision.decision, .meetingMuteUnproven)
        XCTAssertEqual(decoded.decision.reason, .productPauseSegmentsPresent)
        XCTAssertEqual(decoded.decision.privacySegmentIds, ["segment-1"])
        XCTAssertEqual(decoded.decision.targetEvidenceIds, ["evidence-1"])
    }

    func testUnsupportedTargetDecisionFailsClosed() {
        let decision = MuteTruthDecision.mvpDecision(
            sessionId: "session-1",
            privacySegments: [],
            targetEvidence: [],
            targetCapability: .unknown,
            decidedAt: Date(timeIntervalSince1970: 1)
        )

        XCTAssertEqual(decision.decision, .unsupported)
        XCTAssertEqual(decision.reason, .unsupportedTarget)
    }

    func testUnsafeDiagnosticEvidenceFailsClosed() {
        let unsafeSegment = ProductPrivacySegment(
            segmentId: "unsafe-segment",
            sessionId: "session-1",
            control: .pause,
            startedAt: Date(timeIntervalSince1970: 1),
            startMonotonicMs: 0,
            diagnosticSafe: false
        )

        let decision = MuteTruthDecision.mvpDecision(
            sessionId: "session-1",
            privacySegments: [unsafeSegment],
            targetEvidence: [],
            targetCapability: .chromeTelemost,
            decidedAt: Date(timeIntervalSince1970: 2)
        )

        XCTAssertEqual(decision.decision, .failed)
        XCTAssertEqual(decision.reason, .diagnosticRedactionFailed)
        XCTAssertFalse(decision.safeForDiagnostics)
    }

    func testManifestCarriesPrivacySegmentsAndMuteTruthDecision() {
        let startedAt = Date(timeIntervalSince1970: 10)
        let stoppedAt = Date(timeIntervalSince1970: 20)
        let segment = ProductPrivacySegment(
            segmentId: "session-privacy-1",
            sessionId: "session",
            control: .pause,
            startedAt: Date(timeIntervalSince1970: 12),
            endedAt: Date(timeIntervalSince1970: 14),
            startMonotonicMs: 2_000,
            endMonotonicMs: 4_000
        )
        let evidence = MeetingMuteTruthEvidence(
            evidenceId: "chrome-evidence",
            sessionId: "session",
            targetId: TargetMuteCapability.chromeTelemost.targetId,
            targetDisplayName: TargetMuteCapability.chromeTelemost.targetDisplayName,
            source: .productPause,
            status: .meetingMuteUnproven,
            freshness: .unavailable,
            limitationCopyShown: true,
            recordedAt: Date(timeIntervalSince1970: 11)
        )

        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .v5Manifest(
                sessionId: "session",
                directoryId: "dir",
                startedAt: startedAt,
                stoppedAt: stoppedAt,
                tracks: completeMuteTruthTracks(),
                scopeApproval: acceptedMuteTruthScopeApproval(),
                permissions: grantedMuteTruthPermissions(),
                privacySegments: [segment],
                targetMuteCapability: .chromeTelemost,
                meetingMuteTruthEvidence: [evidence],
                limitationCopyShownAt: Date(timeIntervalSince1970: 11)
            )

        XCTAssertEqual(manifest.privacySegments?.map(\.segmentId), ["session-privacy-1"])
        XCTAssertEqual(manifest.meetingMuteTruth?.decision, .meetingMuteUnproven)
        XCTAssertEqual(manifest.meetingMuteTruth?.privacySegmentIds, ["session-privacy-1"])
        XCTAssertEqual(manifest.meetingMuteTruthEvidence?.map(\.evidenceId), ["chrome-evidence"])
        XCTAssertEqual(manifest.targetMuteCapability?.targetId, TargetMuteCapability.chromeTelemost.targetId)
        XCTAssertEqual(manifest.limitationCopyShownAt, Date(timeIntervalSince1970: 11))
    }
}

private struct MuteTruthPayload: Codable, Equatable {
    let segment: ProductPrivacySegment
    let evidence: MeetingMuteTruthEvidence
    let capability: TargetMuteCapability
    let decision: MuteTruthDecision
}

private func completeMuteTruthTracks() -> [LocalRecordingTrack] {
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

private func acceptedMuteTruthScopeApproval() -> CaptureScopeApproval {
    CaptureScopeApproval(
        scopeApprovalId: "scope",
        scopeKind: .display,
        sourceDisplayName: "Chrome Telemost",
        approvedAt: Date(timeIntervalSince1970: 9),
        approvalMode: .userConfirmedSuggestedScope,
        eligibleReason: .manualMeetingScope
    )
}

private func grantedMuteTruthPermissions() -> SystemAudioPermissionSnapshot {
    SystemAudioPermissionSnapshot(
        microphone: .granted,
        systemAudio: .granted,
        evaluatedAt: Date(timeIntervalSince1970: 9)
    )
}
#endif
