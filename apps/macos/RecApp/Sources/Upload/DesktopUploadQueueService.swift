import AVFoundation
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

public enum DesktopUploadFollowUpReason {
    public static let localPurgeAcknowledgementRetry = "local_purge_ack_retry"
    public static let scheduledRetry = "scheduled_retry"

    public static func processing(after reason: String) -> String {
        reason.hasPrefix("processing_follow_up") ? "processing_follow_up" : "processing_follow_up_after_\(reason)"
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
             .silentInput, .noFrames, .stoppedBeforeFrames, .historicalPackage:
            return true
        case .directoryUnavailable, .writeFailed, .finalizationFailed,
             .permissionDenied, .scopeUnavailable, .protectedAudioBlocked, .captureFailed,
             .cpuGateFailed, .deviceUnavailable,
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
             .silentInput, .noFrames, .stoppedBeforeFrames, .historicalPackage:
            return true
        case .directoryUnavailable, .writeFailed, .finalizationFailed,
             .permissionDenied, .scopeUnavailable, .protectedAudioBlocked, .captureFailed,
             .cpuGateFailed, .deviceUnavailable,
             .appClosed, .unknown:
            return false
        }
    }
}

public final class DesktopUploadQueueService: @unchecked Sendable {
    public typealias Clock = @Sendable () -> Date
    public typealias ProgressObserver = @Sendable ([DesktopUploadQueueItem]) async -> Void
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
    private let queue = DispatchQueue(label: "pro.2brain.graf.desktop-upload-queue", qos: .utility)
    private var document: DesktopUploadQueueDocument?

    public init(
        queueURL: URL? = nil,
        recordingsRootURL: URL? = nil,
        channel: GrafAppChannel = .current,
        policy: LocalBufferPolicy = LocalBufferService.defaultPolicy,
        manifestService: LocalRecordingManifestService = LocalRecordingManifestService(),
        client: DesktopUploadClientProtocol? = DesktopUploadClient.configuredFromEnvironment(),
        clock: @escaping Clock = Date.init
    ) {
        self.queueURL = queueURL ?? Self.defaultQueueURL(channel: channel)
        self.recordingsRootURL = recordingsRootURL ?? LocalRecordingStore(channel: channel).rootURL
        self.policy = policy
        self.manifestService = manifestService
        self.client = client
        self.clock = clock
    }

    public static func defaultQueueURL(
        fileManager: FileManager = .default,
        applicationSupportURL: URL? = nil,
        channel: GrafAppChannel = .current
    ) -> URL {
        let base = applicationSupportURL ?? fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ??
            fileManager.temporaryDirectory
        let current = base
            .appendingPathComponent(channel.applicationSupportFolderName, isDirectory: true)
            .appendingPathComponent("UploadQueue", isDirectory: true)
            .appendingPathComponent("upload-queue.json")
        let legacy = base
            .appendingPathComponent("2brain Rec", isDirectory: true)
            .appendingPathComponent("UploadQueue", isDirectory: true)
            .appendingPathComponent("upload-queue.json")
        if channel != .installedDev,
           !fileManager.fileExists(atPath: current.path),
           fileManager.fileExists(atPath: legacy.path) {
            return legacy
        }
        return current
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
        calendarContextEventId: String? = nil,
        calendarMatchAttemptId: String? = nil
    ) throws -> DesktopUploadQueueItem {
        try queue.sync {
            var document = try loadDocumentOnQueue()
            let now = clock()
            let item = try makeItem(
                manifest: manifest,
                directoryURL: directoryURL,
                now: now,
                reason: reason,
                calendarContextEventId: calendarContextEventId,
                calendarMatchAttemptId: calendarMatchAttemptId
            )
            var savedItem = item

            if let index = document.items.firstIndex(where: { $0.id == item.id }) {
                let existing = document.items[index]
                if existing.state.isTerminal {
                    return existing
                }
                let merged = Self.preservingQueueState(from: existing, over: item)
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
    public func enqueueSaving(
        manifest: LocalRecordingManifest,
        directoryURL: URL,
        calendarContextEventId: String? = nil,
        calendarMatchAttemptId: String? = nil
    ) throws -> DesktopUploadQueueItem {
        try queue.sync {
            var document = try loadDocumentOnQueue()
            let now = clock()
            var item = try makeItem(
                manifest: manifest,
                directoryURL: directoryURL,
                now: now,
                reason: "local_recording_saving",
                calendarContextEventId: calendarContextEventId,
                calendarMatchAttemptId: calendarMatchAttemptId
            )
            item.state = .saving
            item.failureCategory = .none
            item.failureReason = nil
            item.retryMode = .manualOnly
            item.nextRetryAt = nil
            if let index = document.items.firstIndex(where: { $0.id == item.id }) {
                guard !document.items[index].state.isTerminal else { return document.items[index] }
                document.items[index] = Self.preservingQueueState(from: document.items[index], over: item)
                item = document.items[index]
            } else {
                document.items.append(item)
            }
            document.items = document.items.sortedForDisplay()
            document.updatedAt = now
            try saveDocumentOnQueue(document)
            return item
        }
    }

    @discardableResult
    public func persistCalendarMatchAttempt(
        localRecordingId: String,
        attemptId: String
    ) throws -> DesktopUploadQueueItem? {
        let normalizedAttemptId = attemptId.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !normalizedAttemptId.isEmpty else { return nil }

        return try queue.sync {
            var document = try loadDocumentOnQueue()
            guard let index = document.items.firstIndex(where: { $0.directoryId == localRecordingId }) else {
                return nil
            }
            guard Self.canPersistCalendarMatchAttempt(in: document.items[index]) else {
                return nil
            }
            let now = clock()
            document.items[index].calendarMatchAttemptId = normalizedAttemptId
            document.items[index].updatedAt = now
            document.items = document.items.sortedForDisplay()
            document.updatedAt = now
            try saveDocumentOnQueue(document)
            return document.items.first { $0.directoryId == localRecordingId }
        }
    }

    public static func canPersistCalendarMatchAttempt(
        in item: DesktopUploadQueueItem
    ) -> Bool {
        item.attemptCount == 0 &&
            item.state != .uploading &&
            !item.state.isTerminal &&
            item.meetingId == nil &&
            item.serverTruth.meetingId == nil
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
    public func deleteLocalCopy(itemId: String) throws -> DesktopUploadQueueItem {
        try queue.sync {
            var document = try loadDocumentOnQueue()
            guard let index = document.items.firstIndex(where: { $0.id == itemId }) else {
                throw DesktopUploadQueueServiceError.packageNotFound(itemId)
            }
            let item = document.items[index]
            guard isInsideRecordingsRoot(item.directoryPath) else {
                throw DesktopUploadQueueServiceError.localArtifactOutsideRecordingsRoot(item.directoryPath)
            }
            if FileManager.default.fileExists(atPath: item.directoryPath) {
                try FileManager.default.removeItem(atPath: item.directoryPath)
            }
            let now = clock()
            let deleted = item.withTransition(
                to: .terminalDeleted,
                now: now,
                failureCategory: UploadFailureCategory.none,
                failureReason: nil,
                retryMode: .terminal,
                nextRetryAt: nil,
                retentionDecision: RetentionDecision(
                    decision: .terminalDeleted,
                    decidedAt: now,
                    reason: "local_copy_deleted_by_user",
                    localArtifactsRetained: false,
                    policyReference: "local_buffer.user_delete"
                )
            )
            document.items[index] = deleted
            document.items = document.items.sortedForDisplay()
            document.updatedAt = now
            try saveDocumentOnQueue(document)
            return deleted
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
    public func submitSupportIncident(
        itemId: String,
        using submitter: any DesktopSupportIncidentSubmitting
    ) async throws -> DesktopSupportIncidentResponse {
        try await submitSupportIncident(itemIds: [itemId], using: submitter)
    }

    @discardableResult
    public func submitSupportIncident(
        itemIds: [String],
        using submitter: any DesktopSupportIncidentSubmitting
    ) async throws -> DesktopSupportIncidentResponse {
        let context = client?.supportIncidentContext() ?? .unknown
        let submission = try markSupportIncidentSending(itemIds: itemIds, context: context)

        do {
            let response = try await submitter.submitSupportIncident(report: submission.report)
            try markSupportIncidentResponse(itemIds: submission.itemIds, report: submission.report, response: response)
            return response
        } catch {
            try markSupportIncidentFailed(itemIds: submission.itemIds, report: submission.report, error: error)
            throw error
        }
    }

    /// Builds the same bounded v2 metadata-only report used for submission.
    /// The queue core returns text only; AppKit owns clipboard side effects.
    public func supportIncidentReportText(itemIds: [String]) throws -> String? {
        let context = client?.supportIncidentContext() ?? .unknown
        return try queue.sync {
            let document = try loadDocumentOnQueue()
            guard let primaryID = itemIds.first,
                  let primary = document.items.first(where: { $0.id == primaryID })
            else {
                throw DesktopUploadQueueServiceError.packageNotFound(itemIds.first ?? "unknown")
            }
            let projection = DesktopUploadCustodyProjection(item: primary, now: clock())
            let affectedItems = itemIds.compactMap { itemID in
                document.items.first(where: { $0.id == itemID })
            }
            return DesktopSupportIncidentReport(
                item: primary,
                projection: projection,
                context: context,
                affectedItems: affectedItems
            )?.clipboardText
        }
    }

    @discardableResult
    public func syncSupportIncident(
        itemId: String,
        using submitter: any DesktopSupportIncidentSubmitting
    ) async throws -> DesktopSupportIncidentResponse {
        try await syncSupportIncident(itemIds: [itemId], using: submitter)
    }

    @discardableResult
    public func syncSupportIncident(
        itemIds: [String],
        using submitter: any DesktopSupportIncidentSubmitting
    ) async throws -> DesktopSupportIncidentResponse {
        let draft = try markSupportIncidentSyncing(itemIds: itemIds)
        do {
            let response = try await submitter.syncSupportIncident(incidentID: draft.incidentNumber)
            try markSupportIncidentResponse(
                itemIds: draft.itemIds,
                reportFingerprint: draft.reportFingerprint,
                dedupeKey: draft.dedupeKey,
                response: response
            )
            return response
        } catch {
            try markSupportIncidentPendingAfterSyncFailure(draft: draft, error: error)
            throw error
        }
    }

    @discardableResult
    public func processDueItems(
        onProgress: @escaping ProgressObserver = { _ in }
    ) async throws -> [DesktopUploadQueueItem] {
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
            try await upload(item: item, client: client, onProgress: onProgress)
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
        let roles = Set(item.artifactProfile.trackCompleteness.map(\.transportRole))
        var files = [item.manifestPath]
        if roles.contains(.microphone) { files.append(item.microphonePath) }
        if roles.contains(.system) { files.append(item.systemAudioPath) }
        if roles.contains(.media) { files.append(item.transcriptionAudioPath) }
        if roles.contains(.playback) { files.append(item.reviewAudioPath) }
        return files.filter { !$0.isEmpty && $0 != "metadata-only" }
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
        client: DesktopUploadClientProtocol,
        onProgress: @escaping ProgressObserver
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
        try await publishProgress(onProgress)

        do {
            let reconciled = try await reconcileBeforeUpload(started, client: client)
            try await publishProgress(onProgress)
            guard reconciled.syncConflictState == .none else {
                return
            }
            guard reconciled.state != .uploaded else {
                return
            }
            let result = try await client.upload(reconciled) { [self] reportedProgress in
                _ = try updateItem(itemId: reconciled.id) { current, now in
                    guard current.state == .uploading else {
                        return current
                    }
                    return current.withTransition(
                        to: .uploading,
                        now: now,
                        serverTruth: current.serverTruth.mergingConfirmedProgress(reportedProgress)
                    )
                }
                try await publishProgress(onProgress)
            }
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
            try await publishProgress(onProgress)
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
            try await publishProgress(onProgress)
        }
    }

    private func publishProgress(_ observer: ProgressObserver) async throws {
        await observer(try loadItems())
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
        calendarContextEventId: String? = nil,
        calendarMatchAttemptId: String? = nil
    ) throws -> DesktopUploadQueueItem {
        let manifestURL = directoryURL.appendingPathComponent(manifest.manifestFileName)
        let microphoneURL = directoryURL.appendingPathComponent("mic.wav")
        let systemAudioURL = directoryURL.appendingPathComponent("incoming.wav")
        let transcriptionURL = directoryURL.appendingPathComponent("meeting-transcription.wav")
        guard FileManager.default.fileExists(atPath: manifestURL.path) else {
            throw DesktopUploadQueueServiceError.manifestMissing(manifestURL)
        }

        let profile = Self.artifactProfile(
            manifest: manifest,
            manifestURL: manifestURL,
            microphoneURL: microphoneURL,
            systemAudioURL: systemAudioURL,
            reviewAudioURL: directoryURL.appendingPathComponent("meeting-review.m4a"),
            transcriptionURL: transcriptionURL
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
            calendarMatchAttemptId: calendarMatchAttemptId,
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
        var merged = Self.preservingQueueState(from: existing, over: refreshed)
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

    private static func preservingQueueState(
        from existing: DesktopUploadQueueItem,
        over refreshed: DesktopUploadQueueItem
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
        merged.supportIncidentSubmission = existing.supportIncidentSubmission
        merged.calendarContextEventId = existing.calendarContextEventId ?? refreshed.calendarContextEventId
        merged.calendarMatchAttemptId = existing.calendarMatchAttemptId ?? refreshed.calendarMatchAttemptId
        merged.recordingMetadata = existing.recordingMetadata ?? refreshed.recordingMetadata
        return merged
    }

    private struct SupportIncidentSubmissionDraft {
        var itemIds: [String]
        var report: DesktopSupportIncidentReport
    }

    private struct SupportIncidentSyncDraft {
        var itemIds: [String]
        var incidentNumber: String
        var reportFingerprint: String
        var dedupeKey: String
        var copyFallbackAvailable: Bool
    }

    private func markSupportIncidentSending(
        itemIds: [String],
        context: DesktopSupportIncidentReportContext
    ) throws -> SupportIncidentSubmissionDraft {
        try queue.sync {
            var document = try loadDocumentOnQueue()
            guard let primaryItemId = itemIds.first,
                  let index = document.items.firstIndex(where: { $0.id == primaryItemId })
            else {
                throw DesktopUploadQueueServiceError.packageNotFound(itemIds.first ?? "unknown")
            }
            let now = clock()
            let item = document.items[index]
            let projection = DesktopUploadCustodyProjection(item: item, now: now)
            let affectedItems = itemIds.compactMap { itemId in
                document.items.first { $0.id == itemId }
            }
            guard let report = DesktopSupportIncidentReport(
                item: item,
                projection: projection,
                context: context,
                affectedItems: affectedItems
            ) else {
                var next = item
                next.updatedAt = now
                next.supportIncidentSubmission = .unavailable(attemptedAt: now)
                document.items[index] = next
                document.updatedAt = now
                try saveDocumentOnQueue(document)
                throw DesktopUploadClientError.httpStatus(422, "support_incident.unavailable")
            }

            let changedIds = Set(affectedItems.map(\.id))
            document.items = document.items.map { candidate in
                guard changedIds.contains(candidate.id) else { return candidate }
                var next = candidate
                next.updatedAt = now
                next.supportIncidentSubmission = .sending(
                    reportFingerprint: report.safeReportFingerprint,
                    dedupeKey: report.dedupeKey,
                    attemptedAt: now
                )
                return next
            }
            document.items = document.items.sortedForDisplay()
            document.updatedAt = now
            try saveDocumentOnQueue(document)
            return SupportIncidentSubmissionDraft(itemIds: Array(changedIds), report: report)
        }
    }

    private func markSupportIncidentResponse(
        itemIds: [String],
        report: DesktopSupportIncidentReport,
        response: DesktopSupportIncidentResponse
    ) throws {
        if response.isPendingSync {
            try markSupportIncidentPending(
                itemIds: itemIds,
                reportFingerprint: report.safeReportFingerprint,
                dedupeKey: report.dedupeKey,
                incidentNumber: response.incidentId,
                copyFallbackAvailable: response.copyFallbackAvailable
            )
            return
        }
        try markSupportIncidentSent(
            itemIds: itemIds,
            reportFingerprint: report.safeReportFingerprint,
            dedupeKey: report.dedupeKey,
            response: response
        )
    }

    private func markSupportIncidentResponse(
        itemIds: [String],
        reportFingerprint: String,
        dedupeKey: String,
        response: DesktopSupportIncidentResponse
    ) throws {
        if response.isPendingSync {
            try markSupportIncidentPending(
                itemIds: itemIds,
                reportFingerprint: reportFingerprint,
                dedupeKey: dedupeKey,
                incidentNumber: response.incidentId,
                copyFallbackAvailable: response.copyFallbackAvailable
            )
            return
        }
        try markSupportIncidentSent(
            itemIds: itemIds,
            reportFingerprint: reportFingerprint,
            dedupeKey: dedupeKey,
            response: response
        )
    }

    private func markSupportIncidentSent(
        itemIds: [String],
        reportFingerprint: String,
        dedupeKey: String,
        response: DesktopSupportIncidentResponse
    ) throws {
        let changedIds = Set(itemIds)
        try updateSupportIncidentSubmission(itemIds: changedIds) { item, now in
            item.supportIncidentSubmission = .sent(
                reportFingerprint: reportFingerprint,
                dedupeKey: dedupeKey,
                incidentNumber: response.incidentId,
                githubIssueNumber: response.githubIssueNumber,
                attemptedAt: now,
                copyFallbackAvailable: response.copyFallbackAvailable
            )
        }
    }

    private func markSupportIncidentPending(
        itemIds: [String],
        reportFingerprint: String,
        dedupeKey: String,
        incidentNumber: String,
        copyFallbackAvailable: Bool,
        failureCode: String? = nil
    ) throws {
        let changedIds = Set(itemIds)
        try updateSupportIncidentSubmission(itemIds: changedIds) { item, now in
            item.supportIncidentSubmission = .pendingSync(
                reportFingerprint: reportFingerprint,
                dedupeKey: dedupeKey,
                incidentNumber: incidentNumber,
                attemptedAt: now,
                copyFallbackAvailable: copyFallbackAvailable,
                failureCode: failureCode
            )
        }
    }

    private func markSupportIncidentSyncing(itemIds: [String]) throws -> SupportIncidentSyncDraft {
        try queue.sync {
            var document = try loadDocumentOnQueue()
            guard let primaryItemId = itemIds.first,
                  let primaryIndex = document.items.firstIndex(where: { $0.id == primaryItemId }),
                  let submission = document.items[primaryIndex].supportIncidentSubmission,
                  submission.state == .pendingSync,
                  let incidentNumber = submission.incidentNumber?.trimmingCharacters(in: .whitespacesAndNewlines),
                  !incidentNumber.isEmpty,
                  let reportFingerprint = submission.localReportFingerprint,
                  let dedupeKey = submission.dedupeKey
            else {
                throw DesktopUploadClientError.httpStatus(409, "support_incident.sync_unavailable")
            }
            let changedIds = Set(itemIds).intersection(Set(document.items.map(\.id)))
            guard !changedIds.isEmpty else {
                throw DesktopUploadQueueServiceError.packageNotFound(primaryItemId)
            }
            let now = clock()
            document.items = document.items.map { candidate in
                guard changedIds.contains(candidate.id) else { return candidate }
                var next = candidate
                next.updatedAt = now
                next.supportIncidentSubmission = DesktopSupportIncidentSubmissionState(
                    state: .sending,
                    localReportFingerprint: reportFingerprint,
                    dedupeKey: dedupeKey,
                    incidentNumber: incidentNumber,
                    lastSubmissionAttemptAt: now,
                    copyFallbackAvailable: submission.copyFallbackAvailable,
                    accessibilityLabel: DesktopSupportIncidentActionCopy.sendingMessage
                )
                return next
            }
            document.items = document.items.sortedForDisplay()
            document.updatedAt = now
            try saveDocumentOnQueue(document)
            return SupportIncidentSyncDraft(
                itemIds: Array(changedIds),
                incidentNumber: incidentNumber,
                reportFingerprint: reportFingerprint,
                dedupeKey: dedupeKey,
                copyFallbackAvailable: submission.copyFallbackAvailable
            )
        }
    }

    private func markSupportIncidentPendingAfterSyncFailure(
        draft: SupportIncidentSyncDraft,
        error: Error
    ) throws {
        let failure = Self.supportIncidentFailure(error)
        try markSupportIncidentPending(
            itemIds: draft.itemIds,
            reportFingerprint: draft.reportFingerprint,
            dedupeKey: draft.dedupeKey,
            incidentNumber: draft.incidentNumber,
            copyFallbackAvailable: draft.copyFallbackAvailable,
            failureCode: failure.code
        )
    }

    private func markSupportIncidentFailed(
        itemIds: [String],
        report: DesktopSupportIncidentReport,
        error: Error
    ) throws {
        let failure = Self.supportIncidentFailure(error)
        let changedIds = Set(itemIds)
        try updateSupportIncidentSubmission(itemIds: changedIds) { item, now in
            item.supportIncidentSubmission = .failedWithCopyFallback(
                reportFingerprint: report.safeReportFingerprint,
                dedupeKey: report.dedupeKey,
                attemptedAt: now,
                failureCategory: failure.category,
                failureCode: failure.code
            )
        }
    }

    private func updateSupportIncidentSubmission(
        itemIds: Set<String>,
        update: (inout DesktopUploadQueueItem, Date) -> Void
    ) throws {
        try queue.sync {
            var document = try loadDocumentOnQueue()
            let now = clock()
            var changed = false
            document.items = document.items.map { item in
                guard itemIds.contains(item.id) else { return item }
                var next = item
                next.updatedAt = now
                update(&next, now)
                changed = true
                return next
            }
            if changed {
                document.items = document.items.sortedForDisplay()
                document.updatedAt = now
                try saveDocumentOnQueue(document)
            }
        }
    }

    private static func supportIncidentFailure(_ error: Error) -> (category: String, code: String) {
        if let clientError = error as? DesktopUploadClientError {
            switch clientError {
            case .httpStatus(_, let code):
                return (clientError.failureCategory.rawValue, code)
            case .invalidBaseURL:
                return (clientError.failureCategory.rawValue, "support_incident.invalid_base_url")
            case .invalidArtifactPackage:
                return (clientError.failureCategory.rawValue, "support_incident.invalid_artifact_package")
            case .invalidResponse:
                return (clientError.failureCategory.rawValue, "support_incident.invalid_response")
            case .localFileMissing:
                return (clientError.failureCategory.rawValue, "support_incident.local_file_missing")
            case .serverStillMissingRanges:
                return (clientError.failureCategory.rawValue, "support_incident.server_still_missing_ranges")
            }
        }
        return (UploadFailureCategory.network.rawValue, "support_incident.unavailable")
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
        let requiredRoles: Set<DesktopUploadTransportRole> = profile.isV5Package
            ? [.manifest, .media, .playback]
            : [.manifest, .microphone, .system]
        let presentRoles = Set(
            profile.trackCompleteness
                .filter(\.present)
                .map(\.transportRole)
        )
        if !requiredRoles.isSubset(of: presentRoles) {
            return "local_artifacts_not_uploadable"
        }
        if manifest.failureReason != .none {
            return manifest.failureReason.rawValue
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
        systemAudioURL: URL,
        reviewAudioURL: URL? = nil,
        transcriptionURL: URL? = nil
    ) -> ArtifactCompletenessProfile {
        let manifestSize = fileSize(manifestURL)
        let microphoneSize = fileSize(microphoneURL)
        let systemAudioSize = fileSize(systemAudioURL)
        let reviewAudio = reviewAudioURL.flatMap(reviewAudioArtifact)
        let durationSeconds = max(1, Int(ceil(Double(max(0, manifest.stoppedAt.timeIntervalSince(manifest.startedAt))))))
        if manifest.isV5Package {
            let mediaURL = transcriptionURL ?? manifestURL
                .deletingLastPathComponent()
                .appendingPathComponent("meeting-transcription.wav")
            let mediaAudio = transcriptionAudioArtifact(mediaURL)
            let manifestTrack = UploadTrackCompleteness(
                transportRole: .manifest,
                fileName: "manifest.json",
                present: manifestSize > 0,
                byteCount: manifestSize,
                sha256: sha256Hex(url: manifestURL),
                durationSeconds: 1
            )
            let mediaTrack = UploadTrackCompleteness(
                transportRole: .media,
                fileName: "meeting-transcription.wav",
                present: mediaAudio != nil,
                byteCount: mediaAudio?.byteCount ?? fileSize(mediaURL),
                sha256: mediaAudio?.sha256,
                durationSeconds: mediaAudio?.durationSeconds ?? durationSeconds
            )
            let playbackTrack = UploadTrackCompleteness(
                transportRole: .playback,
                fileName: "meeting-review.m4a",
                present: reviewAudio != nil,
                byteCount: reviewAudio?.byteCount ?? (reviewAudioURL.map(fileSize) ?? 0),
                sha256: reviewAudio?.sha256,
                durationSeconds: reviewAudio?.durationSeconds ?? durationSeconds
            )
            let tracks = [manifestTrack, mediaTrack, playbackTrack]
            let manifestTracksByRole = Dictionary(
                uniqueKeysWithValues: manifest.tracks.map { ($0.role, $0) }
            )
            let integrityMatches =
                manifestTracksByRole[.mixedMeetingAudio]?.byteCount == mediaTrack.byteCount &&
                manifestTracksByRole[.mixedMeetingAudio]?.sha256 == mediaTrack.sha256 &&
                manifestTracksByRole[.reviewPlayback]?.byteCount == playbackTrack.byteCount &&
                manifestTracksByRole[.reviewPlayback]?.sha256 == playbackTrack.sha256
            let uploadable = manifest.isServerUploadEligible &&
                manifest.isComplete &&
                integrityMatches &&
                tracks.allSatisfy(\.uploadable)
            return ArtifactCompletenessProfile(
                schemaVersion: manifest.schemaVersion,
                manifestPresent: manifestTrack.present,
                microphonePresent: false,
                systemAudioPresent: false,
                manifestSha256: manifestTrack.sha256,
                microphoneSha256: nil,
                systemAudioSha256: nil,
                manifestSizeBytes: manifestSize,
                microphoneSizeBytes: 0,
                systemAudioSizeBytes: 0,
                durationSeconds: durationSeconds,
                trackCompleteness: tracks,
                isUploadable: uploadable,
                qualityWarningReason: uploadable ? Self.qualityWarningReason(for: manifest) : nil
            )
        }
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
        var tracks = [microphoneTrack, systemTrack, manifestTrack]
        if let reviewAudio {
            tracks.append(UploadTrackCompleteness(
                transportRole: .playback,
                fileName: "meeting-review.m4a",
                present: true,
                byteCount: reviewAudio.byteCount,
                sha256: reviewAudio.sha256,
                durationSeconds: reviewAudio.durationSeconds
            ))
        }
        let manifestRoles = Set(manifest.tracks.compactMap { DesktopUploadTransportRole.role(forLocalTrackRole: $0.role) })
        let hasRequiredManifestRoles = manifestRoles.isSuperset(of: [.microphone, .system])
        let uploadable = manifest.isServerUploadEligible &&
            hasRequiredManifestRoles &&
            [microphoneTrack, systemTrack, manifestTrack].allSatisfy(\.uploadable)
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
             .silentInput, .noFrames, .stoppedBeforeFrames, .historicalPackage:
            return reason.rawValue
        case .none, .directoryUnavailable, .writeFailed, .finalizationFailed,
             .permissionDenied, .scopeUnavailable, .protectedAudioBlocked, .captureFailed,
             .cpuGateFailed, .deviceUnavailable,
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
        let now = clock()
        let needsSchemaMigration = loaded.schemaVersion != DesktopUploadQueueDocument.schemaVersion
        if needsSchemaMigration {
            loaded.schemaVersion = DesktopUploadQueueDocument.schemaVersion
        }
        var needsSave = needsSchemaMigration
        loaded.items = loaded.items.map { item in
            guard let submission = item.supportIncidentSubmission,
                  submission.state == .sending
            else {
                return item
            }
            var next = item
            next.updatedAt = now
            next.supportIncidentSubmission = .failedWithCopyFallback(
                reportFingerprint: submission.localReportFingerprint ?? "unknown",
                dedupeKey: submission.dedupeKey ?? "unknown",
                attemptedAt: now,
                failureCategory: UploadFailureCategory.network.rawValue,
                failureCode: "support_incident.interrupted"
            )
            needsSave = true
            return next
        }.sortedForDisplay()
        if needsSave {
            loaded.updatedAt = now
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
            schemaVersion: LocalRecordingManifest.legacySchemaVersion,
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

    private static func reviewAudioArtifact(_ url: URL) -> (byteCount: Int64, sha256: String?, durationSeconds: Int)? {
        let byteCount = fileSize(url)
        guard byteCount > 0,
              let file = try? AVAudioFile(forReading: url),
              (file.fileFormat.settings[AVFormatIDKey] as? NSNumber)?.intValue == Int(kAudioFormatMPEG4AAC),
              Int(file.fileFormat.sampleRate.rounded()) == 48_000,
              Int(file.fileFormat.channelCount) == 1,
              file.length > 0
        else {
            return nil
        }
        return (
            byteCount,
            sha256Hex(url: url),
            max(1, Int(ceil(Double(file.length) / file.fileFormat.sampleRate)))
        )
    }

    private static func transcriptionAudioArtifact(
        _ url: URL
    ) -> (byteCount: Int64, sha256: String?, durationSeconds: Int)? {
        let byteCount = fileSize(url)
        guard byteCount > 44,
              url.pathExtension.lowercased() == "wav",
              let file = try? AVAudioFile(forReading: url),
              (file.fileFormat.settings[AVFormatIDKey] as? NSNumber)?.intValue == Int(kAudioFormatLinearPCM),
              Int(file.fileFormat.sampleRate.rounded()) == 16_000,
              Int(file.fileFormat.channelCount) == 1,
              (file.fileFormat.settings[AVLinearPCMBitDepthKey] as? NSNumber)?.intValue == 16,
              file.length > 0
        else {
            return nil
        }
        return (
            byteCount,
            sha256Hex(url: url),
            max(1, Int(ceil(Double(file.length) / file.fileFormat.sampleRate)))
        )
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
        case LocalRecordingFailureReason.historicalPackage.rawValue:
            return "сохранённая ранее запись будет отправлена в режиме совместимости"
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
