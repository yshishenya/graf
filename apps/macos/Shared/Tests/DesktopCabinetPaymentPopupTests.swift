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
    private let bank = URL(string: "https://3ds.bank.example.test/acs")!

    func testNewWindowFromBillingDocumentLoadsInTheSameWebView() async throws {
        let (view, recorder) = try await makeWebView(documentPath: "/billing/checkout")
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
        let loaded = await waitUntil { recorder.mainFrameRequests.contains(self.bank) }
        XCTAssertTrue(loaded, "адрес банка должен загрузиться в текущем представлении")
    }

    func testNewWindowOutsideBillingDocumentIsNotLoaded() async throws {
        let (view, recorder) = try await makeWebView(documentPath: "/")
        let coordinator = makeCoordinator(view: view)
        let action = try XCTUnwrap(recorder.popupAction)

        let created = coordinator.webView(
            view,
            createWebViewWith: view.configuration,
            for: action,
            windowFeatures: WKWindowFeatures()
        )

        XCTAssertNil(created)
        _ = await waitUntil(timeout: 1) { recorder.mainFrameRequests.contains(self.bank) }
        XCTAssertFalse(
            recorder.mainFrameRequests.contains(bank),
            "вне оплаты внешний адрес по-прежнему не загружается"
        )
    }

    private func makeWebView(documentPath: String) async throws -> (WKWebView, PopupRecorder) {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let view = WKWebView(frame: .zero, configuration: configuration)
        let recorder = PopupRecorder()
        view.navigationDelegate = recorder
        let documentURL = cabinet.appendingPathComponent(documentPath)
        view.loadHTMLString(
            "<a id='pay' href='\(bank.absoluteString)' target='_blank'>Оплатить</a>",
            baseURL: documentURL
        )
        let loaded = await waitUntil { recorder.documentFinished }
        XCTAssertTrue(loaded, "исходный документ должен загрузиться")
        _ = try await view.evaluateJavaScript("document.getElementById('pay').click(); true")
        let captured = await waitUntil { recorder.popupAction != nil }
        XCTAssertTrue(captured, "переход в новое окно должен быть запрошен")
        return (view, recorder)
    }

    private func makeCoordinator(view: WKWebView) -> EmbeddedCabinetWebView.Coordinator {
        let policy = DesktopCabinetRoutePolicy(baseURL: cabinet)
        return EmbeddedCabinetWebView.Coordinator(
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
            navigationController: EmbeddedCabinetNavigationController()
        )
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
