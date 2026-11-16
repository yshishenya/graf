import Foundation
import TwoBrainRecShared

public struct LocalCacheCleanupScopeFence: Sendable {
    public let scope: RecordingDeletionScope?
    public let generation: UInt64
    private let isCurrentCheck: @Sendable () -> Bool

    public init(
        scope: RecordingDeletionScope?,
        generation: UInt64,
        isCurrent: @escaping @Sendable () -> Bool
    ) {
        self.scope = scope
        self.generation = generation
        self.isCurrentCheck = isCurrent
    }

    public func isCurrent() -> Bool {
        isCurrentCheck()
    }
}

/// Manual and automatic WAV cleanup share this service. It re-fetches the
/// server proof, re-evaluates the full predicate, verifies the local file by
/// hash/inode and writes a two-phase receipt around the single unlink.
public struct LocalCacheCleanupService: Sendable {
    public typealias Clock = @Sendable () -> Date

    private let queueURL: URL
    private let recordingsRootURL: URL
    private let receiptDirectoryURL: URL?
    private let client: (any DesktopServerProofFetching)?
    private let appVersion: String
    private let proofTimeout: TimeInterval
    private let policy: LocalCacheEligibilityPolicy
    private let clock: Clock
    private let fenceProvider: @Sendable () -> LocalCacheCleanupScopeFence?

    public init(
        queueURL: URL,
        recordingsRootURL: URL,
        receiptDirectoryURL: URL? = nil,
        client: (any DesktopServerProofFetching)?,
        appVersion: String = LocalCacheCleanupService.currentAppVersion(),
        proofTimeout: TimeInterval = 15,
        policy: LocalCacheEligibilityPolicy = .default,
        clock: @escaping Clock = Date.init,
        fenceProvider: @escaping @Sendable () -> LocalCacheCleanupScopeFence?
    ) {
        self.queueURL = queueURL
        self.recordingsRootURL = recordingsRootURL
        self.receiptDirectoryURL = receiptDirectoryURL
        self.client = client
        self.appVersion = appVersion.isEmpty ? "unknown" : appVersion
        self.proofTimeout = max(0.01, proofTimeout)
        self.policy = policy
        self.clock = clock
        self.fenceProvider = fenceProvider
    }

    public static func currentAppVersion(bundle: Bundle = .main) -> String {
        let short = bundle.infoDictionary?["CFBundleShortVersionString"] as? String ?? "unknown"
        if let build = bundle.infoDictionary?["CFBundleVersion"] as? String, !build.isEmpty {
            return "\(short) (\(build))"
        }
        return short
    }

    public func cleanup(
        itemID: String,
        action: LocalCacheCleanupAction
    ) async -> LocalCacheCleanupOutcome {
        guard let fence = fenceProvider(), fence.isCurrent() else {
            return .scopeChanged
        }

        var snapshot: LocalCacheRawQueueSnapshot
        do {
            snapshot = try LocalCacheRawQueueSnapshot.read(from: queueURL)
        } catch {
            return .failed(code: "queue_unreadable")
        }
        guard var item = snapshot.item(withID: itemID) else {
            return .failed(code: "item_missing")
        }
        guard let transcriptionURL = Self.transcriptionURL(
            for: item,
            recordingsRootURL: recordingsRootURL
        ) else {
            return .notEligible(
                primaryReason: .localArtifactsOutsideRoot,
                allReasons: [.localArtifactsOutsideRoot]
            )
        }

        let localFingerprint = LocalCacheFingerprint.recording(item.directoryId)
        let mediaFingerprint = LocalCacheFingerprint.revision(item.localMediaRevisionId)
        let gateKey = "\(queueURL.standardizedFileURL.path)|\(localFingerprint)|\(mediaFingerprint)"
        guard LocalCacheCleanupGate.shared.acquire(gateKey) else {
            return .failed(code: "cleanup_in_progress")
        }
        defer { LocalCacheCleanupGate.shared.release(gateKey) }
        let resolvedReceiptDirectory = receiptDirectoryURL
            ?? queueURL.deletingLastPathComponent()
                .appendingPathComponent("LocalCacheEviction/receipts", isDirectory: true)
        guard !LocalCacheArtifactProbe.isInside(
            resolvedReceiptDirectory.path,
            root: recordingsRootURL
        ) else {
            return .failed(code: "receipt_directory_rejected")
        }
        let store = LocalCacheCleanupReceiptStore(
            receiptDirectoryURL: resolvedReceiptDirectory,
            action: action,
            localRecordingFingerprint: localFingerprint,
            mediaRevisionFingerprint: mediaFingerprint
        )
        let existing: LocalCacheCleanupReceipt?
        do {
            existing = try store.load()
        } catch {
            return .failed(code: "receipt_unreadable")
        }
        if let existing,
           existing.action != action ||
            existing.localRecordingFingerprint != localFingerprint ||
            existing.mediaRevisionFingerprint != mediaFingerprint {
            return .failed(code: "receipt_unreadable")
        }

        let pathState = LocalCacheFileIdentity.state(atPath: transcriptionURL.path)
        guard case .regular(let initialIdentity) = pathState else {
            if pathState == .missing {
                let anyReceipt: LocalCacheCleanupReceipt?
                do {
                    anyReceipt = try store.loadAnyAction()
                } catch {
                    return .failed(code: "receipt_unreadable")
                }
                return recoverMissing(
                    anyReceipt: anyReceipt,
                    receiptDirectoryURL: store.receiptDirectoryURL
                )
            }
            return .notEligible(
                primaryReason: .localIntegrityUnverified,
                allReasons: [.localIntegrityUnverified]
            )
        }

        guard let client else {
            return .notEligible(
                primaryReason: .dependencyUnavailable,
                allReasons: [.dependencyUnavailable]
            )
        }
        let reconciliation: DesktopUploadReconciliation?
        let proofItem = item
        do {
            reconciliation = try await LocalCacheAsyncTimeout.run(seconds: proofTimeout) {
                try await client.fetchServerProof(for: proofItem)
            }
        } catch {
            return .notEligible(
                primaryReason: .dependencyUnavailable,
                allReasons: [.dependencyUnavailable]
            )
        }
        guard fence.isCurrent() else { return .scopeChanged }
        // A swapped path or a file rewritten during the request must never be
        // evaluated or unlinked as the file that was originally proven.
        guard case .regular(let fetchedIdentity) = LocalCacheFileIdentity.state(
            atPath: transcriptionURL.path
        ),
            fetchedIdentity == initialIdentity else {
            return .localFileChanged
        }

        // A queue mutation during the proof request may add an open deletion,
        // purge or conflict. Re-read and re-evaluate before acting.
        let refreshedSnapshot: LocalCacheRawQueueSnapshot
        do {
            refreshedSnapshot = try LocalCacheRawQueueSnapshot.read(from: queueURL)
        } catch {
            return .failed(code: "queue_unreadable")
        }
        if refreshedSnapshot.fingerprint != snapshot.fingerprint {
            guard let refreshedItem = refreshedSnapshot.item(withID: itemID) else {
                return .failed(code: "queue_item_missing")
            }
            guard Self.hasSameCleanupIdentity(refreshedItem, item) else {
                return .failed(code: "queue_item_changed")
            }
            item = refreshedItem
            snapshot = refreshedSnapshot
        }

        let inspection: LocalArtifactFacts
        let inspectionItem = item
        do {
            inspection = try await LocalCacheAsyncTimeout.run(seconds: 15) {
                await Task.detached(priority: .utility) {
                    LocalCacheArtifactProbe.inspect(
                        item: inspectionItem,
                        recordingsRootURL: recordingsRootURL,
                        computeHashes: true
                    )
                }.value
            }
        } catch {
            return .notEligible(
                primaryReason: .localIntegrityUnverified,
                allReasons: [.localIntegrityUnverified]
            )
        }
        var facts = inspection
        facts.packageBytes = await measurePackage(for: item)
        if let expectedHash = LocalCacheEligibility.transcriptionTrack(for: item)?.sha256,
           facts.transcriptionSha256 != expectedHash {
            return .notEligible(
                primaryReason: .localIntegrityUnverified,
                allReasons: [.localIntegrityUnverified]
            )
        }

        let document = DesktopUploadQueueDocument(
            updatedAt: snapshot.updatedAt ?? clock(),
            items: [],
            deletionOperations: snapshot.deletionOperations
        )
        let decision = LocalCacheEligibility.evaluate(
            item: item,
            document: document,
            scope: fence.scope,
            proof: reconciliation?.proof,
            proofFetchedAt: reconciliation?.fetchedAt,
            localFacts: facts,
            policy: policy,
            now: clock()
        )
        guard decision.verdict == .potentiallyEligible else {
            return .notEligible(
                primaryReason: decision.primaryReason,
                allReasons: decision.allReasons
            )
        }
        // F284 fidelity: the review audio must still be openable before the
        // transcription WAV is removed. This is a read-only native check, never
        // a player call, and it runs before any pending receipt exists.
        let playbackItem = item
        let playbackAvailable: Bool
        do {
            playbackAvailable = try await LocalCacheAsyncTimeout.run(seconds: 10) {
                await Task.detached(priority: .utility) {
                    DesktopUploadQueueService.canOpenLocalPlayback(
                        item: playbackItem,
                        recordingsRootURL: recordingsRootURL
                    )
                }.value
            }
        } catch {
            return .notEligible(
                primaryReason: .localArtifactsMissing,
                allReasons: [.localArtifactsMissing]
            )
        }
        guard playbackAvailable else {
            return .notEligible(
                primaryReason: .localArtifactsMissing,
                allReasons: [.localArtifactsMissing]
            )
        }

        guard let proof = decision.proof,
              let meetingID = proof.meetingId,
              let playbackRevision = proof.playback?.mediaRevisionId,
              let verifiedAt = proof.playback?.verifiedAt?.date else {
            return .failed(code: "receipt_evidence_missing")
        }

        // The file may have changed while the proof request was in flight.
        guard case .regular(let currentIdentity) = LocalCacheFileIdentity.state(
            atPath: transcriptionURL.path
        ),
            currentIdentity == initialIdentity else {
            return .localFileChanged
        }

        let pending = LocalCacheCleanupReceipt(
            action: action,
            state: .pending,
            localRecordingFingerprint: localFingerprint,
            meetingFingerprint: LocalCacheFingerprint.meeting(meetingID),
            mediaRevisionFingerprint: mediaFingerprint,
            playbackRevisionFingerprint: LocalCacheFingerprint.revision(playbackRevision),
            verifiedAt: verifiedAt,
            bytes: currentIdentity.size,
            ownerScopeFingerprint: LocalCacheFingerprint.scope(fence.scope),
            appVersion: appVersion,
            createdAt: clock()
        )
        do {
            try store.write(pending)
        } catch {
            return .failed(code: "receipt_write_failed")
        }

        guard fence.isCurrent() else { return .scopeChanged }
        // Any queue change after the pending intent invalidates the snapshot
        // that justified it. Leave the pending receipt for a retry.
        let preUnlinkSnapshot: LocalCacheRawQueueSnapshot
        do {
            preUnlinkSnapshot = try LocalCacheRawQueueSnapshot.read(from: queueURL)
        } catch {
            return .failed(code: "queue_unreadable")
        }
        guard preUnlinkSnapshot.fingerprint == snapshot.fingerprint else {
            return .failed(code: "queue_changed")
        }
        // Required immediately before unlink: reject a symlink swap or a file
        // that changed after the pending intent was recorded.
        guard case .regular(let finalIdentity) = LocalCacheFileIdentity.state(
            atPath: transcriptionURL.path
        ),
            finalIdentity == currentIdentity else {
            return .localFileChanged
        }
        guard LocalCacheFileIdentity.removeFile(atPath: transcriptionURL.path) else {
            return .failed(code: "unlink_failed")
        }

        do {
            try store.write(pending.withState(.completed, createdAt: pending.createdAt))
        } catch {
            // The pending intent stays durable; a retry completes it without a
            // second unlink.
            return .failed(code: "receipt_write_failed")
        }
        return .completed(bytes: finalIdentity.size)
    }

    private func measurePackage(for item: DesktopUploadQueueItem) async -> Int64? {
        let directoryURL = URL(fileURLWithPath: item.directoryPath)
        do {
            return try await LocalCacheAsyncTimeout.run(seconds: 5) {
                try await Task.detached(priority: .utility) {
                    let snapshot = try LocalRecordingFootprintMeasurer.measure(at: directoryURL)
                    return snapshot.bytes
                }.value
            }
        } catch {
            return nil
        }
    }

    /// A WAV may have been removed by the other action (manual vs automatic).
    /// Any receipt for the same item + local revision is authoritative evidence
    /// that the file was cleaned, so the second action must be a no-op and must
    /// not create a duplicate receipt.
    private static func hasSameCleanupIdentity(
        _ lhs: DesktopUploadQueueItem,
        _ rhs: DesktopUploadQueueItem
    ) -> Bool {
        lhs.state == rhs.state &&
            lhs.localMediaRevisionId == rhs.localMediaRevisionId &&
            lhs.ownerScope == rhs.ownerScope &&
            lhs.isLocalUnbound == rhs.isLocalUnbound &&
            lhs.directoryPath == rhs.directoryPath &&
            lhs.manifestPath == rhs.manifestPath &&
            lhs.transcriptionAudioPath == rhs.transcriptionAudioPath &&
            lhs.reviewAudioPath == rhs.reviewAudioPath &&
            lhs.meetingId == rhs.meetingId &&
            lhs.serverTruth.meetingId == rhs.serverTruth.meetingId
    }

    private func recoverMissing(
        anyReceipt: LocalCacheCleanupReceipt?,
        receiptDirectoryURL: URL
    ) -> LocalCacheCleanupOutcome {
        guard let anyReceipt else { return .unexpectedMissing }
        switch anyReceipt.state {
        case .completed, .noop:
            return .noop
        case .pending:
            let ownerStore = LocalCacheCleanupReceiptStore(
                receiptDirectoryURL: receiptDirectoryURL,
                action: anyReceipt.action,
                localRecordingFingerprint: anyReceipt.localRecordingFingerprint,
                mediaRevisionFingerprint: anyReceipt.mediaRevisionFingerprint
            )
            do {
                try ownerStore.write(anyReceipt.withState(.completed, createdAt: anyReceipt.createdAt))
            } catch {
                return .failed(code: "receipt_write_failed")
            }
            return .noop
        }
    }

    private static func transcriptionURL(
        for item: DesktopUploadQueueItem,
        recordingsRootURL: URL
    ) -> URL? {
        guard !item.directoryPath.isEmpty,
              item.directoryPath != "metadata-only",
              LocalCacheArtifactProbe.isInside(item.directoryPath, root: recordingsRootURL) else {
            return nil
        }
        let url = URL(fileURLWithPath: item.transcriptionAudioPath)
        guard url.lastPathComponent == "meeting-transcription.wav",
              LocalCacheArtifactProbe.isInside(url.path, root: recordingsRootURL) else {
            return nil
        }
        return url
    }
}

// MARK: - Receipts

struct LocalCacheCleanupReceiptStore: Sendable {
    let receiptDirectoryURL: URL
    let action: LocalCacheCleanupAction
    let localRecordingFingerprint: String
    let mediaRevisionFingerprint: String

    var fileURL: URL {
        receiptDirectoryURL.appendingPathComponent(
            LocalCacheCleanupReceipt.fileStem(
                action: action,
                localRecordingFingerprint: localRecordingFingerprint,
                mediaRevisionFingerprint: mediaRevisionFingerprint
            ) + ".json"
        )
    }

    func load() throws -> LocalCacheCleanupReceipt? {
        guard FileManager.default.fileExists(atPath: fileURL.path) else { return nil }
        let data = try Data(contentsOf: fileURL)
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        do {
            let receipt = try decoder.decode(LocalCacheCleanupReceipt.self, from: data)
            guard receipt.action == action,
                  receipt.localRecordingFingerprint == localRecordingFingerprint,
                  receipt.mediaRevisionFingerprint == mediaRevisionFingerprint else {
                throw LocalCacheCleanupServiceError.receiptUnreadable
            }
            return receipt
        } catch {
            throw LocalCacheCleanupServiceError.receiptUnreadable
        }
    }

    /// Checks both cleanup actions for the same item + local revision without
    /// creating or rewriting a receipt.
    func loadAnyAction() throws -> LocalCacheCleanupReceipt? {
        for candidateAction in LocalCacheCleanupAction.allCases {
            let candidateStore = LocalCacheCleanupReceiptStore(
                receiptDirectoryURL: receiptDirectoryURL,
                action: candidateAction,
                localRecordingFingerprint: localRecordingFingerprint,
                mediaRevisionFingerprint: mediaRevisionFingerprint
            )
            if let receipt = try candidateStore.load() {
                return receipt
            }
        }
        return nil
    }

    func write(_ receipt: LocalCacheCleanupReceipt) throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        encoder.dateEncodingStrategy = .iso8601
        let data = try encoder.encode(receipt)
        try LocalCustodyFileProtection.write(data, to: fileURL)
    }
}

enum LocalCacheCleanupServiceError: Error {
    case receiptUnreadable
}

/// Serializes manual and automatic cleanup for one item + local revision. A
/// concurrent second call must not write a second pending receipt or unlink.
private final class LocalCacheCleanupGate: @unchecked Sendable {
    static let shared = LocalCacheCleanupGate()

    private let lock = NSLock()
    private var active: Set<String> = []

    func acquire(_ key: String) -> Bool {
        lock.lock()
        defer { lock.unlock() }
        guard !active.contains(key) else { return false }
        active.insert(key)
        return true
    }

    func release(_ key: String) {
        lock.lock()
        active.remove(key)
        lock.unlock()
    }
}

// MARK: - Local file identity

enum LocalCachePathState: Equatable, Sendable {
    case missing
    case notRegular
    case regular(LocalCacheFileIdentity)
}

struct LocalCacheFileIdentity: Equatable, Sendable {
    let device: Int64
    let inode: UInt64
    let size: Int64

    static func state(atPath path: String) -> LocalCachePathState {
        var info = stat()
        guard path.withCString({ lstat($0, &info) }) == 0 else {
            return errno == ENOENT ? .missing : .notRegular
        }
        guard (info.st_mode & S_IFMT) == S_IFREG else {
            return .notRegular
        }
        return .regular(
            LocalCacheFileIdentity(
                device: Int64(info.st_dev),
                inode: UInt64(info.st_ino),
                size: Int64(info.st_size)
            )
        )
    }

    static func removeFile(atPath path: String) -> Bool {
        path.withCString { Darwin.unlink($0) } == 0
    }
}
