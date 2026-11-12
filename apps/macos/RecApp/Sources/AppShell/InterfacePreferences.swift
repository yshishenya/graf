import AppKit
import Foundation

public final class InterfacePreferencesStore {
    public static let minimumWindowSize = NSSize(width: 1040, height: 680)
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
        guard frame.width >= Self.minimumWindowSize.width,
              frame.height >= Self.minimumWindowSize.height,
              frame.width.isFinite,
              frame.height.isFinite else {
            return nil
        }
        return frame
    }

    public func saveWindowFrame(_ frame: NSRect) {
        guard frame.width.isFinite,
              frame.height.isFinite,
              frame.width >= Self.minimumWindowSize.width,
              frame.height >= Self.minimumWindowSize.height else {
            return
        }
        defaults.set(NSStringFromRect(frame), forKey: Self.windowFrameKey)
    }

    public static func clampedFrame(
        _ frame: NSRect,
        to visibleFrame: NSRect,
        minimumSize: NSSize = minimumWindowSize
    ) -> NSRect {
        var result = frame
        result.size.width = max(minimumSize.width, min(frame.width, visibleFrame.width))
        result.size.height = max(minimumSize.height, min(frame.height, visibleFrame.height))
        result.origin.x = min(max(frame.origin.x, visibleFrame.minX), visibleFrame.maxX - result.width)
        result.origin.y = min(max(frame.origin.y, visibleFrame.minY), visibleFrame.maxY - result.height)
        return result
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
