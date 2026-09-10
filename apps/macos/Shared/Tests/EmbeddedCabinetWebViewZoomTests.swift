import TwoBrainRecAppCore

#if canImport(WebKit) && canImport(XCTest)
import WebKit
import XCTest

@MainActor
final class EmbeddedCabinetWebViewZoomTests: XCTestCase {
    func testReplacementWebViewFillsContainerBeforeDeferredLayout() {
        let webView = WKWebView()
        let container = EmbeddedCabinetWebView.WebViewContainer(webView: webView)
        for size in [NSSize(width: 720, height: 640), NSSize(width: 840, height: 680)] {
            container.setFrameSize(size)
            XCTAssertEqual(webView.frame, container.bounds)
        }
    }

    func testApplyingWorkspaceZoomUpdatesPageZoomWithoutLoadingRoute() {
        let webView = WKWebView()

        EmbeddedCabinetWebView.EmbeddedCabinetZoomBridge.apply(
            WorkspaceZoomPreference(value: 1.2),
            to: webView
        )

        XCTAssertEqual(webView.pageZoom, 1.2, accuracy: 0.000_1)
        XCTAssertNil(webView.url)
    }
}
#endif
