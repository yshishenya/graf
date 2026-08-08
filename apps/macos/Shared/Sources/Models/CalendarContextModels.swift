import Foundation

public enum DesktopCalendarMatchDecisionIntent: String, Codable, Equatable, Sendable {
    case automatic
    case userSelected = "user_selected"
    case userDeclined = "user_declined"
    case unknown

    public init(from decoder: Decoder) throws {
        let rawValue = try decoder.singleValueContainer().decode(String.self)
        self = Self(rawValue: rawValue) ?? .unknown
    }
}

public enum DesktopCalendarMatchAttemptState: String, Codable, Equatable, Sendable {
    case matchedAuto = "matched_auto"
    case matchedUser = "matched_user"
    case provisionalPrestart = "provisional_prestart"
    case ambiguous
    case noContext = "no_context"
    case skippedPrivate = "skipped_private"
    case skippedAllDay = "skipped_all_day"
    case skippedStaleCalendar = "skipped_stale_calendar"
    case calendarUnavailable = "calendar_unavailable"
    case declinedByUser = "declined_by_user"
    case unknown

    public init(from decoder: Decoder) throws {
        let rawValue = try decoder.singleValueContainer().decode(String.self)
        self = Self(rawValue: rawValue) ?? .unknown
    }
}

public enum DesktopCalendarContextConfidence: String, Codable, Equatable, Sendable {
    case high
    case selected
    case ambiguous
    case none
    case unknown

    public init(from decoder: Decoder) throws {
        let rawValue = try decoder.singleValueContainer().decode(String.self)
        self = Self(rawValue: rawValue) ?? .unknown
    }
}

public struct DesktopCalendarContextResolveRequest: Encodable, Equatable, Sendable {
    public static let currentContractVersion = "calendar_auto_context_v1"

    public let recordingStartedAt: Date
    public let decisionIntent: DesktopCalendarMatchDecisionIntent
    public let eventId: String?
    public let contractVersion: String

    public init(
        recordingStartedAt: Date,
        decisionIntent: DesktopCalendarMatchDecisionIntent,
        eventId: String? = nil,
        contractVersion: String = "calendar_auto_context_v1"
    ) {
        self.recordingStartedAt = recordingStartedAt
        self.decisionIntent = decisionIntent
        self.eventId = decisionIntent == .userSelected ? eventId : nil
        self.contractVersion = contractVersion
    }

    private enum CodingKeys: String, CodingKey {
        case recordingStartedAt = "recording_started_at"
        case decisionIntent = "decision_intent"
        case eventId = "event_id"
        case contractVersion = "contract_version"
    }
}

public struct DesktopCalendarContextResolveResponse: Decodable, Equatable, Sendable {
    public let attemptId: String
    public let contextState: DesktopCalendarMatchAttemptState
    public let reasonCode: String
    public let contextConfidence: DesktopCalendarContextConfidence
    public let candidateCount: Int
    public let matcherVersion: String
    public let expiresAt: Date

    private enum CodingKeys: String, CodingKey {
        case attemptId = "attempt_id"
        case contextState = "context_state"
        case reasonCode = "reason_code"
        case contextConfidence = "context_confidence"
        case candidateCount = "candidate_count"
        case matcherVersion = "matcher_version"
        case expiresAt = "expires_at"
    }
}

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

public struct DesktopCalendarPromptChoice: Equatable, Identifiable, Sendable {
    public var id: String
    public var eventId: String?
    public var title: String
    public var openMeetingURL: URL?

    public init(
        id: String,
        eventId: String?,
        title: String,
        openMeetingURL: URL? = nil
    ) {
        self.id = id
        self.eventId = eventId
        self.title = title
        self.openMeetingURL = openMeetingURL
    }
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
            "meet.google.com",
            "teams.microsoft.com",
            "zoom.us/",
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
    public var choices: [DesktopCalendarPromptChoice]

    public var requiresExplicitCalendarChoice: Bool {
        choices.contains { $0.eventId != nil } &&
            choices.contains { $0.eventId == nil }
    }

    public init(
        id: String,
        kind: DesktopCalendarPromptKind,
        eventId: String?,
        title: String,
        message: String,
        primaryActionTitle: String,
        dismissActionTitle: String = SystemAudioStatusLabels.calendarPromptDismissActionTitle,
        accessibilityLabel: String,
        openMeetingURL: URL? = nil,
        choices: [DesktopCalendarPromptChoice] = []
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
        self.choices = choices
    }
}
