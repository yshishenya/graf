import Foundation

public enum DesktopCabinetBillingHandoff {
    public static let endpointPath = "/api/v1/cabinet/billing/handoff"
    public static let browserPath = "/billing/handoff"

    private struct Response: Decodable {
        let state: String
    }

    public static func request(
        for billingURL: URL,
        desktopHeaders: [String: String],
        requestExecutor: @escaping @Sendable (URLRequest) async throws -> (Data, URLResponse) = { request in
            try await URLSession.shared.data(for: request)
        }
    ) async -> URL? {
        guard let endpoint = endpointURL(for: billingURL),
              let sessionToken = sessionToken(for: billingURL, desktopHeaders: desktopHeaders)
        else { return nil }

        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.timeoutInterval = 10
        request.httpShouldHandleCookies = false
        request.setValue(sessionToken, forHTTPHeaderField: "X-Auth-Session")
        do {
            let (data, response) = try await requestExecutor(request)
            guard let httpResponse = response as? HTTPURLResponse,
                  (200..<300).contains(httpResponse.statusCode)
            else { return nil }
            let handoff = try JSONDecoder().decode(Response.self, from: data)
            let state = handoff.state.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !state.isEmpty,
                  var components = URLComponents(url: billingURL, resolvingAgainstBaseURL: false)
            else { return nil }
            components.user = nil
            components.password = nil
            components.path = browserPath
            components.queryItems = [URLQueryItem(name: "state", value: state)]
            components.fragment = nil
            return components.url
        } catch {
            return nil
        }
    }

    public static func endpointURL(for url: URL) -> URL? {
        guard let scheme = url.scheme?.lowercased(),
              ["http", "https"].contains(scheme),
              let host = url.host, !host.isEmpty
        else { return nil }
        var components = URLComponents()
        components.scheme = scheme
        components.host = host
        components.port = url.port
        components.path = endpointPath
        return components.url
    }

    public static func browserURL(for billingURL: URL, state: String) -> URL? {
        guard !state.isEmpty,
              var components = URLComponents(url: billingURL, resolvingAgainstBaseURL: false)
        else { return nil }
        components.user = nil
        components.password = nil
        components.path = browserPath
        components.queryItems = [URLQueryItem(name: "state", value: state)]
        components.fragment = nil
        return components.url
    }

    private static func sessionToken(for url: URL, desktopHeaders: [String: String]) -> String? {
        if let header = desktopHeaders.first(where: { $0.key.caseInsensitiveCompare("X-Auth-Session") == .orderedSame })?.value,
           !header.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            return header
        }
        return DesktopUploadClient.defaultAuthSessionToken(for: url)
    }
}
