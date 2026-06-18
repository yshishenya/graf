import SwiftUI

#if canImport(WebKit)
import AppKit
import WebKit

public struct EmbeddedCabinetWebView: NSViewRepresentable {
    private let request: URLRequest
    private let routePolicy: DesktopCabinetRoutePolicy
    @Binding private var cabinetState: DesktopCabinetState

    public init(
        request: URLRequest,
        routePolicy: DesktopCabinetRoutePolicy,
        cabinetState: Binding<DesktopCabinetState>
    ) {
        self.request = request
        self.routePolicy = routePolicy
        _cabinetState = cabinetState
    }

    public nonisolated static func loadIdentity(for request: URLRequest) -> String {
        let method = request.httpMethod ?? "GET"
        let url = request.url?.absoluteString ?? ""
        return "\(method) \(url)"
    }

    public nonisolated static func shouldLoad(request: URLRequest, lastLoadedRequestIdentity: String?) -> Bool {
        lastLoadedRequestIdentity != loadIdentity(for: request)
    }

    public func makeNSView(context: Context) -> NSView {
        let configuration = WKWebViewConfiguration()
        configuration.allowsAirPlayForMediaPlayback = false
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.wantsLayer = true
        webView.layer?.backgroundColor = DesktopMeetingShellChrome.webEmbeddedBackgroundNSColor.cgColor
        webView.navigationDelegate = context.coordinator
        webView.allowsBackForwardNavigationGestures = true
        let container = WebViewContainer(webView: webView)
        container.lastLoadedRequestIdentity = Self.loadIdentity(for: request)
        webView.load(request)
        return container
    }

    public func updateNSView(_ container: NSView, context _: Context) {
        guard let container = container as? WebViewContainer else { return }
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
            cabinetState: $cabinetState
        )
    }

    public final class Coordinator: NSObject, WKNavigationDelegate {
        private let routePolicy: DesktopCabinetRoutePolicy
        private let navigationRequestPolicy: DesktopCabinetNavigationRequestPolicy
        @Binding private var cabinetState: DesktopCabinetState

        init(
            routePolicy: DesktopCabinetRoutePolicy,
            desktopHeaders: [String: String],
            cabinetState: Binding<DesktopCabinetState>
        ) {
            self.routePolicy = routePolicy
            navigationRequestPolicy = DesktopCabinetNavigationRequestPolicy(
                routePolicy: routePolicy,
                desktopHeaders: desktopHeaders
            )
            _cabinetState = cabinetState
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

            let decision = routePolicy.decision(for: url)
            switch decision.decision {
            case .allow:
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
                NSWorkspace.shared.open(url)
                decisionHandler(.cancel)
            case .blockWithMessage:
                cabinetState = .blockedRoute
                decisionHandler(.cancel)
            }
        }

        public func webView(_ webView: WKWebView, didFinish _: WKNavigation!) {
            guard let url = webView.url,
                  routePolicy.decision(for: url).decision == .allow
            else {
                return
            }
            cabinetState = .ready
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
                decisionHandler(.cancel)
            }
        }

        public func webView(_: WKWebView, didFail _: WKNavigation!, withError error: Error) {
            cabinetState = DesktopCabinetState.state(forNavigationError: error, currentState: cabinetState)
        }

        public func webView(_: WKWebView, didFailProvisionalNavigation _: WKNavigation!, withError error: Error) {
            cabinetState = DesktopCabinetState.state(forNavigationError: error, currentState: cabinetState)
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
}
#else
public struct EmbeddedCabinetWebView: View {
    private let message: String

    public init(
        request _: URLRequest,
        routePolicy _: DesktopCabinetRoutePolicy,
        cabinetState _: Binding<DesktopCabinetState>
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

    public var body: some View {
        Text(message)
            .font(.caption)
            .foregroundStyle(.secondary)
    }
}
#endif
