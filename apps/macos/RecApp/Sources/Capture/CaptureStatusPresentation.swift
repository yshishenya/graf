import Foundation
import TwoBrainRecShared

public enum StatusTone: String, Equatable, Sendable {
    case neutral
    case success
    case warning
    case danger
    case muted
}

public enum CaptureStatusKind: String, Equatable, Sendable {
    case idle
    case detecting
    case starting
    case active
    case paused
    case degraded
    case stopping
    case stopped
    case failed
}

public struct CaptureStatusPresentation: Equatable, Sendable {
    public let kind: CaptureStatusKind
    public let title: String
    public let detail: String?
    public let systemImage: String
    public let tone: StatusTone

    public init(
        kind: CaptureStatusKind,
        title: String,
        detail: String? = nil,
        systemImage: String,
        tone: StatusTone
    ) {
        self.kind = kind
        self.title = title
        self.detail = detail
        self.systemImage = systemImage
        self.tone = tone
    }

    public static func title(for kind: CaptureStatusKind) -> String {
        switch kind {
        case .idle:
            return "Готово к записи"
        case .detecting:
            return "Проверяем готовность"
        case .starting:
            return "Начинаем запись…"
        case .active:
            return "Идет запись"
        case .paused:
            return "Идет запись · микрофон выключен"
        case .degraded:
            return "Запись с ограничением"
        case .stopping:
            return "Сохраняем запись…"
        case .stopped:
            return SystemAudioStatusLabels.recordingStopped
        case .failed:
            return "Нужна помощь"
        }
    }

    public static func resolve(session: CaptureSession?) -> CaptureStatusPresentation {
        guard let session else {
            return .init(
                kind: .idle,
                title: title(for: .idle),
                systemImage: "record.circle",
                tone: .muted
            )
        }
        switch session.state {
        case .idle, .ready:
            return .init(kind: .idle, title: title(for: .idle), systemImage: "record.circle", tone: .muted)
        case .detecting:
            return .init(kind: .detecting, title: title(for: .detecting), systemImage: "clock", tone: .muted)
        case .starting:
            return .init(
                kind: .starting,
                title: title(for: .starting),
                systemImage: "clock",
                tone: .success
            )
        case .active:
            return .init(
                kind: .active,
                title: title(for: .active),
                systemImage: "dot.radiowaves.left.and.right",
                tone: .success
            )
        case .paused:
            return .init(
                kind: .paused,
                title: title(for: .paused),
                systemImage: "mic.slash",
                tone: .warning
            )
        case .degraded:
            return .init(
                kind: .degraded,
                title: title(for: .degraded),
                systemImage: "exclamationmark.triangle.fill",
                tone: .warning
            )
        case .stopping:
            return .init(
                kind: .stopping,
                title: title(for: .stopping),
                systemImage: "stop.circle",
                tone: .warning
            )
        case .stopped, .finalized:
            return .init(
                kind: .stopped,
                title: title(for: .stopped),
                systemImage: "stop.circle",
                tone: .muted
            )
        case .failed:
            return .init(
                kind: .failed,
                title: title(for: .failed),
                systemImage: "xmark.octagon.fill",
                tone: .danger
            )
        }
    }

    public static func showsStopButton(for session: CaptureSession) -> Bool {
        switch session.state {
        case .starting, .active, .paused, .degraded, .stopping:
            return true
        case .idle, .detecting, .ready, .stopped, .failed, .finalized:
            return false
        }
    }
}
