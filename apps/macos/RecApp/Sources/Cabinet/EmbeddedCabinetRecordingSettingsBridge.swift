import Foundation
import WebKit
import TwoBrainRecShared

#if swift(<6.1)
typealias RecordingSettingsReply = (Any?, String?) -> Void
#else
typealias RecordingSettingsReply = @MainActor @Sendable (Any?, String?) -> Void
#endif

/// Only local automatic-recording preferences cross this boundary, never capture commands.
@MainActor
final class EmbeddedCabinetRecordingSettingsBridge: NSObject, @preconcurrency WKScriptMessageHandlerWithReply {
    static let handlerName = "grafRecordingSettings"

    struct Request: Decodable {
        let version: Int
        let nonce: String
        let action: String
        let targetID: String?
        let rule: AutomaticRecordingRule?
    }

    private let routePolicy: DesktopCabinetRoutePolicy
    private let store: MeetingDetectionSettingsStore
    private let targets: () throws -> [MeetingTargetRegistryTarget]
    private weak var webView: WKWebView?
    private var nonce: String?

    init(
        routePolicy: DesktopCabinetRoutePolicy,
        store: MeetingDetectionSettingsStore = MeetingDetectionSettingsStore(),
        targets: @escaping () throws -> [MeetingTargetRegistryTarget] = {
            try MeetingTargetRegistryStore(
                cacheURL: MeetingDetectionAppModule.targetRegistryCacheURL(),
                bundledRegistryURL: MeetingDetectionAppModule.bundledTargetRegistryURL
            ).resolve().document.targets
        }
    ) {
        self.routePolicy = routePolicy
        self.store = store
        self.targets = targets
        super.init()
        for name in [Notification.Name.twoBrainRecMeetingDetectionSettingsDidChange, .twoBrainRecMeetingTargetRegistryDidChange] {
            NotificationCenter.default.addObserver(self, selector: #selector(refresh), name: name, object: nil)
        }
    }

    deinit { NotificationCenter.default.removeObserver(self) }

    func activate(_ webView: WKWebView) {
        self.webView = webView
        let nonce = UUID().uuidString
        self.nonce = nonce
        webView.evaluateJavaScript("window.GRAFRecordingSettings?.connect('\(nonce)')", completionHandler: nil)
    }

    func invalidate() {
        nonce = nil
        webView = nil
    }

    @objc private func refresh() {
        guard let webView, nonce != nil, !webView.isLoading,
              Self.isSettingsURL(webView.url, policy: routePolicy) else { return }
        webView.evaluateJavaScript("window.GRAFRecordingSettings?.refresh()", completionHandler: nil)
    }

    static func isSettingsURL(_ url: URL?, policy: DesktopCabinetRoutePolicy) -> Bool {
        guard let url, url.query == nil,
              url.path == "/desktop/settings/recording" else { return false }
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
        case "read": break
        case "set":
            guard request.targetID != nil, request.rule != nil else { return nil }
            keys.formUnion(["targetID", "rule"])
        case "setAll":
            guard request.rule != nil else { return nil }
            keys.insert("rule")
        default: return nil
        }
        return Set(object.keys) == keys ? request : nil
    }

    func response(to request: Request) throws -> [String: Any] {
        let targets = try targets().filter(\.isVerifiedNativePromptTarget)
            .sorted { $0.displayName.localizedCaseInsensitiveCompare($1.displayName) == .orderedAscending }
        var settings = try store.load()
        var errorMessage: String?
        if request.action != "read" {
            guard let rule = request.rule,
                  request.action == "setAll" || targets.contains(where: { $0.id == request.targetID }) else {
                throw CocoaError(.validationMissingMandatoryProperty)
            }
            do {
                settings = try store.update { draft in
                    for target in targets where request.action == "setAll" || target.id == request.targetID {
                        draft.setRecordingRule(rule, for: target.id)
                    }
                }
                NotificationCenter.default.post(name: .twoBrainRecMeetingDetectionSettingsDidChange, object: nil)
            } catch {
                settings = try store.load()
                errorMessage = "Не удалось сохранить настройки. Повторите попытку."
            }
        }
        var result: [String: Any] = [
            "version": 1,
            "targets": targets.map { ["id": $0.id, "name": $0.displayName, "rule": settings.recordingRule(for: $0.id).rawValue] }
        ]
        if let errorMessage { result["error"] = errorMessage }
        return result
    }

    func userContentController(
        _ userContentController: WKUserContentController,
        didReceive message: WKScriptMessage,
        replyHandler: @escaping RecordingSettingsReply
    ) {
        guard let webView, message.webView === webView,
              message.name == Self.handlerName,
              let request = Self.allowedRequest(
                message.body, sourceURL: message.frameInfo.documentRequestURL, currentURL: webView.url,
                isMainFrame: message.frameInfo.isMainFrame, isLoading: webView.isLoading,
                nonce: nonce, routePolicy: routePolicy
              ) else {
            replyHandler(nil, "Настройки недоступны на этой странице.")
            return
        }
        do {
            replyHandler(try response(to: request), nil)
        } catch {
            replyHandler(nil, "Не удалось загрузить настройки этого Mac. Откройте локальные настройки или повторите попытку.")
        }
    }
}
