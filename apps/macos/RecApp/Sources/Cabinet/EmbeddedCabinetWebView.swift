import Foundation
import SwiftUI

#if canImport(WebKit)
import AppKit
import WebKit

public enum EmbeddedCabinetUpdateBridge {
    public static let messageHandlerName = "grafAppUpdate"
    public static let checkForUpdatesAction = "checkForUpdates"

    public static let documentScript = """
    (() => {
      const button = document.querySelector('[data-graf-app-update]');
      if (!button || button.dataset.grafUpdateBridgeBound === 'true') return;
      button.dataset.grafUpdateBridgeBound = 'true';
      button.addEventListener('click', () => {
        window.webkit.messageHandlers.grafAppUpdate.postMessage('checkForUpdates');
      });
    })();
    """

    public static func visibilityScript(showsBadge: Bool) -> String {
        """
        (() => {
          const button = document.querySelector('[data-graf-app-update]');
          if (!button) return;
          button.hidden = \(showsBadge ? "false" : "true");
        })();
        """
    }

    public static func isAllowedMessageBody(_ body: Any) -> Bool {
        (body as? String) == checkForUpdatesAction
    }
}

@MainActor
public final class EmbeddedCabinetSupportIncidentBridge: DesktopSupportIncidentSubmitting {
    public static let intakePath = "/api/v1/desktop/support-incidents"
    public static let requestScript = """
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (!csrfToken) {
      return JSON.stringify([401, JSON.stringify({code: 'support_incident.auth_session_required'})]);
    }
    const headers = {
      'Accept': 'application/json',
      'X-CSRF-Token': csrfToken
    };
    if (request.hasBody) headers['Content-Type'] = 'application/json';
    if (request.idempotencyKey) headers['Idempotency-Key'] = request.idempotencyKey;
    try {
      const response = await fetch(request.path, {
        method: 'POST',
        credentials: "same-origin",
        headers,
        body: request.hasBody ? request.body : undefined
      });
      return JSON.stringify([response.status, await response.text()]);
    } catch (_error) {
      return JSON.stringify([503, JSON.stringify({code: 'support_incident.network_unavailable'})]);
    }
    """

    private weak var webView: WKWebView?
    private var routePolicy: DesktopCabinetRoutePolicy?

    public init() {}

    public func attach(webView: WKWebView, routePolicy: DesktopCabinetRoutePolicy) {
        self.webView = webView
        self.routePolicy = routePolicy
    }

    public func detach(webView: WKWebView) {
        guard self.webView === webView else { return }
        self.webView = nil
        routePolicy = nil
    }

    public func submitSupportIncident(
        report: DesktopSupportIncidentReport
    ) async throws -> DesktopSupportIncidentResponse {
        let body = String(decoding: try JSONEncoder().encode(report), as: UTF8.self)
        return try await execute(
            path: Self.intakePath,
            body: body,
            idempotencyKey: "support-incident:\(report.safeReportFingerprint)"
        )
    }

    public func syncSupportIncident(incidentID: String) async throws -> DesktopSupportIncidentResponse {
        guard incidentID.range(of: #"^CUST-[A-Z0-9-]{1,27}$"#, options: .regularExpression) != nil else {
            throw DesktopUploadClientError.httpStatus(400, "support_incident.invalid_correlation_number")
        }
        return try await execute(
            path: "\(Self.intakePath)/\(incidentID)/sync",
            body: nil,
            idempotencyKey: nil
        )
    }

    public nonisolated static func isAllowedCabinetDocument(
        _ url: URL,
        routePolicy: DesktopCabinetRoutePolicy
    ) -> Bool {
        let decision = routePolicy.decision(for: url)
        guard decision.decision == .allow else { return false }
        switch decision.route.kind {
        case .meetingList, .meetingDetail, .meetingShare, .meetingDeletionReport:
            return true
        case .artifactDownload, .calendarSettings, .meetingDetectionSettings, .admin, .authLogin, .authSignup,
             .authProvider, .authCallback, .unsupported, .external, .forbiddenAction:
            return false
        }
    }

    private func execute(
        path: String,
        body: String?,
        idempotencyKey: String?
    ) async throws -> DesktopSupportIncidentResponse {
        guard let webView,
              let routePolicy,
              let documentURL = webView.url,
              Self.isAllowedCabinetDocument(documentURL, routePolicy: routePolicy)
        else {
            throw DesktopUploadClientError.httpStatus(401, "support_incident.auth_session_required")
        }

        let request: [String: Any] = [
            "path": path,
            "body": body ?? "",
            "hasBody": body != nil,
            "idempotencyKey": idempotencyKey ?? ""
        ]
        let rawResult = try await evaluate(script: Self.requestScript, arguments: ["request": request], in: webView)
        let result = try Self.decodeJavaScriptResult(rawResult)
        guard let responseData = result.body.data(using: .utf8) else {
            throw DesktopUploadClientError.invalidResponse
        }
        guard (200..<300).contains(result.status) else {
            let problem = try? JSONDecoder().decode(ProblemCode.self, from: responseData)
            throw DesktopUploadClientError.httpStatus(
                result.status,
                problem?.code ?? "support_incident.unavailable"
            )
        }
        do {
            return try JSONDecoder().decode(DesktopSupportIncidentResponse.self, from: responseData)
        } catch {
            throw DesktopUploadClientError.invalidResponse
        }
    }

    private func evaluate(
        script: String,
        arguments: [String: Any],
        in webView: WKWebView
    ) async throws -> Any {
        do {
            guard let value = try await webView.callAsyncJavaScript(
                script,
                arguments: arguments,
                in: nil,
                contentWorld: .page
            ) else {
                throw DesktopUploadClientError.invalidResponse
            }
            return value
        } catch let error as DesktopUploadClientError {
            throw error
        } catch {
            throw DesktopUploadClientError.httpStatus(
                503,
                "support_incident.network_unavailable"
            )
        }
    }

    static func decodeJavaScriptResult(_ value: Any) throws -> JavaScriptResult {
        let data: Data
        if let rawResult = value as? String, let rawData = rawResult.data(using: .utf8) {
            data = rawData
        } else if JSONSerialization.isValidJSONObject(value) {
            do {
                data = try JSONSerialization.data(withJSONObject: value)
            } catch {
                throw DesktopUploadClientError.invalidResponse
            }
        } else {
            throw DesktopUploadClientError.invalidResponse
        }

        if let result = try? JSONDecoder().decode(JavaScriptResult.self, from: data) {
            return result
        }
        guard let pair = try? JSONSerialization.jsonObject(with: data) as? [Any],
              pair.count == 2
        else {
            throw DesktopUploadClientError.invalidResponse
        }
        let status: Int
        if let rawStatus = pair[0] as? Int {
            status = rawStatus
        } else if let rawStatus = pair[0] as? NSNumber {
            status = rawStatus.intValue
        } else {
            throw DesktopUploadClientError.invalidResponse
        }
        guard let body = pair[1] as? String else {
            throw DesktopUploadClientError.invalidResponse
        }
        return JavaScriptResult(status: status, body: body)
    }

    struct JavaScriptResult: Decodable, Equatable {
        let status: Int
        let body: String
    }

    private struct ProblemCode: Decodable {
        let code: String?
    }
}

public struct EmbeddedCabinetWebView: NSViewRepresentable {
    public typealias NavigationEventLogger = @MainActor @Sendable (_ event: String, _ detail: String) -> Void
    public typealias CheckForUpdatesAction = @MainActor @Sendable () -> Void

    private let request: URLRequest
    private let routePolicy: DesktopCabinetRoutePolicy
    private let workspaceZoom: WorkspaceZoomPreference
    private let navigationEventLogger: NavigationEventLogger?
    private let showsAppUpdateBadge: Bool
    private let onCheckForUpdates: CheckForUpdatesAction
    private let supportIncidentBridge: EmbeddedCabinetSupportIncidentBridge?
    @Binding private var cabinetState: DesktopCabinetState
    @Binding private var currentRoute: URL?

    public init(
        request: URLRequest,
        routePolicy: DesktopCabinetRoutePolicy,
        cabinetState: Binding<DesktopCabinetState>,
        workspaceZoom: WorkspaceZoomPreference = .default,
        currentRoute: Binding<URL?> = .constant(nil),
        navigationEventLogger: NavigationEventLogger? = nil,
        showsAppUpdateBadge: Bool = false,
        onCheckForUpdates: @escaping CheckForUpdatesAction = {},
        supportIncidentBridge: EmbeddedCabinetSupportIncidentBridge? = nil
    ) {
        self.request = request
        self.routePolicy = routePolicy
        self.workspaceZoom = workspaceZoom
        self.navigationEventLogger = navigationEventLogger
        self.showsAppUpdateBadge = showsAppUpdateBadge
        self.onCheckForUpdates = onCheckForUpdates
        self.supportIncidentBridge = supportIncidentBridge
        _cabinetState = cabinetState
        _currentRoute = currentRoute
    }

    public nonisolated static func loadIdentity(for request: URLRequest) -> String {
        let method = request.httpMethod ?? "GET"
        let url = request.url?.absoluteString ?? ""
        return "\(method) \(url)"
    }

    public nonisolated static func loadIdentity(method: String = "GET", url: URL) -> String {
        "\(method) \(url.absoluteString)"
    }

    public nonisolated static func shouldLoad(request: URLRequest, lastLoadedRequestIdentity: String?) -> Bool {
        lastLoadedRequestIdentity != loadIdentity(for: request)
    }

    public nonisolated static func trackedRoute(current _: URL?, loaded: URL) -> URL {
        loaded
    }

    public nonisolated static func allowsFilePicker(
        webViewURL: URL?,
        frameURL: URL?,
        frameIsMainFrame: Bool,
        routePolicy: DesktopCabinetRoutePolicy
    ) -> Bool {
        guard frameIsMainFrame, let webViewURL, let frameURL else {
            return false
        }
        guard sameOrigin(webViewURL, frameURL) else {
            return false
        }
        let webViewDecision = routePolicy.decision(for: webViewURL)
        let frameDecision = routePolicy.decision(for: frameURL)
        return webViewDecision.decision == .allow
            && frameDecision.decision == .allow
            && webViewDecision.route.kind == .meetingList
            && frameDecision.route.kind == .meetingList
    }

    public nonisolated static func allowsBlobDownload(
        requested: Bool,
        targetURL: URL?,
        sourceURL: URL?,
        sourceIsMainFrame: Bool,
        routePolicy: DesktopCabinetRoutePolicy
    ) -> Bool {
        guard requested,
              sourceIsMainFrame,
              targetURL?.scheme?.lowercased() == "blob",
              let sourceURL
        else {
            return false
        }
        let sourceDecision = routePolicy.decision(for: sourceURL)
        return sourceDecision.decision == .allow && sourceDecision.route.kind == .meetingDetail
    }

    public nonisolated static func allowsArtifactDownload(
        targetURL: URL?,
        sourceURL: URL?,
        sourceIsMainFrame: Bool,
        routePolicy: DesktopCabinetRoutePolicy
    ) -> Bool {
        guard sourceIsMainFrame, let targetURL, let sourceURL else { return false }
        let targetDecision = routePolicy.decision(for: targetURL)
        let sourceDecision = routePolicy.decision(for: sourceURL)
        guard targetDecision.decision == .allow,
              targetDecision.route.kind == .artifactDownload,
              sourceDecision.decision == .allow,
              sourceDecision.route.kind == .meetingDetail
        else {
            return false
        }
        return targetDecision.route.meetingId == sourceDecision.route.meetingId
    }

    public nonisolated static func safeDownloadFilename(_ suggestedFilename: String) -> String {
        let filename = (suggestedFilename as NSString).lastPathComponent
        return filename.isEmpty || filename == "." || filename == ".." || filename == "/"
            ? "GRAF export"
            : filename
    }

    public nonisolated static func nativeSaveDestination(
        response: NSApplication.ModalResponse,
        selectedURL: URL?
    ) -> URL? {
        response == .OK ? selectedURL : nil
    }

    private nonisolated static func sameOrigin(_ lhs: URL, _ rhs: URL) -> Bool {
        guard
            let leftScheme = lhs.scheme?.lowercased(),
            let rightScheme = rhs.scheme?.lowercased(),
            let leftHost = lhs.host?.lowercased(),
            let rightHost = rhs.host?.lowercased(),
            leftScheme == rightScheme,
            leftHost == rightHost
        else {
            return false
        }
        let leftPort = lhs.port ?? (leftScheme == "https" ? 443 : 80)
        let rightPort = rhs.port ?? (rightScheme == "https" ? 443 : 80)
        return leftPort == rightPort
    }

    public nonisolated static func finishedState(for routeKind: DesktopCabinetRouteKind) -> DesktopCabinetState {
        switch routeKind {
        case .authLogin, .authSignup, .authProvider, .authCallback:
            return .expiredSession
        case .meetingList, .meetingDetail, .meetingShare, .meetingDeletionReport, .calendarSettings, .meetingDetectionSettings:
            return .ready
        case .artifactDownload:
            return .ready
        case .admin, .unsupported, .external, .forbiddenAction:
            return .blockedRoute
        }
    }

    public func makeNSView(context: Context) -> NSView {
        let configuration = WKWebViewConfiguration()
        configuration.allowsAirPlayForMediaPlayback = false
        configuration.userContentController.addUserScript(
            WKUserScript(
                source: EmbeddedCabinetUpdateBridge.documentScript,
                injectionTime: .atDocumentEnd,
                forMainFrameOnly: true
            )
        )
        configuration.userContentController.add(
            context.coordinator,
            name: EmbeddedCabinetUpdateBridge.messageHandlerName
        )
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.wantsLayer = true
        webView.layer?.backgroundColor = DesktopMeetingShellChrome.webEmbeddedBackgroundNSColor.cgColor
        webView.navigationDelegate = context.coordinator
        webView.uiDelegate = context.coordinator
        webView.allowsBackForwardNavigationGestures = true
        EmbeddedCabinetZoomBridge.apply(workspaceZoom, to: webView)
        supportIncidentBridge?.attach(webView: webView, routePolicy: routePolicy)
        context.coordinator.update(
            showsAppUpdateBadge: showsAppUpdateBadge,
            onCheckForUpdates: onCheckForUpdates
        )
        let container = WebViewContainer(webView: webView)
        container.lastLoadedRequestIdentity = Self.loadIdentity(for: request)
        webView.load(request)
        return container
    }

    public func updateNSView(_ container: NSView, context: Context) {
        guard let container = container as? WebViewContainer else { return }
        context.coordinator.update(
            showsAppUpdateBadge: showsAppUpdateBadge,
            onCheckForUpdates: onCheckForUpdates
        )
        supportIncidentBridge?.attach(webView: container.webView, routePolicy: routePolicy)
        EmbeddedCabinetZoomBridge.apply(workspaceZoom, to: container.webView)
        context.coordinator.applyUpdateVisibility(to: container.webView)
        guard Self.shouldLoad(request: request, lastLoadedRequestIdentity: container.lastLoadedRequestIdentity) else {
            return
        }
        container.lastLoadedRequestIdentity = Self.loadIdentity(for: request)
        container.webView.load(request)
    }

    public func makeCoordinator() -> Coordinator {
        Coordinator(
            routePolicy: routePolicy,
            desktopHeaders: request.allHTTPHeaderFields ?? [:],
            cabinetState: $cabinetState,
            currentRoute: $currentRoute,
            navigationEventLogger: navigationEventLogger,
            showsAppUpdateBadge: showsAppUpdateBadge,
            onCheckForUpdates: onCheckForUpdates,
            supportIncidentBridge: supportIncidentBridge
        )
    }

    public static func dismantleNSView(_ nsView: NSView, coordinator: Coordinator) {
        guard let container = nsView as? WebViewContainer else { return }
        coordinator.detachSupportIncidentBridge(from: container.webView)
        container.webView.configuration.userContentController.removeScriptMessageHandler(
            forName: EmbeddedCabinetUpdateBridge.messageHandlerName
        )
    }

    public final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler, WKDownloadDelegate {
        private let routePolicy: DesktopCabinetRoutePolicy
        private let navigationRequestPolicy: DesktopCabinetNavigationRequestPolicy
        private let navigationEventLogger: NavigationEventLogger?
        private var authContinuationActive = false
        private var showsAppUpdateBadge: Bool
        private var onCheckForUpdates: CheckForUpdatesAction
        private let supportIncidentBridge: EmbeddedCabinetSupportIncidentBridge?
        private weak var downloadHostWindow: NSWindow?
        @Binding private var cabinetState: DesktopCabinetState
        @Binding private var currentRoute: URL?

        init(
            routePolicy: DesktopCabinetRoutePolicy,
            desktopHeaders: [String: String],
            cabinetState: Binding<DesktopCabinetState>,
            currentRoute: Binding<URL?>,
            navigationEventLogger: NavigationEventLogger?,
            showsAppUpdateBadge: Bool,
            onCheckForUpdates: @escaping CheckForUpdatesAction,
            supportIncidentBridge: EmbeddedCabinetSupportIncidentBridge?
        ) {
            self.routePolicy = routePolicy
            navigationRequestPolicy = DesktopCabinetNavigationRequestPolicy(
                routePolicy: routePolicy,
                desktopHeaders: desktopHeaders
            )
            self.navigationEventLogger = navigationEventLogger
            self.showsAppUpdateBadge = showsAppUpdateBadge
            self.onCheckForUpdates = onCheckForUpdates
            self.supportIncidentBridge = supportIncidentBridge
            _cabinetState = cabinetState
            _currentRoute = currentRoute
        }

        @MainActor
        public func update(
            showsAppUpdateBadge: Bool,
            onCheckForUpdates: @escaping CheckForUpdatesAction
        ) {
            self.showsAppUpdateBadge = showsAppUpdateBadge
            self.onCheckForUpdates = onCheckForUpdates
        }

        @MainActor
        public func applyUpdateVisibility(to webView: WKWebView) {
            webView.evaluateJavaScript(
                EmbeddedCabinetUpdateBridge.visibilityScript(showsBadge: showsAppUpdateBadge),
                completionHandler: nil
            )
        }

        @MainActor
        public func detachSupportIncidentBridge(from webView: WKWebView) {
            supportIncidentBridge?.detach(webView: webView)
        }

        @MainActor
        public func userContentController(
            _: WKUserContentController,
            didReceive message: WKScriptMessage
        ) {
            guard
                message.name == EmbeddedCabinetUpdateBridge.messageHandlerName,
                EmbeddedCabinetUpdateBridge.isAllowedMessageBody(message.body),
                message.frameInfo.isMainFrame,
                let sourceURL = message.frameInfo.request.url,
                routePolicy.decision(for: sourceURL).decision == .allow
            else {
                return
            }
            onCheckForUpdates()
        }

        @MainActor
        public func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction,
            decisionHandler: @escaping @MainActor @Sendable (WKNavigationActionPolicy) -> Void
        ) {
            guard let url = navigationAction.request.url else {
                cabinetState = .malformedResponse
                decisionHandler(.cancel)
                return
            }
            if url.scheme?.lowercased() == "about" {
                decisionHandler(.allow)
                return
            }
            if routePolicy.decision(for: url).route.kind == .artifactDownload,
               !EmbeddedCabinetWebView.allowsArtifactDownload(
                   targetURL: url,
                   sourceURL: artifactSourceURL(
                       for: navigationAction,
                       webViewURL: webView.url
                   ),
                   sourceIsMainFrame: navigationAction.sourceFrame.isMainFrame,
                   routePolicy: routePolicy
               ) {
                cabinetState = .blockedRoute
                decisionHandler(.cancel)
                return
            }
            if EmbeddedCabinetWebView.allowsBlobDownload(
                requested: navigationAction.shouldPerformDownload,
                targetURL: url,
                sourceURL: navigationAction.sourceFrame.request.url,
                sourceIsMainFrame: navigationAction.sourceFrame.isMainFrame,
                routePolicy: routePolicy
            ) {
                decisionHandler(.download)
                return
            }
            if navigationAction.targetFrame?.isMainFrame == false {
                decisionHandler(.allow)
                return
            }

            let decision = routePolicy.decision(
                for: url,
                allowExternalAuthProvider: authContinuationActive || isAuthRoute(webView.url)
            )
            switch decision.decision {
            case .allow:
                updateAuthContinuation(for: decision.route.kind)
                switch navigationRequestPolicy.decision(
                    forNavigationRequest: navigationAction.request,
                    isForMainFrame: navigationAction.targetFrame?.isMainFrame != false
                ) {
                case .allow:
                    break
                case let .reload(reloadedRequest):
                    if decision.route.kind != .artifactDownload {
                        cabinetState = .loading
                    }
                    webView.load(reloadedRequest)
                    decisionHandler(.cancel)
                    return
                }
                if decision.route.kind != .artifactDownload {
                    cabinetState = .loading
                }
                decisionHandler(.allow)
            case .openExternally:
                authContinuationActive = false
                NSWorkspace.shared.open(url)
                decisionHandler(.cancel)
            case .blockWithMessage:
                authContinuationActive = false
                cabinetState = .blockedRoute
                decisionHandler(.cancel)
            }
        }

        @MainActor
        public func webView(
            _ webView: WKWebView,
            navigationAction _: WKNavigationAction,
            didBecome download: WKDownload
        ) {
            downloadHostWindow = webView.window
            download.delegate = self
        }

        @MainActor
        public func webView(
            _ webView: WKWebView,
            navigationResponse _: WKNavigationResponse,
            didBecome download: WKDownload
        ) {
            downloadHostWindow = webView.window
            download.delegate = self
        }

        @MainActor
        public func download(
            _ download: WKDownload,
            decideDestinationUsing _: URLResponse,
            suggestedFilename: String,
            completionHandler: @escaping @MainActor @Sendable (URL?) -> Void
        ) {
            let panel = NSSavePanel()
            panel.nameFieldStringValue = EmbeddedCabinetWebView.safeDownloadFilename(
                suggestedFilename
            )
            panel.canCreateDirectories = true
            panel.isExtensionHidden = false
            panel.title = "Сохранить файл"
            panel.message = "Выберите папку и имя файла."
            panel.prompt = "Сохранить"
            let finish: (NSApplication.ModalResponse) -> Void = { [weak self] response in
                let destination = EmbeddedCabinetWebView.nativeSaveDestination(
                    response: response,
                    selectedURL: panel.url
                )
                self?.downloadHostWindow = nil
                if destination == nil {
                    self?.logNavigationEvent(
                        "cabinet_download_cancelled",
                        detail: "result=cancelled"
                    )
                } else {
                    self?.logNavigationEvent("cabinet_download_started", detail: "result=started")
                }
                completionHandler(destination)
            }
            if let window = downloadHostWindow {
                panel.beginSheetModal(for: window, completionHandler: finish)
            } else {
                panel.begin(completionHandler: finish)
            }
        }

        @MainActor
        public func downloadDidFinish(_: WKDownload) {
            logNavigationEvent("cabinet_download_finished", detail: "result=completed")
        }

        @MainActor
        public func download(
            _: WKDownload,
            didFailWithError error: Error,
            resumeData _: Data?
        ) {
            let nsError = error as NSError
            if nsError.domain == NSURLErrorDomain && nsError.code == NSURLErrorCancelled {
                return
            }
            logNavigationEvent(
                "cabinet_download_failed",
                detail: "domain=\(sanitized(nsError.domain)) code=\(nsError.code)"
            )
        }

        @MainActor
        public func webView(
            _ webView: WKWebView,
            runOpenPanelWith parameters: WKOpenPanelParameters,
            initiatedByFrame: WKFrameInfo,
            completionHandler: @escaping @MainActor @Sendable ([URL]?) -> Void
        ) {
            guard EmbeddedCabinetWebView.allowsFilePicker(
                webViewURL: webView.url,
                frameURL: initiatedByFrame.request.url,
                frameIsMainFrame: initiatedByFrame.isMainFrame,
                routePolicy: routePolicy
            ) else {
                completionHandler(nil)
                return
            }
            let panel = NSOpenPanel()
            panel.canChooseFiles = true
            panel.canChooseDirectories = false
            panel.allowsMultipleSelection = false
            panel.canCreateDirectories = false
            panel.resolvesAliases = true
            panel.title = "Выберите аудиофайл"
            panel.message = "Выберите один файл записи для загрузки в GRAF."
            panel.prompt = "Выбрать"

            let complete: (NSApplication.ModalResponse) -> Void = { response in
                guard response == .OK else {
                    completionHandler(nil)
                    return
                }
                let urls = Array(panel.urls.prefix(1))
                completionHandler(urls.isEmpty ? nil : urls)
            }

            if let window = webView.window {
                panel.beginSheetModal(for: window, completionHandler: complete)
            } else {
                complete(panel.runModal())
            }
        }

        @MainActor
        public func webView(_ webView: WKWebView, didFinish _: WKNavigation!) {
            guard let url = webView.url else {
                return
            }
            let routeDecision = routePolicy.decision(for: url, allowExternalAuthProvider: authContinuationActive)
            guard routeDecision.decision == .allow else {
                return
            }
            if routeDecision.route.kind == .artifactDownload {
                // A successful artifact response must never become the
                // workspace document or overwrite the last useful route.
                return
            }
            updateAuthContinuation(for: routeDecision.route.kind)
            let finishedState = EmbeddedCabinetWebView.finishedState(for: routeDecision.route.kind)
            DesktopCabinetSessionBridge.syncAuthSessionCookies(from: webView)
            if let container = webView.superview as? WebViewContainer {
                container.lastLoadedRequestIdentity = EmbeddedCabinetWebView.loadIdentity(url: url)
            }
            currentRoute = EmbeddedCabinetWebView.trackedRoute(current: currentRoute, loaded: url)
            cabinetState = finishedState
            applyUpdateVisibility(to: webView)
            logNavigationEvent(
                "cabinet_navigation_finished",
                detail: "state=\(finishedState.rawValue) \(urlLogDetail(url))"
            )
        }

        @MainActor
        public func webView(
            _: WKWebView,
            decidePolicyFor navigationResponse: WKNavigationResponse,
            decisionHandler: @escaping @MainActor @Sendable (WKNavigationResponsePolicy) -> Void
        ) {
            switch DesktopCabinetNavigationResponsePolicy(routePolicy: routePolicy).decision(
                forNavigationResponse: navigationResponse.response,
                isForMainFrame: navigationResponse.isForMainFrame
            ) {
            case .allow:
                decisionHandler(.allow)
            case .download:
                logNavigationEvent(
                    "cabinet_download_response",
                    detail: responseLogDetail(navigationResponse.response, state: .ready)
                )
                decisionHandler(.download)
            case .cancelResource:
                logNavigationEvent(
                    "cabinet_download_response_blocked",
                    detail: responseLogDetail(navigationResponse.response, state: cabinetState)
                )
                decisionHandler(.cancel)
            case let .cancel(state):
                cabinetState = state
                logNavigationEvent(
                    "cabinet_navigation_response_blocked",
                    detail: responseLogDetail(navigationResponse.response, state: state)
                )
                decisionHandler(.cancel)
            }
        }

        @MainActor
        public func webView(_ webView: WKWebView, didFail _: WKNavigation!, withError error: Error) {
            transitionAfterNavigationFailure(error, webViewURL: webView.url, phase: "committed")
        }

        @MainActor
        public func webView(_ webView: WKWebView, didFailProvisionalNavigation _: WKNavigation!, withError error: Error) {
            transitionAfterNavigationFailure(error, webViewURL: webView.url, phase: "provisional")
        }

        private func transitionAfterNavigationFailure(_ error: Error, webViewURL: URL?, phase: String) {
            let previousState = cabinetState
            let nextState = DesktopCabinetState.state(forNavigationError: error, currentState: cabinetState)
            cabinetState = nextState
            logNavigationEvent(
                "cabinet_navigation_failed",
                detail: errorLogDetail(error, webViewURL: webViewURL, phase: phase, from: previousState, to: nextState)
            )
        }

        private func logNavigationEvent(_ event: String, detail: String) {
            navigationEventLogger?(event, detail)
        }

        private func responseLogDetail(_ response: URLResponse, state: DesktopCabinetState) -> String {
            guard let httpResponse = response as? HTTPURLResponse else {
                return "state=\(state.rawValue) response=non_http"
            }
            return [
                "state=\(state.rawValue)",
                "status=\(httpResponse.statusCode)",
                urlLogDetail(httpResponse.url)
            ].joined(separator: " ")
        }

        private func errorLogDetail(
            _ error: Error,
            webViewURL: URL?,
            phase: String,
            from previousState: DesktopCabinetState,
            to nextState: DesktopCabinetState
        ) -> String {
            let nsError = error as NSError
            let failingURL = (nsError.userInfo[NSURLErrorFailingURLErrorKey] as? URL) ?? webViewURL
            return [
                "phase=\(phase)",
                "domain=\(sanitized(nsError.domain))",
                "code=\(nsError.code)",
                "from=\(previousState.rawValue)",
                "to=\(nextState.rawValue)",
                urlLogDetail(failingURL)
            ].joined(separator: " ")
        }

        private func urlLogDetail(_ url: URL?) -> String {
            guard let url else {
                return "scheme=none host=none routeKind=unknown"
            }
            let decision = routePolicy.decision(for: url)
            return [
                "scheme=\(sanitized(url.scheme ?? "none"))",
                "host=\(sanitized(url.host ?? "none"))",
                "routeKind=\(decision.route.kind.rawValue)"
            ].joined(separator: " ")
        }

        private func sanitized(_ value: String) -> String {
            value
                .replacingOccurrences(of: " ", with: "_")
                .replacingOccurrences(of: "\n", with: "_")
                .replacingOccurrences(of: "\r", with: "_")
        }

        private func isAuthRoute(_ url: URL?) -> Bool {
            guard let url else { return false }
            let decision = routePolicy.decision(for: url, allowExternalAuthProvider: authContinuationActive)
            return [
                .authLogin,
                .authSignup,
                .authProvider,
                .authCallback
            ].contains(decision.route.kind)
        }

        private func artifactSourceURL(
            for navigationAction: WKNavigationAction,
            webViewURL: URL?
        ) -> URL? {
            if let sourceURL = navigationAction.sourceFrame.request.url {
                let sourceDecision = routePolicy.decision(for: sourceURL)
                if sourceDecision.decision == .allow,
                   sourceDecision.route.kind == .meetingDetail {
                    return sourceURL
                }
            }
            if let webViewURL {
                let documentDecision = routePolicy.decision(for: webViewURL)
                if documentDecision.decision == .allow,
                   documentDecision.route.kind == .meetingDetail {
                    return webViewURL
                }
            }
            return nil
        }

        private func updateAuthContinuation(for routeKind: DesktopCabinetRouteKind) {
            authContinuationActive = [
                .authLogin,
                .authSignup,
                .authProvider,
                .authCallback
            ].contains(routeKind)
        }
    }

    public final class WebViewContainer: NSView {
        public let webView: WKWebView
        public var lastLoadedRequestIdentity: String?

        public init(webView: WKWebView) {
            self.webView = webView
            super.init(frame: .zero)
            wantsLayer = true
            clipsToBounds = true
            layer?.backgroundColor = DesktopMeetingShellChrome.webEmbeddedBackgroundNSColor.cgColor
            layer?.masksToBounds = true
            webView.clipsToBounds = true
            webView.layer?.masksToBounds = true
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

    public enum EmbeddedCabinetZoomBridge {
        @MainActor
        public static func apply(_ preference: WorkspaceZoomPreference, to webView: WKWebView) {
            webView.pageZoom = CGFloat(preference.value)
        }
    }
}
#else
@MainActor
public final class EmbeddedCabinetSupportIncidentBridge: DesktopSupportIncidentSubmitting {
    public static let intakePath = "/api/v1/desktop/support-incidents"
    public static let requestScript = ""

    public init() {}

    public nonisolated static func isAllowedCabinetDocument(
        _: URL,
        routePolicy _: DesktopCabinetRoutePolicy
    ) -> Bool {
        false
    }

    public func submitSupportIncident(
        report _: DesktopSupportIncidentReport
    ) async throws -> DesktopSupportIncidentResponse {
        throw DesktopUploadClientError.httpStatus(401, "support_incident.auth_session_required")
    }

    public func syncSupportIncident(
        incidentID _: String
    ) async throws -> DesktopSupportIncidentResponse {
        throw DesktopUploadClientError.httpStatus(401, "support_incident.auth_session_required")
    }
}

public struct EmbeddedCabinetWebView: View {
    public typealias NavigationEventLogger = @MainActor @Sendable (_ event: String, _ detail: String) -> Void
    public typealias CheckForUpdatesAction = @MainActor @Sendable () -> Void

    private let message: String

    public init(
        request _: URLRequest,
        routePolicy _: DesktopCabinetRoutePolicy,
        cabinetState _: Binding<DesktopCabinetState>,
        workspaceZoom _: WorkspaceZoomPreference = .default,
        currentRoute _: Binding<URL?> = .constant(nil),
        navigationEventLogger _: NavigationEventLogger? = nil,
        showsAppUpdateBadge _: Bool = false,
        onCheckForUpdates _: @escaping CheckForUpdatesAction = {},
        supportIncidentBridge _: EmbeddedCabinetSupportIncidentBridge? = nil
    ) {
        message = DesktopCabinetState.notConfigured.userMessage
    }

    public nonisolated static func loadIdentity(for request: URLRequest) -> String {
        let method = request.httpMethod ?? "GET"
        let url = request.url?.absoluteString ?? ""
        return "\(method) \(url)"
    }

    public nonisolated static func shouldLoad(request: URLRequest, lastLoadedRequestIdentity: String?) -> Bool {
        lastLoadedRequestIdentity != loadIdentity(for: request)
    }

    public nonisolated static func trackedRoute(current _: URL?, loaded: URL) -> URL {
        loaded
    }

    public nonisolated static func finishedState(for _: DesktopCabinetRouteKind) -> DesktopCabinetState {
        .notConfigured
    }

    public var body: some View {
        Text(message)
            .font(.caption)
            .foregroundStyle(.secondary)
    }
}
#endif
