import Foundation

#if canImport(WebKit) && canImport(XCTest)
import WebKit
import XCTest

@MainActor
final class CabinetSidebarRuntimeTests: XCTestCase {
    func testEmbeddedCompactProfileHasComputedFortyPointTargetAt720Width() async throws {
        let root = try repositoryRoot()
        let css = try String(
            contentsOf: root.appendingPathComponent(
                "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css"
            ),
            encoding: .utf8
        )
        let webView = WKWebView(frame: CGRect(x: 0, y: 0, width: 720, height: 720))

        try await load(
            """
            <!doctype html>
            <html data-cabinet-js="ready">
            <head><meta name="viewport" content="width=device-width, initial-scale=1"><style>\(css)</style></head>
            <body>
              <div class="app-shell desktop-embedded" data-cabinet-shell>
                <aside class="sidebar">
                  <nav class="cabinet-sidebar-nav"><a class="cabinet-sidebar-nav__item" href="#">Встречи</a></nav>
                  <div class="sidebar-foot">
                    <div class="sidebar-profile">
                      <button class="sidebar-profile__trigger" type="button"><span class="sidebar-profile__icon">●</span><span class="sidebar-profile__copy">Профиль</span></button>
                    </div>
                  </div>
                </aside>
                <main></main>
              </div>
            </body>
            </html>
            """,
            in: webView
        )

        let result = try await webView.evaluateJavaScript(
            """
            (() => {
              const foot = document.querySelector('.sidebar-foot');
              const trigger = document.querySelector('.sidebar-profile__trigger');
              const rect = trigger.getBoundingClientRect();
              const style = getComputedStyle(foot);
              return {
                display: style.display,
                visibility: style.visibility,
                opacity: Number(style.opacity),
                width: rect.width,
                height: rect.height,
                overflow: document.documentElement.scrollWidth - window.innerWidth
              };
            })()
            """
        )
        let metrics = try XCTUnwrap(result as? [String: Any])

        XCTAssertEqual(metrics["display"] as? String, "grid")
        XCTAssertEqual(metrics["visibility"] as? String, "visible")
        XCTAssertEqual(try number("opacity", in: metrics), 1, accuracy: 0.01)
        XCTAssertEqual(try number("width", in: metrics), 40, accuracy: 0.5)
        XCTAssertEqual(try number("height", in: metrics), 40, accuracy: 0.5)
        XCTAssertLessThanOrEqual(try number("overflow", in: metrics), 0.5)
    }

    func testProfileDisclosureRestoresFocusOnlyForEscape() async throws {
        let root = try repositoryRoot()
        let script = try String(
            contentsOf: root.appendingPathComponent(
                "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
            ),
            encoding: .utf8
        )
        let webView = WKWebView(frame: CGRect(x: 0, y: 0, width: 720, height: 720))

        try await load(
            """
            <!doctype html>
            <html><body>
              <div data-profile-menu-root>
                <button id="profile" data-profile-menu-trigger aria-expanded="false">Профиль</button>
                <div id="profile-menu" data-profile-menu hidden><a href="#settings">Настройки</a></div>
              </div>
              <button id="outside">Другая кнопка</button>
              <script>\(script)</script>
            </body></html>
            """,
            in: webView
        )

        let result = try await webView.evaluateJavaScript(
            """
            (() => {
              const trigger = document.querySelector('#profile');
              const menu = document.querySelector('#profile-menu');
              const outside = document.querySelector('#outside');
              trigger.click();
              outside.focus();
              outside.click();
              const pointerFocus = document.activeElement.id;
              const closedAfterPointer = menu.hidden;
              trigger.click();
              document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
              return {
                pointerFocus,
                closedAfterPointer,
                escapeFocus: document.activeElement.id,
                closedAfterEscape: menu.hidden
              };
            })()
            """
        )
        let state = try XCTUnwrap(result as? [String: Any])

        XCTAssertEqual(state["pointerFocus"] as? String, "outside")
        XCTAssertEqual(state["closedAfterPointer"] as? Bool, true)
        XCTAssertEqual(state["escapeFocus"] as? String, "profile")
        XCTAssertEqual(state["closedAfterEscape"] as? Bool, true)
    }

    private func load(_ html: String, in webView: WKWebView) async throws {
        let delegate = NavigationDelegate()
        let loaded = expectation(description: "WKWebView loaded synthetic cabinet")
        delegate.didFinish = { loaded.fulfill() }
        webView.navigationDelegate = delegate
        webView.loadHTMLString(html, baseURL: nil)
        await fulfillment(of: [loaded], timeout: 5)
    }

    private func number(_ key: String, in values: [String: Any]) throws -> Double {
        try XCTUnwrap(values[key] as? NSNumber).doubleValue
    }

    private func repositoryRoot() throws -> URL {
        var candidate = URL(fileURLWithPath: #filePath)
        while candidate.path != "/" {
            if FileManager.default.fileExists(
                atPath: candidate.appendingPathComponent("AGENTS.md").path
            ) {
                return candidate
            }
            candidate.deleteLastPathComponent()
        }
        throw CocoaError(.fileNoSuchFile)
    }
}

@MainActor
private final class NavigationDelegate: NSObject, WKNavigationDelegate {
    var didFinish: (() -> Void)?

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        didFinish?()
    }
}
#endif
