import Foundation
import TwoBrainRecShared

public struct DesktopCalendarResolveCommand: Equatable, Sendable {
    public let localRecordingId: String
    public let recordingStartedAt: Date
    public let decisionIntent: DesktopCalendarMatchDecisionIntent
    public let eventId: String?
}

public enum DesktopCalendarResolvePolicy {
    public static func commandAfterCaptureStarted(
        localRecordingActive: Bool,
        localRecordingId: String,
        recordingStartedAt: Date,
        decisionIntent: DesktopCalendarMatchDecisionIntent,
        eventId: String?
    ) -> DesktopCalendarResolveCommand? {
        guard localRecordingActive, !localRecordingId.isEmpty else { return nil }
        return DesktopCalendarResolveCommand(
            localRecordingId: localRecordingId,
            recordingStartedAt: recordingStartedAt,
            decisionIntent: decisionIntent,
            eventId: eventId
        )
    }

    public static func shouldProcessQueuedRecording(queueHasRecording: Bool) -> Bool {
        queueHasRecording
    }
}

@MainActor
public struct DesktopCalendarPromptActions {
    public var openURL: (URL) -> Void
    public var startRecording: (DesktopCalendarMatchDecisionIntent, String?) -> Void
    public var dismiss: (DesktopCalendarPrompt) -> Void

    public init(
        openURL: @escaping (URL) -> Void,
        startRecording: @escaping (DesktopCalendarMatchDecisionIntent, String?) -> Void,
        dismiss: @escaping (DesktopCalendarPrompt) -> Void
    ) {
        self.openURL = openURL
        self.startRecording = startRecording
        self.dismiss = dismiss
    }

    public init(
        openURL: @escaping (URL) -> Void,
        startRecording: @escaping () -> Void,
        dismiss: @escaping (DesktopCalendarPrompt) -> Void
    ) {
        self.init(
            openURL: openURL,
            startRecording: { _, _ in startRecording() },
            dismiss: dismiss
        )
    }

    public func performPrimaryAction(for prompt: DesktopCalendarPrompt) {
        switch prompt.kind {
        case .join:
            if let url = prompt.openMeetingURL {
                openURL(url)
            }
        case .record:
            if prompt.requiresExplicitCalendarChoice, prompt.eventId != nil {
                startRecording(.userSelected, prompt.eventId)
            } else if prompt.requiresExplicitCalendarChoice {
                startRecording(.userDeclined, nil)
            } else {
                startRecording(.automatic, nil)
            }
        }
        dismiss(prompt)
    }

    public func dismissPrompt(_ prompt: DesktopCalendarPrompt) {
        dismiss(prompt)
    }
}
