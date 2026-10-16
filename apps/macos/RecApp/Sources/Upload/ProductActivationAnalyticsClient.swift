import Foundation
import TwoBrainRecShared

public struct ProductActivationAnalyticsClient: Sendable {
    public let baseURL: URL
    public let headers: [String: String]
    public let explicitFunnel: Bool

    public init?(rawBaseURL: String, headers: [String: String], explicitFunnel: Bool = false) {
        guard let url = URL(string: rawBaseURL),
              let scheme = url.scheme?.lowercased(),
              scheme == "http" || scheme == "https",
              let origin = URL(string: "\(scheme)://\(url.host ?? "")")
        else {
            return nil
        }
        self.baseURL = origin
        self.headers = headers
        self.explicitFunnel = explicitFunnel
    }

    public func eventURL() -> URL {
        baseURL.appendingPathComponent(explicitFunnel ? "api/v1/product-analytics/explicit-events" : "api/v1/product-analytics/events")
    }

    public func contextRequest() -> URLRequest {
        var request = URLRequest(url: baseURL.appendingPathComponent("api/v1/product-analytics/explicit-context"))
        for (key, value) in headers { request.setValue(value, forHTTPHeaderField: key) }
        return request
    }

    public func request(for payload: ProductActivationAnalyticsPayload) throws -> URLRequest {
        var request = URLRequest(url: eventURL())
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        for (key, value) in headers {
            request.setValue(value, forHTTPHeaderField: key)
        }
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        request.httpBody = try encoder.encode(payload)
        return request
    }

    public func directPostHogRequest(
        for payload: ProductActivationAnalyticsPayload,
        config: ProductAnalyticsDirectProviderConfig
    ) throws -> URLRequest? {
        guard config.allowsPostHogDirectRoute else {
            return nil
        }
        guard let endpoint = config.posthogCaptureEndpoint else {
            return nil
        }
        guard let distinctId = payload.stablePseudonymousUserId else {
            return nil
        }
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(config.posthogProjectKeyState, forHTTPHeaderField: "X-GRAF-PostHog-Project-Key-State")
        request.setValue("first_party_posthog_desktop_proxy", forHTTPHeaderField: "X-GRAF-Analytics-Route")
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        request.httpBody = try encoder.encode(PostHogDesktopCaptureEnvelope(payload: payload, distinctId: distinctId))
        return request
    }

    public static func directProviderEgressAllowed(
        legalApproved: Bool,
        securityApproved: Bool,
        qaApproved: Bool,
        telemetryAccepted: Bool,
        directEgressDisclosed: Bool
    ) -> Bool {
        legalApproved && securityApproved && qaApproved && telemetryAccepted && directEgressDisclosed
    }
}

public struct ProductActivationAnalyticsContext: Decodable, Sendable {
    public let enabled: Bool
    public let telemetryGateState: String
    public let stablePseudonymousUserId: String?
    public let csrfToken: String?

    enum CodingKeys: String, CodingKey {
        case enabled
        case telemetryGateState = "telemetry_gate_state"
        case stablePseudonymousUserId = "stable_pseudonymous_user_id"
        case csrfToken = "csrf_token"
    }
}

private struct PostHogDesktopCaptureEnvelope: Encodable {
    let event: String
    let distinctId: String
    let timestamp: Date?
    let properties: [String: String]
    let telemetryGateState: String
    let apiKeyState: String

    init(payload: ProductActivationAnalyticsPayload, distinctId: String) {
        event = payload.eventName.rawValue
        self.distinctId = distinctId
        timestamp = payload.occurredAt
        var mergedProperties = payload.properties
        mergedProperties["delivery_mode"] = "first_party_desktop_proxy"
        mergedProperties["source_feature"] = "096-product-analytics-provider-rollout"
        properties = mergedProperties
        telemetryGateState = payload.telemetryGateState.rawValue
        apiKeyState = "server_injected_redacted"
    }

    private enum CodingKeys: String, CodingKey {
        case event
        case distinctId = "distinct_id"
        case timestamp
        case properties
        case telemetryGateState = "telemetry_gate_state"
        case apiKeyState = "api_key_state"
    }
}
