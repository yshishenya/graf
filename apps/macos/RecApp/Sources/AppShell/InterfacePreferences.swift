import AppKit
import Foundation

public final class InterfacePreferencesStore {
    public static let windowFrameKey = "pro.2brain.graf.windowFrame"
    public static let inspectorExpandedKey = "pro.2brain.graf.inspectorExpanded"
    public static let selectedMicrophoneKey = "pro.2brain.graf.selectedMicrophoneDeviceID"

    private let defaults: UserDefaults

    public init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
    }

    public var windowFrame: NSRect? {
        guard let value = defaults.string(forKey: Self.windowFrameKey) else { return nil }
        let frame = NSRectFromString(value)
        guard frame.width >= 320, frame.height >= 240, frame.width.isFinite, frame.height.isFinite else {
            return nil
        }
        return frame
    }

    public func saveWindowFrame(_ frame: NSRect) {
        guard frame.width.isFinite, frame.height.isFinite, frame.width >= 320, frame.height >= 240 else { return }
        defaults.set(NSStringFromRect(frame), forKey: Self.windowFrameKey)
    }

    public var inspectorExpanded: Bool {
        defaults.bool(forKey: Self.inspectorExpandedKey)
    }

    public func saveInspectorExpanded(_ value: Bool) {
        defaults.set(value, forKey: Self.inspectorExpandedKey)
    }

    public var selectedMicrophoneDeviceID: String? {
        guard let value = defaults.string(forKey: Self.selectedMicrophoneKey), !value.isEmpty else { return nil }
        return value
    }

    public func saveSelectedMicrophoneDeviceID(_ value: String?) {
        if let value, !value.isEmpty {
            defaults.set(value, forKey: Self.selectedMicrophoneKey)
        } else {
            defaults.removeObject(forKey: Self.selectedMicrophoneKey)
        }
    }
}
