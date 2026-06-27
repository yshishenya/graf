import Foundation

public enum CalendarEventTitleState: String, Codable, Sendable {
    case available
    case privateRedacted = "private_redacted"
    case freeBusyOnly = "free_busy_only"
    case policyHidden = "policy_hidden"
    case unknown

    public init(from decoder: Decoder) throws {
        let rawValue = try decoder.singleValueContainer().decode(String.self)
        self = Self(rawValue: rawValue) ?? .unknown
    }

    public var allowsTitleDisplay: Bool {
        self == .available
    }
}

public enum DesktopCalendarPromptState: String, Codable, Sendable {
    case notDue = "not_due"
    case shown
    case dismissed
    case opened
    case started
    case notAvailable = "not_available"
    case blockedByPolicy = "blocked_by_policy"
    case expired
    case unknown

    public init(from decoder: Decoder) throws {
        let rawValue = try decoder.singleValueContainer().decode(String.self)
        self = Self(rawValue: rawValue) ?? .unknown
    }

    public var canSurfacePrompt: Bool {
        self == .notDue || self == .shown
    }
}

public enum DesktopCalendarPromptKind: String, Codable, Sendable {
    case join
    case record
}

public struct DesktopCalendarPromptResponse: Codable, Equatable, Sendable {
    public var events: [DesktopCalendarPromptEvent]

    public init(events: [DesktopCalendarPromptEvent] = []) {
        self.events = events
    }
}

public struct DesktopCalendarPromptEvent: Codable, Equatable, Identifiable, Sendable {
    public var id: String { eventId }

    public var eventId: String
    public var providerFamily: String
    public var startsAt: Date
    public var endsAt: Date
    public var title: String?
    public var titleState: CalendarEventTitleState
    public var meetingLinkPresent: Bool
    public var attendeeCount: Int
    public var privacyClass: String
    public var joinPromptDueAt: Date?
    public var recordPromptDueAt: Date?
    public var joinPromptState: DesktopCalendarPromptState
    public var recordPromptState: DesktopCalendarPromptState
    public var openMeetingURL: URL?

    public init(
        eventId: String,
        providerFamily: String = "calendar",
        startsAt: Date,
        endsAt: Date,
        title: String? = nil,
        titleState: CalendarEventTitleState = .policyHidden,
        meetingLinkPresent: Bool = false,
        attendeeCount: Int = 0,
        privacyClass: String = "unknown",
        joinPromptDueAt: Date? = nil,
        recordPromptDueAt: Date? = nil,
        joinPromptState: DesktopCalendarPromptState = .notDue,
        recordPromptState: DesktopCalendarPromptState = .notDue,
        openMeetingURL: URL? = nil
    ) {
        self.eventId = eventId
        self.providerFamily = providerFamily
        self.startsAt = startsAt
        self.endsAt = endsAt
        self.title = title
        self.titleState = titleState
        self.meetingLinkPresent = meetingLinkPresent
        self.attendeeCount = attendeeCount
        self.privacyClass = privacyClass
        self.joinPromptDueAt = joinPromptDueAt
        self.recordPromptDueAt = recordPromptDueAt
        self.joinPromptState = joinPromptState
        self.recordPromptState = recordPromptState
        self.openMeetingURL = openMeetingURL
    }

    private enum CodingKeys: String, CodingKey {
        case eventId = "event_id"
        case providerFamily = "provider_family"
        case startsAt = "starts_at"
        case endsAt = "ends_at"
        case title
        case titleState = "title_state"
        case meetingLinkPresent = "meeting_link_present"
        case attendeeCount = "attendee_count"
        case privacyClass = "privacy_class"
        case joinPromptDueAt = "join_prompt_due_at"
        case recordPromptDueAt = "record_prompt_due_at"
        case joinPromptState = "join_prompt_state"
        case recordPromptState = "record_prompt_state"
        case openMeetingURL = "open_meeting_url"
    }

    public func safeDisplayTitle(genericTitle: String = SystemAudioStatusLabels.calendarGenericMeetingTitle) -> String {
        guard titleState.allowsTitleDisplay,
              let candidate = title?.trimmingCharacters(in: .whitespacesAndNewlines),
              !candidate.isEmpty,
              Self.isSafePromptTitle(candidate)
        else {
            return genericTitle
        }
        return candidate
    }

    public func overlaps(_ date: Date) -> Bool {
        startsAt <= date && date < endsAt
    }

    public static func isSafePromptTitle(_ title: String) -> Bool {
        let normalized = title.lowercased()
        let unsafeFragments = [
            "@",
            "http://",
            "https://",
            "zoom.us/",
            "meet.google.com/",
            "teams.microsoft.com/",
            "passcode",
            "password",
            "парол",
            "код доступа"
        ]
        return !unsafeFragments.contains { normalized.contains($0) }
    }
}

public struct DesktopCalendarPrompt: Equatable, Identifiable, Sendable {
    public var id: String
    public var kind: DesktopCalendarPromptKind
    public var eventId: String?
    public var title: String
    public var message: String
    public var primaryActionTitle: String
    public var dismissActionTitle: String
    public var accessibilityLabel: String
    public var openMeetingURL: URL?

    public init(
        id: String,
        kind: DesktopCalendarPromptKind,
        eventId: String?,
        title: String,
        message: String,
        primaryActionTitle: String,
        dismissActionTitle: String = SystemAudioStatusLabels.calendarPromptDismissActionTitle,
        accessibilityLabel: String,
        openMeetingURL: URL? = nil
    ) {
        self.id = id
        self.kind = kind
        self.eventId = eventId
        self.title = title
        self.message = message
        self.primaryActionTitle = primaryActionTitle
        self.dismissActionTitle = dismissActionTitle
        self.accessibilityLabel = accessibilityLabel
        self.openMeetingURL = openMeetingURL
    }
}
