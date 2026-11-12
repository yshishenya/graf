import Foundation

public struct RecordingBlockerPresentation: Equatable, Sendable {
    public enum Kind: String, Equatable, Sendable {
        case permission
        case storage
        case capture
        case policy
        case indicator
        case source
        case alreadyRecording
        case unknown
    }

    public let kind: Kind
    public let message: String

    public init(kind: Kind, message: String) {
        self.kind = kind
        self.message = message
    }

    public var title: String {
        switch kind {
        case .permission:
            return "Нужно разрешение"
        case .storage:
            return "Нужна помощь"
        case .capture:
            return "Запись не началась"
        case .policy:
            return "Запись недоступна"
        case .indicator:
            return "Нужна помощь"
        case .source:
            return "Проверьте источник"
        case .alreadyRecording:
            return "Запись уже идёт"
        case .unknown:
            return "Нужна помощь"
        }
    }

    public var systemImage: String {
        switch kind {
        case .permission:
            return "lock.trianglebadge.exclamationmark"
        case .storage:
            return "externaldrive.badge.exclamationmark"
        case .capture:
            return "exclamationmark.triangle.fill"
        case .policy:
            return "hand.raised"
        case .indicator:
            return "eye.slash"
        case .source:
            return "mic.badge.xmark"
        case .alreadyRecording:
            return "record.circle"
        case .unknown:
            return "exclamationmark.triangle.fill"
        }
    }

    public var tone: StatusTone {
        switch kind {
        case .alreadyRecording:
            return .muted
        case .permission, .storage, .capture, .policy, .indicator, .source, .unknown:
            return .warning
        }
    }

    public var isActionable: Bool {
        kind != .alreadyRecording
    }
}
