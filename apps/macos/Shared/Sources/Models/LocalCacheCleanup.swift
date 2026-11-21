import Foundation

public enum LocalCacheCleanupAction: String, Codable, CaseIterable, Equatable, Sendable {
    case manualCleanup = "manual_cleanup"
    case automaticEviction = "automatic_eviction"
}

public enum LocalCacheCleanupReceiptState: String, Codable, Equatable, Sendable {
    case pending
    case completed
    case noop
}

/// Durable, non-private evidence of a local transcription cleanup. It never
/// contains a path, title, transcript, token or raw server identifier.
public struct LocalCacheCleanupReceipt: Codable, Equatable, Sendable {
    public static let schemaVersion = "local-cache-cleanup-receipt.v1"

    public let schemaVersion: String
    public let action: LocalCacheCleanupAction
    public let state: LocalCacheCleanupReceiptState
    public let localRecordingFingerprint: String
    public let meetingFingerprint: String
    public let mediaRevisionFingerprint: String
    public let playbackRevisionFingerprint: String
    public let verifiedAt: Date
    public let bytes: Int64
    public let ownerScopeFingerprint: String
    public let appVersion: String
    public let createdAt: Date

    public init(
        action: LocalCacheCleanupAction,
        state: LocalCacheCleanupReceiptState,
        localRecordingFingerprint: String,
        meetingFingerprint: String,
        mediaRevisionFingerprint: String,
        playbackRevisionFingerprint: String,
        verifiedAt: Date,
        bytes: Int64,
        ownerScopeFingerprint: String,
        appVersion: String,
        createdAt: Date
    ) {
        self.schemaVersion = Self.schemaVersion
        self.action = action
        self.state = state
        self.localRecordingFingerprint = localRecordingFingerprint
        self.meetingFingerprint = meetingFingerprint
        self.mediaRevisionFingerprint = mediaRevisionFingerprint
        self.playbackRevisionFingerprint = playbackRevisionFingerprint
        self.verifiedAt = verifiedAt
        self.bytes = max(0, bytes)
        self.ownerScopeFingerprint = ownerScopeFingerprint
        self.appVersion = appVersion
        self.createdAt = createdAt
    }

    public func withState(
        _ state: LocalCacheCleanupReceiptState,
        createdAt: Date
    ) -> LocalCacheCleanupReceipt {
        LocalCacheCleanupReceipt(
            action: action,
            state: state,
            localRecordingFingerprint: localRecordingFingerprint,
            meetingFingerprint: meetingFingerprint,
            mediaRevisionFingerprint: mediaRevisionFingerprint,
            playbackRevisionFingerprint: playbackRevisionFingerprint,
            verifiedAt: verifiedAt,
            bytes: bytes,
            ownerScopeFingerprint: ownerScopeFingerprint,
            appVersion: appVersion,
            createdAt: createdAt
        )
    }

    /// Action + local recording + local revision identify one cleanup ledger
    /// entry. The playback revision stays in the content, so a pending intent
    /// can be found before the network proof is fetched.
    public var fileStem: String {
        Self.fileStem(
            action: action,
            localRecordingFingerprint: localRecordingFingerprint,
            mediaRevisionFingerprint: mediaRevisionFingerprint
        )
    }

    public static func fileStem(
        action: LocalCacheCleanupAction,
        localRecordingFingerprint: String,
        mediaRevisionFingerprint: String
    ) -> String {
        "receipt-\(action.rawValue)-\(localRecordingFingerprint)-\(mediaRevisionFingerprint)"
    }
}

public enum LocalCacheCleanupOutcome: Equatable, Sendable {
    case completed(bytes: Int64)
    case noop
    case notEligible(primaryReason: LocalCacheEligibilityReason, allReasons: [LocalCacheEligibilityReason])
    case unexpectedMissing
    case scopeChanged
    case localFileChanged
    case failed(code: String)
}

public enum LocalCacheByteFormat {
    public static func string(from bytes: Int64) -> String {
        let formatter = ByteCountFormatter()
        formatter.countStyle = .decimal
        formatter.allowedUnits = [.useGB, .useMB, .useKB]
        formatter.includesUnit = true
        formatter.isAdaptive = true
        return formatter.string(fromByteCount: max(0, bytes))
    }
}

/// One local WAV that is locally eligible for the manual cleanup surface. It
/// carries only a date and a byte count; the panel never renders a meeting
/// title or a path.
public struct LocalCacheCleanupCandidate: Identifiable, Equatable, Sendable {
    public let itemID: String
    public let startedAt: Date
    public let bytes: Int64

    public var id: String { itemID }

    public init(itemID: String, startedAt: Date, bytes: Int64) {
        self.itemID = itemID
        self.startedAt = startedAt
        self.bytes = max(0, bytes)
    }
}

/// Shared local eligibility for the manual surface. Server proof is revalidated
/// by `LocalCacheCleanupService`; this policy only decides whether the action
/// should be offered at all.
public enum LocalCacheCleanupCandidatePolicy {
    public static let maximumPanelCandidates = 30

    public static func cleanupBytes(for item: DesktopUploadQueueItem) -> Int64? {
        guard item.state == .uploaded,
              item.isV5Package,
              item.partialContinuity != true,
              !item.lifecycleBlocksContent,
              item.isLocalUnbound != true,
              item.meetingId != nil || item.serverTruth.meetingId != nil,
              let bytes = LocalCacheEligibility.expectedTranscriptionBytes(for: item),
              bytes > 0 else {
            return nil
        }
        return bytes
    }

    public static func eligibleCandidateCount(for items: [DesktopUploadQueueItem]) -> Int {
        items.reduce(into: 0) { count, item in
            if cleanupBytes(for: item) != nil { count += 1 }
        }
    }

    public static func panelCandidates(
        for items: [DesktopUploadQueueItem],
        limit: Int = maximumPanelCandidates
    ) -> [LocalCacheCleanupCandidate] {
        guard limit > 0 else { return [] }
        return items
            .compactMap { item -> LocalCacheCleanupCandidate? in
                guard let bytes = cleanupBytes(for: item) else { return nil }
                return LocalCacheCleanupCandidate(
                    itemID: item.id,
                    startedAt: item.displayStartedAt,
                    bytes: bytes
                )
            }
            .sorted {
                if $0.startedAt != $1.startedAt { return $0.startedAt < $1.startedAt }
                return $0.itemID < $1.itemID
            }
            .prefix(limit)
            .map { $0 }
    }
}

public enum LocalCacheCleanupCopy {
    public static let actionTitle = "Освободить место"
    public static let confirmationTitle = "Удалить локальную копию транскрипции?"
    public static let confirmationBody =
        "Будет удалён только файл транскрипции этой записи. Аудио для прослушивания и описание записи " +
        "останутся на Mac. Встреча на сервере не удалится."
    public static let cancelTitle = "Отмена"
    public static let success =
        "Локальная копия транскрипции удалена. Аудио для прослушивания осталось."
    public static let noop = "Эта запись уже очищена."
    public static let unexpectedMissing =
        "Файл уже отсутствует. Проверьте запись перед повторной очисткой."
    public static let scopeChanged =
        "Аккаунт или состояние удаления изменились. Запись оставлена на Mac."
    public static let localFileChanged =
        "Локальный файл изменился во время проверки. Очистка отменена."
    public static let defaultUnavailable =
        "Очистка сейчас недоступна. Запись оставлена на Mac."

    public static let accessibilityAction =
        "Освободить место. Будет удалён только локальный файл транскрипции. Аудио и описание записи останутся."
    public static let accessibilityConfirmation =
        "Подтвердите удаление локальной копии транскрипции. Серверная встреча не удаляется."

    public static let cacheTitle = "Локальный кэш"
    public static let cacheExplanation =
        "GRAF может автоматически удалять только локальные файлы транскрипции подтверждённых записей. " +
        "Аудио для прослушивания и описание записи остаются."
    public static let autoEvictionToggle = "Автоматически освобождать место"
    public static let autoEvictionToggleDetail =
        "Удаляются только файлы транскрипции записей, которые уже доступны на сервере."
    public static let autoEvictionDisabled =
        "Автоматическая очистка выключена. Новые файлы не удаляются."
    public static let autoEvictionOperatorOverride =
        "Автоматическая очистка временно отключена администратором."
    public static let cacheWarning =
        "Локальный кэш заполняется. Старые подтверждённые файлы транскрипции будут очищены автоматически."

    public static func spaceLine(size: String) -> String {
        "Освободится: \(size)."
    }

    public static func confirmButtonTitle(size: String) -> String {
        "Освободить \(size)"
    }

    public static func evictionResult(size: String) -> String {
        "Освобождено \(size). Аудио для прослушивания осталось."
    }

    public static func statusLine(used: String, budget: String) -> String {
        "Занято \(used) из \(budget)."
    }

    public static func accessibilityStatus(used: String, budget: String) -> String {
        "Локальный кэш: занято \(used) из \(budget)."
    }

    public static func accessibilityToggle(detail: String) -> String {
        "Автоматически освобождать место. \(detail)"
    }

    public static func reason(_ code: LocalCacheEligibilityReason) -> String {
        switch code {
        case .proofMissing:
            return "Серверная копия ещё не подтверждена. Запись оставлена на Mac."
        case .proofStale:
            return "Данные о серверной копии устарели. Повторите проверку позже."
        case .revisionMismatch:
            return "Серверная копия относится к другой версии записи. Запись оставлена на Mac."
        case .playbackNotAvailable:
            return "Сервер пока не может воспроизвести запись. Запись оставлена на Mac."
        case .playbackNotVerified:
            return "Сервер не подтвердил сохранность аудио. Запись оставлена на Mac."
        case .archiveAudioFalse, .archiveAudioUnknown:
            return "Сервер не сохранил аудио для этой записи. Запись оставлена на Mac."
        case .retentionUnsafe, .retentionUnknown, .retentionExpired, .retentionTooClose:
            return "Срок хранения на сервере скоро истечёт. Запись оставлена на Mac."
        case .deletionOperationOpen:
            return "Встреча удаляется. Дождитесь завершения удаления."
        case .confirmedDeletion:
            return "Встреча уже удаляется на сервере. Запись оставлена на Mac."
        case .accountScopeMismatch:
            return "Запись относится к другому аккаунту. Переключитесь на нужный аккаунт."
        case .localArtifactsMissing, .localArtifactsOutsideRoot:
            return "Локальные файлы записи неполные. Очистка недоступна."
        case .localIntegrityUnverified:
            return "Локальные файлы не прошли проверку. Очистка недоступна."
        case .dependencyUnavailable:
            return "Не удалось проверить серверную копию. Попробуйте позже."
        default:
            return defaultUnavailable
        }
    }

    public static func outcomeMessage(_ outcome: LocalCacheCleanupOutcome) -> String {
        switch outcome {
        case .completed:
            return success
        case .noop:
            return noop
        case .unexpectedMissing:
            return unexpectedMissing
        case .scopeChanged:
            return scopeChanged
        case .localFileChanged:
            return localFileChanged
        case .notEligible(let primaryReason, _):
            return reason(primaryReason)
        case .failed:
            return defaultUnavailable
        }
    }
}
