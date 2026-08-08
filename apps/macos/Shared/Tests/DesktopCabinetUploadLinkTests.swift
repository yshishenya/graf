import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class DesktopCabinetUploadLinkTests: XCTestCase {
    func testEmbeddedRecurringPointerStaysOnServerOwnedListAndDetailRoutes() throws {
        // FR-024/FR-048: recurring continuity reuses server-owned cabinet routes.
        let policy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
        )
        let listURL = try XCTUnwrap(
            URL(string: "https://rec.2brain.dev/desktop/meetings?q=synthetic-recurring-current")
        )
        let previousMeetingURL = try XCTUnwrap(
            URL(string: "https://rec.2brain.dev/desktop/meetings/server-previous-recurring-098")
        )

        let listDecision = policy.decision(for: listURL)
        let previousMeetingDecision = policy.decision(for: previousMeetingURL)

        XCTAssertEqual(listDecision.decision, .allow)
        XCTAssertEqual(listDecision.reason, .allowedMeetingList)
        XCTAssertEqual(listDecision.route.kind, .meetingList)
        XCTAssertEqual(previousMeetingDecision.decision, .allow)
        XCTAssertEqual(previousMeetingDecision.reason, .allowedMeetingDetail)
        XCTAssertEqual(previousMeetingDecision.route.kind, .meetingDetail)
        XCTAssertEqual(previousMeetingDecision.route.meetingId, "server-previous-recurring-098")
    }

    func testEmbeddedMeetingCalendarContextActionsStayInsideMeetingReview() throws {
        // FR-048: chooser mutations preserve the embedded review route boundary.
        let policy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
        )

        for action in ["choose", "continue-without", "clear"] {
            let url = try XCTUnwrap(
                URL(string: "https://rec.2brain.dev/desktop/meetings/server-meeting-098/calendar-context/\(action)")
            )
            let decision = policy.decision(for: url)

            XCTAssertEqual(decision.decision, .allow, action)
            XCTAssertEqual(decision.reason, .allowedMeetingDetail, action)
            XCTAssertEqual(decision.route.kind, .meetingDetail, action)
            XCTAssertEqual(decision.route.meetingId, "server-meeting-098", action)
        }
    }

    func testUploadedItemWithServerMeetingIdOpensReviewDestination() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let item = uploadItem(
            state: .uploaded,
            meetingId: nil,
            serverTruth: ServerTruthFingerprint(
                meetingId: "server-meeting-033",
                mediaRevisionId: "server-media-revision-033",
                processingStatus: "processed"
            )
        )

        let link = configuration.reviewLink(for: item)

        XCTAssertEqual(link.availability, .available)
        XCTAssertEqual(link.reason, "server_meeting_available")
        XCTAssertEqual(link.mediaRevisionId, "server-media-revision-033")
        XCTAssertEqual(link.destination?.absoluteString, "https://rec.2brain.dev/desktop/meetings/server-meeting-033")
    }

    func testUploadedItemWithAcceptedMediaRevisionKeepsProcessedReviewContext() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let item = uploadItem(
            state: .uploaded,
            meetingId: nil,
            serverTruth: ServerTruthFingerprint(
                meetingId: "server-meeting-045",
                mediaRevisionId: "server-media-revision-045",
                processingStatus: "processed"
            )
        )

        let link = configuration.reviewLink(for: item)

        XCTAssertEqual(link.availability, .available)
        XCTAssertEqual(link.reason, "server_meeting_available")
        XCTAssertEqual(link.meetingId, "server-meeting-045")
        XCTAssertEqual(link.mediaRevisionId, "server-media-revision-045")
        XCTAssertEqual(link.destination?.absoluteString, "https://rec.2brain.dev/desktop/meetings/server-meeting-045")
    }

    func testUploadedLocalOnlyItemDoesNotClaimReviewExists() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let item = uploadItem(
            state: .uploaded,
            meetingId: "local-only-meeting",
            serverTruth: ServerTruthFingerprint()
        )

        let link = configuration.reviewLink(for: item)

        XCTAssertEqual(link.availability, .unavailable)
        XCTAssertNil(link.destination)
        XCTAssertEqual(link.reason, "server_meeting_missing")
    }

    func testQueuedItemWithServerMeetingIdStaysProcessingOnly() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let item = uploadItem(
            state: .queued,
            meetingId: nil,
            serverTruth: ServerTruthFingerprint(meetingId: "server-meeting-033")
        )

        let link = configuration.reviewLink(for: item)

        XCTAssertEqual(link.availability, .processingOnly)
        XCTAssertEqual(link.reason, "server_meeting_processing")
        XCTAssertNil(link.destination)
    }

    func testUploadedServerKnownItemWithoutProcessedReviewDoesNotOpenDestination() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let item = uploadItem(
            state: .uploaded,
            meetingId: nil,
            serverTruth: ServerTruthFingerprint(
                meetingId: "server-meeting-processing",
                mediaRevisionId: "server-media-revision-processing",
                processingStatus: "pending_processing"
            )
        )

        let link = configuration.reviewLink(for: item)

        XCTAssertEqual(link.availability, .processingOnly)
        XCTAssertNil(link.destination)
        XCTAssertEqual(link.reason, "server_meeting_processing")
    }

    func testCabinetModeDoesNotCreateNativeRowsForLocalCustody() {
        let localQueued = uploadItem(state: .queued, meetingId: nil, serverTruth: ServerTruthFingerprint())
        let localBlocked = uploadItem(state: .blocked, meetingId: nil, serverTruth: ServerTruthFingerprint())
        let serverKnown = uploadItem(
            state: .uploaded,
            meetingId: nil,
            serverTruth: ServerTruthFingerprint(meetingId: "server-meeting-known", processingStatus: "processed")
        )

        let rows = DesktopMeetingShellLocalQueuePolicy.rowsNeedingNativeVisibility([
            localQueued,
            localBlocked,
            serverKnown
        ])

        XCTAssertTrue(rows.isEmpty)
    }

    func testLocalModeStillCanListLocalCustodyRows() {
        let newer = uploadItem(state: .blocked, meetingId: nil, serverTruth: ServerTruthFingerprint())
        let older = uploadItem(state: .queued, meetingId: nil, serverTruth: ServerTruthFingerprint())

        let rows = DesktopMeetingShellLocalQueuePolicy.allRowsForLocalMode([older, newer])

        XCTAssertEqual(rows.count, 2)
    }

    func testUploadedItemWithReviewBlockingConflictDoesNotOpenReviewDestination() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let item = uploadItem(
            state: .uploaded,
            meetingId: nil,
            serverTruth: ServerTruthFingerprint(meetingId: "server-meeting-deleted"),
            syncConflictState: .serverMeetingDeleted
        )

        let link = configuration.reviewLink(for: item)

        XCTAssertEqual(link.availability, .unavailable)
        XCTAssertNil(link.destination)
        XCTAssertEqual(link.reason, "server_meeting_deleted")
    }

    func testTerminalDeletedItemWithServerMeetingIdDoesNotOpenReviewDestination() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let item = uploadItem(
            state: .terminalDeleted,
            meetingId: nil,
            serverTruth: ServerTruthFingerprint(meetingId: "server-meeting-033")
        )

        let link = configuration.reviewLink(for: item)

        XCTAssertEqual(link.availability, .unavailable)
        XCTAssertNil(link.destination)
        XCTAssertEqual(link.reason, "server_meeting_terminal")
    }

    private func uploadItem(
        state: UploadItemState,
        meetingId: String?,
        serverTruth: ServerTruthFingerprint,
        syncConflictState: DesktopSyncConflictState = .none
    ) -> DesktopUploadQueueItem {
        let profile = ArtifactCompletenessProfile(
            schemaVersion: LocalRecordingManifest.legacySchemaVersion,
            manifestPresent: true,
            microphonePresent: true,
            systemAudioPresent: true,
            manifestSha256: String(repeating: "a", count: 64),
            microphoneSha256: String(repeating: "b", count: 64),
            systemAudioSha256: String(repeating: "c", count: 64),
            manifestSizeBytes: 64,
            microphoneSizeBytes: 128,
            systemAudioSizeBytes: 128,
            durationSeconds: 1,
            trackCompleteness: [],
            isUploadable: true
        )
        return DesktopUploadQueueItem(
            id: "upload-\(state.rawValue)-\(meetingId ?? serverTruth.meetingId ?? "none")",
            sessionId: "session-033",
            directoryId: "directory-033",
            directoryPath: "/tmp/upload-033",
            manifestPath: "/tmp/upload-033/manifest.json",
            microphonePath: "/tmp/upload-033/mic.wav",
            systemAudioPath: "/tmp/upload-033/incoming.wav",
            state: state,
            retryMode: .terminal,
            retentionDeadline: Date(timeIntervalSince1970: 100),
            createdAt: Date(timeIntervalSince1970: 1),
            updatedAt: Date(timeIntervalSince1970: 2),
            meetingId: meetingId,
            syncConflictState: syncConflictState,
            artifactProfile: profile,
            serverTruth: serverTruth,
            retentionDecision: RetentionDecision(
                decision: .retain,
                decidedAt: Date(timeIntervalSince1970: 1),
                reason: "test",
                localArtifactsRetained: true,
                policyReference: "test"
            )
        )
    }
}
#endif
