import SwiftUI

#if canImport(WebKit)
import AppKit
import WebKit

public struct EmbeddedCabinetWebView: NSViewRepresentable {
    public typealias NavigationEventLogger = @MainActor @Sendable (_ event: String, _ detail: String) -> Void

    private let request: URLRequest
    private let routePolicy: DesktopCabinetRoutePolicy
    private let workspaceZoom: WorkspaceZoomPreference
    private let navigationEventLogger: NavigationEventLogger?
    @Binding private var cabinetState: DesktopCabinetState
    @Binding private var currentRoute: URL?

    public init(
        request: URLRequest,
        routePolicy: DesktopCabinetRoutePolicy,
        cabinetState: Binding<DesktopCabinetState>,
        workspaceZoom: WorkspaceZoomPreference = .default,
        currentRoute: Binding<URL?> = .constant(nil),
        navigationEventLogger: NavigationEventLogger? = nil
    ) {
        self.request = request
        self.routePolicy = routePolicy
        self.workspaceZoom = workspaceZoom
        self.navigationEventLogger = navigationEventLogger
        _cabinetState = cabinetState
        _currentRoute = currentRoute
    }

    public nonisolated static func loadIdentity(for request: URLRequest) -> String {
        let method = request.httpMethod ?? "GET"
        let url = request.url?.absoluteString ?? ""
        return "\(method) \(url)"
    }

    public nonisolated static func loadIdentity(method: String = "GET", url: URL) -> String {
        "\(method) \(url.absoluteString)"
    }

    public nonisolated static func shouldLoad(request: URLRequest, lastLoadedRequestIdentity: String?) -> Bool {
        lastLoadedRequestIdentity != loadIdentity(for: request)
    }

    public nonisolated static func trackedRoute(current _: URL?, loaded: URL) -> URL {
        loaded
    }

    public nonisolated static func finishedState(for routeKind: DesktopCabinetRouteKind) -> DesktopCabinetState {
        switch routeKind {
        case .authLogin, .authSignup, .authProvider, .authCallback:
            return .expiredSession
        case .meetingList, .meetingDetail, .meetingDeletionReport, .calendarSettings:
            return .ready
        case .admin, .unsupported, .external, .forbiddenAction:
            return .blockedRoute
        }
    }

    public func makeNSView(context: Context) -> NSView {
        let configuration = WKWebViewConfiguration()
        configuration.allowsAirPlayForMediaPlayback = false
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.wantsLayer = true
        webView.layer?.backgroundColor = DesktopMeetingShellChrome.webEmbeddedBackgroundNSColor.cgColor
        webView.navigationDelegate = context.coordinator
        webView.allowsBackForwardNavigationGestures = true
        EmbeddedCabinetZoomBridge.apply(workspaceZoom, to: webView)
        let container = WebViewContainer(webView: webView)
        container.lastLoadedRequestIdentity = Self.loadIdentity(for: request)
        webView.load(request)
        return container
    }

    public func updateNSView(_ container: NSView, context _: Context) {
        guard let container = container as? WebViewContainer else { return }
        EmbeddedCabinetZoomBridge.apply(workspaceZoom, to: container.webView)
        guard Self.shouldLoad(request: request, lastLoadedRequestIdentity: container.lastLoadedRequestIdentity) else {
            return
        }
        container.lastLoadedRequestIdentity = Self.loadIdentity(for: request)
        container.webView.load(request)
    }

    public func makeCoordinator() -> Coordinator {
        Coordinator(
            routePolicy: routePolicy,
            desktopHeaders: request.allHTTPHeaderFields ?? [:],
            cabinetState: $cabinetState,
            currentRoute: $currentRoute,
            navigationEventLogger: navigationEventLogger
        )
    }

    public final class Coordinator: NSObject, WKNavigationDelegate {
        private let routePolicy: DesktopCabinetRoutePolicy
        private let navigationRequestPolicy: DesktopCabinetNavigationRequestPolicy
        private let navigationEventLogger: NavigationEventLogger?
        private var authContinuationActive = false
        @Binding private var cabinetState: DesktopCabinetState
        @Binding private var currentRoute: URL?

        init(
            routePolicy: DesktopCabinetRoutePolicy,
            desktopHeaders: [String: String],
            cabinetState: Binding<DesktopCabinetState>,
            currentRoute: Binding<URL?>,
            navigationEventLogger: NavigationEventLogger?
        ) {
            self.routePolicy = routePolicy
            navigationRequestPolicy = DesktopCabinetNavigationRequestPolicy(
                routePolicy: routePolicy,
                desktopHeaders: desktopHeaders
            )
            self.navigationEventLogger = navigationEventLogger
            _cabinetState = cabinetState
            _currentRoute = currentRoute
        }

        @MainActor
        public func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction,
            decisionHandler: @escaping @MainActor @Sendable (WKNavigationActionPolicy) -> Void
        ) {
            guard let url = navigationAction.request.url else {
                cabinetState = .malformedResponse
                decisionHandler(.cancel)
                return
            }
            if url.scheme?.lowercased() == "about" {
                decisionHandler(.allow)
                return
            }
            if navigationAction.targetFrame?.isMainFrame == false {
                decisionHandler(.allow)
                return
            }

            let decision = routePolicy.decision(
                for: url,
                allowExternalAuthProvider: authContinuationActive || isAuthRoute(webView.url)
            )
            switch decision.decision {
            case .allow:
                updateAuthContinuation(for: decision.route.kind)
                switch navigationRequestPolicy.decision(
                    forNavigationRequest: navigationAction.request,
                    isForMainFrame: navigationAction.targetFrame?.isMainFrame != false
                ) {
                case .allow:
                    break
                case let .reload(reloadedRequest):
                    cabinetState = .loading
                    webView.load(reloadedRequest)
                    decisionHandler(.cancel)
                    return
                }
                cabinetState = .loading
                decisionHandler(.allow)
            case .openExternally:
                authContinuationActive = false
                NSWorkspace.shared.open(url)
                decisionHandler(.cancel)
            case .blockWithMessage:
                authContinuationActive = false
                cabinetState = .blockedRoute
                decisionHandler(.cancel)
            }
        }

        @MainActor
        public func webView(_ webView: WKWebView, didFinish _: WKNavigation!) {
            guard let url = webView.url else {
                return
            }
            let routeDecision = routePolicy.decision(for: url, allowExternalAuthProvider: authContinuationActive)
            guard routeDecision.decision == .allow else {
                return
            }
            updateAuthContinuation(for: routeDecision.route.kind)
            let finishedState = EmbeddedCabinetWebView.finishedState(for: routeDecision.route.kind)
            DesktopCabinetSessionBridge.syncAuthSessionCookies(from: webView)
            if let container = webView.superview as? WebViewContainer {
                container.lastLoadedRequestIdentity = EmbeddedCabinetWebView.loadIdentity(url: url)
            }
            currentRoute = EmbeddedCabinetWebView.trackedRoute(current: currentRoute, loaded: url)
            cabinetState = finishedState
            logNavigationEvent(
                "cabinet_navigation_finished",
                detail: "state=\(finishedState.rawValue) \(urlLogDetail(url))"
            )
        }

        @MainActor
        public func webView(
            _: WKWebView,
            decidePolicyFor navigationResponse: WKNavigationResponse,
            decisionHandler: @escaping @MainActor @Sendable (WKNavigationResponsePolicy) -> Void
        ) {
            switch DesktopCabinetNavigationResponsePolicy().decision(
                forNavigationResponse: navigationResponse.response,
                isForMainFrame: navigationResponse.isForMainFrame
            ) {
            case .allow:
                decisionHandler(.allow)
            case let .cancel(state):
                cabinetState = state
                logNavigationEvent(
                    "cabinet_navigation_response_blocked",
                    detail: responseLogDetail(navigationResponse.response, state: state)
                )
                decisionHandler(.cancel)
            }
        }

        @MainActor
        public func webView(_ webView: WKWebView, didFail _: WKNavigation!, withError error: Error) {
            transitionAfterNavigationFailure(error, webViewURL: webView.url, phase: "committed")
        }

        @MainActor
        public func webView(_ webView: WKWebView, didFailProvisionalNavigation _: WKNavigation!, withError error: Error) {
            transitionAfterNavigationFailure(error, webViewURL: webView.url, phase: "provisional")
        }

        private func transitionAfterNavigationFailure(_ error: Error, webViewURL: URL?, phase: String) {
            let previousState = cabinetState
            let nextState = DesktopCabinetState.state(forNavigationError: error, currentState: cabinetState)
            cabinetState = nextState
            logNavigationEvent(
                "cabinet_navigation_failed",
                detail: errorLogDetail(error, webViewURL: webViewURL, phase: phase, from: previousState, to: nextState)
            )
        }

        private func logNavigationEvent(_ event: String, detail: String) {
            navigationEventLogger?(event, detail)
        }

        private func responseLogDetail(_ response: URLResponse, state: DesktopCabinetState) -> String {
            guard let httpResponse = response as? HTTPURLResponse else {
                return "state=\(state.rawValue) response=non_http"
            }
            return [
                "state=\(state.rawValue)",
                "status=\(httpResponse.statusCode)",
                urlLogDetail(httpResponse.url)
            ].joined(separator: " ")
        }

        private func errorLogDetail(
            _ error: Error,
            webViewURL: URL?,
            phase: String,
            from previousState: DesktopCabinetState,
            to nextState: DesktopCabinetState
        ) -> String {
            let nsError = error as NSError
            let failingURL = (nsError.userInfo[NSURLErrorFailingURLErrorKey] as? URL) ?? webViewURL
            return [
                "phase=\(phase)",
                "domain=\(sanitized(nsError.domain))",
                "code=\(nsError.code)",
                "from=\(previousState.rawValue)",
                "to=\(nextState.rawValue)",
                urlLogDetail(failingURL)
            ].joined(separator: " ")
        }

        private func urlLogDetail(_ url: URL?) -> String {
            guard let url else {
                return "scheme=none host=none routeKind=unknown"
            }
            let decision = routePolicy.decision(for: url)
            return [
                "scheme=\(sanitized(url.scheme ?? "none"))",
                "host=\(sanitized(url.host ?? "none"))",
                "routeKind=\(decision.route.kind.rawValue)"
            ].joined(separator: " ")
        }

        private func sanitized(_ value: String) -> String {
            value
                .replacingOccurrences(of: " ", with: "_")
                .replacingOccurrences(of: "\n", with: "_")
                .replacingOccurrences(of: "\r", with: "_")
        }

        private func isAuthRoute(_ url: URL?) -> Bool {
            guard let url else { return false }
            let decision = routePolicy.decision(for: url, allowExternalAuthProvider: authContinuationActive)
            return [
                .authLogin,
                .authSignup,
                .authProvider,
                .authCallback
            ].contains(decision.route.kind)
        }

        private func updateAuthContinuation(for routeKind: DesktopCabinetRouteKind) {
            authContinuationActive = [
                .authLogin,
                .authSignup,
                .authProvider,
                .authCallback
            ].contains(routeKind)
        }
    }

    public final class WebViewContainer: NSView {
        public let webView: WKWebView
        public var lastLoadedRequestIdentity: String?

        public init(webView: WKWebView) {
            self.webView = webView
            super.init(frame: .zero)
            wantsLayer = true
            layer?.backgroundColor = DesktopMeetingShellChrome.webEmbeddedBackgroundNSColor.cgColor
            addSubview(webView)
        }

        @available(*, unavailable)
        required init?(coder _: NSCoder) {
            nil
        }

        public override func layout() {
            super.layout()
            webView.frame = bounds
        }
    }

    public enum EmbeddedCabinetZoomBridge {
        @MainActor
        public static func apply(_ preference: WorkspaceZoomPreference, to webView: WKWebView) {
            webView.pageZoom = CGFloat(preference.value)
        }
    }
}
#else
public struct EmbeddedCabinetWebView: View {
    public typealias NavigationEventLogger = @MainActor @Sendable (_ event: String, _ detail: String) -> Void

    private let message: String

    public init(
        request _: URLRequest,
        routePolicy _: DesktopCabinetRoutePolicy,
        cabinetState _: Binding<DesktopCabinetState>,
        workspaceZoom _: WorkspaceZoomPreference = .default,
        currentRoute _: Binding<URL?> = .constant(nil),
        navigationEventLogger _: NavigationEventLogger? = nil
    ) {
        message = DesktopCabinetState.notConfigured.userMessage
    }

    public nonisolated static func loadIdentity(for request: URLRequest) -> String {
        let method = request.httpMethod ?? "GET"
        let url = request.url?.absoluteString ?? ""
        return "\(method) \(url)"
    }

    public nonisolated static func shouldLoad(request: URLRequest, lastLoadedRequestIdentity: String?) -> Bool {
        lastLoadedRequestIdentity != loadIdentity(for: request)
    }

    public nonisolated static func trackedRoute(current _: URL?, loaded: URL) -> URL {
        loaded
    }

    public nonisolated static func finishedState(for _: DesktopCabinetRouteKind) -> DesktopCabinetState {
        .notConfigured
    }

    public var body: some View {
        Text(message)
            .font(.caption)
            .foregroundStyle(.secondary)
    }
}
#endif
