import AppKit
import Foundation
import WebKit

/// Reports only the current surface's foreground state; never sends analytics or content.
@MainActor
final class EmbeddedCabinetResultVisibilityBridge: NSObject, @preconcurrency WKScriptMessageHandlerWithReply {
    static let handlerName = "grafResultVisibility"
    private let routePolicy: DesktopCabinetRoutePolicy
    private weak var webView: WKWebView?
    private var nonce: String?
    private var generation: UInt64?
    private var isCurrentDocument: @MainActor () -> Bool = { false }

    init(routePolicy: DesktopCabinetRoutePolicy) {
        self.routePolicy = routePolicy
        super.init()
        NotificationCenter.default.addObserver(self, selector: #selector(invalidate), name: .twoBrainRecDesktopAuthSessionDidChange, object: nil)
        for name in [NSApplication.didBecomeActiveNotification, NSApplication.didResignActiveNotification,
                     NSWindow.didMiniaturizeNotification, NSWindow.didDeminiaturizeNotification,
                     NSWindow.didChangeOcclusionStateNotification, NSWindow.didBecomeKeyNotification,
                     NSWindow.didResignKeyNotification] {
            NotificationCenter.default.addObserver(self, selector: #selector(refresh), name: name, object: nil)
        }
    }

    deinit { NotificationCenter.default.removeObserver(self) }

    func activate(_ webView: WKWebView, isCurrentDocument: @escaping @MainActor () -> Bool) {
        let generation = DesktopCabinetSessionBridge.generation
        guard isCurrentDocument(), DesktopCabinetSessionBridge.isCurrentSession(generation),
              !webView.isLoading, Self.isDetailURL(webView.url, policy: routePolicy) else { return }
        self.webView = webView; self.generation = generation; self.isCurrentDocument = isCurrentDocument
        let nonce = UUID().uuidString; self.nonce = nonce
        webView.evaluateJavaScript("window.GRAFResultVisibility?.connect('\(nonce)')", completionHandler: nil)
    }

    @objc func invalidate() {
        nonce = nil; generation = nil; isCurrentDocument = { false }
        webView?.evaluateJavaScript("window.GRAFResultVisibility?.disconnect()", completionHandler: nil)
        webView = nil
    }

    @objc private func refresh() {
        guard let webView, let generation, nonce != nil, isCurrentDocument(),
              DesktopCabinetSessionBridge.isCurrentSession(generation), !webView.isLoading,
              Self.isDetailURL(webView.url, policy: routePolicy) else { return }
        webView.evaluateJavaScript("window.GRAFResultVisibility?.refresh()", completionHandler: nil)
    }

    static func isDetailURL(_ url: URL?, policy: DesktopCabinetRoutePolicy) -> Bool {
        guard let url, let parts = URLComponents(url: url, resolvingAgainstBaseURL: false),
              let id = UUID(uuidString: String(parts.percentEncodedPath.split(separator: "/").last ?? "")),
              parts.percentEncodedPath == "/desktop/meetings/\(id.uuidString.lowercased())" else { return false }
        let decision = policy.decision(for: url)
        return decision.decision == .allow && decision.route.kind == .meetingDetail
    }

    static func allowedRequest(
        _ body: Any, sourceURL: URL?, currentURL: URL?, isMainFrame: Bool,
        isLoading: Bool, nonce: String?, routePolicy: DesktopCabinetRoutePolicy
    ) -> Bool {
        struct Request: Decodable { let version: Int; let nonce: String }
        guard let nonce, isMainFrame, !isLoading,
              isDetailURL(sourceURL, policy: routePolicy), isDetailURL(currentURL, policy: routePolicy),
              sourceURL?.path == currentURL?.path,
              let object = body as? [String: Any], Set(object.keys) == ["version", "nonce"],
              let value = object["nonce"] as? String, value == nonce,
              let data = try? JSONSerialization.data(withJSONObject: object),
              let request = try? JSONDecoder().decode(Request.self, from: data) else { return false }
        return request.version == 1 && request.nonce == nonce
    }

    static func foregroundReady(applicationActive: Bool, viewVisible: Bool, windowVisible: Bool,
                                miniaturized: Bool, occlusionVisible: Bool) -> Bool {
        applicationActive && viewVisible && windowVisible && !miniaturized && occlusionVisible
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage,
                               replyHandler: @escaping RecordingSettingsReply) {
        guard let webView, message.webView === webView, message.name == Self.handlerName,
              let generation, DesktopCabinetSessionBridge.isCurrentSession(generation), isCurrentDocument(),
              Self.allowedRequest(message.body, sourceURL: message.frameInfo.documentRequestURL, currentURL: webView.url,
                isMainFrame: message.frameInfo.isMainFrame, isLoading: webView.isLoading, nonce: nonce, routePolicy: routePolicy) else {
            replyHandler(nil, "unavailable"); return
        }
        let window = webView.window
        let ready = Self.foregroundReady(applicationActive: NSApplication.shared.isActive,
            viewVisible: webView.superview != nil && !webView.isHiddenOrHasHiddenAncestor,
            windowVisible: window?.isVisible == true, miniaturized: window?.isMiniaturized != false,
            occlusionVisible: window?.occlusionState.contains(.visible) == true)
        replyHandler(["version": 1, "ready": ready], nil)
    }
}
