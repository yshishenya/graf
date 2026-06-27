import Foundation
import TwoBrainRecShared

@MainActor
public struct DesktopCalendarPromptActions {
    public var openURL: (URL) -> Void
    public var startRecording: () -> Void
    public var dismiss: (DesktopCalendarPrompt) -> Void

    public init(
        openURL: @escaping (URL) -> Void,
        startRecording: @escaping () -> Void,
        dismiss: @escaping (DesktopCalendarPrompt) -> Void
    ) {
        self.openURL = openURL
        self.startRecording = startRecording
        self.dismiss = dismiss
    }

    public func performPrimaryAction(for prompt: DesktopCalendarPrompt) {
        switch prompt.kind {
        case .join:
            if let url = prompt.openMeetingURL {
                openURL(url)
            }
        case .record:
            startRecording()
        }
        dismiss(prompt)
    }

    public func dismissPrompt(_ prompt: DesktopCalendarPrompt) {
        dismiss(prompt)
    }
}
