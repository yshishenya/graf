import Foundation

#if canImport(WebKit)
import WebKit

public enum DesktopCabinetSessionBridge {
    public static let authSessionCookieName = "__Host-twobrain_rec_owner_session"

    @MainActor
    public static func syncAuthSessionCookies(from webView: WKWebView) {
        webView.configuration.websiteDataStore.httpCookieStore.getAllCookies { cookies in
            let authCookies = cookies.filter { $0.name == authSessionCookieName }
            guard !authCookies.isEmpty else { return }
            for cookie in authCookies {
                HTTPCookieStorage.shared.setCookie(cookie)
            }
            NotificationCenter.default.post(name: .twoBrainRecDesktopAuthSessionDidChange, object: nil)
        }
    }
}
#else
public enum DesktopCabinetSessionBridge {
    public static let authSessionCookieName = "__Host-twobrain_rec_owner_session"
}
#endif

public extension Notification.Name {
    static let twoBrainRecDesktopAuthSessionDidChange = Notification.Name("pro.2brain.rec.desktopAuthSessionDidChange")
}
