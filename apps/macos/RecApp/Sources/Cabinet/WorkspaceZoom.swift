import Combine
import Foundation

public enum WorkspaceZoomCommand: String, CaseIterable, Equatable, Sendable {
    case increase
    case decrease
    case reset
}

public struct WorkspaceZoomPreference: Equatable, Sendable {
    public static let defaultValue = 1.0
    public static let minimumValue = 0.8
    public static let maximumValue = 1.4
    public static let step = 0.1
    public static let `default` = WorkspaceZoomPreference(value: defaultValue)

    public let value: Double

    public init(value: Double) {
        self.value = Self.normalized(value)
    }

    public func applying(_ command: WorkspaceZoomCommand) -> WorkspaceZoomPreference {
        switch command {
        case .increase:
            return WorkspaceZoomPreference(value: value + Self.step)
        case .decrease:
            return WorkspaceZoomPreference(value: value - Self.step)
        case .reset:
            return .default
        }
    }

    public static func normalized(_ value: Double) -> Double {
        guard value.isFinite else { return defaultValue }
        let stepped = (value / step).rounded() * step
        let clamped = min(max(stepped, minimumValue), maximumValue)
        return (clamped * 10).rounded() / 10
    }
}

public struct WorkspaceZoomMenuItem: Equatable, Sendable {
    public let command: WorkspaceZoomCommand
    public let title: String
    public let keyEquivalent: String

    public init(command: WorkspaceZoomCommand, title: String, keyEquivalent: String) {
        self.command = command
        self.title = title
        self.keyEquivalent = keyEquivalent
    }
}

public enum WorkspaceZoomMenu {
    public static let items: [WorkspaceZoomMenuItem] = [
        WorkspaceZoomMenuItem(command: .increase, title: "Zoom In", keyEquivalent: "+"),
        WorkspaceZoomMenuItem(command: .increase, title: "Zoom In", keyEquivalent: "="),
        WorkspaceZoomMenuItem(command: .decrease, title: "Zoom Out", keyEquivalent: "-"),
        WorkspaceZoomMenuItem(command: .reset, title: "Actual Size", keyEquivalent: "0")
    ]
}

public final class WorkspaceZoomStore: ObservableObject {
    public static let preferenceKey = "pro.2brain.graf.workspaceZoom"

    @Published public private(set) var preference: WorkspaceZoomPreference

    private let defaults: UserDefaults

    public init(
        preference: WorkspaceZoomPreference? = nil,
        defaults: UserDefaults = .standard
    ) {
        self.defaults = defaults
        self.preference = preference ?? Self.storedPreference(from: defaults)
    }

    public func apply(_ command: WorkspaceZoomCommand) {
        preference = preference.applying(command)
        persist()
    }

    public func set(_ preference: WorkspaceZoomPreference) {
        self.preference = preference
        persist()
    }

    private func persist() {
        defaults.set(preference.value, forKey: Self.preferenceKey)
    }

    private static func storedPreference(from defaults: UserDefaults) -> WorkspaceZoomPreference {
        guard let stored = defaults.object(forKey: preferenceKey) as? NSNumber else {
            return .default
        }

        let value = stored.doubleValue
        guard value.isFinite,
              value >= WorkspaceZoomPreference.minimumValue,
              value <= WorkspaceZoomPreference.maximumValue
        else {
            return .default
        }

        return WorkspaceZoomPreference(value: value)
    }
}
