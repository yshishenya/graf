import Foundation
import TwoBrainRecShared

public struct LocalRecordingPresentation: Equatable, Sendable {
    public enum Status: String, Equatable, Sendable {
        case active
        case saved
        case degraded
        case blocked
        case failed
    }

    public let status: Status
    public let title: String
    public let detail: String?
    public let systemImage: String
    public let tone: StatusTone
    public let requiresAttention: Bool

    public init(
        status: Status,
        title: String,
        detail: String? = nil,
        systemImage: String,
        tone: StatusTone,
        requiresAttention: Bool
    ) {
        self.status = status
        self.title = title
        self.detail = detail
        self.systemImage = systemImage
        self.tone = tone
        self.requiresAttention = requiresAttention
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
                requiresAttention: false
            )
        case .degraded:
            return .init(
                status: .degraded,
                title: "Сохранено с ограничением",
                detail: "Есть ограничения проверки",
                systemImage: "exclamationmark.triangle.fill",
                tone: .warning,
                requiresAttention: true
            )
        case .blocked:
            return .init(
                status: .blocked,
                title: "Нужна помощь",
                detail: "Локальная запись заблокирована",
                systemImage: "lock.trianglebadge.exclamationmark",
                tone: .warning,
                requiresAttention: true
            )
        case .failed:
            return .init(
                status: .failed,
                title: "Нужна помощь",
                detail: "Запись завершилась с ошибкой",
                systemImage: "exclamationmark.triangle.fill",
                tone: .danger,
                requiresAttention: true
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
}
