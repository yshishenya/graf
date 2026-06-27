import CryptoKit
import Foundation
import TwoBrainRecShared

public enum DesktopUploadQueueServiceError: Error, CustomStringConvertible, Sendable {
    case manifestMissing(URL)
    case packageNotFound(String)
    case localArtifactOutsideRecordingsRoot(String)

    public var description: String {
        switch self {
        case .manifestMissing(let url):
            return "manifest_missing:\(url.lastPathComponent)"
        case .packageNotFound(let id):
            return "package_not_found:\(id)"
        case .localArtifactOutsideRecordingsRoot(let path):
            return "local_artifact_outside_recordings_root:\(URL(fileURLWithPath: path).lastPathComponent)"
        }
    }
}

private extension LocalRecordingManifest {
    var isServerUploadEligible: Bool {
        Self.sessionStatusAllowsUpload(status, failureReason: failureReason) &&
            !externalEgressStarted &&
            !transcriptionStarted &&
            scopeApproval?.isAcceptedForMeetingRecording == true &&
            permissions?.allowsAcceptedRecording == true &&
            Self.isUploadSafeFailure(failureReason) &&
            tracks.allSatisfy(\.isServerUploadEligible)
    }

    private static func sessionStatusAllowsUpload(
        _ status: LocalRecordingSessionStatus,
        failureReason: LocalRecordingFailureReason
    ) -> Bool {
        switch status {
        case .saved, .degraded:
            return true
        case .failed:
            return isUploadSafeFailure(failureReason)
        case .active, .blocked:
            return false
        }
    }

    private static func isUploadSafeFailure(_ reason: LocalRecordingFailureReason) -> Bool {
        switch reason {
        case .none, .emptyRequiredTrack, .formatNotReady, .timelineMisaligned,
             .leakageDetected, .leakageUnproven, .leakageNotMeasured,
             .insufficientReference, .derivedResidualLeakage, .derivedDeletionNotRegistered,
             .silentInput, .noFrames, .stoppedBeforeFrames:
            return true
        case .directoryUnavailable, .writeFailed, .finalizationFailed,
             .permissionDenied, .scopeUnavailable, .protectedAudioBlocked, .captureFailed,
             .cpuGateFailed, .halProbeObserved, .deviceUnavailable, .legacyNotReady,
             .appClosed, .unknown:
            return false
        }
    }
}

private extension LocalRecordingTrack {
    var isServerUploadEligible: Bool {
        Self.trackStatusAllowsUpload(status, failureReason: failureReason) &&
            Self.isUploadSafeFailure(failureReason)
    }

    private static func trackStatusAllowsUpload(
        _ status: LocalRecordingTrackStatus,
        failureReason: LocalRecordingFailureReason
    ) -> Bool {
        switch status {
        case .saved, .degraded:
            return true
        case .failed, .blocked:
            return isUploadSafeFailure(failureReason)
        case .pending, .recording, .missing:
            return false
        }
    }

    private static func isUploadSafeFailure(_ reason: LocalRecordingFailureReason) -> Bool {
        switch reason {
        case .none, .emptyRequiredTrack, .formatNotReady, .timelineMisaligned,
             .leakageDetected, .leakageUnproven, .leakageNotMeasured,
             .insufficientReference, .derivedResidualLeakage, .derivedDeletionNotRegistered,
             .silentInput, .noFrames, .stoppedBeforeFrames:
            return true
        case .directoryUnavailable, .writeFailed, .finalizationFailed,
             .permissionDenied, .scopeUnavailable, .protectedAudioBlocked, .captureFailed,
             .cpuGateFailed, .halProbeObserved, .deviceUnavailable, .legacyNotReady,
             .appClosed, .unknown:
            return false
        }
    }
}

public final class DesktopUploadQueueService: @unchecked Sendable {
    public typealias Clock = @Sendable () -> Date
    private static let processingFollowUpWindowSeconds: TimeInterval = 15 * 60
    private static let uploadedReconciliationStaleSeconds: TimeInterval = 60
    private static let finalProcessingStatuses: Set<String> = [
        "processed",
        "blocked",
        "failed_terminal",
        "canceled"
    ]

    private let queueURL: URL
    private let recordingsRootURL: URL
    private let policy: LocalBufferPolicy
    private let manifestService: LocalRecordingManifestService
    private let client: DesktopUploadClientProtocol?
    private let clock: Clock
    private let queue = DispatchQueue(label: "pro.2brain.rec.desktop-upload-queue", qos: .utility)
    private var document: DesktopUploadQueueDocument?

    public init(
        queueURL: URL? = nil,
        recordingsRootURL: URL = LocalRecordingStore().rootURL,
        policy: LocalBufferPolicy = LocalBufferService.defaultPolicy,
        manifestService: LocalRecordingManifestService = LocalRecordingManifestService(),
        client: DesktopUploadClientProtocol? = DesktopUploadClient.configuredFromEnvironment(),
        clock: @escaping Clock = Date.init
    ) {
        self.queueURL = queueURL ?? Self.defaultQueueURL()
        self.recordingsRootURL = recordingsRootURL
        self.policy = policy
        self.manifestService = manifestService
        self.client = client
        self.clock = clock
    }

    public static func defaultQueueURL() -> URL {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ??
            FileManager.default.temporaryDirectory
        return base
            .appendingPathComponent("2brain Rec", isDirectory: true)
            .appendingPathComponent("UploadQueue", isDirectory: true)
            .appendingPathComponent("upload-queue.json")
    }

    public func loadItems() throws -> [DesktopUploadQueueItem] {
        try queue.sync {
            try loadDocumentOnQueue().items.sortedForDisplay()
        }
    }

    @discardableResult
    public func scanAndEnqueueCompletedRecordings() throws -> [DesktopUploadQueueItem] {
        try queue.sync {
            var document = try loadDocumentOnQueue()
            let directories = (try? FileManager.default.contentsOfDirectory(
                at: recordingsRootURL,
                includingPropertiesForKeys: [.isDirectoryKey],
                options: [.skipsHiddenFiles]
            )) ?? []

            var changed = false
            for directory in directories {
                let manifestURL = directory.appendingPathComponent("manifest.json")
                guard FileManager.default.fileExists(atPath: manifestURL.path),
                      let manifest = try? manifestService.read(from: manifestURL)
                else {
                    continue
                }
                let item = try makeItem(
                    manifest: manifest,
                    directoryURL: directory,
                    now: clock()
                )
                if let existingIndex = document.items.firstIndex(where: { $0.id == item.id }) {
                    guard !document.items[existingIndex].state.isTerminal else {
                        continue
                    }
                    let existing = document.items[existingIndex]
                    let merged = mergeRefreshedLocalItem(
                        existing: existing,
                        refreshed: item,
                        now: clock()
                    )
                    if merged != existing {
                        document.items[existingIndex] = merged
                        changed = true
                    }
                    continue
                }
                document.items.append(item)
                changed = true
            }

            if changed {
                document.items = document.items.sortedForDisplay()
                document.updatedAt = clock()
                try saveDocumentOnQueue(document)
            }
            return document.items.sortedForDisplay()
        }
    }

    @discardableResult
    public func enqueue(
        manifest: LocalRecordingManifest,
        directoryURL: URL,
        reason: String = "local_recording_finalized",
        calendarContextEventId: String? = nil
    ) throws -> DesktopUploadQueueItem {
        try queue.sync {
            var document = try loadDocumentOnQueue()
            let now = clock()
            let item = try makeItem(
                manifest: manifest,
                directoryURL: directoryURL,
                now: now,
                reason: reason,
                calendarContextEventId: calendarContextEventId
            )
            var savedItem = item

            if let index = document.items.firstIndex(where: { $0.id == item.id }) {
                let existing = document.items[index]
                if existing.state.isTerminal {
                    return existing
                }
                var merged = item
                merged.attemptCount = existing.attemptCount
                merged.meetingId = existing.meetingId
                merged.localMediaRevisionId = existing.localMediaRevisionId
                merged.mediaRevisionId = existing.mediaRevisionId
                merged.uploadSessionId = existing.uploadSessionId
                merged.syncGeneration = existing.syncGeneration
                merged.lastReconciledAt = existing.lastReconciledAt
                merged.syncConflictState = existing.syncConflictState
                merged.serverTruth = existing.serverTruth
                merged.retryRecords = existing.retryRecords
                merged.createdAt = existing.createdAt
                merged.calendarContextEventId = existing.calendarContextEventId ?? merged.calendarContextEventId
                merged.recordingMetadata = existing.recordingMetadata ?? merged.recordingMetadata
                document.items[index] = merged
                savedItem = merged
            } else {
                document.items.append(item)
            }

            document.items = document.items.sortedForDisplay()
            document.updatedAt = now
            try saveDocumentOnQueue(document)
            return savedItem
        }
    }

    @discardableResult
    public func retry(itemId: String) throws -> DesktopUploadQueueItem {
        try updateItem(itemId: itemId) { item, now in
            let blockedFailureReason = item.failureReason ?? "local_artifacts_not_uploadable"
            return item.withTransition(
                to: item.artifactProfile.isUploadable ? .queued : .blocked,
                now: now,
                failureCategory: item.artifactProfile.isUploadable ? UploadFailureCategory.none : .localResource,
                failureReason: item.artifactProfile.isUploadable ? nil : blockedFailureReason,
                retryMode: item.artifactProfile.isUploadable ? .automatic : .manualOnly,
                nextRetryAt: item.artifactProfile.isUploadable ? now : nil,
                syncConflictState: item.artifactProfile.isUploadable ? DesktopSyncConflictState.none : .localFilesMissing,
                retentionDecision: RetentionDecision(
                    decision: item.artifactProfile.isUploadable ? .retain : .manualOnly,
                    decidedAt: now,
                    reason: "manual_retry_requested",
                    localArtifactsRetained: true,
                    policyReference: "local_buffer.retention_days.\(self.policy.retentionDays)"
                )
            )
        }
    }

    @discardableResult
    public func stopRetry(itemId: String) throws -> DesktopUploadQueueItem {
        try updateItem(itemId: itemId) { item, now in
            item.withTransition(
                to: .blocked,
                now: now,
                failureCategory: .cancelled,
                failureReason: "automatic_retry_stopped_by_user",
                retryMode: .manualOnly,
                nextRetryAt: nil,
                retentionDecision: RetentionDecision(
                    decision: .manualOnly,
                    decidedAt: now,
                    reason: "automatic_retry_stopped_by_user",
                    localArtifactsRetained: true,
                    policyReference: "local_buffer.retention_days.\(self.policy.retentionDays)"
                )
            )
        }
    }

    @discardableResult
    public func applyRetentionExpiry() throws -> [DesktopUploadQueueItem] {
        try queue.sync {
            var document = try loadDocumentOnQueue()
            let now = clock()
            var changed = false
            document.items = document.items.map { item in
                guard !item.state.isTerminal,
                      now >= item.retentionDeadline,
                      item.retryMode == .automatic
                else {
                    return item
                }
                changed = true
                return item.withTransition(
                    to: .blocked,
                    now: now,
                    failureCategory: item.failureCategory == .none ? .network : item.failureCategory,
                    failureReason: "automatic_retry_window_expired",
                    retryMode: .manualOnly,
                    nextRetryAt: nil,
                    syncConflictState: .retentionExpired,
                    retentionDecision: RetentionDecision(
                        decision: .manualOnly,
                        decidedAt: now,
                        reason: "automatic_retry_window_expired",
                        localArtifactsRetained: true,
                        policyReference: "local_buffer.retention_days.\(policy.retentionDays)"
                    )
                )
            }
            if changed {
                document.updatedAt = now
                try saveDocumentOnQueue(document)
            }
            return document.items.sortedForDisplay()
        }
    }

    @discardableResult
    public func processDueItems() async throws -> [DesktopUploadQueueItem] {
        guard let client else {
            return try loadItems()
        }

        let dueItems = try queue.sync {
            let document = try loadDocumentOnQueue()
            let now = clock()
            return document.items.filter { item in
                !item.state.isTerminal &&
                    item.retryMode == .automatic &&
                    item.artifactProfile.isUploadable &&
                    (item.nextRetryAt == nil || item.nextRetryAt ?? now <= now)
            }
        }

        for item in dueItems {
            try await upload(item: item, client: client)
        }
        await reconcileUploadedItemsIfNeeded(
            client: client,
            excludingItemIds: Set(dueItems.map(\.id))
        )
        return try loadItems()
    }

    public static func nextScheduledRetryDate(
        for items: [DesktopUploadQueueItem],
        now: Date = Date()
    ) -> Date? {
        items
            .filter {
                !$0.state.isTerminal &&
                    $0.retryMode == .automatic &&
                    $0.artifactProfile.isUploadable &&
                    ($0.nextRetryAt ?? now) > now
            }
            .compactMap(\.nextRetryAt)
            .min()
    }

    public static func needsProcessingFollowUp(
        _ item: DesktopUploadQueueItem,
        now: Date = Date()
    ) -> Bool {
        guard item.state == .uploaded,
              item.serverTruth.meetingId != nil || item.meetingId != nil
        else {
            return false
        }
        guard let status = normalizedProcessingStatus(item.serverTruth.processingStatus) else {
            return true
        }
        guard !finalProcessingStatuses.contains(status) else {
            return false
        }
        let referenceDate = item.serverTruth.finalizedAt ?? item.lastReconciledAt ?? item.updatedAt
        return now.timeIntervalSince(referenceDate) <= processingFollowUpWindowSeconds
    }

    public func acknowledgePendingLocalPurgeTasks() async throws -> [DesktopLocalPurgeTask] {
        guard let client else {
            return []
        }
        await reconcileUploadedItemsIfNeeded(client: client, excludingItemIds: [])
        let tasks = try await client.listLocalPurgeTasks()
        var items = try queue.sync {
            try loadDocumentOnQueue().items
        }
        var updatedTasks: [DesktopLocalPurgeTask] = []
        for task in tasks where task.state == .pending || task.state == .claimed {
            var candidateIdsToFinalize = Set<String>()
            var verificationOverride: DesktopLocalPurgeVerificationState?
            let candidates = localPurgeCandidates(for: task, items: items)
            if task.taskType == .purgeLocalBuffers, !candidates.isEmpty {
                do {
                    let purgeableCandidates = try await reconcileLocalPurgeCandidates(
                        candidates,
                        task: task,
                        client: client
                    )
                    if purgeableCandidates.count != candidates.count {
                        verificationOverride = .failed
                    }
                    if !purgeableCandidates.isEmpty {
                        try deleteLocalArtifacts(for: purgeableCandidates)
                        candidateIdsToFinalize = Set(purgeableCandidates.map(\.id))
                    }
                } catch {
                    switch localPurgeVerificationState(for: task, items: items) {
                    case .deleted, .tombstoned, .cryptographicallyUnrecoverable:
                        break
                    case .failed, .unverified:
                        verificationOverride = .failed
                    }
                }
                items = try queue.sync {
                    try loadDocumentOnQueue().items
                }
            } else if task.taskType != .purgeLocalBuffers, !candidates.isEmpty {
                verificationOverride = .unverified
            }
            let verificationState = verificationOverride ?? localPurgeVerificationState(for: task, items: items)
            let acknowledgement = DesktopLocalPurgeAcknowledgement(
                verificationState: verificationState,
                clientVersion: nil,
                completedAt: clock()
            )
            let updated = try await client.acknowledgeLocalPurgeTask(
                task,
                state: acknowledgement.state,
                reasonCode: acknowledgement.reasonCode,
                completedAt: acknowledgement.completedAt
            )
            updatedTasks.append(updated)
            if acknowledgement.state == .acknowledged {
                try markLocalPurgeAcknowledged(
                    itemIds: candidateIdsToFinalize.isEmpty ? Set(candidates.map(\.id)) : candidateIdsToFinalize,
                    task: task
                )
                items = try queue.sync {
                    try loadDocumentOnQueue().items
                }
            }
        }
        return updatedTasks
    }

    private func reconcileLocalPurgeCandidates(
        _ items: [DesktopUploadQueueItem],
        task: DesktopLocalPurgeTask,
        client: DesktopUploadClientProtocol
    ) async throws -> [DesktopUploadQueueItem] {
        var purgeable: [DesktopUploadQueueItem] = []
        for item in items {
            guard let reconciliation = try await client.reconcile(item) else {
                continue
            }
            let reconciled = try applyLocalPurgeReconciliation(itemId: item.id, reconciliation: reconciliation)
            if Self.localPurgeReconciliationAllowsBufferDelete(reconciliation, item: reconciled, task: task) {
                purgeable.append(reconciled)
            }
        }
        return purgeable
    }

    private func applyLocalPurgeReconciliation(
        itemId: String,
        reconciliation: DesktopUploadReconciliation
    ) throws -> DesktopUploadQueueItem {
        try updateItem(itemId: itemId) { current, now in
            var next = current
            next.serverTruth = reconciliation.serverTruth
            next.meetingId = reconciliation.serverTruth.meetingId ?? next.meetingId
            next.mediaRevisionId = reconciliation.serverTruth.mediaRevisionId ?? next.mediaRevisionId
            next.uploadSessionId = reconciliation.serverTruth.uploadSessionId ?? next.uploadSessionId
            next.lastReconciledAt = now
            next.syncGeneration += 1
            next.syncConflictState = reconciliation.conflictState
            if reconciliation.conflictState == .none || reconciliation.conflictState == .serverMeetingDeleted {
                next.failureCategory = .none
                next.failureReason = nil
            } else {
                next.failureCategory = .serverValidation
                next.failureReason = reconciliation.conflictReason ?? reconciliation.conflictState.rawValue
            }
            return next
        }
    }

    private static func localPurgeReconciliationAllowsBufferDelete(
        _ reconciliation: DesktopUploadReconciliation,
        item: DesktopUploadQueueItem,
        task: DesktopLocalPurgeTask
    ) -> Bool {
        guard reconciliation.serverTruth.meetingId == task.meetingId else {
            return false
        }
        if reconciliation.conflictState == .serverMeetingDeleted {
            return true
        }
        if item.state == .uploaded && reconciliation.conflictState == .none {
            return true
        }
        return reconciliation.canContinueUpload &&
            reconciliationShowsServerFinalized(reconciliation.serverTruth)
    }

    private func markLocalPurgeAcknowledged(
        itemIds: Set<String>,
        task: DesktopLocalPurgeTask
    ) throws {
        guard task.taskType == .purgeLocalBuffers, !itemIds.isEmpty else {
            return
        }
        let now = clock()
        try queue.sync {
            var document = try loadDocumentOnQueue()
            var changed = false
            document.items = document.items.map { item in
                guard itemIds.contains(item.id), Self.localArtifactsDeleted(for: item) else {
                    return item
                }
                changed = true
                return item.withTransition(
                    to: .terminalDeleted,
                    now: now,
                    failureCategory: UploadFailureCategory.none,
                    failureReason: nil,
                    retryMode: .terminal,
                    nextRetryAt: nil,
                    syncConflictState: .serverMeetingDeleted,
                    retentionDecision: RetentionDecision(
                        decision: .terminalDeleted,
                        decidedAt: now,
                        reason: "local_purge_acknowledged",
                        localArtifactsRetained: false,
                        policyReference: "local_purge.\(task.taskType.rawValue)"
                    )
                )
            }
            if changed {
                document.updatedAt = now
                try saveDocumentOnQueue(document)
            }
        }
    }

    private func localPurgeVerificationState(
        for task: DesktopLocalPurgeTask,
        items: [DesktopUploadQueueItem]
    ) -> DesktopLocalPurgeVerificationState {
        guard task.taskType == .purgeLocalBuffers else {
            return .unverified
        }
        let candidates = localPurgeCandidates(for: task, items: items)
        guard !candidates.isEmpty else {
            return .unverified
        }
        if candidates.allSatisfy(Self.localArtifactsDeleted) {
            return .deleted
        }
        if candidates.allSatisfy(Self.localArtifactsTombstoned) {
            return .tombstoned
        }
        if candidates.allSatisfy(Self.localArtifactsCryptographicallyUnrecoverable) {
            return .cryptographicallyUnrecoverable
        }
        return .failed
    }

    private func localPurgeCandidates(
        for task: DesktopLocalPurgeTask,
        items: [DesktopUploadQueueItem]
    ) -> [DesktopUploadQueueItem] {
        items.filter { item in
            item.serverTruth.meetingId == task.meetingId || item.meetingId == task.meetingId
        }
    }

    private func deleteLocalArtifacts(for items: [DesktopUploadQueueItem]) throws {
        let paths = try Set(items.flatMap(localArtifactPathsInsideRecordingsRoot))
        for path in paths.sorted(by: { $0.count > $1.count }) where FileManager.default.fileExists(atPath: path) {
            try FileManager.default.removeItem(atPath: path)
        }
    }

    private func localArtifactPathsInsideRecordingsRoot(for item: DesktopUploadQueueItem) throws -> [String] {
        try Self.localArtifactPaths(for: item)
            .filter { !$0.isEmpty && $0 != "metadata-only" }
            .map { path in
                guard isInsideRecordingsRoot(path) else {
                    throw DesktopUploadQueueServiceError.localArtifactOutsideRecordingsRoot(path)
                }
                return path
            }
    }

    private func isInsideRecordingsRoot(_ path: String) -> Bool {
        let rootPath = recordingsRootURL
            .standardizedFileURL
            .resolvingSymlinksInPath()
            .path
        let candidatePath = URL(fileURLWithPath: path)
            .standardizedFileURL
            .resolvingSymlinksInPath()
            .path
        return candidatePath.hasPrefix(rootPath + "/")
    }

    private static func localArtifactsDeleted(for item: DesktopUploadQueueItem) -> Bool {
        let paths = localArtifactPaths(for: item)
        guard !paths.isEmpty else { return false }
        return paths.allSatisfy { !FileManager.default.fileExists(atPath: $0) }
    }

    private static func localArtifactsTombstoned(for item: DesktopUploadQueueItem) -> Bool {
        guard !localArtifactFiles(for: item).contains(where: { FileManager.default.fileExists(atPath: $0) }) else {
            return false
        }
        return localPurgeTombstonePaths(for: item).contains { FileManager.default.fileExists(atPath: $0) }
    }

    private static func localArtifactsCryptographicallyUnrecoverable(for item: DesktopUploadQueueItem) -> Bool {
        item.retentionDecision.decision == .terminalDeleted &&
            !item.retentionDecision.localArtifactsRetained &&
            !localArtifactFiles(for: item).contains(where: { FileManager.default.fileExists(atPath: $0) })
    }

    private static func localArtifactPaths(for item: DesktopUploadQueueItem) -> [String] {
        [item.directoryPath] + localArtifactFiles(for: item)
    }

    private static func localArtifactFiles(for item: DesktopUploadQueueItem) -> [String] {
        [item.manifestPath, item.microphonePath, item.systemAudioPath].filter { !$0.isEmpty && $0 != "metadata-only" }
    }

    private static func localPurgeTombstonePaths(for item: DesktopUploadQueueItem) -> [String] {
        let directoryURL = URL(fileURLWithPath: item.directoryPath)
        return [
            directoryURL.appendingPathComponent(".2brain-local-purge-tombstone.json").path,
            directoryURL.deletingLastPathComponent().appendingPathComponent("\(directoryURL.lastPathComponent).purged").path
        ]
    }

    public static func visibleSummary(for items: [DesktopUploadQueueItem]) -> DesktopUploadQueueSummary? {
        let sorted = items.sortedForDisplay()
        guard let primary = sorted.first else { return nil }
        return DesktopUploadQueueSummary(
            primaryItem: primary,
            pendingCount: sorted.filter { !$0.state.isTerminal }.count,
            totalCount: sorted.count
        )
    }

    public static func custodyProjections(
        for items: [DesktopUploadQueueItem],
        now: Date = Date()
    ) -> [DesktopUploadCustodyProjection] {
        items.sortedForDisplay().map { DesktopUploadCustodyProjection(item: $0, now: now) }
    }

    private func upload(
        item: DesktopUploadQueueItem,
        client: DesktopUploadClientProtocol
    ) async throws {
        let started = try updateItem(itemId: item.id) { current, now in
            var next = current.withTransition(
                to: .uploading,
                now: now,
                failureCategory: UploadFailureCategory.none,
                failureReason: nil,
                retryMode: .automatic,
                nextRetryAt: nil
            )
            next.attemptCount += 1
            next.retryRecords.append(
                RetryRecord(
                    attemptNumber: next.attemptCount,
                    startedAt: now,
                    stateBefore: current.state,
                    stateAfter: .uploading,
                    failureCategory: .none
                )
            )
            return next
        }

        do {
            let reconciled = try await reconcileBeforeUpload(started, client: client)
            guard reconciled.syncConflictState == .none else {
                return
            }
            guard reconciled.state != .uploaded else {
                return
            }
            let result = try await client.upload(reconciled)
            _ = try updateItem(itemId: started.id) { current, now in
                var next = current.withTransition(
                    to: result.state,
                    now: now,
                    failureCategory: UploadFailureCategory.none,
                    failureReason: nil,
                    retryMode: .terminal,
                    nextRetryAt: nil,
                    serverTruth: result.serverTruth,
                    retentionDecision: RetentionDecision(
                        decision: .terminalUploaded,
                        decidedAt: now,
                        reason: "server_finalized_upload",
                        localArtifactsRetained: true,
                        policyReference: "server_truth.finalized"
                    )
                )
                next.retryRecords.append(
                    RetryRecord(
                        attemptNumber: next.attemptCount,
                        startedAt: reconciled.updatedAt,
                        finishedAt: now,
                        stateBefore: .uploading,
                        stateAfter: result.state,
                        failureCategory: .none,
                        acceptedBytesByTrack: result.serverTruth.acceptedBytesByTrack
                    )
                )
                return next
            }
        } catch {
            let category = (error as? DesktopUploadClientError)?.failureCategory ?? .network
            let reason = String(describing: error)
            _ = try updateItem(itemId: started.id) { current, now in
                let nextRetry = nextRetryDate(
                    attemptCount: current.attemptCount,
                    now: now,
                    retentionDeadline: current.retentionDeadline
                )
                let retryMode: UploadRetryMode = category.isAutomaticallyRetryable && nextRetry != nil
                    ? .automatic
                    : .manualOnly
                let state: UploadItemState = retryMode == .automatic ? .retrying : .blocked
                var next = current.withTransition(
                    to: state,
                    now: now,
                    failureCategory: category,
                    failureReason: reason,
                    retryMode: retryMode,
                    nextRetryAt: nextRetry,
                    retentionDecision: RetentionDecision(
                        decision: retryMode == .automatic ? .retain : .manualOnly,
                        decidedAt: now,
                        reason: reason,
                        localArtifactsRetained: true,
                        policyReference: "local_buffer.retention_days.\(policy.retentionDays)"
                    )
                )
                next.retryRecords.append(
                    RetryRecord(
                        attemptNumber: next.attemptCount,
                        startedAt: started.updatedAt,
                        finishedAt: now,
                        stateBefore: .uploading,
                        stateAfter: state,
                        failureCategory: category,
                        failureReason: reason,
                        nextRetryAt: nextRetry
                    )
                )
                return next
            }
        }
    }

    private func reconcileBeforeUpload(
        _ item: DesktopUploadQueueItem,
        client: DesktopUploadClientProtocol
    ) async throws -> DesktopUploadQueueItem {
        guard let reconciliation = try await client.reconcile(item) else {
            return item
        }
        return try updateItem(itemId: item.id) { current, now in
            var next = current
            next.serverTruth = reconciliation.serverTruth
            next.meetingId = reconciliation.serverTruth.meetingId ?? next.meetingId
            next.mediaRevisionId = reconciliation.serverTruth.mediaRevisionId ?? next.mediaRevisionId
            next.uploadSessionId = reconciliation.serverTruth.uploadSessionId ?? next.uploadSessionId
            if reconciliation.conflictState == .uploadSessionExpired && reconciliation.nextAction == "create_upload_session" {
                next.uploadSessionId = nil
                next.serverTruth.uploadSessionId = nil
            }
            next.lastReconciledAt = now
            next.syncGeneration += 1
            if reconciliation.canContinueUpload {
                if Self.reconciliationShowsServerFinalized(reconciliation.serverTruth) {
                    next.state = .uploaded
                    next.retryMode = .terminal
                    next.nextRetryAt = nil
                    next.failureCategory = .none
                    next.failureReason = nil
                    next.syncConflictState = .none
                    next.retentionDecision = RetentionDecision(
                        decision: .terminalUploaded,
                        decidedAt: now,
                        reason: "server_reconciliation_finalized",
                        localArtifactsRetained: true,
                        policyReference: "server_truth.reconciliation"
                    )
                    return next
                }
                next.syncConflictState = .none
                return next
            }
            next.state = .blocked
            next.failureCategory = .serverValidation
            next.failureReason = reconciliation.conflictReason ?? reconciliation.conflictState.rawValue
            next.retryMode = .manualOnly
            next.nextRetryAt = nil
            next.syncConflictState = reconciliation.conflictState
            next.retentionDecision = RetentionDecision(
                decision: .manualOnly,
                decidedAt: now,
                reason: next.failureReason ?? "server_reconciliation_conflict",
                localArtifactsRetained: true,
                policyReference: "server_truth.reconciliation"
            )
            return next
        }
    }

    private func reconcileUploadedItemsIfNeeded(
        client: DesktopUploadClientProtocol,
        excludingItemIds: Set<String>
    ) async {
        let candidates: [DesktopUploadQueueItem]
        do {
            candidates = try queue.sync {
                let document = try loadDocumentOnQueue()
                let now = clock()
                return document.items.filter {
                    !excludingItemIds.contains($0.id) &&
                        Self.shouldReconcileUploadedItem($0, now: now)
                }
            }
        } catch {
            return
        }

        for item in candidates {
            do {
                guard let reconciliation = try await client.reconcile(item) else {
                    continue
                }
                try applyUploadedReconciliation(itemId: item.id, reconciliation: reconciliation)
            } catch {
                continue
            }
        }
    }

    private static func shouldReconcileUploadedItem(_ item: DesktopUploadQueueItem, now: Date) -> Bool {
        guard item.state == .uploaded,
              item.serverTruth.meetingId != nil || item.meetingId != nil
        else {
            return false
        }
        if needsProcessingFollowUp(item, now: now) {
            return true
        }
        guard let lastReconciledAt = item.lastReconciledAt else {
            return true
        }
        return now.timeIntervalSince(lastReconciledAt) >= uploadedReconciliationStaleSeconds
    }

    private static func normalizedProcessingStatus(_ status: String?) -> String? {
        let normalized = status?.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return normalized?.isEmpty == false ? normalized : nil
    }

    private static func reconciliationShowsServerFinalized(_ serverTruth: ServerTruthFingerprint) -> Bool {
        let status = serverTruth.serverStatus?.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return status == "ingested_pending_processing" ||
            status == "degraded" ||
            serverTruth.finalizedAt != nil
    }

    private func applyUploadedReconciliation(
        itemId: String,
        reconciliation: DesktopUploadReconciliation
    ) throws {
        _ = try updateItem(itemId: itemId) { current, now in
            guard current.state == .uploaded else {
                return current
            }
            var next = current
            next.serverTruth = reconciliation.serverTruth
            next.meetingId = reconciliation.serverTruth.meetingId ?? next.meetingId
            next.mediaRevisionId = reconciliation.serverTruth.mediaRevisionId ?? next.mediaRevisionId
            next.uploadSessionId = reconciliation.serverTruth.uploadSessionId ?? next.uploadSessionId
            next.lastReconciledAt = now
            next.syncGeneration += 1
            next.syncConflictState = reconciliation.conflictState
            if reconciliation.conflictState == .none {
                next.failureCategory = .none
                next.failureReason = nil
            } else {
                next.failureCategory = .serverValidation
                next.failureReason = reconciliation.conflictReason ?? reconciliation.conflictState.rawValue
            }
            return next
        }
    }

    private func updateItem(
        itemId: String,
        update: (DesktopUploadQueueItem, Date) -> DesktopUploadQueueItem
    ) throws -> DesktopUploadQueueItem {
        try queue.sync {
            var document = try loadDocumentOnQueue()
            guard let index = document.items.firstIndex(where: { $0.id == itemId }) else {
                throw DesktopUploadQueueServiceError.packageNotFound(itemId)
            }
            let now = clock()
            let updated = update(document.items[index], now)
            document.items[index] = updated
            document.items = document.items.sortedForDisplay()
            document.updatedAt = now
            try saveDocumentOnQueue(document)
            return updated
        }
    }

    private func makeItem(
        manifest: LocalRecordingManifest,
        directoryURL: URL,
        now: Date,
        reason: String = "local_recording_discovered",
        calendarContextEventId: String? = nil
    ) throws -> DesktopUploadQueueItem {
        let manifestURL = directoryURL.appendingPathComponent(manifest.manifestFileName)
        let microphoneURL = directoryURL.appendingPathComponent("mic.wav")
        let systemAudioURL = directoryURL.appendingPathComponent("incoming.wav")
        guard FileManager.default.fileExists(atPath: manifestURL.path) else {
            throw DesktopUploadQueueServiceError.manifestMissing(manifestURL)
        }

        let profile = Self.artifactProfile(
            manifest: manifest,
            manifestURL: manifestURL,
            microphoneURL: microphoneURL,
            systemAudioURL: systemAudioURL
        )
        let state: UploadItemState = profile.isUploadable ? .queued : .blocked
        let failureCategory: UploadFailureCategory = profile.isUploadable ? .none : .schemaIncompatibility
        let retryMode: UploadRetryMode = profile.isUploadable ? .automatic : .manualOnly
        let retentionDeadline = Calendar.current.date(
            byAdding: .day,
            value: policy.retentionDays,
            to: manifest.stoppedAt
        ) ?? now
        let recordingMetadata = manifest.recordingMetadata ?? RecordingMetadataResolver(clock: clock).resolve(
            startedAt: manifest.startedAt,
            stoppedAt: manifest.stoppedAt,
            directoryId: manifest.directoryId,
            sessionId: manifest.sessionId,
            approvedAppName: manifest.scopeApproval?.sourceDisplayName
        )
        return DesktopUploadQueueItem(
            id: DesktopUploadQueueItem.deterministicId(
                directoryId: manifest.directoryId,
                sessionId: manifest.sessionId
            ),
            sessionId: manifest.sessionId,
            directoryId: manifest.directoryId,
            localMediaRevisionId: DesktopUploadQueueItem.initialMediaRevisionId(directoryId: manifest.directoryId),
            directoryPath: directoryURL.path,
            manifestPath: manifestURL.path,
            microphonePath: microphoneURL.path,
            systemAudioPath: systemAudioURL.path,
            state: state,
            failureCategory: failureCategory,
            failureReason: profile.isUploadable ? nil : Self.blockedFailureReason(
                manifest: manifest,
                profile: profile
            ),
            retryMode: retryMode,
            nextRetryAt: profile.isUploadable ? now : nil,
            retentionDeadline: retentionDeadline,
            createdAt: now,
            updatedAt: now,
            calendarContextEventId: calendarContextEventId,
            recordingMetadata: recordingMetadata,
            artifactProfile: profile,
            retentionDecision: RetentionDecision(
                decision: .retain,
                decidedAt: now,
                reason: reason,
                localArtifactsRetained: true,
                policyReference: "local_buffer.retention_days.\(policy.retentionDays)"
            )
        )
    }

    private func mergeRefreshedLocalItem(
        existing: DesktopUploadQueueItem,
        refreshed: DesktopUploadQueueItem,
        now: Date
    ) -> DesktopUploadQueueItem {
        var merged = refreshed
        merged.attemptCount = existing.attemptCount
        merged.meetingId = existing.meetingId
        merged.localMediaRevisionId = existing.localMediaRevisionId
        merged.mediaRevisionId = existing.mediaRevisionId
        merged.uploadSessionId = existing.uploadSessionId
        merged.syncGeneration = existing.syncGeneration
        merged.lastReconciledAt = existing.lastReconciledAt
        merged.syncConflictState = existing.syncConflictState
        merged.serverTruth = existing.serverTruth
        merged.retryRecords = existing.retryRecords
        merged.createdAt = existing.createdAt
        merged.calendarContextEventId = existing.calendarContextEventId ?? refreshed.calendarContextEventId
        merged.recordingMetadata = existing.recordingMetadata ?? refreshed.recordingMetadata
        if refreshed.artifactProfile.isUploadable && existing.syncConflictState == .localFilesMissing {
            merged.syncConflictState = .none
        }
        if !refreshed.artifactProfile.isUploadable && existing.state == .blocked {
            merged.state = existing.state
            merged.failureCategory = existing.failureCategory
            merged.failureReason = Self.mostSpecificFailureReason(
                existing: existing.failureReason,
                refreshed: refreshed.failureReason
            )
            merged.retryMode = existing.retryMode
            merged.nextRetryAt = existing.nextRetryAt
            merged.retentionDecision = existing.retentionDecision
        } else if refreshed.artifactProfile.isUploadable && existing.state == .blocked {
            merged.state = .queued
            merged.failureCategory = .none
            merged.failureReason = nil
            merged.retryMode = .automatic
            merged.nextRetryAt = now
            merged.retentionDecision = RetentionDecision(
                decision: .retain,
                decidedAt: now,
                reason: "local_artifact_profile_refreshed",
                localArtifactsRetained: true,
                policyReference: "local_buffer.retention_days.\(policy.retentionDays)"
            )
        }
        return merged
    }

    private static func blockedFailureReason(
        manifest: LocalRecordingManifest,
        profile: ArtifactCompletenessProfile
    ) -> String {
        if manifest.scopeApproval?.isAcceptedForMeetingRecording != true {
            return LocalRecordingFailureReason.scopeUnavailable.rawValue
        }
        if manifest.permissions?.allowsAcceptedRecording != true {
            return LocalRecordingFailureReason.permissionDenied.rawValue
        }
        if !profile.manifestPresent || !profile.microphonePresent || !profile.systemAudioPresent {
            return "local_artifacts_not_uploadable"
        }
        if manifest.failureReason != .none {
            return manifest.failureReason.rawValue
        }
        if let leakageReason = manifest.leakageFinalization?.failureReason,
           leakageReason != .none {
            return leakageReason.rawValue
        }
        return "local_recording_package_not_uploadable"
    }

    private static func mostSpecificFailureReason(
        existing: String?,
        refreshed: String?
    ) -> String? {
        guard let refreshed, !refreshed.isEmpty else { return existing }
        guard let existing, !existing.isEmpty else { return refreshed }
        let genericReasons: Set<String> = [
            "local_recording_package_not_uploadable",
            "local_artifacts_not_uploadable"
        ]
        return genericReasons.contains(existing) ? refreshed : existing
    }

    public static func artifactProfile(
        manifest: LocalRecordingManifest,
        manifestURL: URL,
        microphoneURL: URL,
        systemAudioURL: URL
    ) -> ArtifactCompletenessProfile {
        let manifestSize = fileSize(manifestURL)
        let microphoneSize = fileSize(microphoneURL)
        let systemAudioSize = fileSize(systemAudioURL)
        let durationSeconds = max(1, Int(ceil(Double(max(0, manifest.stoppedAt.timeIntervalSince(manifest.startedAt))))))
        let manifestTrack = UploadTrackCompleteness(
            transportRole: .manifest,
            fileName: "manifest.json",
            present: manifestSize > 0,
            byteCount: manifestSize,
            sha256: sha256Hex(url: manifestURL),
            durationSeconds: 1
        )
        let microphoneTrack = UploadTrackCompleteness(
            transportRole: .microphone,
            fileName: "mic.wav",
            present: microphoneSize > 44,
            byteCount: microphoneSize,
            sha256: sha256Hex(url: microphoneURL),
            durationSeconds: durationSeconds
        )
        let systemTrack = UploadTrackCompleteness(
            transportRole: .system,
            fileName: "incoming.wav",
            present: systemAudioSize > 44,
            byteCount: systemAudioSize,
            sha256: sha256Hex(url: systemAudioURL),
            durationSeconds: durationSeconds
        )
        let tracks = [microphoneTrack, systemTrack, manifestTrack]
        let manifestRoles = Set(manifest.tracks.compactMap { DesktopUploadTransportRole.role(forLocalTrackRole: $0.role) })
        let hasRequiredManifestRoles = manifestRoles.isSuperset(of: [.microphone, .system])
        let uploadable = manifest.isServerUploadEligible &&
            hasRequiredManifestRoles &&
            tracks.allSatisfy(\.uploadable)
        let qualityWarningReason = uploadable ? Self.qualityWarningReason(for: manifest) : nil
        return ArtifactCompletenessProfile(
            schemaVersion: manifest.schemaVersion,
            manifestPresent: manifestTrack.present,
            microphonePresent: microphoneTrack.present,
            systemAudioPresent: systemTrack.present,
            manifestSha256: manifestTrack.sha256,
            microphoneSha256: microphoneTrack.sha256,
            systemAudioSha256: systemTrack.sha256,
            manifestSizeBytes: manifestSize,
            microphoneSizeBytes: microphoneSize,
            systemAudioSizeBytes: systemAudioSize,
            durationSeconds: durationSeconds,
            trackCompleteness: tracks,
            isUploadable: uploadable,
            qualityWarningReason: qualityWarningReason
        )
    }

    private static func qualityWarningReason(for manifest: LocalRecordingManifest) -> String? {
        if let reason = uploadableQualityWarningReason(manifest.failureReason) {
            return reason
        }
        if let leakageReason = manifest.leakageFinalization?.failureReason,
           let reason = uploadableQualityWarningReason(leakageReason) {
            return reason
        }
        for track in manifest.tracks {
            if let reason = uploadableQualityWarningReason(track.failureReason) {
                return reason
            }
        }
        return nil
    }

    private static func uploadableQualityWarningReason(_ reason: LocalRecordingFailureReason) -> String? {
        switch reason {
        case .emptyRequiredTrack, .formatNotReady, .timelineMisaligned,
             .leakageDetected, .leakageUnproven, .leakageNotMeasured,
             .insufficientReference, .derivedResidualLeakage, .derivedDeletionNotRegistered,
             .silentInput, .noFrames, .stoppedBeforeFrames:
            return reason.rawValue
        case .none, .directoryUnavailable, .writeFailed, .finalizationFailed,
             .permissionDenied, .scopeUnavailable, .protectedAudioBlocked, .captureFailed,
             .cpuGateFailed, .halProbeObserved, .deviceUnavailable, .legacyNotReady,
             .appClosed, .unknown:
            return nil
        }
    }

    private func loadDocumentOnQueue() throws -> DesktopUploadQueueDocument {
        if let document {
            return document
        }
        guard FileManager.default.fileExists(atPath: queueURL.path) else {
            let empty = DesktopUploadQueueDocument(updatedAt: clock(), items: [])
            document = empty
            return empty
        }
        let data = try Data(contentsOf: queueURL)
        let loadedDocument: DesktopUploadQueueDocument
        do {
            loadedDocument = try JSONDecoder.uploadQueueDecoder.decode(DesktopUploadQueueDocument.self, from: data)
        } catch {
            let now = clock()
            try quarantineMalformedQueueDocument(data: data, now: now)
            let quarantined = DesktopUploadQueueDocument(
                updatedAt: now,
                items: [malformedQueueDocumentItem(now: now)]
            )
            try saveDocumentOnQueue(quarantined)
            document = quarantined
            return quarantined
        }
        var loaded = loadedDocument
        let needsSchemaMigration = loaded.schemaVersion != DesktopUploadQueueDocument.schemaVersion
        if needsSchemaMigration {
            loaded.schemaVersion = DesktopUploadQueueDocument.schemaVersion
        }
        loaded.items = loaded.items.sortedForDisplay()
        if needsSchemaMigration {
            loaded.updatedAt = clock()
            try saveDocumentOnQueue(loaded)
        }
        document = loaded
        return loaded
    }

    private func saveDocumentOnQueue(_ document: DesktopUploadQueueDocument) throws {
        let data = try JSONEncoder.uploadQueueEncoder.encode(document)
        try LocalCustodyFileProtection.write(data, to: queueURL)
        self.document = document
    }

    private func quarantineMalformedQueueDocument(data: Data, now: Date) throws {
        let quarantineDirectory = queueURL
            .deletingLastPathComponent()
            .appendingPathComponent("Quarantine", isDirectory: true)
        let timestamp = Int(now.timeIntervalSince1970)
        let quarantineURL = quarantineDirectory
            .appendingPathComponent("upload-queue.\(timestamp).malformed.json")
        try LocalCustodyFileProtection.write(data, to: quarantineURL)
        try? FileManager.default.removeItem(at: queueURL)
    }

    private func malformedQueueDocumentItem(now: Date) -> DesktopUploadQueueItem {
        let profile = ArtifactCompletenessProfile(
            schemaVersion: LocalRecordingManifest.schemaVersion,
            manifestPresent: false,
            microphonePresent: false,
            systemAudioPresent: false,
            manifestSha256: nil,
            microphoneSha256: nil,
            systemAudioSha256: nil,
            manifestSizeBytes: 0,
            microphoneSizeBytes: 0,
            systemAudioSizeBytes: 0,
            durationSeconds: 1,
            trackCompleteness: [],
            isUploadable: false
        )
        return DesktopUploadQueueItem(
            id: DesktopUploadQueueItem.deterministicId(
                directoryId: "queue-document-malformed",
                sessionId: "local-custody"
            ),
            sessionId: "local-custody",
            directoryId: "queue-document-malformed",
            localMediaRevisionId: "queue-document-malformed--metadata",
            directoryPath: "metadata-only",
            manifestPath: "metadata-only",
            microphonePath: "metadata-only",
            systemAudioPath: "metadata-only",
            state: .blocked,
            failureCategory: .schemaIncompatibility,
            failureReason: "queue_document_malformed",
            retryMode: .manualOnly,
            retentionDeadline: Calendar.current.date(byAdding: .day, value: policy.retentionDays, to: now) ?? now,
            createdAt: now,
            updatedAt: now,
            syncConflictState: .queueDocumentMalformed,
            artifactProfile: profile,
            retentionDecision: RetentionDecision(
                decision: .manualOnly,
                decidedAt: now,
                reason: "queue_document_malformed",
                localArtifactsRetained: true,
                policyReference: "local_upload_custody.queue_document"
            )
        )
    }

    private static func fileSize(_ url: URL) -> Int64 {
        (try? FileManager.default.attributesOfItem(atPath: url.path)[.size] as? NSNumber)?.int64Value ?? 0
    }

    private static func sha256Hex(url: URL) -> String? {
        guard let handle = try? FileHandle(forReadingFrom: url) else { return nil }
        defer { try? handle.close() }
        var hasher = SHA256()
        while autoreleasepool(invoking: {
            let data = try? handle.read(upToCount: 1024 * 1024)
            guard let data, !data.isEmpty else { return false }
            hasher.update(data: data)
            return true
        }) {}
        return hasher.finalize().map { String(format: "%02x", $0) }.joined()
    }

    private func nextRetryDate(
        attemptCount: Int,
        now: Date,
        retentionDeadline: Date
    ) -> Date? {
        let delay = min(pow(2.0, Double(min(max(attemptCount, 1), 8))) * 5, 120)
        let candidate = now.addingTimeInterval(delay)
        return candidate < retentionDeadline ? candidate : nil
    }
}

public struct DesktopUploadQueueSummary: Equatable, Sendable {
    public let primaryItem: DesktopUploadQueueItem
    public let pendingCount: Int
    public let totalCount: Int

    public init(primaryItem: DesktopUploadQueueItem, pendingCount: Int, totalCount: Int) {
        self.primaryItem = primaryItem
        self.pendingCount = pendingCount
        self.totalCount = totalCount
    }

    public var title: String {
        pendingCount > 1
            ? "\(primaryItem.state.displayName) + ещё \(pendingCount - 1)"
            : primaryItem.state.displayName
    }

    public var detail: String {
        if let conflictDetail = primaryItem.syncConflictState.safeDetail {
            return conflictDetail
        }
        if primaryItem.state == .queued && primaryItem.serverTruth.meetingId == nil {
            return "локальная копия сохранена, отправим при сети"
        }
        if primaryItem.state == .retrying && primaryItem.serverTruth.meetingId == nil {
            return "локальная копия сохранена, повторим отправку"
        }
        if primaryItem.state == .uploading {
            return "отправляем локальную копию на сервер"
        }
        if primaryItem.state == .uploaded && primaryItem.serverTruth.meetingId == nil {
            return "серверный обзор пока не подтвержден"
        }
        if let reason = primaryItem.failureReason, !reason.isEmpty {
            return Self.failureReasonText(reason)
        }
        return primaryItem.retryMode.displayName
    }

    private static func failureReasonText(_ reason: String) -> String {
        switch reason {
        case "local_recording_package_not_uploadable", "local_artifacts_not_uploadable":
            return "нужна ручная проверка локальной записи"
        case LocalRecordingFailureReason.leakageDetected.rawValue:
            return "звук динамиков попал в микрофон; отправим как есть"
        case LocalRecordingFailureReason.leakageUnproven.rawValue:
            return "чистота микрофона не доказана; отправим как есть"
        case LocalRecordingFailureReason.leakageNotMeasured.rawValue:
            return "не удалось проверить утечку динамиков; отправим как есть"
        case LocalRecordingFailureReason.insufficientReference.rawValue:
            return "не хватает системной аудио-дорожки для проверки; отправим как есть"
        case LocalRecordingFailureReason.silentInput.rawValue:
            return "микрофон был слишком тихим или пустым; отправим как есть"
        case LocalRecordingFailureReason.permissionDenied.rawValue:
            return "нужно разрешение на запись микрофона и системного звука"
        case LocalRecordingFailureReason.scopeUnavailable.rawValue:
            return "не подтвержден источник встречи для отправки"
        case LocalRecordingFailureReason.timelineMisaligned.rawValue:
            return "дорожки записи не совпали по времени"
        case LocalRecordingFailureReason.formatNotReady.rawValue:
            return "аудиоформат еще не готов для сервера"
        case LocalRecordingFailureReason.emptyRequiredTrack.rawValue,
             LocalRecordingFailureReason.noFrames.rawValue,
             LocalRecordingFailureReason.stoppedBeforeFrames.rawValue:
            return "в записи нет достаточного аудио для транскрибации"
        case LocalRecordingFailureReason.protectedAudioBlocked.rawValue:
            return "защищенный звук не отправляется на сервер"
        case LocalRecordingFailureReason.captureFailed.rawValue,
             LocalRecordingFailureReason.finalizationFailed.rawValue,
             LocalRecordingFailureReason.writeFailed.rawValue:
            return "запись не завершилась корректно"
        case "automatic_retry_window_expired":
            return "автоповтор остановлен"
        default:
            return "нужна проверка"
        }
    }
}

private extension Array where Element == DesktopUploadQueueItem {
    func sortedForDisplay() -> [DesktopUploadQueueItem] {
        sorted {
            if $0.state.sortPriority != $1.state.sortPriority {
                return $0.state.sortPriority < $1.state.sortPriority
            }
            if $0.updatedAt != $1.updatedAt {
                return $0.updatedAt > $1.updatedAt
            }
            return $0.id < $1.id
        }
    }
}

private extension JSONEncoder {
    static var uploadQueueEncoder: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }
}

private extension JSONDecoder {
    static var uploadQueueDecoder: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }
}
