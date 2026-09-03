import TwoBrainRecAppCore

#if canImport(WebKit) && canImport(XCTest)
import WebKit
import XCTest

@MainActor
final class EmbeddedCabinetWebViewZoomTests: XCTestCase {
    func testApplyingWorkspaceZoomUpdatesPageZoomWithoutLoadingRoute() {
        let configuration = WKWebViewConfiguration()
        configuration.processPool = CabinetRuntimeWebKitTestSupport.processPool
        let webView = WKWebView(frame: .zero, configuration: configuration)

        EmbeddedCabinetWebView.EmbeddedCabinetZoomBridge.apply(
            WorkspaceZoomPreference(value: 1.2),
            to: webView
        )

        XCTAssertEqual(webView.pageZoom, 1.2, accuracy: 0.000_1)
        XCTAssertNil(webView.url)
    }
}
#endif
