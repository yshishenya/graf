import Foundation
import TwoBrainRecShared

public struct DesktopCalendarReminderService: Sendable {
    public private(set) var dismissedPromptIDs: Set<String>

    public init(dismissedPromptIDs: Set<String> = []) {
        self.dismissedPromptIDs = dismissedPromptIDs
    }

    public mutating func dismiss(_ prompt: DesktopCalendarPrompt) {
        dismissedPromptIDs.insert(prompt.id)
    }

    public func activePrompt(
        from events: [DesktopCalendarPromptEvent],
        now: Date = Date(),
        isRecordingActive: Bool
    ) -> DesktopCalendarPrompt? {
        Self.activePrompt(
            from: events,
            now: now,
            isRecordingActive: isRecordingActive,
            dismissedPromptIDs: dismissedPromptIDs
        )
    }

    public static func activePrompt(
        from events: [DesktopCalendarPromptEvent],
        now: Date = Date(),
        isRecordingActive: Bool,
        dismissedPromptIDs: Set<String> = []
    ) -> DesktopCalendarPrompt? {
        let recordCandidates = isRecordingActive ? [] : events
            .filter { isRecordPromptDue(for: $0, now: now) }
            .sorted { $0.startsAt < $1.startsAt }

        if recordCandidates.count > 1 {
            let prompt = overlapRecordPrompt(for: recordCandidates)
            return dismissedPromptIDs.contains(prompt.id) ? nil : prompt
        }

        if let event = recordCandidates.first {
            let prompt = recordPrompt(for: event)
            if !dismissedPromptIDs.contains(prompt.id) {
                return prompt
            }
        }

        for event in events.sorted(by: { $0.startsAt < $1.startsAt }) where isJoinPromptDue(for: event, now: now) {
            let prompt = joinPrompt(for: event)
            if !dismissedPromptIDs.contains(prompt.id) {
                return prompt
            }
        }

        return nil
    }

    public static func isJoinPromptDue(for event: DesktopCalendarPromptEvent, now: Date) -> Bool {
        let dueAt = event.joinPromptDueAt ?? event.startsAt.addingTimeInterval(-60)
        return event.joinPromptState.canSurfacePrompt &&
            event.meetingLinkPresent &&
            event.openMeetingURL != nil &&
            dueAt <= now &&
            now < event.startsAt
    }

    public static func isRecordPromptDue(for event: DesktopCalendarPromptEvent, now: Date) -> Bool {
        let dueAt = event.recordPromptDueAt ?? event.startsAt
        return event.recordPromptState.canSurfacePrompt &&
            dueAt <= now &&
            event.overlaps(now)
    }

    public static func joinPrompt(for event: DesktopCalendarPromptEvent) -> DesktopCalendarPrompt {
        let title = event.safeDisplayTitle()
        return DesktopCalendarPrompt(
            id: promptID(kind: .join, eventIDs: [event.eventId]),
            kind: .join,
            eventId: event.eventId,
            title: title,
            message: SystemAudioStatusLabels.calendarJoinPromptMessage,
            primaryActionTitle: SystemAudioStatusLabels.calendarPromptJoinActionTitle,
            accessibilityLabel: SystemAudioStatusLabels.calendarPromptAccessibilityLabel(
                title: title,
                action: SystemAudioStatusLabels.calendarPromptJoinActionTitle
            ),
            openMeetingURL: event.openMeetingURL
        )
    }

    public static func recordPrompt(for event: DesktopCalendarPromptEvent) -> DesktopCalendarPrompt {
        let title = event.safeDisplayTitle()
        return DesktopCalendarPrompt(
            id: promptID(kind: .record, eventIDs: [event.eventId]),
            kind: .record,
            eventId: event.eventId,
            title: title,
            message: SystemAudioStatusLabels.calendarRecordPromptMessage,
            primaryActionTitle: SystemAudioStatusLabels.calendarPromptRecordActionTitle,
            accessibilityLabel: SystemAudioStatusLabels.calendarPromptAccessibilityLabel(
                title: title,
                action: SystemAudioStatusLabels.calendarPromptRecordActionTitle
            )
        )
    }

    public static func overlapRecordPrompt(for events: [DesktopCalendarPromptEvent]) -> DesktopCalendarPrompt {
        DesktopCalendarPrompt(
            id: promptID(kind: .record, eventIDs: events.map(\.eventId)),
            kind: .record,
            eventId: nil,
            title: SystemAudioStatusLabels.calendarGenericMeetingTitle,
            message: SystemAudioStatusLabels.calendarOverlapPromptMessage,
            primaryActionTitle: SystemAudioStatusLabels.calendarPromptRecordActionTitle,
            accessibilityLabel: SystemAudioStatusLabels.calendarPromptAccessibilityLabel(
                title: SystemAudioStatusLabels.calendarGenericMeetingTitle,
                action: SystemAudioStatusLabels.calendarPromptRecordActionTitle
            )
        )
    }

    private static func promptID(kind: DesktopCalendarPromptKind, eventIDs: [String]) -> String {
        "\(kind.rawValue):\(eventIDs.sorted().joined(separator: ","))"
    }
}
