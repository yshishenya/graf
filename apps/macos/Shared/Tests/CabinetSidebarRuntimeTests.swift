import Foundation

#if canImport(WebKit) && canImport(XCTest)
import WebKit
import XCTest

@MainActor
final class CabinetSidebarRuntimeTests: XCTestCase {
    // WebKit may deliver callbacks after XCTest has released a test instance.
    // Keep the synthetic browser objects alive for the whole test process so
    // one test's teardown cannot race the next test's WebKit startup.
    private var testWebViews: [WKWebView] = []
    private var teardownRegistered = false
    private static var retainedNavigationDelegates: [NavigationDelegate] = []

    func testRailUsesInitialBreakpointAndKeepsManualChoiceAfterWindowResize() async throws {
        let root = try repositoryRoot()
        let script = try String(
            contentsOf: root.appendingPathComponent(
                "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
            ),
            encoding: .utf8
        )
        let webView = makeWebView(frame: CGRect(x: 0, y: 0, width: 1200, height: 844))
        let origin = try XCTUnwrap(URL(string: "https://rail-breakpoint.graf.test/meetings"))

        try await load(
            """
            <!doctype html>
            <html><body>
              <div class="app-shell" data-cabinet-shell>
                <aside class="sidebar" data-cabinet-navigation>
                  <button data-cabinet-rail-toggle aria-expanded="false">Панель</button>
                </aside>
                <main></main>
              </div>
              <script>\(script)</script>
            </body></html>
            """,
            in: webView,
            baseURL: origin
        )

        func railState() async throws -> [String: Any] {
            let result = try await webView.evaluateJavaScript(
                """
                (() => {
                  const shell = document.querySelector('[data-cabinet-shell]');
                  const toggle = document.querySelector('[data-cabinet-rail-toggle]');
                  return {
                    pinned: shell.classList.contains('is-rail-pinned'),
                    expanded: toggle.getAttribute('aria-expanded'),
                    viewportWidth: window.innerWidth
                  };
                })()
                """
            )
            return try XCTUnwrap(result as? [String: Any])
        }

        let wide = try await railState()
        XCTAssertEqual(wide["pinned"] as? Bool, true)
        XCTAssertEqual(wide["expanded"] as? String, "true")

        webView.frame = CGRect(x: 0, y: 0, width: 390, height: 844)
        try await Task.sleep(for: .milliseconds(100))
        let autoCompact = try await railState()
        XCTAssertEqual(try number("viewportWidth", in: autoCompact), 390, accuracy: 0.5)
        XCTAssertEqual(autoCompact["pinned"] as? Bool, false)

        webView.frame = CGRect(x: 0, y: 0, width: 1200, height: 844)
        try await Task.sleep(for: .milliseconds(100))
        let autoWide = try await railState()
        XCTAssertEqual(autoWide["pinned"] as? Bool, true)

        _ = try await webView.evaluateJavaScript(
            "document.querySelector('[data-cabinet-rail-toggle]').click()"
        )
        let manuallyCollapsed = try await railState()
        XCTAssertEqual(manuallyCollapsed["pinned"] as? Bool, false)
        XCTAssertEqual(manuallyCollapsed["expanded"] as? String, "false")

        webView.frame = CGRect(x: 0, y: 0, width: 390, height: 844)
        try await Task.sleep(for: .milliseconds(100))
        let compact = try await railState()
        XCTAssertEqual(try number("viewportWidth", in: compact), 390, accuracy: 0.5)
        XCTAssertEqual(compact["pinned"] as? Bool, false)
        XCTAssertEqual(compact["expanded"] as? String, "false")

        webView.frame = CGRect(x: 0, y: 0, width: 1200, height: 844)
        try await Task.sleep(for: .milliseconds(100))
        let wideAgain = try await railState()
        XCTAssertEqual(wideAgain["pinned"] as? Bool, false)
        XCTAssertEqual(wideAgain["expanded"] as? String, "false")

        let compactWebView = makeWebView(frame: CGRect(x: 0, y: 0, width: 390, height: 844))
        try await load(
            """
            <!doctype html>
            <html><body>
              <div class="app-shell" data-cabinet-shell>
                <aside class="sidebar" data-cabinet-navigation>
                  <button data-cabinet-rail-toggle aria-expanded="true">Панель</button>
                </aside>
                <main></main>
              </div>
              <script>\(script)</script>
            </body></html>
            """,
            in: compactWebView,
            baseURL: origin
        )
        let compactInitial = try await compactWebView.evaluateJavaScript(
            "document.querySelector('[data-cabinet-shell]').classList.contains('is-rail-pinned')"
        )
        XCTAssertEqual(compactInitial as? Bool, false)
    }

    func testRailKeepsManualChoiceAcrossSameSessionNavigation() async throws {
        let root = try repositoryRoot()
        let script = try String(
            contentsOf: root.appendingPathComponent(
                "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
            ),
            encoding: .utf8
        )
        let webView = makeWebView(frame: CGRect(x: 0, y: 0, width: 1200, height: 844))
        let page = """
            <!doctype html>
            <html><body>
              <div class="app-shell" data-cabinet-shell>
                <aside class="sidebar" data-cabinet-navigation>
                  <button data-cabinet-rail-toggle aria-expanded="false">Панель</button>
                </aside>
                <main></main>
              </div>
              <script>\(script)</script>
            </body></html>
            """
        let origin = try XCTUnwrap(URL(string: "https://graf.test"))

        try await load(page, in: webView, baseURL: origin.appendingPathComponent("meetings"))
        _ = try await webView.evaluateJavaScript(
            "document.querySelector('[data-cabinet-rail-toggle]').click()"
        )
        try await navigate(page, to: origin.appendingPathComponent("settings"), in: webView)
        var state = try await railState(in: webView)
        XCTAssertEqual(state["pinned"] as? Bool, false)
        XCTAssertEqual(state["stored"] as? String, "collapsed")

        _ = try await webView.evaluateJavaScript(
            "document.querySelector('[data-cabinet-rail-toggle]').click()"
        )
        try await navigate(page, to: origin.appendingPathComponent("archive"), in: webView)
        state = try await railState(in: webView)
        XCTAssertEqual(state["pinned"] as? Bool, true)
        XCTAssertEqual(state["stored"] as? String, "expanded")

        _ = try await webView.evaluateJavaScript(
            "document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))"
        )
        try await navigate(page, to: origin.appendingPathComponent("meetings"), in: webView)
        state = try await railState(in: webView)
        XCTAssertEqual(state["pinned"] as? Bool, false)
        XCTAssertEqual(state["stored"] as? String, "collapsed")
        _ = try await webView.evaluateJavaScript(
            "sessionStorage.removeItem('graf-cabinet-rail')"
        )
    }

    func testAccountLinkingPageAt390WidthKeepsReadingFocusAndActionsReachable() async throws {
        let root = try repositoryRoot()
        let css = try String(
            contentsOf: root.appendingPathComponent(
                "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css"
            ),
            encoding: .utf8
        )
        let webView = makeWebView(frame: CGRect(x: 0, y: 0, width: 390, height: 844))

        try await load(accountLinkingHTML(css: css), in: webView)

        let result = try await webView.evaluateJavaScript(
            """
            (() => {
              const documentRoot = document.documentElement;
              const main = document.querySelector('#cabinet-main');
              const content = document.querySelector('.settings-page__content');
              const comparison = document.querySelector('.account-linking-comparison');
              const details = document.querySelector('details.account-linking-details');
              const summary = details?.querySelector(':scope > summary');
              const primary = document.querySelector('[data-account-linking-primary]');
              const secondary = document.querySelector('[data-account-linking-secondary]');
              const mainRect = main.getBoundingClientRect();
              const ctaRects = [primary, secondary].map(element => element.getBoundingClientRect());

              summary.focus();
              const summaryFocusable = document.activeElement === summary;
              summary.click();
              primary.focus();
              const primaryFocusable = document.activeElement === primary;
              secondary.focus();
              const secondaryFocusable = document.activeElement === secondary;

              return {
                viewportWidth: window.innerWidth,
                documentOverflow: documentRoot.scrollWidth - documentRoot.clientWidth,
                mainOverflow: main.scrollWidth - main.clientWidth,
                contentOverflow: content.scrollWidth - content.clientWidth,
                headings: Array.from(main.querySelectorAll('h1, h2, h3'), heading => heading.textContent.trim()),
                detailsTag: details?.tagName,
                summaryTag: summary?.tagName,
                summaryFocusable,
                detailsOpen: details?.open,
                primaryFocusable,
                secondaryFocusable,
                ctaLabels: [primary, secondary].map(element => element.textContent.trim()),
                ctaHorizontalOverflow: Math.max(
                  0,
                  ...ctaRects.map(rect => mainRect.left - rect.left),
                  ...ctaRects.map(rect => rect.right - mainRect.right)
                ),
                comparisonColumns: getComputedStyle(comparison).gridTemplateColumns.split(' ').length
              };
            })()
            """
        )
        let metrics = try XCTUnwrap(result as? [String: Any])

        XCTAssertEqual(try number("viewportWidth", in: metrics), 390, accuracy: 0.5)
        XCTAssertLessThanOrEqual(try number("documentOverflow", in: metrics), 0.5)
        XCTAssertLessThanOrEqual(try number("mainOverflow", in: metrics), 0.5)
        XCTAssertLessThanOrEqual(try number("contentOverflow", in: metrics), 0.5)
        XCTAssertEqual(
            metrics["headings"] as? [String],
            [
                "Один профиль — все способы входа",
                "Что изменится",
                "Сейчас",
                "После подключения",
            ]
        )
        XCTAssertEqual(metrics["detailsTag"] as? String, "DETAILS")
        XCTAssertEqual(metrics["summaryTag"] as? String, "SUMMARY")
        XCTAssertEqual(metrics["summaryFocusable"] as? Bool, true)
        XCTAssertEqual(metrics["detailsOpen"] as? Bool, true)
        XCTAssertEqual(metrics["primaryFocusable"] as? Bool, true)
        XCTAssertEqual(metrics["secondaryFocusable"] as? Bool, true)
        XCTAssertEqual(
            metrics["ctaLabels"] as? [String],
            ["Подключить email", "Оставить профили раздельными"]
        )
        XCTAssertLessThanOrEqual(try number("ctaHorizontalOverflow", in: metrics), 0.5)
        XCTAssertEqual(try number("comparisonColumns", in: metrics), 1, accuracy: 0.01)
    }

    func testEmbeddedCompactProfileHasComputedFortyPointTargetAt720Width() async throws {
        let root = try repositoryRoot()
        let css = try String(
            contentsOf: root.appendingPathComponent(
                "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css"
            ),
            encoding: .utf8
        )
        let webView = makeWebView(frame: CGRect(x: 0, y: 0, width: 720, height: 720))

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

    func testProfileDisclosureConsumesFirstEscapeBeforeRail() async throws {
        let root = try repositoryRoot()
        let script = try String(
            contentsOf: root.appendingPathComponent(
                "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
            ),
            encoding: .utf8
        )
        let webView = makeWebView(frame: CGRect(x: 0, y: 0, width: 1200, height: 720))
        let origin = try XCTUnwrap(URL(string: "https://profile-menu.graf.test/settings"))

        try await load(
            """
            <!doctype html>
            <html><body>
              <div data-cabinet-shell>
                <aside data-cabinet-navigation>
                  <button id="rail" data-cabinet-rail-toggle aria-expanded="false">Панель</button>
                  <div data-profile-menu-root>
                    <button id="profile" data-profile-menu-trigger aria-expanded="false">Профиль</button>
                    <div id="profile-menu" data-profile-menu hidden><a href="#settings">Настройки</a></div>
                  </div>
                </aside>
                <main><button id="outside">Другая кнопка</button></main>
              </div>
              <script>\(script)</script>
            </body></html>
            """,
            in: webView,
            baseURL: origin
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
              const railPinnedAfterMenuEscape = document.querySelector('[data-cabinet-shell]').classList.contains('is-rail-pinned');
              document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
              return {
                pointerFocus,
                closedAfterPointer,
                escapeFocus: document.activeElement.id,
                closedAfterEscape: menu.hidden,
                railPinnedAfterMenuEscape,
                railPinnedAfterSecondEscape: document.querySelector('[data-cabinet-shell]').classList.contains('is-rail-pinned'),
                storedRailState: sessionStorage.getItem('graf-cabinet-rail')
              };
            })()
            """
        )
        let state = try XCTUnwrap(result as? [String: Any])

        XCTAssertEqual(state["pointerFocus"] as? String, "outside")
        XCTAssertEqual(state["closedAfterPointer"] as? Bool, true)
        XCTAssertEqual(state["escapeFocus"] as? String, "profile")
        XCTAssertEqual(state["closedAfterEscape"] as? Bool, true)
        XCTAssertEqual(state["railPinnedAfterMenuEscape"] as? Bool, true)
        XCTAssertEqual(state["railPinnedAfterSecondEscape"] as? Bool, false)
        XCTAssertEqual(state["storedRailState"] as? String, "collapsed")
    }

    private func railState(in webView: WKWebView) async throws -> [String: Any] {
        let result = try await webView.evaluateJavaScript(
            """
            (() => ({
              pinned: document.querySelector('[data-cabinet-shell]').classList.contains('is-rail-pinned'),
              stored: sessionStorage.getItem('graf-cabinet-rail') ?? ''
            }))()
            """
        )
        return try XCTUnwrap(result as? [String: Any])
    }

    private func makeWebView(frame: CGRect) -> WKWebView {
        if !teardownRegistered {
            teardownRegistered = true
            addTeardownBlock { @MainActor [weak self] in
                self?.releaseTestWebViews()
            }
        }
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let webView = WKWebView(frame: frame, configuration: configuration)
        testWebViews.append(webView)
        return webView
    }

    private func releaseTestWebViews() {
        for webView in testWebViews {
            webView.stopLoading()
            webView.navigationDelegate = nil
        }
        testWebViews.removeAll()
    }

    private func load(_ html: String, in webView: WKWebView, baseURL: URL? = nil) async throws {
        let delegate = NavigationDelegate()
        Self.retainedNavigationDelegates.append(delegate)
        let loaded = expectation(description: "WKWebView loaded synthetic cabinet")
        delegate.didFinish = { loaded.fulfill() }
        webView.navigationDelegate = delegate
        webView.loadHTMLString(html, baseURL: baseURL)
        // XCTest expectations are owned by the test instance.  The delegate
        // is retained for WebKit's late callbacks, so never retain this
        // per-load callback beyond the load that owns its expectation.
        defer { delegate.didFinish = nil }
        await fulfillment(of: [loaded], timeout: 5)
        try await waitUntilReady(in: webView)
    }

    private func navigate(_ html: String, to url: URL, in webView: WKWebView) async throws {
        let htmlJSON = try XCTUnwrap(
            String(
                data: try JSONSerialization.data(withJSONObject: [html]),
                encoding: .utf8
            )
        )
        let urlJSON = try XCTUnwrap(
            String(
                data: try JSONSerialization.data(withJSONObject: [url.absoluteString]),
                encoding: .utf8
            )
        )
        _ = try await webView.evaluateJavaScript(
            """
            (() => {
              const destination = \(urlJSON)[0];
              const documentHTML = \(htmlJSON)[0];
              history.replaceState({}, "", destination);
              document.open();
              document.write(documentHTML);
              document.close();
            })()
            """
        )
        try await waitUntilReady(in: webView)
    }

    private func waitUntilReady(in webView: WKWebView) async throws {
        for _ in 0..<50 {
            let ready = try await webView.evaluateJavaScript(
                "(() => { const shell = document.querySelector('[data-cabinet-shell]'); const navigation = shell?.querySelector('[data-cabinet-navigation]'); return document.readyState === 'complete' && (!navigation || shell?.dataset.railReady === 'true'); })()"
            ) as? Bool ?? false
            if ready { return }
            try await Task.sleep(for: .milliseconds(20))
        }
        throw NSError(domain: "CabinetSidebarRuntimeTests", code: 1, userInfo: [
            NSLocalizedDescriptionKey: "Cabinet rail did not finish initializing"
        ])
    }

    private func accountLinkingHTML(css: String) -> String {
        """
        <!doctype html>
        <html data-cabinet-js="ready">
        <head><meta name="viewport" content="width=device-width, initial-scale=1"><style>\(css)</style></head>
        <body>
          <div class="app-shell desktop-embedded" data-cabinet-shell>
            <aside class="sidebar">
              <button class="cabinet-rail-toggle" type="button" aria-label="Развернуть боковую панель">☰</button>
              <nav class="cabinet-sidebar-nav"><a class="cabinet-sidebar-nav__item" href="#cabinet-main"><span class="cabinet-sidebar-nav__label">Настройки</span></a></nav>
            </aside>
            <main id="cabinet-main" class="cabinet-main" tabindex="-1">
              <div class="cabinet-workspace settings-page account-linking-page">
                <div class="settings-page__content">
                  <header class="cabinet-topbar settings-page__topbar"><div class="page-title">
                    <h1>Один профиль — все способы входа</h1>
                    <p class="page-subtitle">Вы подтвердили доступ к обоим профилям.</p>
                  </div></header>
                  <section class="settings-section account-linking-summary" aria-labelledby="account-linking-result-title">
                    <div class="settings-section__heading"><div>
                      <h2 id="account-linking-result-title">Что изменится</h2>
                    </div></div>
                    <div class="account-linking-comparison">
                      <article class="account-linking-comparison__card"><h3>Сейчас</h3><div class="account-linking-provider-group"><strong>Текущий профиль</strong><ul><li>Яндекс</li></ul></div><div class="account-linking-provider-group"><strong>Другой профиль</strong><ul><li>Email</li></ul></div></article>
                      <article class="account-linking-comparison__card"><h3>После подключения</h3><p>Один основной профиль со всеми подтверждёнными способами входа:</p><ul><li>Яндекс</li><li>Email</li></ul></article>
                    </div>
                    <ul class="settings-list account-linking-results"><li class="settings-list-item"><div class="settings-list-item__content"><span class="settings-list-item__title">2 пространства останутся отдельными.</span><span class="settings-list-item__desc">Встречи, записи, файлы и результаты обработки сохранятся.</span></div></li></ul>
                    <p class="account-linking-alert account-linking-alert--warning" role="status">Все активные сессии завершатся, а доверие устройств будет отозвано.</p>
                    <details class="account-linking-details"><summary>Настройки, устройства и сессии</summary><div><p>Настройки основного профиля сохранятся.</p></div></details>
                  </section>
                  <div class="settings-actions account-linking-actions" aria-label="Действия с профилями">
                    <form><button class="button primary" data-account-linking-primary type="submit">Подключить email</button></form>
                    <form><button class="button quiet" data-account-linking-secondary type="submit">Оставить профили раздельными</button></form>
                  </div>
                </div>
              </div>
            </main>
          </div>
        </body>
        </html>
        """
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

    nonisolated func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        Task { @MainActor [weak self] in
            self?.didFinish?()
        }
    }
}
#endif
