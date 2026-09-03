import Foundation

#if canImport(WebKit) && canImport(XCTest)
import WebKit
import XCTest

@MainActor
final class CabinetBillingRuntimeTests: XCTestCase {
    func testBillingViewsReflowAcrossBrowserAndEmbeddedWidths() async throws {
        let css = try String(
            contentsOf: repositoryRoot().appendingPathComponent(
                "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css"
            ),
            encoding: .utf8
        )
        let sizes: [(width: CGFloat, height: CGFloat)] = [
            (390, 844), (768, 1024), (1024, 768), (1280, 720), (1440, 900),
            (731, 680), (987, 680), (971, 760), (1227, 760), (1131, 900), (1387, 900),
        ]

        for size in sizes {
            let webView = makeWebView(frame: CGRect(x: 0, y: 0, width: size.width, height: size.height))
            try await load(html(css: css), in: webView)
            let metrics = try await layoutMetrics(in: webView)

            XCTAssertEqual(try number("viewportWidth", in: metrics), Double(size.width), accuracy: 0.5)
            XCTAssertLessThanOrEqual(try number("documentOverflow", in: metrics), 0.5)
            XCTAssertLessThanOrEqual(try number("mainOverflow", in: metrics), 0.5)
            XCTAssertLessThanOrEqual(try number("contentOverflow", in: metrics), 0.5)
            XCTAssertLessThanOrEqual(try number("primaryOverflow", in: metrics), 0.5)
            XCTAssertGreaterThanOrEqual(try number("primaryMinHeight", in: metrics), 40)
            XCTAssertGreaterThanOrEqual(try number("planColumns", in: metrics), 1)
            XCTAssertEqual(metrics["primaryFocusable"] as? Bool, true)
        }

        for width: CGFloat in [390, 731] {
            let webView = makeWebView(frame: CGRect(x: 0, y: 0, width: width, height: 844))
            try await load(html(css: css), in: webView)
            webView.pageZoom = 2
            let metrics = try await layoutMetrics(in: webView)
            XCTAssertLessThanOrEqual(try number("documentOverflow", in: metrics), 0.5)
            XCTAssertLessThanOrEqual(try number("primaryOverflow", in: metrics), 0.5)
            XCTAssertGreaterThanOrEqual(
                try number("primaryMinHeight", in: metrics) * webView.pageZoom,
                40
            )
        }
    }

    private func layoutMetrics(in webView: WKWebView) async throws -> [String: Any] {
        let result = try await webView.evaluateJavaScript(
            """
            (() => {
              const root = document.documentElement;
              const main = document.querySelector('#cabinet-main');
              const content = document.querySelector('.billing-page__content');
              const primary = document.querySelector('[data-billing-primary]');
              const grid = document.querySelector('.billing-plan-grid');
              const mainRect = main.getBoundingClientRect();
              const primaryRect = primary.getBoundingClientRect();
              primary.focus();
              return {
                viewportWidth: window.innerWidth,
                documentOverflow: root.scrollWidth - root.clientWidth,
                mainOverflow: main.scrollWidth - main.clientWidth,
                contentOverflow: content.scrollWidth - content.clientWidth,
                primaryOverflow: Math.max(0, mainRect.left - primaryRect.left, primaryRect.right - mainRect.right),
                primaryMinHeight: Number.parseFloat(getComputedStyle(primary).minHeight),
                primaryFocusable: document.activeElement === primary,
                planColumns: getComputedStyle(grid).gridTemplateColumns.split(' ').filter(Boolean).length
              };
            })()
            """
        )
        return try XCTUnwrap(result as? [String: Any])
    }

    private func html(css: String) -> String {
        """
        <!doctype html>
        <html><head><meta name="viewport" content="width=device-width, initial-scale=1"><style>\(css)</style></head>
        <body><main id="cabinet-main" class="cabinet-main billing-page" tabindex="-1">
          <div class="cabinet-workspace settings-page"><div class="settings-page__content billing-page__content billing-page__content--wide">
            <header class="cabinet-topbar billing-page__header"><div class="page-title"><h1>Тарифы</h1></div></header>
            <nav class="billing-period-switch" aria-label="Период тарифа"><a href="#">Ежемесячно</a><a href="#" aria-current="true">Ежегодно</a></nav>
            <section class="billing-plan-grid" aria-label="Доступные тарифы">
              <article class="billing-plan-card is-current"><div class="billing-plan-card__heading"><h2>Free</h2></div><p class="billing-plan-card__price"><strong>0 ₽</strong><span>без оплаты</span></p><ul class="billing-feature-list"><li>300 минут в месяц</li><li>250 MB</li></ul></article>
              <article class="billing-plan-card"><div class="billing-plan-card__heading"><h2>Пробный</h2></div><p class="billing-plan-card__price"><strong>0 ₽</strong><span>7 дней</span></p><ul class="billing-feature-list"><li>Без лимита</li><li>2 GB</li></ul></article>
              <article class="billing-plan-card billing-plan-card--featured"><div class="billing-plan-card__heading"><h2>Личный</h2></div><p class="billing-plan-card__price"><strong>7 900 ₽</strong><span>в год</span></p><ul class="billing-feature-list"><li>Без лимита по минутам и встречам</li><li>2 GB</li></ul><div class="billing-plan-card__action"><a class="button" data-billing-primary href="#checkout">Выбрать «Личный»</a></div></article>
            </section>
            <section id="checkout" class="billing-checkout-card"><div class="billing-checkout-card__heading"><h2>Личный</h2><p class="billing-price"><strong>7 900 ₽</strong><span>в год</span></p></div><dl class="billing-order-summary"><div><dt>К оплате сегодня</dt><dd>7 900 ₽</dd></div></dl></section>
          </div></div>
        </main></body></html>
        """
    }

    private func makeWebView(frame: CGRect) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        return WKWebView(frame: frame, configuration: configuration)
    }

    private func load(_ html: String, in webView: WKWebView) async throws {
        let delegate = BillingNavigationDelegate()
        let loaded = expectation(description: "WKWebView loaded synthetic billing")
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
            if FileManager.default.fileExists(atPath: candidate.appendingPathComponent("AGENTS.md").path) {
                return candidate
            }
            candidate.deleteLastPathComponent()
        }
        throw CocoaError(.fileNoSuchFile)
    }
}

@MainActor
private final class BillingNavigationDelegate: NSObject, WKNavigationDelegate {
    var didFinish: (() -> Void)?

    nonisolated func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        Task { @MainActor [weak self] in
            self?.didFinish?()
        }
    }
}
#endif
