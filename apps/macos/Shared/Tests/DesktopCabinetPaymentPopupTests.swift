import Foundation
import SwiftUI
@testable import TwoBrainRecAppCore
import WebKit
import XCTest

/// Оплата и подтверждение банка нередко открываются новым окном или ссылкой с
/// target="_blank". Отдельного окна у кабинета нет, поэтому такой переход должен
/// выполняться в текущем представлении — и только если адрес прошёл проверку
/// маршрута так же, как обычный переход.
@MainActor
final class DesktopCabinetPaymentPopupTests: XCTestCase {
    private let cabinet = URL(string: "https://rec.2brain.dev")!
    private let provider = URL(string: "https://yookassa.test/checkout/abc")!
    private let bank = URL(string: "https://3ds.bank.example.test/acs")!
    private let evil = URL(string: "https://evil.example/checkout")!

    func testProviderPopupFromBillingDocumentLoadsInTheSameWebView() async throws {
        let (view, recorder) = try await makeWebView(documentPath: "/billing/checkout", target: provider)
        let coordinator = makeCoordinator(view: view)
        let action = try XCTUnwrap(
            recorder.popupAction,
            "ссылка target=_blank должна запросить новое окно"
        )

        let created = coordinator.webView(
            view,
            createWebViewWith: view.configuration,
            for: action,
            windowFeatures: WKWindowFeatures()
        )

        XCTAssertNil(created, "отдельное окно кабинет не создаёт")
        let loaded = await waitUntil { view.url == self.provider }
        XCTAssertTrue(loaded, "страница провайдера должна загрузиться в текущем представлении")
        XCTAssertTrue(view.navigationDelegate === coordinator)
        XCTAssertTrue(view.uiDelegate === coordinator)
    }

    func testProviderPopupFailureClearsNavigationState() async throws {
        let (view, recorder) = try await makeWebView(documentPath: "/billing/checkout", target: provider)
        let navigation = EmbeddedCabinetNavigationController()
        let coordinator = makeCoordinator(view: view, navigation: navigation)
        let action = try XCTUnwrap(recorder.popupAction)

        XCTAssertNil(coordinator.webView(
            view,
            createWebViewWith: view.configuration,
            for: action,
            windowFeatures: WKWindowFeatures()
        ))
        let providerNavigation = try XCTUnwrap(view.requestedNavigations.last)
        coordinator.webView(
            view,
            didFailProvisionalNavigation: providerNavigation,
            withError: NSError(domain: NSURLErrorDomain, code: NSURLErrorCannotConnectToHost)
        )

        XCTAssertFalse(navigation.isLoading, "неудачный popup не должен оставлять контроллер в состоянии загрузки")
    }

    func testProviderPopupFinishClearsNavigationState() async throws {
        let (view, recorder) = try await makeWebView(documentPath: "/billing/checkout", target: provider)
        let navigation = EmbeddedCabinetNavigationController()
        let coordinator = makeCoordinator(view: view, navigation: navigation)
        let action = try XCTUnwrap(recorder.popupAction)

        XCTAssertNil(coordinator.webView(
            view,
            createWebViewWith: view.configuration,
            for: action,
            windowFeatures: WKWindowFeatures()
        ))
        let providerNavigation = try XCTUnwrap(view.requestedNavigations.last)
        coordinator.webView(view, didFinish: providerNavigation)

        XCTAssertFalse(navigation.isLoading, "завершившийся popup не должен оставлять контроллер в состоянии загрузки")
    }

    func testPopupWithNoWebKitNavigationClearsNavigationState() async throws {
        let (sourceView, recorder) = try await makeWebView(documentPath: "/billing/checkout", target: provider)
        let action = try XCTUnwrap(recorder.popupAction)
        let configuration = WKWebViewConfiguration()
        let view = NilLoadingPaymentWebView(frame: .zero, configuration: configuration)
        view.documentURL = cabinet.appendingPathComponent("/billing/checkout")
        let navigation = EmbeddedCabinetNavigationController()
        let coordinator = makeCoordinator(view: view, navigation: navigation)

        XCTAssertNil(coordinator.webView(
            view,
            createWebViewWith: sourceView.configuration,
            for: action,
            windowFeatures: WKWindowFeatures()
        ))
        XCTAssertFalse(navigation.isLoading, "nil от WKWebView.load не должен оставлять зависшую навигацию")
    }

    func testWebContentProcessTerminationClearsNavigationState() async throws {
        let (view, recorder) = try await makeWebView(documentPath: "/billing/checkout", target: provider)
        let navigation = EmbeddedCabinetNavigationController()
        let coordinator = makeCoordinator(view: view, navigation: navigation)
        let action = try XCTUnwrap(recorder.popupAction)

        XCTAssertNil(coordinator.webView(
            view,
            createWebViewWith: view.configuration,
            for: action,
            windowFeatures: WKWindowFeatures()
        ))
        coordinator.webViewWebContentProcessDidTerminate(view)

        XCTAssertFalse(navigation.isLoading, "после завершения процесса WebKit навигация должна быть закрыта")
    }

    func testDirectBankPopupFromBillingDocumentIsNotLoadedBeforeProviderHandoff() async throws {
        let (view, recorder) = try await makeWebView(documentPath: "/billing/checkout", target: bank)
        let coordinator = makeCoordinator(view: view)
        let action = try XCTUnwrap(recorder.popupAction)

        XCTAssertNil(
            coordinator.webView(
                view,
                createWebViewWith: view.configuration,
                for: action,
                windowFeatures: WKWindowFeatures()
            )
        )
        _ = await waitUntil(timeout: 1) { view.url == self.bank }
        XCTAssertFalse(view.url == bank)
        XCTAssertFalse(recorder.mainFrameRequests.contains(bank))
    }

    func testEvilPopupFromBillingDocumentIsNotLoaded() async throws {
        let (view, recorder) = try await makeWebView(documentPath: "/billing/checkout", target: evil)
        let coordinator = makeCoordinator(view: view)
        let action = try XCTUnwrap(recorder.popupAction)

        XCTAssertNil(
            coordinator.webView(
                view,
                createWebViewWith: view.configuration,
                for: action,
                windowFeatures: WKWindowFeatures()
            )
        )
        _ = await waitUntil(timeout: 1) { view.url == self.evil }
        XCTAssertFalse(view.url == evil)
        XCTAssertFalse(recorder.mainFrameRequests.contains(evil))
    }

    func testNewWindowOutsideBillingDocumentIsNotLoaded() async throws {
        let (view, recorder) = try await makeWebView(documentPath: "/", target: bank)
        let coordinator = makeCoordinator(view: view)
        let action = try XCTUnwrap(recorder.popupAction)

        XCTAssertNil(coordinator.webView(
            view,
            createWebViewWith: view.configuration,
            for: action,
            windowFeatures: WKWindowFeatures()
        ))
        _ = await waitUntil(timeout: 1) { view.url == self.bank }
        XCTAssertFalse(view.url == bank)
        XCTAssertFalse(recorder.mainFrameRequests.contains(bank))
    }

    private func makeWebView(documentPath: String, target: URL? = nil) async throws -> (TrackingPaymentWebView, PopupRecorder) {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let view = TrackingPaymentWebView(frame: .zero, configuration: configuration)
        let recorder = PopupRecorder()
        view.navigationDelegate = recorder
        let documentURL = cabinet.appendingPathComponent(documentPath)
        let target = target ?? bank
        view.loadHTMLString(
            "<a id='pay' href='\(target.absoluteString)' target='_blank'>Оплатить</a>",
            baseURL: documentURL
        )
        let loaded = await waitUntil { recorder.documentFinished }
        XCTAssertTrue(loaded, "исходный документ должен загрузиться")
        _ = try await view.evaluateJavaScript("document.getElementById('pay').click(); true")
        let captured = await waitUntil { recorder.popupAction != nil }
        XCTAssertTrue(captured, "переход в новое окно должен быть запрошен")
        return (view, recorder)
    }

    private func makeCoordinator(
        view: WKWebView,
        navigation: EmbeddedCabinetNavigationController = .init()
    ) -> EmbeddedCabinetWebView.Coordinator {
        let policy = DesktopCabinetRoutePolicy(baseURL: cabinet)
        let request = URLRequest(url: view.url ?? cabinet.appendingPathComponent("/billing/checkout"))
        navigation.attach(
            webView: view,
            routePolicy: policy,
            fallbackRequest: request,
            initialRequest: request,
            sessionExpired: false
        )
        let coordinator = EmbeddedCabinetWebView.Coordinator(
            routePolicy: policy,
            desktopHeaders: [:],
            cabinetState: .constant(.ready),
            currentRoute: .constant(view.url),
            navigationEventLogger: nil,
            showsAppUpdateBadge: false,
            onCheckForUpdates: {},
            onOpenMeetingDetectionSettings: {},
            supportIncidentBridge: nil,
            notificationPresenter: DesktopNotificationPresenter(
                store: .init(defaults: UserDefaults(suiteName: UUID().uuidString)!),
                model: DesktopControlModel(),
                status: { .denied }
            ),
            navigationController: navigation
        )
        view.navigationDelegate = coordinator
        view.uiDelegate = coordinator
        return coordinator
    }

    private func waitUntil(timeout: TimeInterval = 5, _ condition: () -> Bool) async -> Bool {
        let deadline = Date().addingTimeInterval(timeout)
        while Date() < deadline {
            if condition() { return true }
            try? await Task.sleep(nanoseconds: 50_000_000)
        }
        return condition()
    }
}

@MainActor
private final class PopupRecorder: NSObject, @preconcurrency WKNavigationDelegate {
    private(set) var popupAction: WKNavigationAction?
    private(set) var mainFrameRequests: [URL] = []
    private(set) var documentFinished = false

    func resetPopupAction() {
        popupAction = nil
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        documentFinished = true
    }

    func webView(
        _ webView: WKWebView,
        decidePolicyFor navigationAction: WKNavigationAction,
        decisionHandler: @escaping EmbeddedCabinetNavigationDecisionHandler
    ) {
        if navigationAction.targetFrame == nil {
            popupAction = navigationAction
            decisionHandler(.cancel)
            return
        }
        if let url = navigationAction.request.url {
            mainFrameRequests.append(url)
        }
        decisionHandler(.allow)
    }
}

@MainActor
private final class TrackingPaymentWebView: WKWebView {
    private(set) var requestedNavigations: [WKNavigation] = []

    override func load(_ request: URLRequest) -> WKNavigation? {
        let navigation = super.load(request)
        if let navigation {
            requestedNavigations.append(navigation)
        }
        return navigation
    }
}

@MainActor
private final class NilLoadingPaymentWebView: WKWebView {
    var documentURL: URL?

    override var url: URL? { documentURL }

    override func load(_: URLRequest) -> WKNavigation? { nil }
}
