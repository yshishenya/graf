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
}
#endif
