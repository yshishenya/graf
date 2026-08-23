import Foundation

public struct DesktopAuthSessionCookieReconciliation: Sendable {
    public let cookiesToDelete: [HTTPCookie]
    public let cookiesToSet: [HTTPCookie]
}

#if canImport(WebKit)
import WebKit

public enum DesktopCabinetSessionBridge {
    public static let authSessionCookieName = DesktopCabinetConfiguration.productionAuthSessionCookieName

    @MainActor
    public static func syncAuthSessionCookies(from webView: WKWebView) {
        guard let originURL = webView.url else { return }
        webView.configuration.websiteDataStore.httpCookieStore.getAllCookies { cookies in
            Task { @MainActor in
                let storage = HTTPCookieStorage.shared
                let plan = reconciliation(
                    webCookies: cookies,
                    nativeCookies: storage.cookies ?? [],
                    originURL: originURL
                )
                guard !plan.cookiesToDelete.isEmpty || !plan.cookiesToSet.isEmpty else { return }
                for cookie in plan.cookiesToDelete {
                    storage.deleteCookie(cookie)
                }
                for cookie in plan.cookiesToSet {
                    storage.setCookie(cookie)
                }
                NotificationCenter.default.post(name: .twoBrainRecDesktopAuthSessionDidChange, object: nil)
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
            .sorted { cookieFingerprint($0) < cookieFingerprint($1) }
        let nativeAuthCookies = nativeCookies
            .filter { DesktopUploadClient.authCookieScopeMatches($0, url: originURL) }
            .sorted { cookieFingerprint($0) < cookieFingerprint($1) }
        guard nativeAuthCookies.map(cookieFingerprint) != webAuthCookies.map(cookieFingerprint) else {
            return DesktopAuthSessionCookieReconciliation(cookiesToDelete: [], cookiesToSet: [])
        }
        return DesktopAuthSessionCookieReconciliation(
            cookiesToDelete: nativeAuthCookies,
            cookiesToSet: webAuthCookies
        )
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
