import Foundation
import TwoBrainRecShared

public struct LocalRecordingPresentation: Equatable, Sendable {
    public enum Status: String, Equatable, Sendable {
        case saving
        case active
        case saved
        case degraded
        case blocked
        case failed
        case terminal
        case deleting
        case corrupted
        case uploading
        case expired
    }

    public let status: Status
    public let title: String
    public let detail: String?
    public let systemImage: String
    public let tone: StatusTone
    public let requiresAttention: Bool
    public let allowsOpen: Bool
    public let allowsSend: Bool
    public let allowsDelete: Bool

    public init(
        status: Status,
        title: String,
        detail: String? = nil,
        systemImage: String,
        tone: StatusTone,
        requiresAttention: Bool,
        allowsOpen: Bool = false,
        allowsSend: Bool = false,
        allowsDelete: Bool = false
    ) {
        self.status = status
        self.title = title
        self.detail = detail
        self.systemImage = systemImage
        self.tone = tone
        self.requiresAttention = requiresAttention
        self.allowsOpen = allowsOpen
        self.allowsSend = allowsSend
        self.allowsDelete = allowsDelete
    }

    public static func from(_ status: LocalRecordingSessionStatus) -> LocalRecordingPresentation {
        switch status {
        case .active:
            return .init(
                status: .active,
                title: "Идет запись",
                systemImage: "waveform.path.badge.plus",
                tone: .muted,
                requiresAttention: false
            )
        case .saved:
            return .init(
                status: .saved,
                title: "Сохранено на Mac",
                systemImage: "checkmark.circle",
                tone: .success,
                requiresAttention: false,
                allowsOpen: true,
                allowsSend: true,
                allowsDelete: true
            )
        case .degraded:
            return .init(
                status: .degraded,
                title: "Сохранено с ограничением",
                detail: "Есть ограничения проверки",
                systemImage: "exclamationmark.triangle.fill",
                tone: .warning,
                requiresAttention: true,
                allowsOpen: true,
                allowsSend: true,
                allowsDelete: true
            )
        case .blocked:
            return .init(
                status: .blocked,
                title: "Нужна помощь",
                detail: SystemAudioStatusLabels.localRecordingStatus(.blocked),
                systemImage: "lock.trianglebadge.exclamationmark",
                tone: .warning,
                requiresAttention: true,
                allowsOpen: true
            )
        case .failed:
            return .init(
                status: .failed,
                title: "Нужна помощь",
                detail: SystemAudioStatusLabels.localRecordingStatus(.failed),
                systemImage: "exclamationmark.triangle.fill",
                tone: .danger,
                requiresAttention: true,
                allowsOpen: true
            )
        }
    }

    public static func active(paused: Bool) -> LocalRecordingPresentation {
        paused
            ? .init(
                status: .active,
                title: "Идет запись · микрофон выключен",
                detail: SystemAudioStatusLabels.localRecordingPausedStatus,
                systemImage: "mic.slash",
                tone: .warning,
                requiresAttention: false
            )
            : .init(
                status: .active,
                title: "Идет запись",
                systemImage: "waveform.path.badge.plus",
                tone: .muted,
                requiresAttention: false
            )
    }

    public static let saving = LocalRecordingPresentation(
        status: .saving,
        title: "Сохраняем запись…",
        systemImage: "clock",
        tone: .warning,
        requiresAttention: false
    )

    public static let terminal = LocalRecordingPresentation(
        status: .terminal,
        title: "Удалено",
        systemImage: "xmark.circle",
        tone: .muted,
        requiresAttention: false
    )

    public static let deleting = LocalRecordingPresentation(
        status: .deleting,
        title: "Удаляем локальную копию…",
        systemImage: "trash",
        tone: .warning,
        requiresAttention: false
    )

    public static let corrupted = LocalRecordingPresentation(
        status: .corrupted,
        title: "Запись повреждена",
        detail: "Локальная копия требует проверки",
        systemImage: "exclamationmark.triangle.fill",
        tone: .danger,
        requiresAttention: true
    )

    public static func uploading(percent: Int?) -> LocalRecordingPresentation {
        let detail = percent.map { "Отправляем запись… \($0)%" } ?? "Отправляем запись…"
        return .init(
            status: .uploading,
            title: "Отправляем запись",
            detail: detail,
            systemImage: "icloud.and.arrow.up",
            tone: .neutral,
            requiresAttention: false
        )
    }

    public static let expired = LocalRecordingPresentation(
        status: .expired,
        title: "Срок хранения истёк",
        detail: "Автоматическая отправка больше не выполнится. Локальная копия сохранена на этом Mac.",
        systemImage: "clock.badge.exclamationmark",
        tone: .warning,
        requiresAttention: true,
        allowsOpen: true,
        allowsDelete: true
    )
}
