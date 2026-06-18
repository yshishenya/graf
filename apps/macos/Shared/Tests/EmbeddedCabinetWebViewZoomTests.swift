import TwoBrainRecAppCore

#if canImport(WebKit) && canImport(XCTest)
import WebKit
import XCTest

@MainActor
final class EmbeddedCabinetWebViewZoomTests: XCTestCase {
    func testApplyingWorkspaceZoomUpdatesPageZoomWithoutLoadingRoute() {
        let webView = WKWebView()

        EmbeddedCabinetWebView.EmbeddedCabinetZoomBridge.apply(
            WorkspaceZoomPreference(value: 1.2),
            to: webView
        )

        XCTAssertEqual(webView.pageZoom, 1.2, accuracy: 0.000_1)
        XCTAssertNil(webView.url)
    }

    func testWebViewContainerPinsEmbeddedWebViewWithAutoLayout() {
        let webView = WKWebView()

        let container = EmbeddedCabinetWebView.WebViewContainer(webView: webView)

        XCTAssertFalse(webView.translatesAutoresizingMaskIntoConstraints)
        XCTAssertTrue(container.subviews.contains(webView))
        XCTAssertEqual(container.constraints.count, 4)
        XCTAssertTrue(container.constraints.allSatisfy { $0.isActive })
    }

    func testWebViewControllerOwnsContainerLifecycle() {
        let webView = WKWebView()

        let controller = EmbeddedCabinetWebView.WebViewController(webView: webView)

        XCTAssertTrue(controller.view is EmbeddedCabinetWebView.WebViewContainer)
        XCTAssertIdentical(controller.webView, webView)
    }
}
#endif
