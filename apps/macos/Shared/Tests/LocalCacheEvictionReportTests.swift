import Foundation
import XCTest
import TwoBrainRecShared
@testable import TwoBrainRecAppCore

final class LocalCacheEvictionReportTests: XCTestCase {
    private let now = Date(timeIntervalSince1970: 1_800_000_000)

    func testReportMatchesTheContractShapeAndAggregatesTotals() throws {
        let report = LocalCacheEvictionReport(
            generatedAt: now,
            scopeFingerprint: LocalCacheFingerprint.scope(nil),
            policy: LocalCacheEligibilityPolicy(),
            items: [
                makeItem(fingerprint: "rec_fpr_a", state: "uploaded", bytes: 100,
                         verdict: .potentiallyEligible, primary: .serverPlaybackReady, all: []),
                makeItem(fingerprint: "rec_fpr_b", state: "uploaded", bytes: 200,
                         verdict: .potentiallyEligible, primary: .serverPlaybackReady, all: []),
                makeItem(fingerprint: "rec_fpr_c", state: "uploaded", bytes: 50,
                         verdict: .keep, primary: .archiveAudioFalse,
                         all: [.archiveAudioFalse, .localBytesUnknown]),
            ]
        )

        XCTAssertEqual(report.schemaVersion, "local-cache-eviction-dry-run.v1")
        XCTAssertEqual(report.totals.inspected, 3)
        XCTAssertEqual(report.totals.eligible, 2)
        XCTAssertEqual(report.totals.eligibleBytes, 300)
        XCTAssertEqual(report.totals.rejected, 1)
        XCTAssertEqual(report.totals.rejectedBytes, 50)
        XCTAssertEqual(report.totals.unknownBytes, 50)
        XCTAssertEqual(report.totals.inspected, report.totals.eligible + report.totals.rejected)
        XCTAssertEqual(report.byReason.map(\.code), ["server_playback_ready", "archive_audio_false"])

        let object = try jsonObject(report)
        XCTAssertEqual(Set(object.keys), [
            "schemaVersion", "generatedAt", "scopeFingerprint", "truncated", "availableItemCount",
            "policy", "totals", "byReason", "items",
        ])
        XCTAssertEqual(object["truncated"] as? Bool, false)
        XCTAssertEqual(object["availableItemCount"] as? Int, 3)
        XCTAssertEqual(Set(try XCTUnwrap(object["policy"] as? [String: Any]).keys), [
            "maximumProofAgeSeconds", "graceSeconds", "minimumRemainingRetentionSeconds",
        ])
        XCTAssertEqual(Set(try XCTUnwrap(object["totals"] as? [String: Any]).keys), [
            "inspected", "eligible", "eligibleBytes", "rejected", "rejectedBytes", "unknownBytes",
        ])
        let reasons = try XCTUnwrap(object["byReason"] as? [[String: Any]])
        XCTAssertTrue(reasons.allSatisfy { Set($0.keys) == ["code", "count", "bytes"] })
        XCTAssertEqual(reasons.reduce(0) { $0 + (($1["count"] as? Int) ?? 0) }, report.totals.inspected)

        let items = try XCTUnwrap(object["items"] as? [[String: Any]])
        XCTAssertEqual(Set(try XCTUnwrap(items.first).keys), [
            "localRecordingFingerprint", "state", "bytes", "verdict", "primaryReason", "allReasons",
        ])
        XCTAssertEqual(Set(try XCTUnwrap(items.last).keys), [
            "localRecordingFingerprint", "state", "bytes", "verdict", "primaryReason", "allReasons",
        ])
        XCTAssertEqual(try XCTUnwrap(items.first)["verdict"] as? String, "potentially_eligible")
        XCTAssertEqual(try XCTUnwrap(items.last)["verdict"] as? String, "keep")
        XCTAssertEqual(
            try XCTUnwrap(items.last)["allReasons"] as? [String],
            ["archive_audio_false", "local_bytes_unknown"]
        )
        XCTAssertTrue(try XCTUnwrap(object["generatedAt"] as? String).contains("2027-01-15"))
    }

    func testTruncationFieldsDescribeTheCap() throws {
        let report = LocalCacheEvictionReport(
            generatedAt: now,
            scopeFingerprint: "scope_fpr_test",
            policy: LocalCacheEligibilityPolicy(),
            items: [makeItem(
                fingerprint: "rec_fpr_a", state: "uploaded", bytes: 1,
                verdict: .keep, primary: .proofMissing, all: [.proofMissing]
            )],
            truncated: true,
            availableItemCount: 205
        )
        let object = try jsonObject(report)
        XCTAssertEqual(object["truncated"] as? Bool, true)
        XCTAssertEqual(object["availableItemCount"] as? Int, 205)
    }

    func testServerSummaryUsesOnlyContractFields() throws {
        let report = LocalCacheEvictionReport(
            generatedAt: now,
            scopeFingerprint: "scope_fpr_test",
            policy: LocalCacheEligibilityPolicy(),
            items: [
                makeItem(
                    fingerprint: "rec_fpr_d",
                    state: "uploaded",
                    bytes: 10,
                    verdict: .keep,
                    primary: .proofMissing,
                    all: [.proofMissing],
                    server: .init(
                        meetingFingerprint: "meet_fpr_a",
                        mediaRevisionFingerprint: "rev_fpr_b",
                        playbackRevisionFingerprint: "rev_fpr_c",
                        playbackState: "available",
                        canPlay: true,
                        objectVerified: false,
                        archiveAudio: nil,
                        policyState: "active"
                    )
                ),
            ]
        )

        let object = try jsonObject(report)
        let item = try XCTUnwrap((object["items"] as? [[String: Any]])?.first)
        let server = try XCTUnwrap(item["server"] as? [String: Any])
        XCTAssertEqual(Set(server.keys), [
            "meetingFingerprint", "mediaRevisionFingerprint", "playbackRevisionFingerprint",
            "playbackState", "canPlay", "objectVerified", "policyState",
        ])
        XCTAssertEqual(server["canPlay"] as? Bool, true)
        XCTAssertEqual(server["objectVerified"] as? Bool, false)
        XCTAssertEqual(server["policyState"] as? String, "active")
    }

    func testReportContainsNoPathsOrMeetingText() throws {
        let rawMeetingId = "meeting-private-identifier"
        let rawRevision = "revision-private-identifier"
        let report = LocalCacheEvictionReport(
            generatedAt: now,
            scopeFingerprint: LocalCacheFingerprint.scope(nil),
            policy: LocalCacheEligibilityPolicy(),
            items: [
                makeItem(
                    fingerprint: LocalCacheFingerprint.recording("/tmp/private-recordings/meeting-1"),
                    state: "uploaded",
                    bytes: 10,
                    verdict: .keep,
                    primary: .meetingMismatch,
                    all: [.meetingMismatch],
                    server: .init(
                        meetingFingerprint: LocalCacheFingerprint.meeting(rawMeetingId),
                        mediaRevisionFingerprint: LocalCacheFingerprint.revision(rawRevision)
                    )
                ),
            ]
        )

        let json = String(decoding: try encode(report), as: UTF8.self)
        XCTAssertFalse(json.contains("/tmp/private-recordings"))
        XCTAssertFalse(json.contains(rawMeetingId))
        XCTAssertFalse(json.contains(rawRevision))
        XCTAssertFalse(json.contains("meeting-1"))
        XCTAssertTrue(json.contains("rec_fpr_"))
        XCTAssertTrue(json.contains("meet_fpr_"))
        XCTAssertTrue(json.contains("rev_fpr_"))
    }

    func testPolicySecondsMatchTheEligibilityPolicy() throws {
        let policy = LocalCacheEligibilityPolicy(
            maximumProofAge: 90,
            gracePeriod: 3 * 24 * 60 * 60,
            minimumRemainingRetention: 10 * 24 * 60 * 60
        )
        let report = LocalCacheEvictionReport(
            generatedAt: now,
            scopeFingerprint: "scope_fpr_test",
            policy: policy,
            items: []
        )
        let object = try jsonObject(report)
        let policyObject = try XCTUnwrap(object["policy"] as? [String: Any])
        XCTAssertEqual(policyObject["maximumProofAgeSeconds"] as? Int, 90)
        XCTAssertEqual(policyObject["graceSeconds"] as? Int, 259_200)
        XCTAssertEqual(policyObject["minimumRemainingRetentionSeconds"] as? Int, 864_000)
    }

    func testItemProjectionCarriesFingerprintsWithoutRawIdentity() {
        var item = DesktopUploadQueueItem(
            id: "queue-id",
            sessionId: "session",
            directoryId: "private-directory",
            directoryPath: "/tmp/private-directory",
            manifestPath: "/tmp/private-directory/manifest.json",
            microphonePath: "metadata-only",
            systemAudioPath: "metadata-only",
            state: .uploaded,
            retryMode: .terminal,
            retentionDeadline: now,
            createdAt: now,
            updatedAt: now,
            meetingId: "meeting-private",
            artifactProfile: ArtifactCompletenessProfile(
                schemaVersion: LocalRecordingManifest.schemaVersion,
                manifestPresent: true,
                microphonePresent: false,
                systemAudioPresent: false,
                manifestSha256: nil,
                microphoneSha256: nil,
                systemAudioSha256: nil,
                manifestSizeBytes: 1,
                microphoneSizeBytes: 0,
                systemAudioSizeBytes: 0,
                durationSeconds: 1,
                trackCompleteness: [],
                isUploadable: false
            ),
            retentionDecision: RetentionDecision(
                decision: .retain,
                decidedAt: now,
                reason: "test",
                localArtifactsRetained: true,
                policyReference: "test"
            )
        )
        item.localMediaRevisionId = "private-revision"

        let decision = LocalCacheEligibilityDecision(
            verdict: .keep,
            primaryReason: .proofMissing,
            allReasons: [.proofMissing],
            bytes: 42,
            proof: DesktopServerProof(
                meetingId: "meeting-private",
                deletionState: "none",
                accessState: "owner",
                conflictState: "none",
                playback: DesktopPlaybackProof(
                    state: "available",
                    canPlay: true,
                    reasonCode: "canonical_ready",
                    mediaRevisionId: "11111111-1111-4111-8111-111111111111",
                    localMediaRevisionId: "private-revision",
                    objectVerified: true,
                    verifiedAt: ServerTimestamp(date: now),
                    automaticRecovery: false
                ),
                uploadSession: DesktopUploadSessionProof(sessionId: "session", status: "active"),
                finalizedUpload: DesktopFinalizedUploadProof(
                    sessionId: "session",
                    mediaRevisionId: "11111111-1111-4111-8111-111111111111",
                    localMediaRevisionId: "private-revision",
                    archiveAudio: true,
                    finalizedAt: ServerTimestamp(date: now),
                    status: "finalized"
                ),
                retention: DesktopRetentionProof(
                    deleteAfter: ServerTimestamp(date: now.addingTimeInterval(86_400)),
                    policyState: "active"
                )
            )
        )
        let reportItem = LocalCacheEvictionReport.Item.make(
            item: item,
            decision: decision,
            localRecordingFingerprint: LocalCacheFingerprint.recording(item.directoryId)
        )

        XCTAssertEqual(reportItem.bytes, 42)
        XCTAssertEqual(reportItem.server?.meetingFingerprint?.hasPrefix("meet_fpr_"), true)
        XCTAssertEqual(reportItem.server?.mediaRevisionFingerprint?.hasPrefix("rev_fpr_"), true)
        XCTAssertEqual(reportItem.server?.playbackRevisionFingerprint?.hasPrefix("rev_fpr_"), true)
        XCTAssertFalse(reportItem.localRecordingFingerprint.contains("private-directory"))
        XCTAssertFalse(reportItem.server?.meetingFingerprint?.contains("meeting-private") ?? true)
    }

    // MARK: - Fixtures

    private func makeItem(
        fingerprint: String,
        state: String,
        bytes: Int64,
        verdict: LocalCacheVerdict,
        primary: LocalCacheEligibilityReason,
        all: [LocalCacheEligibilityReason],
        server: LocalCacheEvictionReport.Server? = nil
    ) -> LocalCacheEvictionReport.Item {
        LocalCacheEvictionReport.Item(
            localRecordingFingerprint: fingerprint,
            state: state,
            bytes: bytes,
            verdict: verdict,
            primaryReason: primary.rawValue,
            allReasons: all.map(\.rawValue),
            server: server
        )
    }

    private func encode(_ report: LocalCacheEvictionReport) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        encoder.dateEncodingStrategy = .iso8601
        return try encoder.encode(report)
    }

    private func jsonObject(_ report: LocalCacheEvictionReport) throws -> [String: Any] {
        try XCTUnwrap(try JSONSerialization.jsonObject(with: encode(report)) as? [String: Any])
    }
}
