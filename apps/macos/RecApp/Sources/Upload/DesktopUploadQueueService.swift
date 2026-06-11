import CryptoKit
import Foundation
import TwoBrainRecShared

public enum DesktopUploadQueueServiceError: Error, CustomStringConvertible, Sendable {
    case manifestMissing(URL)
    case packageNotFound(String)

    public var description: String {
        switch self {
        case .manifestMissing(let url):
            return "manifest_missing:\(url.lastPathComponent)"
        case .packageNotFound(let id):
            return "package_not_found:\(id)"
        }
    }
}

public final class DesktopUploadQueueService: @unchecked Sendable {
    public typealias Clock = @Sendable () -> Date

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
                guard !document.items.contains(where: { $0.id == item.id }) else {
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
        reason: String = "local_recording_finalized"
    ) throws -> DesktopUploadQueueItem {
        try queue.sync {
            var document = try loadDocumentOnQueue()
            let now = clock()
            let item = try makeItem(
                manifest: manifest,
                directoryURL: directoryURL,
                now: now,
                reason: reason
            )

            if let index = document.items.firstIndex(where: { $0.id == item.id }) {
                let existing = document.items[index]
                if existing.state.isTerminal {
                    return existing
                }
                var merged = item
                merged.attemptCount = existing.attemptCount
                merged.meetingId = existing.meetingId
                merged.uploadSessionId = existing.uploadSessionId
                merged.serverTruth = existing.serverTruth
                merged.retryRecords = existing.retryRecords
                merged.createdAt = existing.createdAt
                document.items[index] = merged
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
    public func retry(itemId: String) throws -> DesktopUploadQueueItem {
        try updateItem(itemId: itemId) { item, now in
            item.withTransition(
                to: item.artifactProfile.isUploadable ? .queued : .blocked,
                now: now,
                failureCategory: item.artifactProfile.isUploadable ? UploadFailureCategory.none : .localResource,
                failureReason: item.artifactProfile.isUploadable ? nil : "local_artifacts_not_uploadable",
                retryMode: item.artifactProfile.isUploadable ? .automatic : .manualOnly,
                nextRetryAt: item.artifactProfile.isUploadable ? now : nil,
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
        return try loadItems()
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
            let result = try await client.upload(started)
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
                        startedAt: started.updatedAt,
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
        reason: String = "local_recording_discovered"
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
        return DesktopUploadQueueItem(
            id: DesktopUploadQueueItem.deterministicId(
                directoryId: manifest.directoryId,
                sessionId: manifest.sessionId
            ),
            sessionId: manifest.sessionId,
            directoryId: manifest.directoryId,
            directoryPath: directoryURL.path,
            manifestPath: manifestURL.path,
            microphonePath: microphoneURL.path,
            systemAudioPath: systemAudioURL.path,
            state: state,
            failureCategory: failureCategory,
            failureReason: profile.isUploadable ? nil : "local_recording_package_not_uploadable",
            retryMode: retryMode,
            nextRetryAt: profile.isUploadable ? now : nil,
            retentionDeadline: retentionDeadline,
            createdAt: now,
            updatedAt: now,
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
        let uploadable = manifest.status == .saved &&
            manifest.isComplete &&
            hasRequiredManifestRoles &&
            tracks.allSatisfy(\.uploadable)
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
            isUploadable: uploadable
        )
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
        var loaded = try JSONDecoder.uploadQueueDecoder.decode(DesktopUploadQueueDocument.self, from: data)
        loaded.items = loaded.items.sortedForDisplay()
        document = loaded
        return loaded
    }

    private func saveDocumentOnQueue(_ document: DesktopUploadQueueDocument) throws {
        try FileManager.default.createDirectory(
            at: queueURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        let data = try JSONEncoder.uploadQueueEncoder.encode(document)
        try data.write(to: queueURL, options: [.atomic])
        self.document = document
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

    public var title: String {
        pendingCount > 1
            ? "\(primaryItem.state.displayName) + \(pendingCount - 1) more"
            : primaryItem.state.displayName
    }

    public var detail: String {
        let progress = Int((primaryItem.progressFraction * 100).rounded())
        if let reason = primaryItem.failureReason, !reason.isEmpty {
            return "\(progress)% - \(reason)"
        }
        return "\(progress)% - \(primaryItem.retryMode.displayName)"
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
