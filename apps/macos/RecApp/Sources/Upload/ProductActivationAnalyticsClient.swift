import Foundation
import TwoBrainRecShared

public struct ProductActivationAnalyticsClient: Sendable {
    public let baseURL: URL
    public let headers: [String: String]

    public init?(rawBaseURL: String, headers: [String: String]) {
        guard let url = URL(string: rawBaseURL),
              let scheme = url.scheme?.lowercased(),
              scheme == "http" || scheme == "https",
              let origin = URL(string: "\(scheme)://\(url.host ?? "")")
        else {
            return nil
        }
        self.baseURL = origin
        self.headers = headers
    }

    public func eventURL() -> URL {
        baseURL.appendingPathComponent("api/v1/product-analytics/events")
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
