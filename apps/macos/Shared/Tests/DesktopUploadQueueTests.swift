import AVFoundation
import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class DesktopUploadQueueTests: XCTestCase {
    func testBackendRoleMappingUsesTransportVocabulary() {
        XCTAssertEqual(DesktopUploadTransportRole.role(forLocalTrackRole: .localMic), .microphone)
        XCTAssertEqual(DesktopUploadTransportRole.role(forLocalTrackRole: .remoteSpeaker), .system)
        XCTAssertNil(DesktopUploadTransportRole.role(forLocalTrackRole: .derivedLocalMic))
    }

    func testTerminalUploadStateDoesNotRegressToQueued() {
        let item = makeQueueItem(state: .uploaded, retryMode: .terminal)
        let changed = item.withTransition(to: .queued, now: Date(timeIntervalSince1970: 20))

        XCTAssertEqual(changed.state, .uploaded)
        XCTAssertEqual(changed.retryMode, .terminal)
    }

    func testUploadQueueDisplayCopyIsProductFacing() {
        XCTAssertEqual(UploadItemState.blocked.displayName, "Нужна проверка")
        XCTAssertEqual(UploadRetryMode.manualOnly.displayName, "Ручная проверка")

        let manual = makeQueueItem(state: .blocked, retryMode: .manualOnly)
        let automatic = makeQueueItem(state: .retrying, retryMode: .automatic)

        XCTAssertNil(manual.nextActionLabel)
        XCTAssertNil(automatic.nextActionLabel)

        let manualSummary = DesktopUploadQueueSummary(
            primaryItem: makeQueueItem(
                state: .blocked,
                retryMode: .manualOnly,
                failureReason: "local_recording_package_not_uploadable"
            ),
            pendingCount: 6,
            totalCount: 6
        )
        XCTAssertEqual(manualSummary.title, "Нужна проверка + ещё 5")
        XCTAssertEqual(manualSummary.detail, "нужна ручная проверка локальной записи")
    }

    func testUploadQueueSummaryExplainsBlockedLocalRecordingReasons() {
        let leakageSummary = DesktopUploadQueueSummary(
            primaryItem: makeQueueItem(
                state: .blocked,
                retryMode: .manualOnly,
                failureReason: LocalRecordingFailureReason.leakageDetected.rawValue
            ),
            pendingCount: 1,
            totalCount: 1
        )
        let silentSummary = DesktopUploadQueueSummary(
            primaryItem: makeQueueItem(
                state: .blocked,
                retryMode: .manualOnly,
                failureReason: LocalRecordingFailureReason.silentInput.rawValue
            ),
            pendingCount: 1,
            totalCount: 1
        )
        let unmeasuredSummary = DesktopUploadQueueSummary(
            primaryItem: makeQueueItem(
                state: .blocked,
                retryMode: .manualOnly,
                failureReason: LocalRecordingFailureReason.leakageNotMeasured.rawValue
            ),
            pendingCount: 1,
            totalCount: 1
        )

        XCTAssertEqual(leakageSummary.detail, "звук динамиков попал в микрофон; отправим как есть")
        XCTAssertEqual(silentSummary.detail, "микрофон был слишком тихим или пустым; отправим как есть")
        XCTAssertEqual(unmeasuredSummary.detail, "не удалось проверить утечку динамиков; отправим как есть")
    }

    func testCabinetMeetingListDoesNotRenderLocalCustodyRows() {
        let blockedLocal = makeQueueItem(
            id: "blocked-local",
            state: .blocked,
            retryMode: .manualOnly,
            failureReason: "local_recording_package_not_uploadable",
            updatedAt: Date(timeIntervalSince1970: 40)
        )
        let uploadedServerVisible = makeQueueItem(
            id: "uploaded-server",
            state: .uploaded,
            retryMode: .terminal,
            meetingId: "meeting-042",
            updatedAt: Date(timeIntervalSince1970: 50)
        )

        let rows = DesktopMeetingShellLocalQueuePolicy.rowsNeedingNativeVisibility([
            uploadedServerVisible,
            blockedLocal
        ])

        XCTAssertTrue(rows.isEmpty)
    }

    func testLocalModeMeetingListPrioritizesNewestLocalOnlyRecording() {
        let olderQueued = makeQueueItem(
            id: "older-queued",
            state: .queued,
            retryMode: .automatic,
            createdAt: Date(timeIntervalSince1970: 30),
            updatedAt: Date(timeIntervalSince1970: 100)
        )
        let newestBlocked = makeQueueItem(
            id: "newest-blocked",
            state: .blocked,
            retryMode: .manualOnly,
            createdAt: Date(timeIntervalSince1970: 60),
            updatedAt: Date(timeIntervalSince1970: 100)
        )

        let rows = DesktopMeetingShellLocalQueuePolicy.allRowsForLocalMode([
            olderQueued,
            newestBlocked
        ])

        XCTAssertEqual(rows.first?.id, "newest-blocked")
    }

    func testPendingLocalPurgeDeletesLocalArtifactsBeforeAcknowledgement() async throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let queueURL = root.appendingPathComponent("upload-queue.json")
        let package = try makeRecordingPackage(
            root: root,
            directoryId: "purge-directory",
            sessionId: "purge-session"
        )
        let meetingId = "72000000-0000-0000-0000-000000000001"
        let initialService = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )
        var item = try XCTUnwrap(initialService.scanAndEnqueueCompletedRecordings().first)
        item.meetingId = meetingId
        try JSONEncoder.uploadQueueTestEncoder
            .encode(DesktopUploadQueueDocument(updatedAt: item.updatedAt, items: [item]))
            .write(to: queueURL, options: [.atomic])
        let task = try makeLocalPurgeTask(meetingId: meetingId)
        let client = LocalPurgeOnlyClient(
            tasks: [task],
            reconciliation: DesktopUploadReconciliation(
                serverTruth: ServerTruthFingerprint(
                    meetingId: meetingId,
                    serverStatus: "ingested_pending_processing"
                )
            )
        )
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: client,
            clock: { Date(timeIntervalSince1970: 200) }
        )

        _ = try await service.acknowledgePendingLocalPurgeTasks()

        XCTAssertEqual(client.acknowledgements.first?.state, .acknowledged)
        XCTAssertEqual(client.acknowledgements.first?.reasonCode, "local_artifacts_deleted")
        XCTAssertFalse(FileManager.default.fileExists(atPath: package.directoryURL.path))
        let saved = try XCTUnwrap(service.loadItems().first)
        XCTAssertEqual(saved.state, .terminalDeleted)
        XCTAssertEqual(saved.retentionDecision.decision, .terminalDeleted)
        XCTAssertFalse(saved.retentionDecision.localArtifactsRetained)
    }

    func testLocalPurgeUnknownSyncStateDoesNotDeleteRecordingBuffers() async throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let queueURL = root.appendingPathComponent("upload-queue.json")
        let package = try makeRecordingPackage(
            root: root,
            directoryId: "unknown-sync-directory",
            sessionId: "unknown-sync-session"
        )
        let meetingId = "72000000-0000-0000-0000-000000000006"
        let initialService = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )
        var item = try XCTUnwrap(initialService.scanAndEnqueueCompletedRecordings().first)
        item.meetingId = meetingId
        try JSONEncoder.uploadQueueTestEncoder
            .encode(DesktopUploadQueueDocument(updatedAt: item.updatedAt, items: [item]))
            .write(to: queueURL, options: [.atomic])
        let task = try makeLocalPurgeTask(meetingId: meetingId)
        let client = LocalPurgeOnlyClient(tasks: [task])
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: client,
            clock: { Date(timeIntervalSince1970: 200) }
        )

        _ = try await service.acknowledgePendingLocalPurgeTasks()

        XCTAssertEqual(client.reconciledItems.map(\.id), [item.id])
        XCTAssertEqual(client.acknowledgements.first?.state, .failed)
        XCTAssertEqual(client.acknowledgements.first?.reasonCode, "local_purge_failed")
        XCTAssertTrue(FileManager.default.fileExists(atPath: package.directoryURL.path))
        XCTAssertNotEqual(try XCTUnwrap(service.loadItems().first).state, .terminalDeleted)
    }

    func testLocalPurgeReconciledMeetingMismatchDoesNotDeleteRecordingBuffers() async throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let queueURL = root.appendingPathComponent("upload-queue.json")
        let package = try makeRecordingPackage(
            root: root,
            directoryId: "meeting-mismatch-directory",
            sessionId: "meeting-mismatch-session"
        )
        let taskMeetingId = "72000000-0000-0000-0000-000000000007"
        let currentMeetingId = "72000000-0000-0000-0000-000000000008"
        let initialService = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )
        var item = try XCTUnwrap(initialService.scanAndEnqueueCompletedRecordings().first)
        item.meetingId = taskMeetingId
        try JSONEncoder.uploadQueueTestEncoder
            .encode(DesktopUploadQueueDocument(updatedAt: item.updatedAt, items: [item]))
            .write(to: queueURL, options: [.atomic])
        let task = try makeLocalPurgeTask(meetingId: taskMeetingId)
        let client = LocalPurgeOnlyClient(
            tasks: [task],
            reconciliation: DesktopUploadReconciliation(
                serverTruth: ServerTruthFingerprint(
                    meetingId: currentMeetingId,
                    serverStatus: "ingested_pending_processing"
                )
            )
        )
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: client,
            clock: { Date(timeIntervalSince1970: 200) }
        )

        _ = try await service.acknowledgePendingLocalPurgeTasks()

        XCTAssertEqual(client.reconciledItems.map(\.id), [item.id])
        XCTAssertEqual(client.acknowledgements.first?.state, .failed)
        XCTAssertEqual(client.acknowledgements.first?.reasonCode, "local_purge_failed")
        XCTAssertTrue(FileManager.default.fileExists(atPath: package.directoryURL.path))
        let saved = try XCTUnwrap(service.loadItems().first)
        XCTAssertEqual(saved.meetingId, currentMeetingId)
        XCTAssertNotEqual(saved.state, .terminalDeleted)
    }

    func testLocalPurgeReconciliationErrorPreservesAlreadyDeletedTruth() async throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let queueURL = root.appendingPathComponent("upload-queue.json")
        let package = try makeRecordingPackage(
            root: root,
            directoryId: "already-deleted-directory",
            sessionId: "already-deleted-session"
        )
        let meetingId = "72000000-0000-0000-0000-000000000009"
        let initialService = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )
        var item = try XCTUnwrap(initialService.scanAndEnqueueCompletedRecordings().first)
        item.meetingId = meetingId
        try FileManager.default.removeItem(at: package.directoryURL)
        try JSONEncoder.uploadQueueTestEncoder
            .encode(DesktopUploadQueueDocument(updatedAt: item.updatedAt, items: [item]))
            .write(to: queueURL, options: [.atomic])
        let task = try makeLocalPurgeTask(meetingId: meetingId)
        let client = LocalPurgeOnlyClient(
            tasks: [task],
            reconciliationError: DesktopUploadClientError.invalidResponse
        )
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: client,
            clock: { Date(timeIntervalSince1970: 200) }
        )

        _ = try await service.acknowledgePendingLocalPurgeTasks()

        XCTAssertEqual(client.acknowledgements.first?.state, .acknowledged)
        XCTAssertEqual(client.acknowledgements.first?.reasonCode, "local_artifacts_deleted")
        XCTAssertEqual(try XCTUnwrap(service.loadItems().first).state, .terminalDeleted)
    }

    func testLocalPurgeExportTaskDoesNotDeleteRecordingBuffers() async throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let queueURL = root.appendingPathComponent("upload-queue.json")
        let package = try makeRecordingPackage(
            root: root,
            directoryId: "export-task-directory",
            sessionId: "export-task-session"
        )
        let meetingId = "72000000-0000-0000-0000-000000000002"
        let initialService = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )
        var item = try XCTUnwrap(initialService.scanAndEnqueueCompletedRecordings().first)
        item.meetingId = meetingId
        try JSONEncoder.uploadQueueTestEncoder
            .encode(DesktopUploadQueueDocument(updatedAt: item.updatedAt, items: [item]))
            .write(to: queueURL, options: [.atomic])
        let task = try makeLocalPurgeTask(meetingId: meetingId, taskType: .purgeLocalExports)
        let client = LocalPurgeOnlyClient(tasks: [task])
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: client,
            clock: { Date(timeIntervalSince1970: 200) }
        )

        _ = try await service.acknowledgePendingLocalPurgeTasks()

        XCTAssertEqual(client.acknowledgements.first?.state, .failed)
        XCTAssertEqual(client.acknowledgements.first?.reasonCode, "local_purge_unverified")
        XCTAssertTrue(FileManager.default.fileExists(atPath: package.directoryURL.path))
        XCTAssertNotEqual(try XCTUnwrap(service.loadItems().first).state, .terminalDeleted)
    }

    func testLocalPurgeRefusesPathsOutsideRecordingRootAndReportsFailedAck() async throws {
        let root = temporaryRoot()
        let outsideRoot = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        defer { try? FileManager.default.removeItem(at: outsideRoot) }
        let queueURL = root.appendingPathComponent("upload-queue.json")
        let package = try makeRecordingPackage(
            root: root,
            directoryId: "outside-path-directory",
            sessionId: "outside-path-session"
        )
        let outsideDirectory = outsideRoot.appendingPathComponent("outside-recording", isDirectory: true)
        try FileManager.default.createDirectory(at: outsideDirectory, withIntermediateDirectories: true)
        let outsideManifest = outsideDirectory.appendingPathComponent("manifest.json")
        let outsideMic = outsideDirectory.appendingPathComponent("mic.wav")
        let outsideIncoming = outsideDirectory.appendingPathComponent("incoming.wav")
        try Data(repeating: 3, count: 16).write(to: outsideManifest)
        try Data(repeating: 4, count: 16).write(to: outsideMic)
        try Data(repeating: 5, count: 16).write(to: outsideIncoming)
        let meetingId = "72000000-0000-0000-0000-000000000003"
        let initialService = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )
        var item = try XCTUnwrap(initialService.scanAndEnqueueCompletedRecordings().first)
        item.meetingId = meetingId
        item.directoryPath = outsideDirectory.path
        item.manifestPath = outsideManifest.path
        item.microphonePath = outsideMic.path
        item.systemAudioPath = outsideIncoming.path
        try JSONEncoder.uploadQueueTestEncoder
            .encode(DesktopUploadQueueDocument(updatedAt: item.updatedAt, items: [item]))
            .write(to: queueURL, options: [.atomic])
        let task = try makeLocalPurgeTask(meetingId: meetingId)
        let client = LocalPurgeOnlyClient(
            tasks: [task],
            reconciliation: DesktopUploadReconciliation(
                serverTruth: ServerTruthFingerprint(
                    meetingId: meetingId,
                    serverStatus: "ingested_pending_processing"
                )
            )
        )
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: client,
            clock: { Date(timeIntervalSince1970: 200) }
        )

        _ = try await service.acknowledgePendingLocalPurgeTasks()

        XCTAssertEqual(client.acknowledgements.first?.state, .failed)
        XCTAssertEqual(client.acknowledgements.first?.reasonCode, "local_purge_failed")
        XCTAssertTrue(FileManager.default.fileExists(atPath: outsideDirectory.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: package.directoryURL.path))
        XCTAssertNotEqual(try XCTUnwrap(service.loadItems().first).state, .terminalDeleted)
    }

    func testPendingLocalPurgeReconcilesBeforeDeletingLocalArtifacts() async throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let queueURL = root.appendingPathComponent("upload-queue.json")
        let package = try makeRecordingPackage(
            root: root,
            directoryId: "purge-reconcile-directory",
            sessionId: "purge-reconcile-session"
        )
        let meetingId = "72000000-0000-0000-0000-000000000004"
        let initialService = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )
        var item = try XCTUnwrap(initialService.scanAndEnqueueCompletedRecordings().first)
        item.meetingId = meetingId
        try JSONEncoder.uploadQueueTestEncoder
            .encode(DesktopUploadQueueDocument(updatedAt: item.updatedAt, items: [item]))
            .write(to: queueURL, options: [.atomic])
        let task = try makeLocalPurgeTask(meetingId: meetingId)
        let client = LocalPurgeOnlyClient(
            tasks: [task],
            reconciliation: DesktopUploadReconciliation(
                serverTruth: ServerTruthFingerprint(meetingId: meetingId),
                conflictState: .accessRevoked,
                conflictReason: "access_revoked",
                nextAction: "sign_in_again"
            )
        )
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: client,
            clock: { Date(timeIntervalSince1970: 200) }
        )

        _ = try await service.acknowledgePendingLocalPurgeTasks()

        XCTAssertEqual(client.reconciledItems.map(\.id), [item.id])
        XCTAssertEqual(client.acknowledgements.first?.state, .failed)
        XCTAssertEqual(client.acknowledgements.first?.reasonCode, "local_purge_failed")
        XCTAssertTrue(FileManager.default.fileExists(atPath: package.directoryURL.path))
        let saved = try XCTUnwrap(service.loadItems().first)
        XCTAssertEqual(saved.syncConflictState, .accessRevoked)
        XCTAssertNotEqual(saved.state, .terminalDeleted)
    }

    func testLocalPurgeAckFailureDoesNotFinalizeLocalQueueState() async throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let queueURL = root.appendingPathComponent("upload-queue.json")
        let package = try makeRecordingPackage(
            root: root,
            directoryId: "ack-failure-directory",
            sessionId: "ack-failure-session"
        )
        let meetingId = "72000000-0000-0000-0000-000000000005"
        let initialService = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )
        var item = try XCTUnwrap(initialService.scanAndEnqueueCompletedRecordings().first)
        item.meetingId = meetingId
        item.state = .uploaded
        item.retryMode = .terminal
        try JSONEncoder.uploadQueueTestEncoder
            .encode(DesktopUploadQueueDocument(updatedAt: item.updatedAt, items: [item]))
            .write(to: queueURL, options: [.atomic])
        let task = try makeLocalPurgeTask(meetingId: meetingId)
        let client = LocalPurgeOnlyClient(
            tasks: [task],
            reconciliation: DesktopUploadReconciliation(
                serverTruth: ServerTruthFingerprint(meetingId: meetingId)
            ),
            acknowledgementError: DesktopUploadClientError.invalidResponse
        )
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: client,
            clock: { Date(timeIntervalSince1970: 200) }
        )

        do {
            _ = try await service.acknowledgePendingLocalPurgeTasks()
            XCTFail("acknowledgePendingLocalPurgeTasks should surface server ack failure")
        } catch DesktopUploadClientError.invalidResponse {
        }

        XCTAssertFalse(FileManager.default.fileExists(atPath: package.directoryURL.path))
        let saved = try XCTUnwrap(service.loadItems().first)
        XCTAssertEqual(saved.state, .uploaded)
        XCTAssertEqual(saved.retryMode, .terminal)
        XCTAssertNotEqual(saved.retentionDecision.decision, .terminalDeleted)
    }

    func testScanEnqueuesCompletedRecordingOnce() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let package = try makeRecordingPackage(root: root, directoryId: "package-1", sessionId: "session-1")
        let queueURL = root.appendingPathComponent("queue.json")
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )

        let firstScan = try service.scanAndEnqueueCompletedRecordings()
        let secondScan = try service.scanAndEnqueueCompletedRecordings()

        XCTAssertTrue(FileManager.default.fileExists(atPath: package.manifestURL.path))
        XCTAssertEqual(firstScan.count, 1)
        XCTAssertEqual(secondScan.count, 1)
        XCTAssertEqual(secondScan.first?.directoryId, "package-1")
        XCTAssertEqual(secondScan.first?.sessionId, "session-1")
        XCTAssertEqual(secondScan.first?.state, .queued)
        XCTAssertTrue(secondScan.first?.artifactProfile.isUploadable == true)
    }

    func testScanPersistsRecordingMetadataFromManifestStartStopAndScopeTitle() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        _ = try makeRecordingPackage(root: root, directoryId: "package-1", sessionId: "session-1")
        let queueURL = root.appendingPathComponent("queue.json")
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )

        let item = try XCTUnwrap(service.scanAndEnqueueCompletedRecordings().first)
        let savedDocument = try JSONDecoder.uploadQueueTestDecoder.decode(
            DesktopUploadQueueDocument.self,
            from: Data(contentsOf: queueURL)
        )
        let savedItem = try XCTUnwrap(savedDocument.items.first)
        let displayLabel = localMinuteLabel(Date(timeIntervalSince1970: 10), separator: " ")
        let basenameLabel = localMinuteLabel(Date(timeIntervalSince1970: 10), separator: "_")
            .replacingOccurrences(of: ":", with: "-")
        let slugLabel = displayLabel
            .replacingOccurrences(of: " ", with: "-")
            .replacingOccurrences(of: ":", with: "-")

        XCTAssertEqual(item.recordingMetadata?.recordingStartedAt, Date(timeIntervalSince1970: 10))
        XCTAssertEqual(item.recordingMetadata?.recordingStoppedAt, Date(timeIntervalSince1970: 20))
        XCTAssertEqual(item.recordingMetadata?.title, "Display - \(displayLabel)")
        XCTAssertEqual(item.recordingMetadata?.titleSource, .appContext)
        XCTAssertEqual(item.recordingMetadata?.titleConfidence, .high)
        XCTAssertTrue(
            item.recordingMetadata?.safeFileBasename.hasPrefix("\(basenameLabel)_display-\(slugLabel)_") == true
        )
        XCTAssertEqual(savedItem.recordingMetadata, item.recordingMetadata)
    }

    func testRefreshPreservesPersistedRecordingMetadataAndStableIdentityWhenScopeChanges() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let package = try makeRecordingPackage(
            root: root,
            directoryId: "package-1",
            sessionId: "session-1",
            scopeApproval: captureScope(sourceDisplayName: "Zoom")
        )
        let queueURL = root.appendingPathComponent("queue.json")
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )

        let first = try XCTUnwrap(service.scanAndEnqueueCompletedRecordings().first)
        let selectedEventId = "00000000-0000-0000-0000-000000000060"
        var persisted = first
        persisted.calendarContextEventId = selectedEventId
        try JSONEncoder.uploadQueueTestEncoder
            .encode(DesktopUploadQueueDocument(updatedAt: first.updatedAt, items: [persisted]))
            .write(to: queueURL, options: [.atomic])
        let refreshedService = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 200) }
        )
        let changedManifest = makeManifest(
            directoryId: "package-1",
            sessionId: "session-1",
            scopeApproval: captureScope(sourceDisplayName: "Slack")
        )
        try LocalRecordingManifestService().write(changedManifest, to: package.manifestURL)

        let refreshed = try XCTUnwrap(refreshedService.scanAndEnqueueCompletedRecordings().first)

        XCTAssertEqual(refreshed.recordingMetadata, first.recordingMetadata)
        XCTAssertEqual(refreshed.calendarContextEventId, selectedEventId)
        XCTAssertEqual(refreshed.recordingMetadata?.recordingStartedAt, first.recordingMetadata?.recordingStartedAt)
        XCTAssertEqual(refreshed.recordingMetadata?.recordingStoppedAt, first.recordingMetadata?.recordingStoppedAt)
        XCTAssertEqual(refreshed.localMediaRevisionId, first.localMediaRevisionId)
        XCTAssertEqual(
            DesktopUploadClient.idempotencyKey(item: refreshed, scope: "meeting"),
            DesktopUploadClient.idempotencyKey(item: first, scope: "meeting")
        )
    }

    func testEnqueuePersistsCalendarContextEventId() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let package = try makeRecordingPackage(
            root: root,
            directoryId: "calendar-package",
            sessionId: "calendar-session"
        )
        let manifest = try LocalRecordingManifestService().read(from: package.manifestURL)
        let queueURL = root.appendingPathComponent("queue.json")
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )
        let eventId = "00000000-0000-0000-0000-000000000060"

        let item = try service.enqueue(
            manifest: manifest,
            directoryURL: package.directoryURL,
            reason: "calendar_prompt_recording",
            calendarContextEventId: eventId
        )

        XCTAssertEqual(item.calendarContextEventId, eventId)
        XCTAssertEqual(try service.loadItems().first?.calendarContextEventId, eventId)
    }

    func testQualityLeakageStateDoesNotBlockStructurallyValidPackageUpload() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let directoryURL = root.appendingPathComponent("leakage-warning-package", isDirectory: true)
        try FileManager.default.createDirectory(at: directoryURL, withIntermediateDirectories: true)
        let manifestURL = directoryURL.appendingPathComponent("manifest.json")
        let micURL = directoryURL.appendingPathComponent("mic.wav")
        let incomingURL = directoryURL.appendingPathComponent("incoming.wav")
        try Data(repeating: 1, count: 128).write(to: micURL)
        try Data(repeating: 2, count: 128).write(to: incomingURL)
        let manifest = makeManifest(
            directoryId: "leakage-warning-package",
            sessionId: "leakage-warning-session",
            leakageFinalization: uploadQueueBlockedLeakageFinalization(),
            webRTCAEC3Outcome: uploadQueueWebRTCAEC3GuidanceOutcome(),
            status: .failed,
            transcriptionReadiness: .failed,
            failureReason: .leakageDetected
        )
        try LocalRecordingManifestService().write(manifest, to: manifestURL)

        let profile = DesktopUploadQueueService.artifactProfile(
            manifest: manifest,
            manifestURL: manifestURL,
            microphoneURL: micURL,
            systemAudioURL: incomingURL
        )

        XCTAssertTrue(profile.isUploadable)
    }

    func testScanQueuesLeakageFailedPackageWhenFilesConsentPermissionsAreValid() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        _ = try makeRecordingPackage(
            root: root,
            directoryId: "leakage-blocked-package",
            sessionId: "leakage-blocked-session",
            leakageFinalization: uploadQueueBlockedLeakageFinalization(),
            status: .failed,
            transcriptionReadiness: .failed,
            failureReason: .leakageDetected
        )
        let service = DesktopUploadQueueService(
            queueURL: root.appendingPathComponent("queue.json"),
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )

        let item = try XCTUnwrap(service.scanAndEnqueueCompletedRecordings().first)
        let summary = DesktopUploadQueueSummary(primaryItem: item, pendingCount: 1, totalCount: 1)

        XCTAssertEqual(item.state, .queued)
        XCTAssertNil(item.failureReason)
        XCTAssertTrue(item.artifactProfile.isUploadable)
        XCTAssertEqual(item.artifactProfile.qualityWarningReason, LocalRecordingFailureReason.leakageDetected.rawValue)
        XCTAssertEqual(summary.detail, "локальная копия сохранена, отправим при сети")
    }

    func testQualityReadinessFailuresRemainUploadableWhenPackageIsStructurallyValid() throws {
        let cases: [(LocalRecordingFailureReason, LeakageFinalization?)] = [
            (.leakageUnproven, uploadQueueLeakageFinalization(
                status: .unproven,
                alignmentStatus: .aligned,
                failureReason: .leakageUnproven,
                transcriptionGate: .blockedUnproven
            )),
            (.leakageNotMeasured, uploadQueueLeakageFinalization(
                status: .notMeasured,
                measurementAttempted: false,
                measurementApplicable: false,
                alignmentStatus: .unknown,
                failureReason: .leakageNotMeasured,
                transcriptionGate: .blockedNotMeasured
            )),
            (.insufficientReference, uploadQueueLeakageFinalization(
                status: .unproven,
                alignmentStatus: .insufficientReference,
                failureReason: .insufficientReference,
                transcriptionGate: .blockedUnproven
            )),
            (.timelineMisaligned, uploadQueueLeakageFinalization(
                status: .unproven,
                alignmentStatus: .misaligned,
                failureReason: .timelineMisaligned,
                transcriptionGate: .blockedTimelineMisaligned
            )),
            (.silentInput, nil)
        ]

        for (index, testCase) in cases.enumerated() {
            let root = temporaryRoot()
            defer { try? FileManager.default.removeItem(at: root) }
            _ = try makeRecordingPackage(
                root: root,
                directoryId: "quality-warning-\(index)",
                sessionId: "quality-warning-session-\(index)",
                leakageFinalization: testCase.1,
                status: .failed,
                transcriptionReadiness: .failed,
                failureReason: testCase.0
            )
            let service = DesktopUploadQueueService(
                queueURL: root.appendingPathComponent("queue.json"),
                recordingsRootURL: root,
                client: nil,
                clock: { Date(timeIntervalSince1970: 100) }
            )

            let item = try XCTUnwrap(service.scanAndEnqueueCompletedRecordings().first)

            XCTAssertEqual(item.state, .queued, "failure reason \(testCase.0.rawValue) must not block upload")
            XCTAssertNil(item.failureReason)
            XCTAssertTrue(item.artifactProfile.isUploadable)
            XCTAssertEqual(item.artifactProfile.qualityWarningReason, testCase.0.rawValue)
        }
    }

    func testMissingFilesConsentAndPermissionsStillBlockUpload() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        _ = try makeRecordingPackage(
            root: root,
            directoryId: "missing-incoming-package",
            sessionId: "missing-incoming-session",
            includeIncoming: false
        )
        _ = try makeRecordingPackage(
            root: root,
            directoryId: "permission-denied-package",
            sessionId: "permission-denied-session",
            permissions: SystemAudioPermissionSnapshot(
                microphone: .denied,
                systemAudio: .granted,
                evaluatedAt: Date(timeIntervalSince1970: 9)
            )
        )
        _ = try makeRecordingPackage(
            root: root,
            directoryId: "scope-rejected-package",
            sessionId: "scope-rejected-session",
            scopeApproval: CaptureScopeApproval(
                scopeApprovalId: "scope-rejected",
                scopeKind: .display,
                sourceDisplayName: "Display",
                approvedBy: "system",
                approvedAt: Date(timeIntervalSince1970: 9),
                approvalMode: .userConfirmedSuggestedScope,
                eligibleReason: .manualMeetingScope
            )
        )
        let service = DesktopUploadQueueService(
            queueURL: root.appendingPathComponent("queue.json"),
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )

        let items = try service.scanAndEnqueueCompletedRecordings()
        let byDirectory = Dictionary(uniqueKeysWithValues: items.map { ($0.directoryId, $0) })

        XCTAssertEqual(byDirectory["missing-incoming-package"]?.state, .blocked)
        XCTAssertEqual(byDirectory["missing-incoming-package"]?.failureReason, "local_artifacts_not_uploadable")
        XCTAssertEqual(byDirectory["permission-denied-package"]?.state, .blocked)
        XCTAssertEqual(byDirectory["permission-denied-package"]?.failureReason, LocalRecordingFailureReason.permissionDenied.rawValue)
        XCTAssertEqual(byDirectory["scope-rejected-package"]?.state, .blocked)
        XCTAssertEqual(byDirectory["scope-rejected-package"]?.failureReason, LocalRecordingFailureReason.scopeUnavailable.rawValue)
    }

    func testOfflineQueueSurvivesRestartWithoutServerTruth() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let package = try makeRecordingPackage(root: root, directoryId: "offline-package-1", sessionId: "offline-session-1")
        let queueURL = root.appendingPathComponent("queue.json")
        let initialService = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )

        let enqueued = try XCTUnwrap(initialService.scanAndEnqueueCompletedRecordings().first)
        let restartedService = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 200) }
        )
        let reloaded = try XCTUnwrap(restartedService.loadItems().first)
        let documentData = try Data(contentsOf: queueURL)
        let document = try JSONDecoder.uploadQueueTestDecoder.decode(DesktopUploadQueueDocument.self, from: documentData)

        XCTAssertEqual(document.schemaVersion, DesktopUploadQueueDocument.schemaVersion)
        XCTAssertEqual(reloaded.id, enqueued.id)
        XCTAssertEqual(reloaded.state, .queued)
        XCTAssertEqual(reloaded.retryMode, .automatic)
        XCTAssertEqual(reloaded.localMediaRevisionId, "offline-package-1--initial")
        XCTAssertNil(reloaded.meetingId)
        XCTAssertNil(reloaded.mediaRevisionId)
        XCTAssertNil(reloaded.serverTruth.meetingId)
        XCTAssertTrue(FileManager.default.fileExists(atPath: package.manifestURL.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: package.localMicURL.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: package.remoteSpeakerURL.path))
    }

    func testMalformedQueueDocumentIsQuarantinedAsBlockedCustodyTruth() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let queueURL = root.appendingPathComponent("upload-queue.json")
        try Data("{ broken queue".utf8).write(to: queueURL)
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )

        let item = try XCTUnwrap(service.loadItems().first)
        let quarantineURLs = try FileManager.default.contentsOfDirectory(
            at: root.appendingPathComponent("Quarantine", isDirectory: true),
            includingPropertiesForKeys: nil
        )

        XCTAssertEqual(item.state, .blocked)
        XCTAssertEqual(item.retryMode, .manualOnly)
        XCTAssertEqual(item.syncConflictState, .queueDocumentMalformed)
        XCTAssertEqual(item.failureReason, "queue_document_malformed")
        XCTAssertEqual(item.directoryPath, "metadata-only")
        XCTAssertTrue(item.retentionDecision.localArtifactsRetained)
        XCTAssertEqual(quarantineURLs.count, 1)
        XCTAssertTrue(LocalCustodyFileProtection.isProtected(queueURL))
        XCTAssertTrue(LocalCustodyFileProtection.isProtected(try XCTUnwrap(quarantineURLs.first)))
    }

    func testQueueDocumentUsesCompleteFileProtectionAndUserOnlyPermissions() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        _ = try makeRecordingPackage(root: root, directoryId: "protected-package", sessionId: "protected-session")
        let queueURL = root.appendingPathComponent("upload-queue.json")
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )

        _ = try service.scanAndEnqueueCompletedRecordings()

        XCTAssertTrue(LocalCustodyFileProtection.isProtected(queueURL))
    }

    func testScanRefreshesExistingNonTerminalItemWhenLocalArtifactProfileChanges() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        _ = try makeRecordingPackage(root: root, directoryId: "refresh-package-1", sessionId: "refresh-session-1")
        let queueURL = root.appendingPathComponent("queue.json")
        let initialService = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )
        var staleItem = try XCTUnwrap(initialService.scanAndEnqueueCompletedRecordings().first)
        staleItem.state = .blocked
        staleItem.failureCategory = .schemaIncompatibility
        staleItem.failureReason = "local_recording_package_not_uploadable"
        staleItem.retryMode = .manualOnly
        staleItem.nextRetryAt = nil
        staleItem.artifactProfile.isUploadable = false
        let staleDocument = DesktopUploadQueueDocument(
            updatedAt: Date(timeIntervalSince1970: 110),
            items: [staleItem]
        )
        try JSONEncoder.uploadQueueTestEncoder
            .encode(staleDocument)
            .write(to: queueURL, options: [.atomic])
        let refreshService = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 120) }
        )

        let refreshed = try XCTUnwrap(refreshService.scanAndEnqueueCompletedRecordings().first)

        XCTAssertEqual(refreshed.id, staleItem.id)
        XCTAssertEqual(refreshed.state, .queued)
        XCTAssertEqual(refreshed.retryMode, .automatic)
        XCTAssertNil(refreshed.failureReason)
        XCTAssertTrue(refreshed.artifactProfile.isUploadable)
        XCTAssertEqual(refreshed.createdAt, staleItem.createdAt)
    }

    func testScanRefreshesGenericBlockedReasonWithManifestWarningMetadata() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        _ = try makeRecordingPackage(
            root: root,
            directoryId: "blocked-reason-refresh",
            sessionId: "blocked-reason-session",
            leakageFinalization: uploadQueueBlockedLeakageFinalization(),
            status: .failed,
            transcriptionReadiness: .failed,
            failureReason: .leakageDetected
        )
        let queueURL = root.appendingPathComponent("queue.json")
        let initialService = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )
        var genericItem = try XCTUnwrap(initialService.scanAndEnqueueCompletedRecordings().first)
        genericItem.failureReason = "local_recording_package_not_uploadable"
        let genericDocument = DesktopUploadQueueDocument(
            updatedAt: Date(timeIntervalSince1970: 110),
            items: [genericItem]
        )
        try JSONEncoder.uploadQueueTestEncoder
            .encode(genericDocument)
            .write(to: queueURL, options: [.atomic])
        let refreshService = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 120) }
        )

        let refreshed = try XCTUnwrap(refreshService.scanAndEnqueueCompletedRecordings().first)

        XCTAssertEqual(refreshed.state, .queued)
        XCTAssertNil(refreshed.failureReason)
        XCTAssertTrue(refreshed.artifactProfile.isUploadable)
        XCTAssertEqual(refreshed.artifactProfile.qualityWarningReason, LocalRecordingFailureReason.leakageDetected.rawValue)
    }

    func testScanClearsStaleLocalFilesMissingConflictWhenUploadingItemIsUploadableAfterRestart() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        _ = try makeRecordingPackage(root: root, directoryId: "stale-upload-package-1", sessionId: "stale-upload-session-1")
        let queueURL = root.appendingPathComponent("queue.json")
        let initialService = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )
        var staleUploadingItem = try XCTUnwrap(initialService.scanAndEnqueueCompletedRecordings().first)
        staleUploadingItem.state = .uploading
        staleUploadingItem.attemptCount = 4
        staleUploadingItem.retryMode = .automatic
        staleUploadingItem.nextRetryAt = nil
        staleUploadingItem.syncConflictState = .localFilesMissing
        let staleDocument = DesktopUploadQueueDocument(
            updatedAt: Date(timeIntervalSince1970: 110),
            items: [staleUploadingItem]
        )
        try JSONEncoder.uploadQueueTestEncoder
            .encode(staleDocument)
            .write(to: queueURL, options: [.atomic])
        let restartScanService = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 120) }
        )

        let refreshed = try XCTUnwrap(restartScanService.scanAndEnqueueCompletedRecordings().first)

        XCTAssertEqual(refreshed.id, staleUploadingItem.id)
        XCTAssertEqual(refreshed.state, .queued)
        XCTAssertEqual(refreshed.retryMode, .automatic)
        XCTAssertEqual(refreshed.nextRetryAt, Date(timeIntervalSince1970: 120))
        XCTAssertEqual(refreshed.syncConflictState, .none)
        XCTAssertNil(refreshed.failureReason)
        XCTAssertTrue(refreshed.artifactProfile.isUploadable)
        XCTAssertEqual(refreshed.attemptCount, 4)
        XCTAssertEqual(refreshed.createdAt, staleUploadingItem.createdAt)
    }

    func testReenqueuePreservesServerRevisionTruth() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let package = try makeRecordingPackage(root: root, directoryId: "reenqueue-package-1", sessionId: "reenqueue-session-1")
        let queueURL = root.appendingPathComponent("queue.json")
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )
        let item = try XCTUnwrap(service.scanAndEnqueueCompletedRecordings().first)
        let linked = item.withTransition(
            to: .retrying,
            now: Date(timeIntervalSince1970: 120),
            serverTruth: ServerTruthFingerprint(
                meetingId: "server-meeting-042",
                mediaRevisionId: "server-media-revision-042",
                uploadSessionId: "server-upload-session-042",
                acceptedBytesByTrack: ["manifest": 32],
                desktopTruthRule: "server_ranges_authoritative"
            )
        )
        let document = DesktopUploadQueueDocument(
            updatedAt: Date(timeIntervalSince1970: 120),
            items: [linked]
        )
        let encoded = try JSONEncoder.uploadQueueTestEncoder.encode(document)
        try encoded.write(to: queueURL, options: [.atomic])
        let manifest = try LocalRecordingManifestService().read(from: package.manifestURL)
        let reenqueueService = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 140) }
        )

        let reenqueue = try reenqueueService.enqueue(
            manifest: manifest,
            directoryURL: package.directoryURL,
            reason: "app_restart_scan"
        )

        XCTAssertEqual(reenqueue.meetingId, "server-meeting-042")
        XCTAssertEqual(reenqueue.mediaRevisionId, "server-media-revision-042")
        XCTAssertEqual(reenqueue.uploadSessionId, "server-upload-session-042")
        XCTAssertEqual(reenqueue.localMediaRevisionId, "reenqueue-package-1--initial")
        XCTAssertEqual(reenqueue.syncGeneration, linked.syncGeneration)
        XCTAssertEqual(reenqueue.serverTruth.acceptedBytesByTrack["manifest"], 32)
    }

    func testRefreshWithNewPlaybackTrackPreservesExistingUploadSession() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let package = try makeRecordingPackage(root: root, directoryId: "reenqueue-package-m4a", sessionId: "reenqueue-session-m4a")
        let queueURL = root.appendingPathComponent("queue.json")
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )
        let item = try XCTUnwrap(service.scanAndEnqueueCompletedRecordings().first)
        let linked = item.withTransition(
            to: .retrying,
            now: Date(timeIntervalSince1970: 120),
            serverTruth: ServerTruthFingerprint(
                meetingId: "server-meeting-m4a",
                mediaRevisionId: "server-media-revision-m4a",
                uploadSessionId: "server-upload-session-without-m4a",
                acceptedBytesByTrack: ["manifest": 32],
                desktopTruthRule: "server_ranges_authoritative"
            )
        )
        let document = DesktopUploadQueueDocument(
            updatedAt: Date(timeIntervalSince1970: 120),
            items: [linked]
        )
        let encoded = try JSONEncoder.uploadQueueTestEncoder.encode(document)
        try encoded.write(to: queueURL, options: [.atomic])
        try writeTestReviewAudio(to: package.directoryURL.appendingPathComponent("meeting-review.m4a"))
        let refreshService = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 140) }
        )

        let refreshed = try XCTUnwrap(refreshService.scanAndEnqueueCompletedRecordings().first)

        XCTAssertEqual(refreshed.meetingId, "server-meeting-m4a")
        XCTAssertEqual(refreshed.mediaRevisionId, "server-media-revision-m4a")
        XCTAssertEqual(refreshed.uploadSessionId, "server-upload-session-without-m4a")
        XCTAssertEqual(refreshed.serverTruth.uploadSessionId, "server-upload-session-without-m4a")
        XCTAssertEqual(refreshed.serverTruth.acceptedBytesByTrack["manifest"], 32)
        XCTAssertTrue(refreshed.artifactProfile.trackCompleteness.contains { $0.transportRole == .playback })
    }

    func testProcessDueItemsReconcilesBeforeUploadAndPersistsServerRanges() async throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        _ = try makeRecordingPackage(root: root, directoryId: "reconcile-package-1", sessionId: "reconcile-session-1")
        let queueURL = root.appendingPathComponent("queue.json")
        let client = ReconcileThenUploadClient(
            reconciliation: DesktopUploadReconciliation(
                serverTruth: ServerTruthFingerprint(
                    meetingId: "server-meeting-us3",
                    mediaRevisionId: "server-media-revision-us3",
                    uploadSessionId: "server-upload-session-us3",
                    acceptedBytesByTrack: ["microphone": 64],
                    desktopTruthRule: "server_ranges_authoritative"
                )
            ),
            result: DesktopUploadResult(
                state: .uploaded,
                serverTruth: ServerTruthFingerprint(
                    meetingId: "server-meeting-us3",
                    mediaRevisionId: "server-media-revision-us3",
                    uploadSessionId: "server-upload-session-us3",
                    acceptedBytesByTrack: ["microphone": 128],
                    desktopTruthRule: "server_ranges_authoritative"
                )
            )
        )
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: client,
            clock: { Date(timeIntervalSince1970: 100) }
        )

        _ = try service.scanAndEnqueueCompletedRecordings()
        _ = try await service.processDueItems()

        let uploadedItem = try XCTUnwrap(client.uploadedItems.first)
        let savedItem = try XCTUnwrap(service.loadItems().first)
        XCTAssertEqual(uploadedItem.meetingId, "server-meeting-us3")
        XCTAssertEqual(uploadedItem.mediaRevisionId, "server-media-revision-us3")
        XCTAssertEqual(uploadedItem.uploadSessionId, "server-upload-session-us3")
        XCTAssertEqual(uploadedItem.serverTruth.acceptedBytesByTrack["microphone"], 64)
        XCTAssertEqual(savedItem.state, .uploaded)
        XCTAssertEqual(savedItem.serverTruth.acceptedBytesByTrack["microphone"], 128)
        XCTAssertGreaterThanOrEqual(savedItem.syncGeneration, 2)
    }

    func testProcessDueItemsTreatsServerFinalizedReconciliationAsUploadedWithoutDuplicateUpload() async throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        _ = try makeRecordingPackage(root: root, directoryId: "finalized-response-loss", sessionId: "finalized-session")
        let queueURL = root.appendingPathComponent("queue.json")
        let client = ReconcileThenUploadClient(
            reconciliation: DesktopUploadReconciliation(
                serverTruth: ServerTruthFingerprint(
                    meetingId: "server-meeting-finalized",
                    mediaRevisionId: "server-media-finalized",
                    uploadSessionId: "server-session-finalized",
                    serverStatus: "ingested_pending_processing",
                    processingStatus: "pending_processing",
                    acceptedBytesByTrack: ["microphone": 128, "system": 128, "manifest": 64],
                    desktopTruthRule: "server_ranges_authoritative"
                )
            ),
            result: DesktopUploadResult(
                state: .uploaded,
                serverTruth: ServerTruthFingerprint(meetingId: "should-not-upload")
            )
        )
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: client,
            clock: { Date(timeIntervalSince1970: 100) }
        )

        _ = try service.scanAndEnqueueCompletedRecordings()
        let items = try await service.processDueItems()

        let savedItem = try XCTUnwrap(items.first)
        XCTAssertTrue(client.uploadedItems.isEmpty)
        XCTAssertEqual(savedItem.state, .uploaded)
        XCTAssertEqual(savedItem.retryMode, .terminal)
        XCTAssertEqual(savedItem.meetingId, "server-meeting-finalized")
        XCTAssertEqual(savedItem.mediaRevisionId, "server-media-finalized")
        XCTAssertEqual(savedItem.uploadSessionId, "server-session-finalized")
        XCTAssertEqual(savedItem.retentionDecision.decision, .terminalUploaded)
        XCTAssertTrue(savedItem.retentionDecision.localArtifactsRetained)
    }

    func testProcessDueItemsRefreshesUploadedProcessingStatusWithoutReuploading() async throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let queueURL = root.appendingPathComponent("queue.json")
        let finalizedAt = Date(timeIntervalSince1970: 100)
        var uploaded = makeQueueItem(
            state: .uploaded,
            retryMode: .terminal,
            serverTruth: ServerTruthFingerprint(
                meetingId: "server-meeting-processed",
                mediaRevisionId: "server-media-processed",
                uploadSessionId: "server-session-processed",
                serverStatus: "ingested_pending_processing",
                processingStatus: "not_submitted",
                acceptedBytesByTrack: ["microphone": 128, "system": 128, "manifest": 64],
                finalizedAt: finalizedAt,
                desktopTruthRule: "server_ranges_authoritative"
            ),
            updatedAt: finalizedAt
        )
        uploaded.lastReconciledAt = finalizedAt
        uploaded.syncGeneration = 1
        let document = DesktopUploadQueueDocument(updatedAt: finalizedAt, items: [uploaded])
        try JSONEncoder.uploadQueueTestEncoder
            .encode(document)
            .write(to: queueURL, options: [.atomic])
        let client = ReconcileThenUploadClient(
            reconciliation: DesktopUploadReconciliation(
                serverTruth: ServerTruthFingerprint(
                    meetingId: "server-meeting-processed",
                    mediaRevisionId: "server-media-processed",
                    uploadSessionId: "server-session-processed",
                    serverStatus: "ingested_pending_processing",
                    processingStatus: "processed",
                    acceptedBytesByTrack: ["microphone": 128, "system": 128, "manifest": 64],
                    finalizedAt: finalizedAt,
                    desktopTruthRule: "server_ranges_authoritative"
                )
            ),
            result: DesktopUploadResult(
                state: .uploaded,
                serverTruth: ServerTruthFingerprint(meetingId: "should-not-reupload")
            )
        )
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: client,
            clock: { Date(timeIntervalSince1970: 130) }
        )

        let items = try await service.processDueItems()

        let savedItem = try XCTUnwrap(items.first)
        XCTAssertTrue(client.uploadedItems.isEmpty)
        XCTAssertEqual(client.reconciledItems.map(\.id), [uploaded.id])
        XCTAssertEqual(savedItem.state, .uploaded)
        XCTAssertEqual(savedItem.retryMode, .terminal)
        XCTAssertEqual(savedItem.serverTruth.processingStatus, "processed")
        XCTAssertEqual(savedItem.syncConflictState, .none)
        XCTAssertEqual(savedItem.failureCategory, .none)
        XCTAssertNil(savedItem.failureReason)
        XCTAssertEqual(savedItem.lastReconciledAt, Date(timeIntervalSince1970: 130))
        XCTAssertEqual(savedItem.syncGeneration, 2)
    }

    func testReconciliationConflictBlocksUploadAndPreservesServerTruth() async throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        _ = try makeRecordingPackage(root: root, directoryId: "conflict-package-1", sessionId: "conflict-session-1")
        let queueURL = root.appendingPathComponent("queue.json")
        let client = ReconcileThenUploadClient(
            reconciliation: DesktopUploadReconciliation(
                serverTruth: ServerTruthFingerprint(
                    meetingId: "server-meeting-conflict",
                    mediaRevisionId: "server-media-revision-conflict",
                    uploadSessionId: "server-upload-session-conflict",
                    acceptedBytesByTrack: ["microphone": 64],
                    desktopTruthRule: "server_ranges_authoritative"
                ),
                conflictState: .accessRevoked,
                conflictReason: "access_revoked",
                nextAction: "sign_in_again"
            ),
            result: DesktopUploadResult(
                state: .uploaded,
                serverTruth: ServerTruthFingerprint(meetingId: "should-not-upload")
            )
        )
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: client,
            clock: { Date(timeIntervalSince1970: 100) }
        )

        _ = try service.scanAndEnqueueCompletedRecordings()
        _ = try await service.processDueItems()

        let savedItem = try XCTUnwrap(service.loadItems().first)
        XCTAssertTrue(client.uploadedItems.isEmpty)
        XCTAssertEqual(savedItem.state, .blocked)
        XCTAssertEqual(savedItem.retryMode, .manualOnly)
        XCTAssertEqual(savedItem.failureCategory, .serverValidation)
        XCTAssertEqual(savedItem.failureReason, "access_revoked")
        XCTAssertEqual(savedItem.syncConflictState, .accessRevoked)
        XCTAssertEqual(savedItem.meetingId, "server-meeting-conflict")
        XCTAssertEqual(savedItem.mediaRevisionId, "server-media-revision-conflict")
        XCTAssertEqual(savedItem.serverTruth.acceptedBytesByTrack["microphone"], 64)
        XCTAssertEqual(savedItem.retentionDecision.decision, .manualOnly)
        XCTAssertTrue(savedItem.retentionDecision.localArtifactsRetained)
    }

    func testConflictSummaryCopyIsSafeAndDoesNotLeakLocalPaths() {
        let localPath = "/Users/test/private/recordings/package/mic.wav"
        let serverDeleted = DesktopUploadQueueSummary(
            primaryItem: makeQueueItem(
                state: .blocked,
                retryMode: .manualOnly,
                failureReason: localPath,
                syncConflictState: .serverMeetingDeleted
            ),
            pendingCount: 1,
            totalCount: 1
        )
        let dependencyFailure = DesktopUploadQueueSummary(
            primaryItem: makeQueueItem(
                state: .retrying,
                retryMode: .automatic,
                failureReason: localPath,
                syncConflictState: .dependencyUnavailable
            ),
            pendingCount: 1,
            totalCount: 1
        )

        XCTAssertEqual(serverDeleted.detail, "запись удалена на сервере, нужна проверка")
        XCTAssertFalse(serverDeleted.detail.contains("/Users/test"))
        XCTAssertEqual(dependencyFailure.detail, "сервер временно недоступен, повторим позже")
        XCTAssertFalse(dependencyFailure.detail.contains("/Users/test"))
    }

    func testCustodySafeReportRedactionKeepsIncidentMetadataOnly() throws {
        let item = makeQueueItem(
            state: .blocked,
            retryMode: .manualOnly,
            failureReason: "/Users/test/private/recordings/package/mic.wav Bearer leaked-token",
            syncConflictState: .serverMeetingDeleted,
            updatedAt: Date(timeIntervalSince1970: 20)
        )
        let projection = DesktopUploadCustodyProjection(
            item: item,
            now: Date(timeIntervalSince1970: 900)
        )
        let report = try XCTUnwrap(DesktopUploadCustodySafeReport(item: item, projection: projection))

        let result = DiagnosticRedactor().redact(report.diagnosticManifest)
        let incident = try XCTUnwrap(result.manifest["custodyIncident"])

        XCTAssertEqual(result.status, .redacted)
        guard case .object(let fields) = incident else {
            return XCTFail("custodyIncident must be an object")
        }
        XCTAssertEqual(fields["owner"], .string("workspace_admin"))
        XCTAssertEqual(fields["problemCode"], .string("server_meeting_deleted"))
        XCTAssertEqual(fields["metadataSafety"], .string("metadata_only"))
        XCTAssertNil(fields["privateLocalPath"])
        XCTAssertNil(fields["signedUrl"])
        XCTAssertFalse(report.clipboardText.contains("/Users/test"))
        XCTAssertFalse(report.clipboardText.contains("Bearer"))
        XCTAssertFalse(report.clipboardText.localizedCaseInsensitiveContains("transcript"))
        XCTAssertFalse(report.clipboardText.localizedCaseInsensitiveContains("audio"))
    }

    func testRetentionExpiryMarksRecoverableConflictWithoutDeletingArtifacts() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        _ = try makeRecordingPackage(root: root, directoryId: "package-retention-conflict", sessionId: "session-retention-conflict")
        let service = DesktopUploadQueueService(
            queueURL: root.appendingPathComponent("queue.json"),
            recordingsRootURL: root,
            policy: LocalBufferPolicy(
                maxBytesPerDevice: 2_000_000_000,
                warningFraction: 0.75,
                criticalFraction: 0.9,
                minimumDiskReserveBytes: 20 * 1024 * 1024,
                retentionDays: 1
            ),
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )
        let item = try XCTUnwrap(service.scanAndEnqueueCompletedRecordings().first)
        _ = try service.stopRetry(itemId: item.id)
        _ = try service.retry(itemId: item.id)
        let expiredService = DesktopUploadQueueService(
            queueURL: root.appendingPathComponent("queue.json"),
            recordingsRootURL: root,
            policy: LocalBufferPolicy(
                maxBytesPerDevice: 2_000_000_000,
                warningFraction: 0.75,
                criticalFraction: 0.9,
                minimumDiskReserveBytes: 20 * 1024 * 1024,
                retentionDays: 1
            ),
            client: nil,
            clock: { Date(timeIntervalSince1970: 200_000) }
        )

        let expired = try XCTUnwrap(expiredService.applyRetentionExpiry().first)

        XCTAssertEqual(expired.state, .blocked)
        XCTAssertEqual(expired.retryMode, .manualOnly)
        XCTAssertEqual(expired.syncConflictState, .retentionExpired)
        XCTAssertTrue(expired.retentionDecision.localArtifactsRetained)
        XCTAssertTrue(FileManager.default.fileExists(atPath: expired.microphonePath))
        XCTAssertTrue(FileManager.default.fileExists(atPath: expired.systemAudioPath))
    }

    func testMuteTruthMetadataDoesNotChangeUploadCompletenessDecision() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        _ = try makeRecordingPackage(
            root: root,
            directoryId: "package-mute-truth",
            sessionId: "session-mute-truth",
            includeMuteTruth: true
        )
        let service = DesktopUploadQueueService(
            queueURL: root.appendingPathComponent("queue.json"),
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )

        let item = try XCTUnwrap(service.scanAndEnqueueCompletedRecordings().first)

        XCTAssertEqual(item.state, .queued)
        XCTAssertTrue(item.artifactProfile.isUploadable)
        XCTAssertTrue(item.artifactProfile.trackCompleteness.contains { $0.transportRole == .microphone })
        XCTAssertTrue(item.artifactProfile.trackCompleteness.contains { $0.transportRole == .system })
        XCTAssertTrue(item.artifactProfile.trackCompleteness.contains { $0.transportRole == .manifest })
    }

    func testMicrophoneSampleGraphMetadataDoesNotChangeUploadCompletenessDecision() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        _ = try makeRecordingPackage(
            root: root,
            directoryId: "package-mic-graph",
            sessionId: "session-mic-graph",
            includeMicrophoneGraphMetadata: true
        )
        let service = DesktopUploadQueueService(
            queueURL: root.appendingPathComponent("queue.json"),
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )

        let item = try XCTUnwrap(service.scanAndEnqueueCompletedRecordings().first)

        XCTAssertEqual(item.state, .queued)
        XCTAssertTrue(item.artifactProfile.isUploadable)
        XCTAssertEqual(item.artifactProfile.trackCompleteness.map(\.transportRole), [.microphone, .system, .manifest])
        XCTAssertEqual(item.artifactProfile.microphoneSizeBytes, 128)
        XCTAssertEqual(item.artifactProfile.systemAudioSizeBytes, 128)
        XCTAssertGreaterThan(item.artifactProfile.manifestSizeBytes, 128)
    }

    func testMicrophoneSampleGraphMetadataDoesNotChangeUploadFileDescriptors() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        _ = try makeRecordingPackage(
            root: root,
            directoryId: "package-mic-graph-descriptors",
            sessionId: "session-mic-graph-descriptors",
            includeMicrophoneGraphMetadata: true
        )
        let service = DesktopUploadQueueService(
            queueURL: root.appendingPathComponent("queue.json"),
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )
        let item = try XCTUnwrap(service.scanAndEnqueueCompletedRecordings().first)

        let descriptors = DesktopUploadClient.uploadFileDescriptors(for: item)

        XCTAssertEqual(descriptors.map(\.transportRole), [.microphone, .system, .manifest])
        XCTAssertEqual(
            descriptors.map { $0.url.lastPathComponent },
            ["mic.wav", "incoming.wav", "manifest.json"]
        )
    }

    func testCompletedPackageWithReviewM4AAddsPlaybackDescriptorWithoutChangingRequiredTracks() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        _ = try makeRecordingPackage(
            root: root,
            directoryId: "package-review-m4a",
            sessionId: "session-review-m4a",
            includeReviewAudio: true
        )
        let service = DesktopUploadQueueService(
            queueURL: root.appendingPathComponent("queue.json"),
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )
        let item = try XCTUnwrap(service.scanAndEnqueueCompletedRecordings().first)

        let descriptors = DesktopUploadClient.uploadFileDescriptors(for: item)

        XCTAssertTrue(item.artifactProfile.isUploadable)
        XCTAssertEqual(item.artifactProfile.trackCompleteness.map(\.transportRole), [.microphone, .system, .manifest, .playback])
        XCTAssertEqual(descriptors.map(\.transportRole), [.microphone, .system, .manifest, .playback])
        XCTAssertEqual(descriptors.last?.url.lastPathComponent, "meeting-review.m4a")
        XCTAssertEqual(descriptors.last?.codec, "m4a-aac-lc")
        XCTAssertEqual(descriptors.last?.sampleRateHz, 48_000)
    }

    func testCompletedPackageWithInvalidReviewM4AIgnoresPlaybackDescriptor() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let package = try makeRecordingPackage(
            root: root,
            directoryId: "package-invalid-review-m4a",
            sessionId: "session-invalid-review-m4a"
        )
        try Data(repeating: 4, count: 256).write(to: package.directoryURL.appendingPathComponent("meeting-review.m4a"))
        let service = DesktopUploadQueueService(
            queueURL: root.appendingPathComponent("queue.json"),
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )

        let item = try XCTUnwrap(service.scanAndEnqueueCompletedRecordings().first)
        let descriptors = DesktopUploadClient.uploadFileDescriptors(for: item)

        XCTAssertTrue(item.artifactProfile.isUploadable)
        XCTAssertEqual(item.artifactProfile.trackCompleteness.map(\.transportRole), [.microphone, .system, .manifest])
        XCTAssertEqual(descriptors.map(\.transportRole), [.microphone, .system, .manifest])
    }

    func testCompletedPackageWithRenamedWAVReviewAudioIgnoresPlaybackDescriptor() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let package = try makeRecordingPackage(
            root: root,
            directoryId: "package-renamed-wav-review-m4a",
            sessionId: "session-renamed-wav-review-m4a"
        )
        try writeTestReviewWAV(to: package.directoryURL.appendingPathComponent("meeting-review.m4a"))
        let service = DesktopUploadQueueService(
            queueURL: root.appendingPathComponent("queue.json"),
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )

        let item = try XCTUnwrap(service.scanAndEnqueueCompletedRecordings().first)
        let descriptors = DesktopUploadClient.uploadFileDescriptors(for: item)

        XCTAssertTrue(item.artifactProfile.isUploadable)
        XCTAssertEqual(item.artifactProfile.trackCompleteness.map(\.transportRole), [.microphone, .system, .manifest])
        XCTAssertEqual(descriptors.map(\.transportRole), [.microphone, .system, .manifest])
    }

    func testIncompletePackageBecomesBlockedAndManualOnly() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        _ = try makeRecordingPackage(root: root, directoryId: "package-2", sessionId: "session-2", includeIncoming: false)
        let service = DesktopUploadQueueService(
            queueURL: root.appendingPathComponent("queue.json"),
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )

        let items = try service.scanAndEnqueueCompletedRecordings()

        XCTAssertEqual(items.first?.state, .blocked)
        XCTAssertEqual(items.first?.retryMode, .manualOnly)
        XCTAssertEqual(items.first?.failureCategory, .schemaIncompatibility)
    }

    func testRetentionExpiryMovesRetryingItemToManualOnlyWithoutDeletingArtifacts() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        _ = try makeRecordingPackage(root: root, directoryId: "package-3", sessionId: "session-3")
        let service = DesktopUploadQueueService(
            queueURL: root.appendingPathComponent("queue.json"),
            recordingsRootURL: root,
            policy: LocalBufferPolicy(
                maxBytesPerDevice: 2_000_000_000,
                warningFraction: 0.75,
                criticalFraction: 0.9,
                minimumDiskReserveBytes: 20 * 1024 * 1024,
                retentionDays: 1
            ),
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )
        let item = try service.scanAndEnqueueCompletedRecordings().first!
        _ = try service.stopRetry(itemId: item.id)
        _ = try service.retry(itemId: item.id)
        let expiredService = DesktopUploadQueueService(
            queueURL: root.appendingPathComponent("queue.json"),
            recordingsRootURL: root,
            policy: LocalBufferPolicy(
                maxBytesPerDevice: 2_000_000_000,
                warningFraction: 0.75,
                criticalFraction: 0.9,
                minimumDiskReserveBytes: 20 * 1024 * 1024,
                retentionDays: 1
            ),
            client: nil,
            clock: { Date(timeIntervalSince1970: 200_000) }
        )

        let expired = try expiredService.applyRetentionExpiry()

        XCTAssertEqual(expired.first?.state, .blocked)
        XCTAssertEqual(expired.first?.retryMode, .manualOnly)
        XCTAssertEqual(expired.first?.retentionDecision.localArtifactsRetained, true)
        XCTAssertEqual(expired.first?.failureReason, "automatic_retry_window_expired")
    }

    func testUploadedProcessingFollowUpStopsAfterProcessedStatus() {
        let active = makeQueueItem(
            state: .uploaded,
            retryMode: .terminal,
            serverTruth: ServerTruthFingerprint(
                meetingId: "meeting-active",
                processingStatus: "workflow_started",
                finalizedAt: Date(timeIntervalSince1970: 100)
            ),
            updatedAt: Date(timeIntervalSince1970: 100)
        )
        let processed = makeQueueItem(
            state: .uploaded,
            retryMode: .terminal,
            serverTruth: ServerTruthFingerprint(
                meetingId: "meeting-processed",
                processingStatus: "processed",
                finalizedAt: Date(timeIntervalSince1970: 100)
            ),
            updatedAt: Date(timeIntervalSince1970: 100)
        )

        XCTAssertTrue(DesktopUploadQueueService.needsProcessingFollowUp(
            active,
            now: Date(timeIntervalSince1970: 130)
        ))
        XCTAssertFalse(DesktopUploadQueueService.needsProcessingFollowUp(
            processed,
            now: Date(timeIntervalSince1970: 130)
        ))
    }

    func testSupportIncidentSubmissionPersistsSentIncidentNumber() async throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let queueURL = root.appendingPathComponent("upload-queue.json")
        let item = makeSupportIncidentItem(id: "support-sent")
        try JSONEncoder.uploadQueueTestEncoder
            .encode(DesktopUploadQueueDocument(updatedAt: item.updatedAt, items: [item]))
            .write(to: queueURL, options: [.atomic])
        let client = SupportIncidentOnlyClient(result: DesktopSupportIncidentResponse(
            incidentId: "CUST-123",
            incidentStatus: "created",
            githubIssueNumber: 123,
            githubIssueURL: "https://github.com/yshishenya/crisp/issues/123",
            dedupeStatus: "created",
            affectedCount: 1,
            copyFallbackAvailable: true,
            userMessage: DesktopSupportIncidentFixture.successMessage
        ))
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: client,
            clock: { Date(timeIntervalSince1970: 200) }
        )

        let response = try await service.submitSupportIncident(itemId: item.id)
        let saved = try XCTUnwrap(service.loadItems().first)

        XCTAssertEqual(response.incidentId, "CUST-123")
        XCTAssertEqual(client.reports.count, 1)
        XCTAssertEqual(client.reports.first?.normalUserAction, "send_support_report")
        XCTAssertEqual(saved.supportIncidentSubmission?.state, .sent)
        XCTAssertEqual(saved.supportIncidentSubmission?.incidentNumber, "CUST-123")
        XCTAssertEqual(saved.supportIncidentSubmission?.githubIssueNumber, 123)
        XCTAssertTrue(saved.supportIncidentSubmission?.copyFallbackAvailable == true)
    }

    func testSupportIncidentSubmissionAggregatesMatchingItems() async throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let queueURL = root.appendingPathComponent("upload-queue.json")
        let items = (0..<6).map { makeSupportIncidentItem(id: "support-aggregate-\($0)") }
        try JSONEncoder.uploadQueueTestEncoder
            .encode(DesktopUploadQueueDocument(updatedAt: Date(timeIntervalSince1970: 20), items: items))
            .write(to: queueURL, options: [.atomic])
        let client = SupportIncidentOnlyClient(result: DesktopSupportIncidentResponse(
            incidentId: "CUST-123",
            incidentStatus: "created",
            githubIssueNumber: 123,
            githubIssueURL: "https://github.com/yshishenya/crisp/issues/123",
            dedupeStatus: "created",
            affectedCount: 6,
            copyFallbackAvailable: true,
            userMessage: DesktopSupportIncidentFixture.successMessage
        ))
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: client,
            clock: { Date(timeIntervalSince1970: 200) }
        )

        let response = try await service.submitSupportIncident(itemIds: items.map(\.id))
        let saved = try service.loadItems()

        XCTAssertEqual(response.affectedCount, 6)
        XCTAssertEqual(client.reports.count, 1)
        XCTAssertEqual(client.reports.first?.affectedCount, 6)
        XCTAssertEqual(client.reports.first?.safeAffectedIdentities.count, 5)
        XCTAssertEqual(saved.compactMap(\.supportIncidentSubmission?.incidentNumber), Array(repeating: "CUST-123", count: 6))
    }

    func testSupportIncidentSubmissionFailurePersistsCopyFallbackState() async throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let queueURL = root.appendingPathComponent("upload-queue.json")
        let item = makeSupportIncidentItem(id: "support-failed")
        try JSONEncoder.uploadQueueTestEncoder
            .encode(DesktopUploadQueueDocument(updatedAt: item.updatedAt, items: [item]))
            .write(to: queueURL, options: [.atomic])
        let client = SupportIncidentOnlyClient(
            error: DesktopUploadClientError.httpStatus(503, "support_incident.github_unavailable")
        )
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: client,
            clock: { Date(timeIntervalSince1970: 200) }
        )

        do {
            _ = try await service.submitSupportIncident(itemId: item.id)
            XCTFail("Expected support incident submission to fail")
        } catch DesktopUploadClientError.httpStatus(let status, let code) {
            XCTAssertEqual(status, 503)
            XCTAssertEqual(code, "support_incident.github_unavailable")
        }
        let saved = try XCTUnwrap(service.loadItems().first)

        XCTAssertEqual(client.reports.count, 1)
        XCTAssertEqual(saved.supportIncidentSubmission?.state, .failedWithCopyFallback)
        XCTAssertEqual(saved.supportIncidentSubmission?.lastFailureCategory, UploadFailureCategory.network.rawValue)
        XCTAssertEqual(saved.supportIncidentSubmission?.lastFailureCode, "support_incident.github_unavailable")
        XCTAssertTrue(saved.supportIncidentSubmission?.copyFallbackAvailable == true)
    }

    func testInterruptedSupportIncidentSubmissionRecoversCopyFallbackOnRestart() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let queueURL = root.appendingPathComponent("upload-queue.json")
        var item = makeSupportIncidentItem(id: "support-interrupted")
        item.supportIncidentSubmission = .sending(
            reportFingerprint: "report_fpr_1234abcd",
            dedupeKey: "support_dedupe_1234abcd",
            attemptedAt: Date(timeIntervalSince1970: 100)
        )
        try JSONEncoder.uploadQueueTestEncoder
            .encode(DesktopUploadQueueDocument(updatedAt: item.updatedAt, items: [item]))
            .write(to: queueURL, options: [.atomic])
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: SupportIncidentOnlyClient(),
            clock: { Date(timeIntervalSince1970: 200) }
        )

        let saved = try XCTUnwrap(service.loadItems().first)

        XCTAssertEqual(saved.supportIncidentSubmission?.state, .failedWithCopyFallback)
        XCTAssertEqual(saved.supportIncidentSubmission?.localReportFingerprint, "report_fpr_1234abcd")
        XCTAssertEqual(saved.supportIncidentSubmission?.dedupeKey, "support_dedupe_1234abcd")
        XCTAssertEqual(saved.supportIncidentSubmission?.lastFailureCategory, UploadFailureCategory.network.rawValue)
        XCTAssertEqual(saved.supportIncidentSubmission?.lastFailureCode, "support_incident.interrupted")
        XCTAssertTrue(saved.supportIncidentSubmission?.copyFallbackAvailable == true)
    }

    func testQueueDocumentUsesRevisionReadyV2Schema() {
        let fixture = makeQueueV2Fixture(directoryId: "recording-sync-001")

        XCTAssertEqual(fixture.localMediaRevisionId, "recording-sync-001--initial")
        XCTAssertEqual(DesktopUploadQueueDocument.schemaVersion, fixture.schemaVersion)
    }

    func testNextScheduledRetryDateSelectsEarliestFutureAutomaticRetry() {
        let now = Date(timeIntervalSince1970: 100)
        var dueNow = makeQueueItem(id: "due-now", state: .queued, retryMode: .automatic)
        dueNow.nextRetryAt = now
        var later = makeQueueItem(id: "later", state: .retrying, retryMode: .automatic)
        later.nextRetryAt = Date(timeIntervalSince1970: 160)
        var sooner = makeQueueItem(id: "sooner", state: .retrying, retryMode: .automatic)
        sooner.nextRetryAt = Date(timeIntervalSince1970: 130)
        var manual = makeQueueItem(id: "manual", state: .blocked, retryMode: .manualOnly)
        manual.nextRetryAt = Date(timeIntervalSince1970: 120)

        let next = DesktopUploadQueueService.nextScheduledRetryDate(
            for: [dueNow, later, sooner, manual],
            now: now
        )

        XCTAssertEqual(next, Date(timeIntervalSince1970: 130))
    }

    private func makeQueueItem(
        id: String = "queue-id",
        state: UploadItemState = .queued,
        retryMode: UploadRetryMode = .automatic,
        failureReason: String? = nil,
        syncConflictState: DesktopSyncConflictState = .none,
        meetingId: String? = nil,
        serverTruth: ServerTruthFingerprint = ServerTruthFingerprint(),
        createdAt: Date = Date(timeIntervalSince1970: 1),
        updatedAt: Date = Date(timeIntervalSince1970: 1)
    ) -> DesktopUploadQueueItem {
        let profile = ArtifactCompletenessProfile(
            schemaVersion: LocalRecordingManifest.schemaVersion,
            manifestPresent: true,
            microphonePresent: true,
            systemAudioPresent: true,
            manifestSha256: String(repeating: "a", count: 64),
            microphoneSha256: String(repeating: "b", count: 64),
            systemAudioSha256: String(repeating: "c", count: 64),
            manifestSizeBytes: 128,
            microphoneSizeBytes: 100,
            systemAudioSizeBytes: 100,
            durationSeconds: 1,
            trackCompleteness: [],
            isUploadable: true
        )
        return DesktopUploadQueueItem(
            id: id,
            sessionId: "session",
            directoryId: "directory",
            directoryPath: "/tmp/directory",
            manifestPath: "/tmp/directory/manifest.json",
            microphonePath: "/tmp/directory/mic.wav",
            systemAudioPath: "/tmp/directory/incoming.wav",
            state: state,
            failureReason: failureReason,
            retryMode: retryMode,
            retentionDeadline: Date(timeIntervalSince1970: 1_000),
            createdAt: createdAt,
            updatedAt: updatedAt,
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

    private func makeSupportIncidentItem(id: String) -> DesktopUploadQueueItem {
        makeQueueItem(
            id: id,
            state: .blocked,
            retryMode: .manualOnly,
            failureReason: "automatic_retry_window_expired",
            syncConflictState: .retentionExpired,
            updatedAt: Date(timeIntervalSince1970: 20)
        )
    }

    private func makeQueueV2Fixture(
        directoryId: String = "directory",
        meetingId: String? = nil,
        mediaRevisionId: String? = nil,
        conflictState: String = "none"
    ) -> QueueV2Fixture {
        QueueV2Fixture(
            schemaVersion: "desktop-upload-queue.v2",
            directoryId: directoryId,
            localMediaRevisionId: "\(directoryId)--initial",
            meetingId: meetingId,
            mediaRevisionId: mediaRevisionId,
            syncGeneration: 1,
            syncConflictState: conflictState
        )
    }

    private func temporaryRoot() -> URL {
        FileManager.default.temporaryDirectory
            .appendingPathComponent("desktop-upload-queue-tests-\(UUID().uuidString)", isDirectory: true)
    }

    private func localMinuteLabel(_ date: Date, separator: String) -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = .current
        formatter.dateFormat = "yyyy-MM-dd\(separator)HH:mm"
        return formatter.string(from: date)
    }

    private func captureScope(sourceDisplayName: String) -> CaptureScopeApproval {
        CaptureScopeApproval(
            scopeApprovalId: "scope-\(sourceDisplayName)",
            scopeKind: .display,
            sourceDisplayName: sourceDisplayName,
            approvedAt: Date(timeIntervalSince1970: 10),
            approvalMode: .userConfirmedSuggestedScope,
            eligibleReason: .manualMeetingScope
        )
    }

    private func makeLocalPurgeTask(
        meetingId: String,
        taskType: DesktopLocalPurgeTaskType = .purgeLocalBuffers,
        state: String = "pending"
    ) throws -> DesktopLocalPurgeTask {
        let payload = """
        {
          "task_id": "71000000-0000-0000-0000-000000000001",
          "meeting_id": "\(meetingId)",
          "task_type": "\(taskType.rawValue)",
          "state": "\(state)",
          "safe_reason": "delete_requested",
          "expires_at": "2026-06-17T00:00:00Z",
          "ack_url": null
        }
        """.data(using: .utf8)!
        return try JSONDecoder.uploadQueueTestDecoder.decode(DesktopLocalPurgeTask.self, from: payload)
    }

    private func makeRecordingPackage(
        root: URL,
        directoryId: String,
        sessionId: String,
        includeIncoming: Bool = true,
        includeMuteTruth: Bool = false,
        includeMicrophoneGraphMetadata: Bool = false,
        includeReviewAudio: Bool = false,
        leakageFinalization: LeakageFinalization? = nil,
        status: LocalRecordingSessionStatus = .saved,
        transcriptionReadiness: TranscriptionReadinessState = .ready,
        failureReason: LocalRecordingFailureReason = .none,
        scopeApproval: CaptureScopeApproval? = nil,
        permissions: SystemAudioPermissionSnapshot? = nil
    ) throws -> TestRecordingPackage {
        let directoryURL = root.appendingPathComponent(directoryId, isDirectory: true)
        try FileManager.default.createDirectory(at: directoryURL, withIntermediateDirectories: true)
        let package = TestRecordingPackage(
            directoryURL: directoryURL,
            manifestURL: directoryURL.appendingPathComponent("manifest.json"),
            localMicURL: directoryURL.appendingPathComponent("mic.wav"),
            remoteSpeakerURL: directoryURL.appendingPathComponent("incoming.wav")
        )
        try Data(repeating: 1, count: 128).write(to: package.localMicURL)
        if includeIncoming {
            try Data(repeating: 2, count: 128).write(to: package.remoteSpeakerURL)
        }
        if includeReviewAudio {
            try writeTestReviewAudio(to: directoryURL.appendingPathComponent("meeting-review.m4a"))
        }
        let manifest = makeManifest(
            directoryId: directoryId,
            sessionId: sessionId,
            includeMuteTruth: includeMuteTruth,
            includeMicrophoneGraphMetadata: includeMicrophoneGraphMetadata,
            leakageFinalization: leakageFinalization,
            status: status,
            transcriptionReadiness: transcriptionReadiness,
            failureReason: failureReason,
            scopeApproval: scopeApproval,
            permissions: permissions
        )
        try LocalRecordingManifestService().write(manifest, to: package.manifestURL)
        return package
    }

    private func writeTestReviewAudio(to url: URL) throws {
        let format = AVAudioFormat(standardFormatWithSampleRate: 48_000, channels: 1)!
        let file = try AVAudioFile(
            forWriting: url,
            settings: [
                AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
                AVSampleRateKey: 48_000.0,
                AVNumberOfChannelsKey: 1,
                AVEncoderBitRateKey: 64_000
            ]
        )
        let frameCount = 4_800
        let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(frameCount))!
        buffer.frameLength = AVAudioFrameCount(frameCount)
        if let channel = buffer.floatChannelData?[0] {
            for index in 0..<frameCount {
                channel[index] = 0.05
            }
        }
        try file.write(from: buffer)
    }

    private func writeTestReviewWAV(to url: URL) throws {
        let format = AVAudioFormat(standardFormatWithSampleRate: 48_000, channels: 1)!
        let wavURL = url
            .deletingLastPathComponent()
            .appendingPathComponent("\(UUID().uuidString)-review.wav")
        defer { try? FileManager.default.removeItem(at: wavURL) }
        var file: AVAudioFile? = try AVAudioFile(
            forWriting: wavURL,
            settings: [
                AVFormatIDKey: Int(kAudioFormatLinearPCM),
                AVSampleRateKey: 48_000.0,
                AVNumberOfChannelsKey: 1,
                AVLinearPCMBitDepthKey: 16,
                AVLinearPCMIsFloatKey: false,
                AVLinearPCMIsBigEndianKey: false,
                AVLinearPCMIsNonInterleaved: false
            ]
        )
        let frameCount = 4_800
        let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(frameCount))!
        buffer.frameLength = AVAudioFrameCount(frameCount)
        if let channel = buffer.floatChannelData?[0] {
            for index in 0..<frameCount {
                channel[index] = 0.05
            }
        }
        try file?.write(from: buffer)
        file = nil
        try? FileManager.default.removeItem(at: url)
        try FileManager.default.moveItem(at: wavURL, to: url)
    }

    private func makeManifest(
        directoryId: String,
        sessionId: String,
        includeMuteTruth: Bool = false,
        includeMicrophoneGraphMetadata: Bool = false,
        leakageFinalization: LeakageFinalization? = nil,
        webRTCAEC3Outcome: WebRTCAEC3DecisionRecord? = nil,
        status: LocalRecordingSessionStatus = .saved,
        transcriptionReadiness: TranscriptionReadinessState = .ready,
        failureReason: LocalRecordingFailureReason = .none,
        scopeApproval: CaptureScopeApproval? = nil,
        permissions: SystemAudioPermissionSnapshot? = nil
    ) -> LocalRecordingManifest {
        let startedAt = Date(timeIntervalSince1970: 10)
        let stoppedAt = Date(timeIntervalSince1970: 20)
        let selection = includeMicrophoneGraphMetadata ? uploadQueueRecordingMicrophoneSelection(
            sessionId: sessionId,
            resolvedAt: Date(timeIntervalSince1970: 9)
        ) : nil
        let tracks = [
            LocalRecordingTrack(
                trackId: "mic-track",
                role: .localMic,
                sourceKind: .microphone,
                status: .saved,
                fileName: "mic.wav",
                format: "wav-pcm-s16le",
                sampleRate: 16_000,
                channelCount: 1,
                bitsPerSample: 16,
                durationMs: 10_000,
                byteCount: 128,
                frameCount: 160_000,
                timelineAligned: true
            ),
            LocalRecordingTrack(
                trackId: "incoming-track",
                role: .remoteSpeaker,
                sourceKind: .systemAudio,
                status: .saved,
                fileName: "incoming.wav",
                format: "wav-pcm-s16le",
                sampleRate: 16_000,
                channelCount: 1,
                bitsPerSample: 16,
                durationMs: 10_000,
                byteCount: 128,
                frameCount: 160_000,
                timelineAligned: true
            )
        ]
        return LocalRecordingManifest(
            sessionId: sessionId,
            createdAt: startedAt,
            startedAt: startedAt,
            stoppedAt: stoppedAt,
            status: status,
            directoryId: directoryId,
            transcriptionReadiness: transcriptionReadiness,
            tracks: tracks,
            leakageFinalization: leakageFinalization,
            failureReason: failureReason,
            durationDifferenceSeconds: 0,
            scopeApproval: scopeApproval ?? CaptureScopeApproval(
                scopeApprovalId: "scope",
                scopeKind: .display,
                sourceDisplayName: "Display",
                approvedAt: startedAt,
                approvalMode: .userConfirmedSuggestedScope,
                eligibleReason: .manualMeetingScope
            ),
            permissions: permissions ?? SystemAudioPermissionSnapshot(
                microphone: .granted,
                systemAudio: .granted,
                evaluatedAt: startedAt
            ),
            microphoneSelection: selection,
            microphoneStream: selection.map {
                AppOwnedMicrophoneStreamSession(
                    sessionId: sessionId,
                    selection: $0,
                    permissionState: .granted,
                    streamKind: .appOwnedSampleSource,
                    startedAt: startedAt,
                    stoppedAt: stoppedAt,
                    sampleRate: 48_000,
                    channelCount: 1,
                    writerSampleRate: 16_000,
                    writerChannelCount: 1,
                    frameCount: 160_000,
                    failureReason: .none
                )
            },
            microphoneStreamHealth: selection.map { _ in
                MicrophoneStreamHealth(
                    gateStatus: .passed,
                    failureReason: .none,
                    framesObserved: true,
                    timingConfidence: .usable,
                    silenceStatus: .audible,
                    cleanupReadiness: .readyForFutureProcessing,
                    evidenceCodes: ["mic_graph_ready", "incoming_reference_present"]
                )
            },
            webRTCAEC3Outcome: webRTCAEC3Outcome,
            privacySegments: includeMuteTruth ? [
                ProductPrivacySegment(
                    segmentId: "\(sessionId)-privacy-1",
                    sessionId: sessionId,
                    control: .pause,
                    startedAt: Date(timeIntervalSince1970: 12),
                    endedAt: Date(timeIntervalSince1970: 13),
                    startMonotonicMs: 2_000,
                    endMonotonicMs: 3_000
                )
            ] : nil,
            meetingMuteTruth: includeMuteTruth ? MuteTruthDecision(
                sessionId: sessionId,
                decision: .meetingMuteUnproven,
                reason: .productPauseSegmentsPresent,
                privacySegmentIds: ["\(sessionId)-privacy-1"],
                targetEvidenceIds: ["\(sessionId)-evidence-1"],
                decidedAt: stoppedAt
            ) : nil,
            meetingMuteTruthEvidence: includeMuteTruth ? [
                MeetingMuteTruthEvidence(
                    evidenceId: "\(sessionId)-evidence-1",
                    sessionId: sessionId,
                    targetId: "chrome_telemost",
                    targetDisplayName: "Chrome + Telemost",
                    source: .productPause,
                    status: .meetingMuteUnproven,
                    freshness: .unavailable,
                    limitationCopyShown: true,
                    recordedAt: startedAt
                )
            ] : nil,
            targetMuteCapability: includeMuteTruth ? .chromeTelemost : nil,
            limitationCopyShownAt: includeMuteTruth ? startedAt : nil
        )
    }

    private func uploadQueueBlockedLeakageFinalization() -> LeakageFinalization {
        uploadQueueLeakageFinalization(
            status: .leakageDetected,
            failureReason: .leakageDetected,
            transcriptionGate: .blockedLeakageDetected
        )
    }

    private func uploadQueueLeakageFinalization(
        status: LeakageStatus,
        measurementAttempted: Bool = true,
        measurementApplicable: Bool = true,
        alignmentStatus: LeakageAlignmentStatus = .aligned,
        failureReason: LocalRecordingFailureReason,
        transcriptionGate: LeakageTranscriptionGate
    ) -> LeakageFinalization {
        LeakageFinalization(
            status: status,
            evaluatedAt: Date(timeIntervalSince1970: 20),
            measurementAttempted: measurementAttempted,
            measurementApplicable: measurementApplicable,
            alignmentStatus: alignmentStatus,
            confidence: 0.95,
            failureReason: failureReason,
            originalEvidenceStatus: status,
            transcriptionGate: transcriptionGate
        )
    }

    private func uploadQueueWebRTCAEC3GuidanceOutcome() -> WebRTCAEC3DecisionRecord {
        WebRTCAEC3DecisionRecord(
            candidateId: "aec3-upload-guidance",
            primaryOutcome: .acceptedForGuidanceOnly,
            validationRows: [
                WebRTCAEC3ValidationRow(
                    rowId: "aec3-upload-row",
                    candidateId: "aec3-upload-guidance",
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

    private func uploadQueueRecordingMicrophoneSelection(
        sessionId: String,
        resolvedAt: Date
    ) -> RecordingMicrophoneSelection {
        RecordingMicrophoneSelection(
            selectionId: "\(sessionId)-selection",
            mode: .userSelected,
            inputDeviceId: "built-in-mic",
            inputDisplayName: "Built-in Microphone",
            deviceClass: .builtIn,
            workingDeviceKind: .physical,
            selectionResult: .accepted,
            resolvedAt: resolvedAt
        )
    }

    private struct TestRecordingPackage {
        let directoryURL: URL
        let manifestURL: URL
        let localMicURL: URL
        let remoteSpeakerURL: URL
    }

    private struct QueueV2Fixture: Equatable {
        let schemaVersion: String
        let directoryId: String
        let localMediaRevisionId: String
        let meetingId: String?
        let mediaRevisionId: String?
        let syncGeneration: Int
        let syncConflictState: String
    }

    private final class LocalPurgeOnlyClient: @unchecked Sendable, DesktopUploadClientProtocol {
        struct Acknowledgement {
            let taskId: String
            let state: DesktopLocalPurgeTaskState
            let reasonCode: String
        }

        private let tasks: [DesktopLocalPurgeTask]
        private let reconciliation: DesktopUploadReconciliation?
        private let reconciliationError: Error?
        private let acknowledgementError: Error?
        private(set) var reconciledItems: [DesktopUploadQueueItem] = []
        private(set) var acknowledgements: [Acknowledgement] = []

        init(
            tasks: [DesktopLocalPurgeTask],
            reconciliation: DesktopUploadReconciliation? = nil,
            reconciliationError: Error? = nil,
            acknowledgementError: Error? = nil
        ) {
            self.tasks = tasks
            self.reconciliation = reconciliation
            self.reconciliationError = reconciliationError
            self.acknowledgementError = acknowledgementError
        }

        func reconcile(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadReconciliation? {
            reconciledItems.append(item)
            if let reconciliationError {
                throw reconciliationError
            }
            return reconciliation
        }

        func upload(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadResult {
            throw DesktopUploadQueueServiceError.packageNotFound(item.id)
        }

        func listLocalPurgeTasks() async throws -> [DesktopLocalPurgeTask] {
            tasks
        }

        func acknowledgeLocalPurgeTask(
            _ task: DesktopLocalPurgeTask,
            state: DesktopLocalPurgeTaskState,
            reasonCode: String,
            completedAt: Date?
        ) async throws -> DesktopLocalPurgeTask {
            acknowledgements.append(Acknowledgement(taskId: task.taskId, state: state, reasonCode: reasonCode))
            if let acknowledgementError {
                throw acknowledgementError
            }
            let payload = """
            {
              "task_id": "\(task.taskId)",
              "meeting_id": "\(task.meetingId)",
              "task_type": "\(task.taskType.rawValue)",
              "state": "\(state.rawValue)",
              "safe_reason": "\(reasonCode)",
              "expires_at": "2026-06-17T00:00:00Z",
              "ack_url": null
            }
            """.data(using: .utf8)!
            return try JSONDecoder.uploadQueueTestDecoder.decode(DesktopLocalPurgeTask.self, from: payload)
        }
    }

    private final class ReconcileThenUploadClient: @unchecked Sendable, DesktopUploadClientProtocol {
        private let reconciliation: DesktopUploadReconciliation?
        private let result: DesktopUploadResult
        private(set) var reconciledItems: [DesktopUploadQueueItem] = []
        private(set) var uploadedItems: [DesktopUploadQueueItem] = []

        init(reconciliation: DesktopUploadReconciliation?, result: DesktopUploadResult) {
            self.reconciliation = reconciliation
            self.result = result
        }

        func reconcile(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadReconciliation? {
            reconciledItems.append(item)
            return reconciliation
        }

        func upload(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadResult {
            uploadedItems.append(item)
            return result
        }

        func listLocalPurgeTasks() async throws -> [DesktopLocalPurgeTask] {
            []
        }

        func acknowledgeLocalPurgeTask(
            _ task: DesktopLocalPurgeTask,
            state: DesktopLocalPurgeTaskState,
            reasonCode: String,
            completedAt: Date?
        ) async throws -> DesktopLocalPurgeTask {
            task
        }
    }

    private final class SupportIncidentOnlyClient: @unchecked Sendable, DesktopUploadClientProtocol {
        private let result: DesktopSupportIncidentResponse?
        private let error: Error?
        private(set) var reports: [DesktopSupportIncidentReport] = []

        init(result: DesktopSupportIncidentResponse? = nil, error: Error? = nil) {
            self.result = result
            self.error = error
        }

        func supportIncidentContext() -> DesktopSupportIncidentReportContext {
            DesktopSupportIncidentReportContext(
                appVersion: "2026.06.27",
                buildVersion: "1234",
                environmentBaseURLIdentity: "rec.2brain.pro",
                workspaceFingerprint: "ws_fpr_717e",
                userFingerprint: "usr_fpr_717e",
                deviceFingerprint: "dev_fpr_717e",
                safeDeviceIdentifier: "device:dev_fpr_717e"
            )
        }

        func submitSupportIncident(report: DesktopSupportIncidentReport) async throws -> DesktopSupportIncidentResponse {
            reports.append(report)
            if let error {
                throw error
            }
            return result ?? DesktopSupportIncidentResponse(
                incidentId: "CUST-123",
                incidentStatus: "created",
                githubIssueNumber: 123,
                githubIssueURL: "https://github.com/yshishenya/crisp/issues/123",
                dedupeStatus: "created",
                affectedCount: 1,
                copyFallbackAvailable: true,
                userMessage: DesktopSupportIncidentFixture.successMessage
            )
        }

        func upload(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadResult {
            throw DesktopUploadQueueServiceError.packageNotFound(item.id)
        }

        func listLocalPurgeTasks() async throws -> [DesktopLocalPurgeTask] {
            []
        }

        func acknowledgeLocalPurgeTask(
            _ task: DesktopLocalPurgeTask,
            state _: DesktopLocalPurgeTaskState,
            reasonCode _: String,
            completedAt _: Date?
        ) async throws -> DesktopLocalPurgeTask {
            task
        }
    }
}
#endif

private extension JSONDecoder {
    static var uploadQueueTestDecoder: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }
}

private extension JSONEncoder {
    static var uploadQueueTestEncoder: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }
}
