import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class DesktopUploadCustodyProjectionTests: XCTestCase {
    func testQueuedLocalOnlyRecordingIsProductAutomaticCustody() {
        let item = custodyFixtureQueueItem(state: .queued)

        let projection = DesktopUploadCustodyProjection(item: item)

        XCTAssertEqual(projection.custodyState, .serverUnknownLocalSaved)
        XCTAssertEqual(projection.owner, .productAutomatic)
        XCTAssertEqual(projection.retryClass, .automatic)
        XCTAssertEqual(projection.normalUserAction, .none)
        XCTAssertEqual(projection.copyKey, "custody.saved_will_send")
        XCTAssertFalse(projection.reviewAvailable)
        XCTAssertEqual(projection.metadataSafety, .metadataOnly)
    }

    func testUploadedProcessedServerKnownRecordingCanOpenReview() {
        let item = custodyFixtureQueueItem(
            state: .uploaded,
            retryMode: .terminal,
            serverTruth: ServerTruthFingerprint(
                meetingId: "server-meeting-057",
                mediaRevisionId: "server-media-revision-057",
                processingStatus: "processed",
                finalizedAt: Date(timeIntervalSince1970: 200)
            )
        )

        let projection = DesktopUploadCustodyProjection(item: item)

        XCTAssertEqual(projection.custodyState, .delivered)
        XCTAssertEqual(projection.owner, .productAutomatic)
        XCTAssertEqual(projection.retryClass, .terminal)
        XCTAssertEqual(projection.normalUserAction, .openReview)
        XCTAssertEqual(projection.copyKey, "custody.known_by_server")
        XCTAssertTrue(projection.reviewAvailable)
        XCTAssertEqual(projection.serverMeetingId, "server-meeting-057")
    }

    func testUploadedProcessingFailureKeepsUploadAndProcessingTruthSeparate() {
        let item = custodyFixtureQueueItem(
            id: "processing-failed",
            state: .uploaded,
            retryMode: .terminal,
            serverTruth: ServerTruthFingerprint(
                meetingId: "server-meeting-processing-failed",
                mediaRevisionId: "server-media-processing-failed",
                serverStatus: "ingested_pending_processing",
                processingStatus: "failed_terminal",
                finalizedAt: Date(timeIntervalSince1970: 200)
            ),
            syncConflictState: .processingFailed
        )

        let projection = DesktopUploadCustodyProjection(item: item)

        XCTAssertEqual(projection.custodyState, .processing)
        XCTAssertEqual(projection.uploadState, .finalized)
        XCTAssertEqual(projection.processingState, .failedTerminal)
        XCTAssertEqual(projection.deletionState, .none)
        XCTAssertEqual(projection.localPurgeState, .none)
        XCTAssertEqual(projection.normalUserAction, .copySafeReport)
        XCTAssertFalse(projection.reviewAvailable)
    }

    func testServerDeletionKeepsDeletionAndLocalPurgeTruthSeparate() {
        let item = custodyFixtureQueueItem(
            id: "server-deleted-local-retained",
            state: .blocked,
            retryMode: .manualOnly,
            serverTruth: ServerTruthFingerprint(
                meetingId: "server-meeting-deleted",
                mediaRevisionId: "server-media-deleted",
                serverStatus: "ingested_pending_processing",
                finalizedAt: Date(timeIntervalSince1970: 200)
            ),
            syncConflictState: .serverMeetingDeleted
        )

        let projection = DesktopUploadCustodyProjection(item: item)

        XCTAssertEqual(projection.custodyState, .retainedAwaitingCondition)
        XCTAssertEqual(projection.uploadState, .finalized)
        XCTAssertEqual(projection.processingState, .notSubmitted)
        XCTAssertEqual(projection.deletionState, .serverDeleted)
        XCTAssertEqual(projection.localPurgeState, .pending)
        XCTAssertEqual(projection.owner, .workspaceAdmin)
        XCTAssertEqual(projection.normalUserAction, .copySafeReport)
    }

    func testVerifiedTerminalLocalPurgeDoesNotOverclaimUploadDelivery() {
        var item = custodyFixtureQueueItem(
            id: "terminal-purged",
            state: .terminalDeleted,
            retryMode: .terminal,
            syncConflictState: .retentionExpired,
            retentionDeadline: Date(timeIntervalSince1970: 10)
        )
        item.retentionDecision = RetentionDecision(
            decision: .terminalDeleted,
            decidedAt: Date(timeIntervalSince1970: 20),
            reason: "local_artifacts_deleted",
            localArtifactsRetained: false,
            policyReference: "local_purge.verified"
        )

        let projection = DesktopUploadCustodyProjection(item: item, now: Date(timeIntervalSince1970: 30))

        XCTAssertEqual(projection.custodyState, .terminalUndelivered)
        XCTAssertEqual(projection.uploadState, .terminal)
        XCTAssertEqual(projection.processingState, .notSubmitted)
        XCTAssertEqual(projection.deletionState, .retentionExpired)
        XCTAssertEqual(projection.localPurgeState, .verified)
        XCTAssertFalse(projection.reviewAvailable)
    }

    func testAuthConflictAsksOwnerToSignInWithoutRetryControls() {
        let item = custodyFixtureQueueItem(
            state: .blocked,
            retryMode: .manualOnly,
            serverTruth: ServerTruthFingerprint(meetingId: "server-meeting-057")
        ).withTransition(
            to: .blocked,
            now: Date(timeIntervalSince1970: 300),
            failureCategory: .authSession,
            failureReason: "auth_required",
            retryMode: .manualOnly,
            syncConflictState: .authRequired
        )

        let projection = DesktopUploadCustodyProjection(item: item)

        XCTAssertEqual(projection.custodyState, .retainedAwaitingCondition)
        XCTAssertEqual(projection.owner, .meetingOwner)
        XCTAssertEqual(projection.retryClass, .pausedUntilUserAction)
        XCTAssertEqual(projection.normalUserAction, .signIn)
        XCTAssertEqual(projection.copyKey, "custody.needs_sign_in")
        XCTAssertFalse(projection.reviewAvailable)
    }

    func testLocalArtifactFailureUsesSupportDiagnosticsNotManualRetry() {
        let item = custodyFixtureQueueItem(
            state: .blocked,
            retryMode: .manualOnly
        ).withTransition(
            to: .blocked,
            now: Date(timeIntervalSince1970: 400),
            failureCategory: .localResource,
            failureReason: "local_artifacts_not_uploadable",
            retryMode: .manualOnly,
            syncConflictState: .localFilesMissing
        )

        let projection = DesktopUploadCustodyProjection(item: item)

        XCTAssertEqual(projection.custodyState, .cannotSend)
        XCTAssertEqual(projection.owner, .support)
        XCTAssertEqual(projection.retryClass, .notRetryable)
        XCTAssertEqual(projection.normalUserAction, .openDiagnostics)
        XCTAssertNotEqual(projection.normalUserAction, .deleteLocalCopy)
        XCTAssertEqual(projection.copyKey, "custody.cannot_send")
        XCTAssertFalse(projection.reviewAvailable)
    }

    func testServerConflictMapsToAdminSafeReportNotRetry() {
        let item = custodyFixtureQueueItem(
            state: .blocked,
            retryMode: .manualOnly,
            serverTruth: ServerTruthFingerprint(meetingId: "server-meeting-deleted"),
            syncConflictState: .serverMeetingDeleted
        )

        let projection = DesktopUploadCustodyProjection(item: item)

        XCTAssertEqual(projection.custodyState, .retainedAwaitingCondition)
        XCTAssertEqual(projection.owner, .workspaceAdmin)
        XCTAssertEqual(projection.retryClass, .pausedUntilAdminAction)
        XCTAssertEqual(projection.normalUserAction, .copySafeReport)
        XCTAssertEqual(projection.copyKey, "custody.needs_admin")
        XCTAssertFalse(projection.reviewAvailable)
    }

    func testUpcomingRetentionDeadlineUsesPolicyLifecycleWarning() {
        let item = custodyFixtureQueueItem(
            state: .retrying,
            retryMode: .automatic,
            retentionDeadline: Date(timeIntervalSince1970: 1_100)
        )

        let projection = DesktopUploadCustodyProjection(
            item: item,
            now: Date(timeIntervalSince1970: 1_000)
        )

        XCTAssertEqual(projection.custodyState, .retainedAwaitingCondition)
        XCTAssertEqual(projection.owner, .policyLifecycle)
        XCTAssertEqual(projection.retryClass, .automatic)
        XCTAssertEqual(projection.normalUserAction, .none)
        XCTAssertEqual(projection.copyKey, "custody.retention_warning")
    }

    func testRetentionExpiredKeepsEvidenceActionInsteadOfSilentLoss() {
        let item = custodyFixtureQueueItem(
            state: .failed,
            retryMode: .terminal,
            syncConflictState: .retentionExpired,
            retentionDeadline: Date(timeIntervalSince1970: 10)
        )

        let projection = DesktopUploadCustodyProjection(item: item, now: Date(timeIntervalSince1970: 20))

        XCTAssertEqual(projection.custodyState, .terminalUndelivered)
        XCTAssertEqual(projection.owner, .policyLifecycle)
        XCTAssertEqual(projection.retryClass, .terminal)
        XCTAssertEqual(projection.normalUserAction, .copySafeReport)
        XCTAssertNotEqual(projection.normalUserAction, .deleteLocalCopy)
    }

    func testAggregateSummaryPrioritizesDiskPressureBeforeAuthAndAutomaticWork() {
        let queued = custodyFixtureQueueItem(
            id: "queued",
            state: .queued,
            updatedAt: Date(timeIntervalSince1970: 30)
        )
        let auth = custodyFixtureQueueItem(
            id: "auth",
            state: .blocked,
            retryMode: .manualOnly,
            failureCategory: .authSession,
            failureReason: "auth_required",
            syncConflictState: .authRequired,
            updatedAt: Date(timeIntervalSince1970: 40)
        )
        let diskPressure = custodyFixtureQueueItem(
            id: "disk-pressure",
            state: .blocked,
            retryMode: .manualOnly,
            failureCategory: .localResource,
            failureReason: "disk_pressure",
            updatedAt: Date(timeIntervalSince1970: 20)
        )

        let summary = DesktopUploadCustodySummary.summary(for: [queued, auth, diskPressure])

        XCTAssertEqual(summary?.primaryItem.id, "disk-pressure")
        XCTAssertEqual(summary?.title, "Не можем отправить запись")
        XCTAssertEqual(summary?.ownerLabel, "Поддержка")
        XCTAssertEqual(summary?.pendingCount, 3)
    }

    func testAggregateSummaryHidesServerKnownDeliveredItems() {
        let delivered = custodyFixtureQueueItem(
            id: "delivered",
            state: .uploaded,
            retryMode: .terminal,
            serverTruth: ServerTruthFingerprint(
                meetingId: "server-meeting-delivered",
                mediaRevisionId: "server-media-delivered",
                processingStatus: "processed"
            )
        )
        let queued = custodyFixtureQueueItem(
            id: "queued",
            state: .queued
        )

        XCTAssertNil(DesktopUploadCustodySummary.summary(for: [delivered]))
        XCTAssertEqual(DesktopUploadCustodySummary.summary(for: [delivered, queued])?.pendingCount, 1)
    }

    func testCustodyDetailSummariesGroupByCopyAndOwner() {
        let queued = custodyFixtureQueueItem(id: "queued", state: .queued)
        let retrying = custodyFixtureQueueItem(id: "retrying", state: .retrying)
        let auth = custodyFixtureQueueItem(
            id: "auth",
            state: .blocked,
            retryMode: .manualOnly,
            failureCategory: .authSession,
            failureReason: "auth_required",
            syncConflictState: .authRequired
        )

        let summaries = DesktopUploadCustodySummary.summaries(for: [queued, retrying, auth])

        XCTAssertEqual(summaries.map(\.copyKey), ["custody.needs_sign_in", "custody.saved_will_send"])
        XCTAssertEqual(summaries.first?.ownerLabel, "Владелец встречи")
        XCTAssertEqual(summaries.last?.pendingCount, 2)
    }

    func testMeetingOwnerActionBadgeCountsOnlyRealOwnerActions() {
        let auth = custodyFixtureQueueItem(
            id: "auth",
            state: .blocked,
            retryMode: .manualOnly,
            failureCategory: .authSession,
            failureReason: "auth_required",
            syncConflictState: .authRequired
        )
        let admin = custodyFixtureQueueItem(
            id: "admin",
            state: .blocked,
            retryMode: .manualOnly,
            syncConflictState: .serverMeetingDeleted
        )
        let automatic = custodyFixtureQueueItem(
            id: "automatic",
            state: .retrying,
            retryMode: .automatic
        )

        let count = DesktopUploadCustodySummary.meetingOwnerActionCount(for: [auth, admin, automatic])

        XCTAssertEqual(count, 1)
    }

    func testSafeIncidentReportUsesMetadataOnlyAdminTruth() throws {
        let item = custodyFixtureQueueItem(
            id: "admin-incident",
            state: .blocked,
            retryMode: .manualOnly,
            serverTruth: ServerTruthFingerprint(meetingId: "server-meeting-sensitive-id"),
            failureReason: "/Users/private/recording Bearer leaked-token",
            syncConflictState: .serverMeetingDeleted,
            updatedAt: Date(timeIntervalSince1970: 200)
        )
        let projection = DesktopUploadCustodyProjection(item: item)

        let report = try XCTUnwrap(DesktopUploadCustodySafeReport(item: item, projection: projection))

        XCTAssertEqual(report.owner, .workspaceAdmin)
        XCTAssertEqual(report.reasonCategory, "server_meeting_deleted")
        XCTAssertEqual(report.problemCode, "server_meeting_deleted")
        XCTAssertEqual(report.lifecycleState, .retainedAwaitingCondition)
        XCTAssertEqual(report.metadataSafety, .metadataOnly)
        XCTAssertTrue(report.serverIdentityPresent)
        XCTAssertTrue(report.safeRecordingIdentity.hasPrefix("server:"))
        XCTAssertTrue(report.clipboardText.contains("Что произошло: нужна проверка доступа или политики рабочего пространства."))
        XCTAssertTrue(report.clipboardText.contains("Что делать: отправьте этот отчет администратору рабочего пространства или поддержке."))
        XCTAssertTrue(report.clipboardText.contains("schema_version=desktop-custody-safe-report.v1"))
        XCTAssertFalse(report.safeRecordingIdentity.contains("server-meeting-sensitive-id"))
        XCTAssertFalse(report.clipboardText.contains("/Users/private"))
        XCTAssertFalse(report.clipboardText.contains("Bearer"))
    }

    func testSafeIncidentReportTracksTerminalLifecycleWithoutRecoveryPromise() throws {
        let item = custodyFixtureQueueItem(
            id: "terminal-incident",
            state: .failed,
            retryMode: .terminal,
            syncConflictState: .retentionExpired,
            retentionDeadline: Date(timeIntervalSince1970: 10),
            updatedAt: Date(timeIntervalSince1970: 20)
        )
        let projection = DesktopUploadCustodyProjection(item: item, now: Date(timeIntervalSince1970: 20))

        let report = try XCTUnwrap(DesktopUploadCustodySafeReport(item: item, projection: projection))

        XCTAssertEqual(report.owner, .policyLifecycle)
        XCTAssertEqual(report.lifecycleState, .terminalUndelivered)
        XCTAssertEqual(report.retentionDeadline, Date(timeIntervalSince1970: 10))
        XCTAssertTrue(report.localMediaRetained)
        XCTAssertTrue(report.clipboardText.contains("Что произошло: истек срок автоматической отправки, запись не отправлена."))
        XCTAssertTrue(report.clipboardText.contains("Локальное хранение: политика считает локальные данные удерживаемыми на этом Mac."))
        XCTAssertTrue(report.clipboardText.contains("Связь с сервером: серверная запись не подтверждена."))
        XCTAssertFalse(report.clipboardText.localizedCaseInsensitiveContains("recovery"))
        XCTAssertFalse(report.clipboardText.localizedCaseInsensitiveContains("восстанов"))
    }

    func testAutomaticCustodyDoesNotCreateIncidentReport() {
        let item = custodyFixtureQueueItem(id: "automatic", state: .queued)
        let projection = DesktopUploadCustodyProjection(item: item)

        XCTAssertNil(DesktopUploadCustodySafeReport(item: item, projection: projection))
    }

    func testQueueServiceBuildsCustodyProjectionsInDisplayOrder() {
        let older = custodyFixtureQueueItem(
            id: "older-uploaded",
            state: .uploaded,
            retryMode: .terminal,
            serverTruth: ServerTruthFingerprint(meetingId: "server-meeting-older"),
            updatedAt: Date(timeIntervalSince1970: 10)
        )
        let newer = custodyFixtureQueueItem(
            id: "newer-blocked",
            state: .blocked,
            retryMode: .manualOnly,
            updatedAt: Date(timeIntervalSince1970: 20)
        )

        let projections = DesktopUploadQueueService.custodyProjections(for: [older, newer])

        XCTAssertEqual(projections.map(\.itemId), ["newer-blocked", "older-uploaded"])
    }
}
#endif
