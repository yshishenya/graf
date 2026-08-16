import Foundation

#if canImport(WebKit)
import WebKit

public enum DesktopCabinetSessionBridge {
    public static let authSessionCookieName = DesktopCabinetConfiguration.productionAuthSessionCookieName

    @MainActor
    public static func syncAuthSessionCookies(from webView: WKWebView) {
        let originURL = webView.url
        webView.configuration.websiteDataStore.httpCookieStore.getAllCookies { cookies in
            let cookieName = originURL.map(DesktopCabinetConfiguration.authSessionCookieName(for:))
                ?? authSessionCookieName
            let authCookies = cookies.filter { $0.name == cookieName }
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
    public static let authSessionCookieName = DesktopCabinetConfiguration.productionAuthSessionCookieName
}
#endif

public extension Notification.Name {
    static let twoBrainRecDesktopAuthSessionDidChange = Notification.Name("pro.2brain.graf.desktopAuthSessionDidChange")
}
