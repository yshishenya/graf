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

        XCTAssertEqual(manual.nextActionLabel, "Повторить")
        XCTAssertEqual(automatic.nextActionLabel, "Остановить повтор")

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

        XCTAssertEqual(leakageSummary.detail, "звук динамиков попал в микрофон; отправка заблокирована")
        XCTAssertEqual(silentSummary.detail, "микрофон был слишком тихим или пустым")
        XCTAssertEqual(unmeasuredSummary.detail, "не удалось проверить утечку динамиков; нужна проверка")
    }

    func testNativeMeetingListKeepsBlockedLocalRecordingsVisibleUntilServerSeesThem() {
        let visibleBlocked = makeQueueItem(
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
            visibleBlocked
        ])

        XCTAssertEqual(rows.map(\.id), ["blocked-local"])
    }

    func testNativeMeetingListPrioritizesNewestLocalOnlyRecording() {
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

        let rows = DesktopMeetingShellLocalQueuePolicy.rowsNeedingNativeVisibility([
            olderQueued,
            newestBlocked
        ])

        XCTAssertEqual(rows.first?.id, "newest-blocked")
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

    func testWebRTCAEC3GuidanceCannotMakeLeakageBlockedPackageUploadable() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let directoryURL = root.appendingPathComponent("aec3-blocked-package", isDirectory: true)
        try FileManager.default.createDirectory(at: directoryURL, withIntermediateDirectories: true)
        let manifestURL = directoryURL.appendingPathComponent("manifest.json")
        let micURL = directoryURL.appendingPathComponent("mic.wav")
        let incomingURL = directoryURL.appendingPathComponent("incoming.wav")
        try Data(repeating: 1, count: 128).write(to: micURL)
        try Data(repeating: 2, count: 128).write(to: incomingURL)
        let manifest = makeManifest(
            directoryId: "aec3-blocked-package",
            sessionId: "aec3-blocked-session",
            leakageFinalization: uploadQueueBlockedLeakageFinalization(),
            webRTCAEC3Outcome: uploadQueueWebRTCAEC3GuidanceOutcome()
        )
        try LocalRecordingManifestService().write(manifest, to: manifestURL)

        let profile = DesktopUploadQueueService.artifactProfile(
            manifest: manifest,
            manifestURL: manifestURL,
            microphoneURL: micURL,
            systemAudioURL: incomingURL
        )

        XCTAssertFalse(profile.isUploadable)
    }

    func testScanCarriesManifestFailureReasonIntoBlockedQueueItem() throws {
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

        XCTAssertEqual(item.state, .blocked)
        XCTAssertEqual(item.failureReason, LocalRecordingFailureReason.leakageDetected.rawValue)
        XCTAssertEqual(summary.detail, "звук динамиков попал в микрофон; отправка заблокирована")
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

    func testScanRefreshesGenericBlockedReasonWithManifestReason() throws {
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

        XCTAssertEqual(refreshed.state, .blocked)
        XCTAssertEqual(refreshed.failureReason, LocalRecordingFailureReason.leakageDetected.rawValue)
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

    func testQueueDocumentUsesRevisionReadyV2Schema() {
        let fixture = makeQueueV2Fixture(directoryId: "recording-sync-001")

        XCTAssertEqual(fixture.localMediaRevisionId, "recording-sync-001--initial")
        XCTAssertEqual(DesktopUploadQueueDocument.schemaVersion, fixture.schemaVersion)
    }

    private func makeQueueItem(
        id: String = "queue-id",
        state: UploadItemState = .queued,
        retryMode: UploadRetryMode = .automatic,
        failureReason: String? = nil,
        syncConflictState: DesktopSyncConflictState = .none,
        meetingId: String? = nil,
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
            retentionDecision: RetentionDecision(
                decision: .retain,
                decidedAt: Date(timeIntervalSince1970: 1),
                reason: "test",
                localArtifactsRetained: true,
                policyReference: "test"
            )
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

    private func makeRecordingPackage(
        root: URL,
        directoryId: String,
        sessionId: String,
        includeIncoming: Bool = true,
        includeMuteTruth: Bool = false,
        includeMicrophoneGraphMetadata: Bool = false,
        leakageFinalization: LeakageFinalization? = nil,
        status: LocalRecordingSessionStatus = .saved,
        transcriptionReadiness: TranscriptionReadinessState = .ready,
        failureReason: LocalRecordingFailureReason = .none
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
        let manifest = makeManifest(
            directoryId: directoryId,
            sessionId: sessionId,
            includeMuteTruth: includeMuteTruth,
            includeMicrophoneGraphMetadata: includeMicrophoneGraphMetadata,
            leakageFinalization: leakageFinalization,
            status: status,
            transcriptionReadiness: transcriptionReadiness,
            failureReason: failureReason
        )
        try LocalRecordingManifestService().write(manifest, to: package.manifestURL)
        return package
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
        failureReason: LocalRecordingFailureReason = .none
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
            scopeApproval: CaptureScopeApproval(
                scopeApprovalId: "scope",
                scopeKind: .display,
                sourceDisplayName: "Display",
                approvedAt: startedAt,
                approvalMode: .userConfirmedSuggestedScope,
                eligibleReason: .manualMeetingScope
            ),
            permissions: SystemAudioPermissionSnapshot(
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
        LeakageFinalization(
            status: .leakageDetected,
            evaluatedAt: Date(timeIntervalSince1970: 20),
            measurementAttempted: true,
            measurementApplicable: true,
            alignmentStatus: .aligned,
            confidence: 0.95,
            failureReason: .leakageDetected,
            originalEvidenceStatus: .leakageDetected,
            transcriptionGate: .blockedLeakageDetected
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

    private final class ReconcileThenUploadClient: @unchecked Sendable, DesktopUploadClientProtocol {
        private let reconciliation: DesktopUploadReconciliation?
        private let result: DesktopUploadResult
        private(set) var uploadedItems: [DesktopUploadQueueItem] = []

        init(reconciliation: DesktopUploadReconciliation?, result: DesktopUploadResult) {
            self.reconciliation = reconciliation
            self.result = result
        }

        func reconcile(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadReconciliation? {
            reconciliation
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
