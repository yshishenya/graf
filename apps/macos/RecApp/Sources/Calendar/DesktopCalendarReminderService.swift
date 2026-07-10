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

        let joinCandidates = events
            .filter { isJoinPromptDue(for: $0, now: now) }
            .sorted { $0.startsAt < $1.startsAt }

        if joinCandidates.count > 1 {
            let prompt = overlapJoinPrompt(for: joinCandidates)
            return dismissedPromptIDs.contains(prompt.id) ? nil : prompt
        }

        if let event = joinCandidates.first {
            let prompt = joinPrompt(for: event)
            if !dismissedPromptIDs.contains(prompt.id) {
                return prompt
            }
        }

        return nil
    }

    public static func meetingDetectionJoinIntentHint(
        from events: [DesktopCalendarPromptEvent],
        now: Date = Date(),
        isRecordingActive: Bool,
        dismissedPromptIDs: Set<String> = []
    ) -> MeetingDetectionCalendarJoinIntentHint? {
        guard !isRecordingActive else {
            return nil
        }

        let joinCandidates = events
            .filter { isJoinPromptDue(for: $0, now: now) }
            .sorted { $0.startsAt < $1.startsAt }
        if let hint = meetingDetectionHint(
            for: joinCandidates,
            kind: .join,
            source: .calendarJoinPrompt,
            dismissedPromptIDs: dismissedPromptIDs
        ) {
            return hint
        }
        if joinCandidates.count > 1 {
            return nil
        }

        let recordCandidates = events
            .filter { event in
                event.meetingLinkPresent &&
                    event.openMeetingURL != nil &&
                    isRecordPromptDue(for: event, now: now)
            }
            .sorted { $0.startsAt < $1.startsAt }
        return meetingDetectionHint(
            for: recordCandidates,
            kind: .record,
            source: .calendarRecordPrompt,
            dismissedPromptIDs: dismissedPromptIDs
        )
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

    public static func overlapJoinPrompt(for events: [DesktopCalendarPromptEvent]) -> DesktopCalendarPrompt {
        let choices = events.sorted { $0.startsAt < $1.startsAt }.map { event in
            DesktopCalendarPromptChoice(
                id: "event:\(event.eventId)",
                eventId: event.eventId,
                title: event.safeDisplayTitle(),
                openMeetingURL: event.openMeetingURL
            )
        }
        return DesktopCalendarPrompt(
            id: promptID(kind: .join, eventIDs: events.map(\.eventId)),
            kind: .join,
            eventId: nil,
            title: SystemAudioStatusLabels.calendarGenericMeetingTitle,
            message: SystemAudioStatusLabels.calendarJoinOverlapPromptMessage,
            primaryActionTitle: SystemAudioStatusLabels.calendarPromptJoinActionTitle,
            accessibilityLabel: SystemAudioStatusLabels.calendarPromptAccessibilityLabel(
                title: SystemAudioStatusLabels.calendarGenericMeetingTitle,
                action: SystemAudioStatusLabels.calendarPromptJoinActionTitle
            ),
            choices: choices
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
        let eventChoices = events.sorted { $0.startsAt < $1.startsAt }.map { event in
            DesktopCalendarPromptChoice(
                id: "event:\(event.eventId)",
                eventId: event.eventId,
                title: event.safeDisplayTitle()
            )
        }
        let choices = eventChoices + [
            DesktopCalendarPromptChoice(
                id: "without-calendar-context",
                eventId: nil,
                title: SystemAudioStatusLabels.calendarPromptRecordWithoutContextActionTitle
            )
        ]
        return DesktopCalendarPrompt(
            id: promptID(kind: .record, eventIDs: events.map(\.eventId)),
            kind: .record,
            eventId: nil,
            title: SystemAudioStatusLabels.calendarGenericMeetingTitle,
            message: SystemAudioStatusLabels.calendarOverlapPromptMessage,
            primaryActionTitle: SystemAudioStatusLabels.calendarPromptRecordWithoutContextActionTitle,
            accessibilityLabel: SystemAudioStatusLabels.calendarPromptAccessibilityLabel(
                title: SystemAudioStatusLabels.calendarGenericMeetingTitle,
                action: SystemAudioStatusLabels.calendarPromptRecordWithoutContextActionTitle
            ),
            choices: choices
        )
    }

    private static func promptID(kind: DesktopCalendarPromptKind, eventIDs: [String]) -> String {
        "\(kind.rawValue):\(eventIDs.sorted().joined(separator: ","))"
    }

    private static func meetingDetectionHint(
        for events: [DesktopCalendarPromptEvent],
        kind: DesktopCalendarPromptKind,
        source: MeetingDetectionCalendarJoinIntentSource,
        dismissedPromptIDs: Set<String>
    ) -> MeetingDetectionCalendarJoinIntentHint? {
        guard events.count == 1,
              let event = events.first,
              !dismissedPromptIDs.contains(promptID(kind: kind, eventIDs: [event.eventId])),
              event.meetingLinkPresent,
              let url = event.openMeetingURL,
              let serviceFamily = BrowserMeetingServiceFamilyResolver.serviceFamily(for: url)
        else {
            return nil
        }
        return MeetingDetectionCalendarJoinIntentHint(
            serviceFamily: serviceFamily,
            source: source,
            matchingEventCount: 1
        )
    }
}
