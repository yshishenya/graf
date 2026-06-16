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

    public func makeNSView(context: Context) -> NSView {
        let configuration = WKWebViewConfiguration()
        configuration.allowsAirPlayForMediaPlayback = false
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = context.coordinator
        webView.allowsBackForwardNavigationGestures = true
        let container = WebViewContainer(webView: webView)
        webView.load(request)
        return container
    }

    public func updateNSView(_ container: NSView, context _: Context) {
        guard let webView = (container as? WebViewContainer)?.webView else { return }
        guard webView.url != request.url else { return }
        webView.load(request)
    }

    public func makeCoordinator() -> Coordinator {
        Coordinator(routePolicy: routePolicy, cabinetState: $cabinetState)
    }

    public final class Coordinator: NSObject, WKNavigationDelegate {
        private let routePolicy: DesktopCabinetRoutePolicy
        @Binding private var cabinetState: DesktopCabinetState

        init(routePolicy: DesktopCabinetRoutePolicy, cabinetState: Binding<DesktopCabinetState>) {
            self.routePolicy = routePolicy
            _cabinetState = cabinetState
        }

        @MainActor
        public func webView(
            _: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction,
            decisionHandler: @escaping @MainActor @Sendable (WKNavigationActionPolicy) -> Void
        ) {
            guard let url = navigationAction.request.url else {
                cabinetState = .malformedResponse
                decisionHandler(.cancel)
                return
            }

            let decision = routePolicy.decision(for: url)
            switch decision.decision {
            case .allow:
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

        public func webView(_: WKWebView, didFinish _: WKNavigation!) {
            cabinetState = .ready
        }

        public func webView(_: WKWebView, didFail _: WKNavigation!, withError _: Error) {
            cabinetState = .offline
        }

        public func webView(_: WKWebView, didFailProvisionalNavigation _: WKNavigation!, withError _: Error) {
            cabinetState = .offline
        }
    }

    public final class WebViewContainer: NSView {
        public let webView: WKWebView

        public init(webView: WKWebView) {
            self.webView = webView
            super.init(frame: .zero)
            wantsLayer = true
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

    public var body: some View {
        Text(message)
            .font(.caption)
            .foregroundStyle(.secondary)
    }
}
#endif
