import AppKit
import Combine
import Foundation
import WebKit

/// Account-scoped local preferences only. No identity or arbitrary URL crosses this boundary.
@MainActor
final class EmbeddedCabinetNotificationSettingsBridge: NSObject, @preconcurrency WKScriptMessageHandlerWithReply {
    static let handlerName = "grafNotificationSettings"
    enum Value: Decodable {
        case bool(Bool), minutes(Int)
        init(from decoder: Decoder) throws {
            let container = try decoder.singleValueContainer()
            if let bool = try? container.decode(Bool.self) { self = .bool(bool) }
            else { self = .minutes(try container.decode(Int.self)) }
        }
    }
    struct Request: Decodable {
        let version: Int
        let nonce: String
        let action: String
        let field: String?
        let value: Value?
    }
    private let routePolicy: DesktopCabinetRoutePolicy
    private let presenter: DesktopNotificationPresenter
    private weak var webView: WKWebView?
    private var nonce: String?
    private var epoch: Int?
    private var observations: [AnyCancellable] = []

    init(routePolicy: DesktopCabinetRoutePolicy, presenter: DesktopNotificationPresenter = .shared) {
        self.routePolicy = routePolicy; self.presenter = presenter
        super.init()
        observations.append(presenter.$authEpoch.dropFirst().sink { [weak self] _ in self?.invalidate() })
        observations.append(NotificationCenter.default.publisher(for: .twoBrainRecDesktopAuthSessionDidChange).sink { [weak self] _ in
            if Thread.isMainThread { MainActor.assumeIsolated { self?.invalidate() } }
            else { DispatchQueue.main.sync { MainActor.assumeIsolated { self?.invalidate() } } }
        })
        observations.append(presenter.$preferences.removeDuplicates().dropFirst().sink { [weak self] _ in
            // @Published fires before the preference is assigned.
            Task { @MainActor in self?.refresh() }
        })
    }
    func activateAfterRefreshingContext(_ webView: WKWebView, expectedAuthEpoch: Int, isCurrentDocument: () -> Bool) async {
        guard expectedAuthEpoch == presenter.authEpoch, isCurrentDocument(),
              let confirmedEpoch = await presenter.refreshContext(),
              confirmedEpoch == presenter.authEpoch, isCurrentDocument() else { return }
        activate(webView)
    }
    func activate(_ webView: WKWebView) {
        guard !webView.isLoading, Self.isSettingsURL(webView.url, policy: routePolicy) else { return }
        self.webView = webView; epoch = presenter.authEpoch
        let nonce = UUID().uuidString; self.nonce = nonce
        webView.evaluateJavaScript("window.GRAFNotificationSettings?.connect('\(nonce)')", completionHandler: nil)
    }
    func invalidate() {
        nonce = nil; epoch = nil
        webView?.evaluateJavaScript("window.GRAFNotificationSettings?.disconnect()", completionHandler: nil)
        webView = nil
    }
    private func refresh() {
        guard let webView, nonce != nil, !webView.isLoading,
              epoch == presenter.authEpoch, Self.isSettingsURL(webView.url, policy: routePolicy) else { return }
        webView.evaluateJavaScript("window.GRAFNotificationSettings?.refresh()", completionHandler: nil)
    }
    static func isSettingsURL(_ url: URL?, policy: DesktopCabinetRoutePolicy) -> Bool {
        guard let url, let parts = URLComponents(url: url, resolvingAgainstBaseURL: false),
              parts.query == nil, parts.fragment == nil,
              parts.percentEncodedPath == "/desktop/settings/notifications" else { return false }
        return policy.decision(for: url).decision == .allow
    }
    static func allowedRequest(
        _ body: Any, sourceURL: URL?, currentURL: URL?, isMainFrame: Bool,
        isLoading: Bool, nonce: String?, routePolicy: DesktopCabinetRoutePolicy
    ) -> Request? {
        guard let nonce, isMainFrame, !isLoading,
              isSettingsURL(sourceURL, policy: routePolicy), isSettingsURL(currentURL, policy: routePolicy),
              let object = body as? [String: Any],
              let data = try? JSONSerialization.data(withJSONObject: object),
              let request = try? JSONDecoder().decode(Request.self, from: data),
              request.version == 1, request.nonce == nonce else { return nil }
        var keys: Set<String> = ["version", "nonce", "action"]
        switch request.action {
        case "read", "requestPermission", "openSystemSettings", "test": break
        case "set":
            keys.formUnion(["field", "value"])
            switch (request.field, request.value) {
            case ("reminders", .bool), ("showTitles", .bool), ("sound", .bool): break
            case ("offsetMinutes", .minutes(let minutes)) where [0, 1, 5].contains(minutes): break
            default: return nil
            }
        default: return nil
        }
        return Set(object.keys) == keys ? request : nil
    }
    func response(to request: Request, epoch: Int, isCurrent: () -> Bool = { true }) async throws -> [String: Any] {
        guard epoch == presenter.authEpoch, isCurrent() else { throw CocoaError(.userCancelled) }
        var error: String?
        switch request.action {
        case "read": await presenter.refreshPermission()
        case "set":
            var value = presenter.preferences
            switch (request.field, request.value) {
            case ("reminders", .bool(let flag)): value.reminders = flag
            case ("showTitles", .bool(let flag)): value.showTitles = flag
            case ("sound", .bool(let flag)): value.sound = flag
            case ("offsetMinutes", .minutes(let minutes)) where [0, 1, 5].contains(minutes): value.offsetMinutes = minutes
            default: throw CocoaError(.validationMissingMandatoryProperty)
            }
            if !presenter.save(value) { error = presenter.message }
        case "requestPermission": await presenter.enable(isCurrent: isCurrent)
        case "test": await presenter.test(isCurrent: isCurrent)
        case "openSystemSettings":
            guard !presenter.owner.isEmpty else { throw CocoaError(.userCancelled) }
            NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.notifications")!)
        default: throw CocoaError(.validationMissingMandatoryProperty)
        }
        guard epoch == presenter.authEpoch, isCurrent() else { throw CocoaError(.userCancelled) }
        let value = presenter.preferences
        var result: [String: Any] = ["version": 1,
            "preferences": ["reminders": value.reminders, "offsetMinutes": value.offsetMinutes, "showTitles": value.showTitles, "sound": value.sound],
            "permission": presenter.permissionText, "canRequestPermission": presenter.canRequestPermission,
            "canEdit": !presenter.owner.isEmpty, "message": presenter.message]
        if let error { result["error"] = error }
        return result
    }
    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage, replyHandler: @escaping RecordingSettingsReply) {
        guard let webView, message.webView === webView, let epoch, epoch == presenter.authEpoch,
              message.name == Self.handlerName,
              let request = Self.allowedRequest(message.body, sourceURL: message.frameInfo.documentRequestURL,
                currentURL: webView.url, isMainFrame: message.frameInfo.isMainFrame, isLoading: webView.isLoading,
                nonce: nonce, routePolicy: routePolicy) else {
            replyHandler(nil, "Обновите страницу настроек после входа в GRAF."); return
        }
        Task { @MainActor [weak self, weak webView] in
            guard let self else { replyHandler(nil, "Настройки закрыты."); return }
            do {
                let result = try await self.response(to: request, epoch: epoch, isCurrent: {
                    guard let webView else { return false }
                    return self.webView === webView && !webView.isLoading && self.nonce == request.nonce
                        && Self.isSettingsURL(webView.url, policy: self.routePolicy)
                })
                replyHandler(result, nil)
            } catch { replyHandler(nil, "Не удалось подтвердить изменение. Обновите страницу настроек.") }
        }
    }
}
