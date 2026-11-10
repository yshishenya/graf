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
    public let showsStop: Bool
    public let showsPause: Bool
    public let showsResume: Bool
    public let isActionable: Bool

    public init(
        kind: CaptureStatusKind,
        title: String,
        detail: String? = nil,
        systemImage: String,
        tone: StatusTone,
        showsStop: Bool = false,
        showsPause: Bool = false,
        showsResume: Bool = false,
        isActionable: Bool = false
    ) {
        self.kind = kind
        self.title = title
        self.detail = detail
        self.systemImage = systemImage
        self.tone = tone
        self.showsStop = showsStop
        self.showsPause = showsPause
        self.showsResume = showsResume
        self.isActionable = isActionable
    }

    public static func resolve(session: CaptureSession?) -> CaptureStatusPresentation {
        guard let session else {
            return .init(
                kind: .idle,
                title: "Готово к записи",
                systemImage: "record.circle",
                tone: .muted
            )
        }
        switch session.state {
        case .idle, .ready:
            return .init(kind: .idle, title: "Готово к записи", systemImage: "record.circle", tone: .muted)
        case .detecting:
            return .init(kind: .detecting, title: "Проверяем готовность", systemImage: "clock", tone: .muted)
        case .starting:
            return .init(
                kind: .starting,
                title: "Начинаем запись…",
                systemImage: "clock",
                tone: .success,
                showsStop: true
            )
        case .active:
            return .init(
                kind: .active,
                title: "Идет запись",
                systemImage: "dot.radiowaves.left.and.right",
                tone: .success,
                showsStop: true,
                showsPause: true
            )
        case .paused:
            return .init(
                kind: .paused,
                title: "Идет запись · микрофон выключен",
                systemImage: "mic.slash",
                tone: .warning,
                showsStop: true,
                showsResume: true
            )
        case .degraded:
            return .init(
                kind: .degraded,
                title: "Запись с ограничением",
                systemImage: "exclamationmark.triangle.fill",
                tone: .warning,
                showsStop: true
            )
        case .stopping:
            return .init(
                kind: .stopping,
                title: "Сохраняем запись…",
                systemImage: "stop.circle",
                tone: .warning,
                showsStop: true
            )
        case .stopped, .finalized:
            return .init(
                kind: .stopped,
                title: SystemAudioStatusLabels.recordingStopped,
                systemImage: "stop.circle",
                tone: .muted
            )
        case .failed:
            return .init(
                kind: .failed,
                title: "Нужна помощь",
                systemImage: "xmark.octagon.fill",
                tone: .danger,
                isActionable: true
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
