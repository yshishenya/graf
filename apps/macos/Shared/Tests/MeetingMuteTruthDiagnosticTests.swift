import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class MeetingMuteTruthDiagnosticTests: XCTestCase {
    func testRedactorPreservesMuteTruthMetadataAndRemovesContent() {
        let manifest: [String: DiagnosticFieldValue] = [
            "privacySegments": .array([
                .object([
                    "segmentId": .string("segment-1"),
                    "control": .string("pause"),
                    "durationMs": .int(2000),
                    "rawAudio": .string("forbidden")
                ])
            ]),
            "meetingMuteTruth": .object([
                "decision": .string("meeting_mute_unproven"),
                "reason": .string("product_pause_segments_present"),
                "transcriptText": .string("forbidden")
            ]),
            "meetingMuteTruthEvidence": .array([
                .object([
                    "targetId": .string("chrome_telemost"),
                    "status": .string("meeting_mute_unproven"),
                    "meetingContent": .string("forbidden")
                ])
            ]),
            "targetMuteCapability": .object([
                "targetId": .string("chrome_telemost"),
                "firstMatrixStatus": .string("pause_validated")
            ])
        ]

        let result = DiagnosticRedactor().redact(manifest)

        XCTAssertNotNil(result.manifest["privacySegments"])
        XCTAssertNotNil(result.manifest["meetingMuteTruth"])
        XCTAssertNotNil(result.manifest["meetingMuteTruthEvidence"])
        XCTAssertNotNil(result.manifest["targetMuteCapability"])
        XCTAssertTrue(result.removedFields.contains("privacySegments[0].rawAudio"))
        XCTAssertTrue(result.removedFields.contains("meetingMuteTruth.transcriptText"))
        XCTAssertTrue(result.removedFields.contains("meetingMuteTruthEvidence[0].meetingContent"))
    }

    func testLocalRecordingDiagnosticBundleIncludesMuteTruthMetadataOnly() throws {
        let manifest = LocalRecordingManifest(
            sessionId: "session",
            createdAt: Date(timeIntervalSince1970: 1),
            startedAt: Date(timeIntervalSince1970: 1),
            stoppedAt: Date(timeIntervalSince1970: 4),
            status: .saved,
            directoryId: "dir",
            transcriptionReadiness: .ready,
            tracks: [completeDiagnosticTrack(role: .localMic), completeDiagnosticTrack(role: .remoteSpeaker)],
            durationDifferenceSeconds: 0,
            privacySegments: [
                ProductPrivacySegment(
                    segmentId: "segment-1",
                    sessionId: "session",
                    control: .pause,
                    startedAt: Date(timeIntervalSince1970: 2),
                    endedAt: Date(timeIntervalSince1970: 3),
                    startMonotonicMs: 1000,
                    endMonotonicMs: 2000
                )
            ],
            meetingMuteTruth: MuteTruthDecision(
                sessionId: "session",
                decision: .meetingMuteUnproven,
                reason: .productPauseSegmentsPresent,
                privacySegmentIds: ["segment-1"],
                targetEvidenceIds: ["evidence-1"],
                decidedAt: Date(timeIntervalSince1970: 4)
            ),
            meetingMuteTruthEvidence: [
                MeetingMuteTruthEvidence(
                    evidenceId: "evidence-1",
                    sessionId: "session",
                    targetId: "chrome_telemost",
                    targetDisplayName: "Chrome + Telemost",
                    source: .productPause,
                    status: .meetingMuteUnproven,
                    freshness: .unavailable,
                    limitationCopyShown: true,
                    recordedAt: Date(timeIntervalSince1970: 1)
                )
            ],
            targetMuteCapability: .chromeTelemost,
            limitationCopyShownAt: Date(timeIntervalSince1970: 1)
        )

        let bundle = try DiagnosticBundleService().buildLocalRecordingBundle(
            manifest: manifest,
            manifestOverrides: [
                "rawAudio": .string("forbidden")
            ]
        )

        XCTAssertEqual(bundle.redactionState, .blockedSensitiveContent)
        XCTAssertNotNil(bundle.manifest["privacySegments"])
        XCTAssertNotNil(bundle.manifest["meetingMuteTruth"])
        XCTAssertNotNil(bundle.manifest["meetingMuteTruthEvidence"])
        XCTAssertNotNil(bundle.manifest["targetMuteCapability"])
        XCTAssertNil(bundle.manifest["rawAudio"])
    }
}

private func completeDiagnosticTrack(role: AudioTrackRole) -> LocalRecordingTrack {
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
#endif
