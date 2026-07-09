import Foundation

public enum ProductActivationEventName: String, Codable, CaseIterable, Sendable {
    case desktopFirstOpened = "desktop_first_opened"
    case desktopAccountConnected = "desktop_account_connected"
    case desktopAutorecordEnabled = "desktop_autorecord_enabled"
    case firstRecordingCompleted = "first_recording_completed"
    case firstResultViewed = "first_result_viewed"
    case firstValueSessionCompleted = "first_value_session_completed"

    public var allowedFields: Set<String> {
        let common: Set<String> = [
            "graf_attribution_id",
            "attribution_reliability",
            "bridge_present",
            "elapsed_bucket",
            "source_bucket"
        ]
        switch self {
        case .desktopFirstOpened:
            return common.union(["app_version_bucket", "platform", "install_channel"])
        case .desktopAccountConnected:
            return common.union(["auth_method_category", "account_connection_state"])
        case .desktopAutorecordEnabled:
            return common.union(["policy_state", "previous_state", "source", "surface"])
        case .firstRecordingCompleted:
            return common.union(["duration_bucket", "capture_mode", "completion_state", "result_pending_state"])
        case .firstResultViewed:
            return common.union(["result_state", "surface", "useful_output_present"])
        case .firstValueSessionCompleted:
            return common.union([
                "first_recording_completed",
                "first_result_viewed",
                "useful_output_present",
                "useful_result_type"
            ])
        }
    }
}

public enum ProductTelemetryGateState: String, Codable, CaseIterable, Sendable {
    case notSeen = "not_seen"
    case accepted
    case withdrawn
    case termsUpdateRequired = "terms_update_required"
    case refusedUpdatedTerms = "refused_updated_terms"
    case limitedToAccountLegalExportDeletion = "limited_to_account_legal_export_deletion"

    public var allowsNormalProductUse: Bool {
        self == .accepted
    }

    public var allowsProductAnalytics: Bool {
        self == .accepted
    }
}

public enum ProductActivationAnalyticsPayloadError: Error, Equatable, Sendable {
    case unsafeIdentity
    case forbiddenField(String)
    case fieldNotAllowlisted(String)
}

public struct ProductActivationAnalyticsPayload: Codable, Equatable, Sendable {
    public let eventName: ProductActivationEventName
    public let stablePseudonymousUserId: String?
    public let occurredAt: Date?
    public let telemetryGateState: ProductTelemetryGateState
    public let properties: [String: String]

    public init(
        eventName: ProductActivationEventName,
        stablePseudonymousUserId: String?,
        occurredAt: Date? = nil,
        telemetryGateState: ProductTelemetryGateState = .accepted,
        properties: [String: String] = [:]
    ) throws {
        if let stablePseudonymousUserId, !Self.isSafePseudonymousIdentity(stablePseudonymousUserId) {
            throw ProductActivationAnalyticsPayloadError.unsafeIdentity
        }
        for key in properties.keys.sorted() {
            if Self.isForbiddenField(key) {
                throw ProductActivationAnalyticsPayloadError.forbiddenField(key)
            }
            if !eventName.allowedFields.contains(key) {
                throw ProductActivationAnalyticsPayloadError.fieldNotAllowlisted(key)
            }
        }
        for value in properties.values {
            if Self.containsForbiddenValue(value) {
                throw ProductActivationAnalyticsPayloadError.forbiddenField("<value>")
            }
        }
        self.eventName = eventName
        self.stablePseudonymousUserId = stablePseudonymousUserId
        self.occurredAt = occurredAt
        self.telemetryGateState = telemetryGateState
        self.properties = properties
    }

    private enum CodingKeys: String, CodingKey {
        case eventName = "event_name"
        case stablePseudonymousUserId = "stable_pseudonymous_user_id"
        case occurredAt = "occurred_at"
        case telemetryGateState = "telemetry_gate_state"
        case properties
    }

    public static func isSafePseudonymousIdentity(_ value: String) -> Bool {
        value.hasPrefix("graf_pseudo_") && !value.contains("@") && !value.contains("/") && !value.contains("\\")
    }

    public static func isForbiddenField(_ key: String) -> Bool {
        let normalized = key.lowercased().replacingOccurrences(of: "-", with: "_")
        let exact: Set<String> = [
            "email",
            "phone",
            "full_name",
            "display_name",
            "company_name",
            "organization_name",
            "workspace_name",
            "account_name",
            "raw_user_id",
            "raw_account_id",
            "raw_workspace_id",
            "raw_meeting_id",
            "user_id",
            "account_id",
            "workspace_id",
            "meeting_id",
            "device_id",
            "device_name",
            "local_path",
            "object_key",
            "signed_url",
            "token",
            "api_key",
            "secret",
            "password",
            "passcode",
            "meeting_title",
            "participants",
            "calendar_text",
            "transcript",
            "summary_text",
            "raw_audio",
            "private_text"
        ]
        if exact.contains(normalized) {
            return true
        }
        return [
            "access_token",
            "refresh_token",
            "oauth_token",
            "api_key",
            "signed_url",
            "local_path",
            "object_key",
            "meeting_title",
            "calendar_text",
            "transcript",
            "raw_audio"
        ].contains { normalized.contains($0) }
    }

    public static func containsForbiddenValue(_ value: String) -> Bool {
        let normalized = value.lowercased()
        return normalized.contains("@") ||
            normalized.contains("/users/") ||
            normalized.contains("access_token") ||
            normalized.contains("secret") ||
            normalized.contains("password") ||
            normalized.contains("signed_url")
    }
}
