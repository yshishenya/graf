import Foundation

public struct DesktopAuthSessionCookieReconciliation: Sendable {
    public let cookiesToDelete: [HTTPCookie]
    public let cookiesToSet: [HTTPCookie]
    public let authenticationChanged: Bool
}

#if canImport(WebKit)
import WebKit

public enum DesktopCabinetSessionBridge {
    public static let authSessionCookieName = DesktopCabinetConfiguration.productionAuthSessionCookieName

    @MainActor static var generation: UInt64 = 0
    @MainActor private static var pendingRenewal: Task<Void, Never>?

    @MainActor
    static func renewAuthSessionCookies(
        request: URLRequest,
        response: URLResponse,
        expectedGeneration: UInt64,
        storage: HTTPCookieStorage = .shared,
        cookieStore: WKHTTPCookieStore = WKWebsiteDataStore.default().httpCookieStore
    ) async {
        guard let response = response as? HTTPURLResponse,
              let expiry = renewalExpiry(request: request, response: response),
              let origin = request.url,
              let token = request.value(forHTTPHeaderField: "X-Auth-Session") else { return }
        // Serialize native renewals across the asynchronous WebKit read/write boundary.
        let previous = pendingRenewal
        let task = Task { @MainActor in
            await previous?.value
            guard generation == expectedGeneration else { return }
            let webCookies = await cookieStore.allCookies()
            guard generation == expectedGeneration,
                  let pair = renewalCookies(webCookies: webCookies, nativeCookies: storage.cookies ?? [],
                                            originURL: origin, token: token, expiresAt: expiry) else { return }
            // No suspension between the current native-token check and submitting the WebKit write.
            if let web = pair.web { await cookieStore.setCookie(web) }
            guard generation == expectedGeneration,
                  DesktopUploadClient.authSessionToken(from: storage.cookies ?? [], origin) == token else { return }
            // Re-read WebKit before touching native state: logout/account changes remain authoritative.
            let currentWeb = await cookieStore.allCookies()
            guard generation == expectedGeneration,
                  let current = renewalCookies(webCookies: currentWeb, nativeCookies: storage.cookies ?? [],
                                               originURL: origin, token: token, expiresAt: expiry) else { return }
            if let native = current.native { storage.setCookie(native) }
        }
        pendingRenewal = task
        await task.value
    }

    @MainActor
    public static func syncAuthSessionCookies(
        from webView: WKWebView,
        isCurrentDocument: @escaping @MainActor () -> Bool = { true },
        completion: @escaping @MainActor () -> Void = {}
    ) {
        guard let originURL = webView.url else { return }
        webView.configuration.websiteDataStore.httpCookieStore.getAllCookies { cookies in
            Task { @MainActor in
                guard isCurrentDocument() else { return }
                let storage = HTTPCookieStorage.shared
                let plan = reconciliation(
                    webCookies: cookies,
                    nativeCookies: storage.cookies ?? [],
                    originURL: originURL
                )
                guard !plan.cookiesToDelete.isEmpty || !plan.cookiesToSet.isEmpty else {
                    completion()
                    return
                }
                if plan.authenticationChanged {
                    generation &+= 1
                    DesktopUserTimeContext.shared.reset()
                }
                for cookie in plan.cookiesToDelete {
                    storage.deleteCookie(cookie)
                }
                for cookie in plan.cookiesToSet {
                    storage.setCookie(cookie)
                }
                if plan.authenticationChanged {
                    NotificationCenter.default.post(name: .twoBrainRecDesktopAuthSessionDidChange, object: nil)
                }
                completion()
            }
        }
    }
}
#else
public enum DesktopCabinetSessionBridge {
    public static let authSessionCookieName = DesktopCabinetConfiguration.productionAuthSessionCookieName
}
#endif

public extension DesktopCabinetSessionBridge {
    static func reconciliation(
        webCookies: [HTTPCookie],
        nativeCookies: [HTTPCookie],
        originURL: URL,
        now: Date = Date()
    ) -> DesktopAuthSessionCookieReconciliation {
        let webAuthCookies = webCookies
            .filter { DesktopUploadClient.authCookieIsApplicable($0, to: originURL, now: now) }
            .map { web in
                // A WebKit observer snapshot can predate a completed native renewal.
                // Preserve the later deadline only for the identical existing session.
                guard let native = nativeCookies.first(where: { cookieIdentity($0) == cookieIdentity(web) }),
                      let expiry = native.expiresDate,
                      let extended = extendedCookie(web, expiresAt: expiry) else { return web }
                return extended
            }
            .sorted { cookieFingerprint($0) < cookieFingerprint($1) }
        let nativeAuthCookies = nativeCookies
            .filter { DesktopUploadClient.authCookieScopeMatches($0, url: originURL) }
            .sorted { cookieFingerprint($0) < cookieFingerprint($1) }
        guard nativeAuthCookies.map(cookieFingerprint) != webAuthCookies.map(cookieFingerprint) else {
            return DesktopAuthSessionCookieReconciliation(cookiesToDelete: [], cookiesToSet: [], authenticationChanged: false)
        }
        return DesktopAuthSessionCookieReconciliation(
            cookiesToDelete: nativeAuthCookies,
            cookiesToSet: webAuthCookies,
            authenticationChanged: nativeAuthCookies.map(cookieIdentity).sorted() != webAuthCookies.map(cookieIdentity).sorted()
        )
    }

    static func renewalExpiry(request: URLRequest, response: HTTPURLResponse, now: Date = Date()) -> Date? {
        guard (200..<300).contains(response.statusCode) || response.statusCode == 304,
              let origin = request.url, let destination = response.url,
              sameOrigin(origin, destination),
              let token = request.value(forHTTPHeaderField: "X-Auth-Session"), !token.isEmpty,
              let raw = response.value(forHTTPHeaderField: "X-GRAF-Auth-Expires-At"),
              !raw.isEmpty, raw.utf8.allSatisfy({ (48...57).contains($0) }),
              let seconds = Int64(raw) else { return nil }
        let expiry = Date(timeIntervalSince1970: TimeInterval(seconds))
        // Preserve configurable server TTLs within Foundation's representable cookie dates.
        guard expiry > now, expiry <= Date.distantFuture else { return nil }
        return expiry
    }

    static func renewalCookies(
        webCookies: [HTTPCookie], nativeCookies: [HTTPCookie], originURL: URL,
        token: String, expiresAt: Date, now: Date = Date()
    ) -> (web: HTTPCookie?, native: HTTPCookie?)? {
        guard expiresAt > now,
              DesktopUploadClient.authSessionToken(from: webCookies, originURL, now: now) == token,
              DesktopUploadClient.authSessionToken(from: nativeCookies, originURL, now: now) == token,
              let web = webCookies.first(where: { $0.value == token && DesktopUploadClient.authCookieIsApplicable($0, to: originURL, now: now) }),
              let native = nativeCookies.first(where: { $0.value == token && DesktopUploadClient.authCookieIsApplicable($0, to: originURL, now: now) }),
              cookieIdentity(web) == cookieIdentity(native) else { return nil }
        return (extendedCookie(web, expiresAt: expiresAt), extendedCookie(native, expiresAt: expiresAt))
    }

    private static func extendedCookie(_ cookie: HTTPCookie, expiresAt: Date) -> HTTPCookie? {
        guard let currentExpiry = cookie.expiresDate, expiresAt > currentExpiry,
              var properties = cookie.properties else { return nil }
        // Max-Age takes precedence over Expires in Foundation; do not retain the old deadline.
        properties.removeValue(forKey: .maximumAge)
        properties[.expires] = expiresAt
        return HTTPCookie(properties: properties)
    }

    private static func sameOrigin(_ lhs: URL, _ rhs: URL) -> Bool {
        guard let scheme = lhs.scheme?.lowercased(), ["http", "https"].contains(scheme),
              let host = lhs.host?.lowercased() else { return false }
        return scheme == rhs.scheme?.lowercased() && host == rhs.host?.lowercased()
            && (lhs.port ?? (scheme == "https" ? 443 : 80)) == (rhs.port ?? (scheme == "https" ? 443 : 80))
    }

    private static func cookieIdentity(_ cookie: HTTPCookie) -> String {
        [cookie.name, cookie.domain.lowercased(), cookie.path, cookie.isSecure ? "secure" : "insecure", cookie.value]
            .joined(separator: "\u{0}")
    }

    private static func cookieFingerprint(_ cookie: HTTPCookie) -> String {
        [
            cookie.name,
            cookie.domain.lowercased(),
            cookie.path,
            cookie.isSecure ? "secure" : "insecure",
            cookie.expiresDate.map { String(Int64($0.timeIntervalSince1970)) } ?? "session",
            cookie.value,
        ].joined(separator: "\u{0}")
    }
}

public extension Notification.Name {
    static let twoBrainRecDesktopAuthSessionDidChange = Notification.Name("pro.2brain.graf.desktopAuthSessionDidChange")
}
