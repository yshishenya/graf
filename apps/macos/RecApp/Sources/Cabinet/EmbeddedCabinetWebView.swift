import Foundation
import Combine
import SwiftUI

public enum EmbeddedCabinetBackNavigationDecision: Equatable, Sendable {
    case history
    case meetingsList
    case unavailable
}

public enum EmbeddedCabinetNavigationPolicy {
    public static func backDecision(
        currentURL: URL?,
        backURL: URL?,
        fallbackURL: URL?,
        routePolicy: DesktopCabinetRoutePolicy,
        sessionExpired: Bool = false
    ) -> EmbeddedCabinetBackNavigationDecision {
        let currentKind = currentURL.map { routePolicy.decision(for: $0).route.kind }
        let backKind = backURL.map { routePolicy.decision(for: $0).route.kind }

        if sessionExpired && (
            isProtectedDocumentRoute(backKind)
                || (isMeetingReviewRoute(currentKind) && isMeetingList(fallbackURL, routePolicy: routePolicy))
        ) {
            return .unavailable
        }

        if isMeetingReviewRoute(currentKind) {
            if isSafeDocument(backURL, routePolicy: routePolicy), isMeetingHistoryRoute(backKind) {
                return .history
            }
            if isMeetingList(fallbackURL, routePolicy: routePolicy) {
                return .meetingsList
            }
            return .unavailable
        }

        return isSafeDocument(backURL, routePolicy: routePolicy) ? .history : .unavailable
    }

    public static func isSafeDocument(
        _ url: URL?,
        routePolicy: DesktopCabinetRoutePolicy
    ) -> Bool {
        guard let url else { return false }
        let decision = routePolicy.decision(for: url)
        return decision.decision == .allow
            && ![.artifactDownload, .authCallback, .authProvider].contains(decision.route.kind)
    }

    public static func isSafeHistoryRequest(
        _ request: URLRequest,
        routePolicy: DesktopCabinetRoutePolicy
    ) -> Bool {
        guard (request.httpMethod ?? "GET").uppercased() == "GET" else { return false }
        guard let url = request.url else { return false }
        let decision = routePolicy.decision(for: url)
        guard decision.decision == .allow else { return false }
        return ![.authCallback, .authProvider].contains(decision.route.kind)
            && decision.route.kind != .artifactDownload
    }

    private static func isMeetingList(
        _ url: URL?,
        routePolicy: DesktopCabinetRoutePolicy
    ) -> Bool {
        guard let url else { return false }
        let decision = routePolicy.decision(for: url)
        return decision.decision == .allow && decision.route.kind == .meetingList
    }

    private static func isMeetingReviewRoute(_ kind: DesktopCabinetRouteKind?) -> Bool {
        switch kind {
        case .meetingDetail, .meetingShare, .meetingDeletionReport:
            return true
        default:
            return false
        }
    }

    private static func isMeetingHistoryRoute(_ kind: DesktopCabinetRouteKind?) -> Bool {
        switch kind {
        case .meetingList, .meetingDetail, .meetingShare, .meetingDeletionReport:
            return true
        default:
            return false
        }
    }

    private static func isProtectedDocumentRoute(_ kind: DesktopCabinetRouteKind?) -> Bool {
        switch kind {
        case .meetingList, .meetingDetail, .meetingShare, .meetingDeletionReport,
             .settings, .calendarSettings, .meetingDetectionSettings:
            return true
        default:
            return false
        }
    }
}

#if canImport(WebKit)
import AppKit
import WebKit

@MainActor
public final class EmbeddedCabinetNavigationController: ObservableObject {
    @Published public private(set) var canGoBack = false
    @Published public private(set) var canGoForward = false
    @Published public private(set) var canReload = false
    @Published public private(set) var isLoading = false
    @Published public private(set) var sessionBoundaryID = UUID()

    private weak var webView: WKWebView?
    private var routePolicy: DesktopCabinetRoutePolicy?
    private var fallbackRequest: URLRequest?
    private var syntheticMeetingsListURL: URL?
    private var syntheticLoadInFlight = false
    private var activeNavigation: WKNavigation?
    private var activeNavigationURL: URL?
    private var pendingNavigationURL: URL?
    private let invalidNavigations = NSHashTable<WKNavigation>.weakObjects()
    private var historyFencePending = false
    private var controllerNavigationPending = false
    private var sessionExpired = false
    private var safeHistoryURLs = Set<URL>()
    private var unsafeHistoryURLs = Set<URL>()

    public init() {}

    public func goBack() {
        guard !isLoading, let webView, let routePolicy else { return }
        let backItem = preferredBackItem(for: webView, routePolicy: routePolicy)
        let decision = EmbeddedCabinetNavigationPolicy.backDecision(
            currentURL: webView.url,
            backURL: backItem?.url,
            fallbackURL: fallbackRequest?.url,
            routePolicy: routePolicy,
            sessionExpired: sessionExpired
        )
        isLoading = true
        switch decision {
        case .history:
            if let backItem {
                guard let navigation = webView.go(to: backItem) else {
                    isLoading = false
                    syncNavigationState()
                    return
                }
                beginControllerNavigation(navigation, targetURL: backItem.url)
            } else {
                isLoading = false
                syncNavigationState()
            }
        case .meetingsList:
            guard let fallbackRequest else {
                isLoading = false
                return
            }
            syntheticMeetingsListURL = fallbackRequest.url
            syntheticLoadInFlight = true
            observeNavigationRequest(fallbackRequest, webView: webView)
            guard let navigation = webView.load(fallbackRequest) else {
                syntheticMeetingsListURL = nil
                syntheticLoadInFlight = false
                isLoading = false
                syncNavigationState()
                return
            }
            beginControllerNavigation(navigation, targetURL: fallbackRequest.url)
        case .unavailable:
            isLoading = false
            syncNavigationState()
        }
    }

    public func goForward() {
        guard !isLoading, canGoForward, let webView, let routePolicy,
              let forwardURL = webView.backForwardList.forwardItem?.url,
              isSafeHistoryDocument(forwardURL, routePolicy: routePolicy),
              (!sessionExpired || !isProtectedMeetingRoute(forwardURL, routePolicy: routePolicy))
        else { return }
        isLoading = true
        guard let navigation = webView.goForward() else {
            isLoading = false
            syncNavigationState()
            return
        }
        beginControllerNavigation(navigation, targetURL: forwardURL)
    }

    public func reload() {
        guard !isLoading, canReload, let webView, let routePolicy,
              isSafeHistoryDocument(webView.url, routePolicy: routePolicy),
              (!sessionExpired || !isProtectedMeetingRoute(webView.url, routePolicy: routePolicy))
        else { return }
        isLoading = true
        guard let navigation = webView.reload() else {
            isLoading = false
            syncNavigationState()
            return
        }
        beginControllerNavigation(navigation, targetURL: webView.url)
    }

    fileprivate func attach(
        webView: WKWebView,
        routePolicy: DesktopCabinetRoutePolicy,
        fallbackRequest: URLRequest,
        initialRequest: URLRequest,
        sessionExpired: Bool
    ) {
        self.webView = webView
        self.routePolicy = routePolicy
        self.fallbackRequest = fallbackRequest
        self.sessionExpired = sessionExpired
        safeHistoryURLs = []
        unsafeHistoryURLs = []
        syntheticMeetingsListURL = nil
        syntheticLoadInFlight = false
        activeNavigation = nil
        activeNavigationURL = nil
        pendingNavigationURL = nil
        invalidNavigations.removeAllObjects()
        historyFencePending = false
        controllerNavigationPending = false
        observeNavigationRequest(initialRequest, webView: webView)
        isLoading = true
        syncNavigationState()
    }

    fileprivate func updateConfiguration(
        routePolicy: DesktopCabinetRoutePolicy,
        fallbackRequest: URLRequest,
        sessionExpired: Bool
    ) {
        self.routePolicy = routePolicy
        self.fallbackRequest = fallbackRequest
        if sessionExpired {
            self.sessionExpired = true
        }
        syncNavigationState()
    }

    fileprivate func markSessionExpired(webView: WKWebView) {
        guard self.webView === webView else { return }
        if !sessionExpired {
            sessionExpired = true
            sessionBoundaryID = UUID()
        }
        syncNavigationState()
    }

    fileprivate func detach(webView: WKWebView) {
        guard self.webView === webView else { return }
        self.webView = nil
        self.routePolicy = nil
        self.fallbackRequest = nil
        syntheticMeetingsListURL = nil
        syntheticLoadInFlight = false
        activeNavigation = nil
        activeNavigationURL = nil
        pendingNavigationURL = nil
        invalidNavigations.removeAllObjects()
        historyFencePending = false
        controllerNavigationPending = false
        sessionExpired = false
        safeHistoryURLs = []
        unsafeHistoryURLs = []
        canGoBack = false
        canGoForward = false
        canReload = false
        isLoading = false
    }

    fileprivate func isAttached(to webView: WKWebView) -> Bool {
        self.webView === webView
    }

    fileprivate func navigationDidStart(
        webView: WKWebView,
        navigation: WKNavigation?,
        targetURL: URL? = nil,
        controllerInitiated: Bool = false
    ) {
        guard self.webView === webView else { return }
        guard let navigation else {
            activeNavigation = nil
            activeNavigationURL = nil
            pendingNavigationURL = nil
            controllerNavigationPending = false
            isLoading = false
            syncNavigationState()
            return
        }
        if invalidNavigations.contains(navigation) {
            invalidNavigations.remove(navigation)
            return
        }
        if let activeNavigation, activeNavigation !== navigation {
            invalidNavigations.add(activeNavigation)
        }
        activeNavigation = navigation
        activeNavigationURL = targetURL ?? pendingNavigationURL ?? activeNavigationURL
        pendingNavigationURL = nil
        controllerNavigationPending = controllerInitiated
        isLoading = true
        syncNavigationState()
    }

    @discardableResult
    fileprivate func navigationDidFinish(
        webView: WKWebView,
        navigation: WKNavigation? = nil,
        expectedURL: URL? = nil
    ) -> Bool {
        guard self.webView === webView, isCurrentNavigation(navigation, expectedURL: expectedURL) else { return false }
        activeNavigation = nil
        activeNavigationURL = nil
        pendingNavigationURL = nil
        controllerNavigationPending = false
        isLoading = false
        let historyWasFenced = fencePendingHistory()
        if let url = webView.url, let routePolicy {
            let wasSessionExpired = sessionExpired
            let kind = routePolicy.decision(for: url).route.kind
            if !historyWasFenced {
                observeNavigationRequest(URLRequest(url: url), webView: webView, registersNavigation: false)
            }
            if isAuthRoute(kind) {
                sessionExpired = true
            } else if isProtectedMeetingRoute(url, routePolicy: routePolicy) {
                if wasSessionExpired && !historyWasFenced {
                    sessionBoundaryID = UUID()
                    safeHistoryURLs = []
                    unsafeHistoryURLs = []
                }
                sessionExpired = false
            }
        }
        if syntheticLoadInFlight {
            if isMeetingList(webView.url, routePolicy: routePolicy) {
                syntheticMeetingsListURL = webView.url
            } else {
                syntheticMeetingsListURL = nil
            }
            syntheticLoadInFlight = false
        } else if syntheticMeetingsListURL != webView.url {
            syntheticMeetingsListURL = nil
        }
        syncNavigationState()
        return true
    }

    @discardableResult
    fileprivate func navigationDidFail(webView: WKWebView, navigation: WKNavigation?, error: Error) -> Bool {
        guard self.webView === webView, isCurrentNavigation(navigation) else { return false }
        activeNavigation = nil
        activeNavigationURL = nil
        pendingNavigationURL = nil
        fencePendingHistory()
        controllerNavigationPending = false
        syntheticMeetingsListURL = nil
        syntheticLoadInFlight = false
        isLoading = false
        syncNavigationState()
        return true
    }

    fileprivate func navigationDidCancel(webView: WKWebView, expectedURL: URL? = nil) {
        guard self.webView === webView,
              isCurrentNavigation(nil, expectedURL: expectedURL)
        else { return }
        activeNavigation = nil
        activeNavigationURL = nil
        pendingNavigationURL = nil
        fencePendingHistory()
        controllerNavigationPending = false
        syntheticMeetingsListURL = nil
        syntheticLoadInFlight = false
        isLoading = false
        syncNavigationState()
    }

    fileprivate func shouldAllowBackForwardNavigation(to url: URL, in webView: WKWebView) -> Bool {
        guard self.webView === webView, let routePolicy else { return false }
        guard !isLoading || controllerNavigationPending else { return false }
        guard syntheticMeetingsListURL != webView.url else { return false }
        let isBackNavigation = webView.backForwardList.backList.contains { $0.url == url }
        let isForwardNavigation = webView.backForwardList.forwardList.contains { $0.url == url }
        guard isBackNavigation || isForwardNavigation else { return false }
        if isBackNavigation {
            guard EmbeddedCabinetNavigationPolicy.backDecision(
                currentURL: webView.url,
                backURL: url,
                fallbackURL: fallbackRequest?.url,
                routePolicy: routePolicy,
                sessionExpired: sessionExpired
            ) == .history else { return false }
        }
        guard isSafeHistoryDocument(url, routePolicy: routePolicy),
              (!sessionExpired || !isProtectedMeetingRoute(url, routePolicy: routePolicy))
        else { return false }
        return true
    }

    fileprivate func shouldAllowReload(in webView: WKWebView) -> Bool {
        guard self.webView === webView, let routePolicy else { return false }
        guard !isLoading || controllerNavigationPending else { return false }
        return canReload
            && isSafeHistoryDocument(webView.url, routePolicy: routePolicy)
            && (!sessionExpired || !isProtectedMeetingRoute(webView.url, routePolicy: routePolicy))
    }

    fileprivate func observeNavigationRequest(
        _ request: URLRequest,
        webView: WKWebView,
        registersNavigation: Bool = true,
        allowExternalAuthProvider: Bool = false
    ) {
        guard self.webView === webView, let url = request.url, let routePolicy else { return }
        let decision = routePolicy.decision(
            for: url,
            allowExternalAuthProvider: allowExternalAuthProvider
        )
        guard decision.decision == .allow else { return }
        if registersNavigation {
            // WebKit may report a server redirect as another action for the
            // same WKNavigation. Retire an older operation only when the
            // replacement WKNavigation is actually announced in
            // navigationDidStart, where its identity is available.
            pendingNavigationURL = url
            if (request.httpMethod ?? "GET").uppercased() != "GET",
               (isProtectedMeetingRoute(url, routePolicy: routePolicy)
                    || isAuthRoute(decision.route.kind)) {
                historyFencePending = true
            }
        }
        // Artifact downloads are intentionally excluded from the document
        // history ledgers, but still need an active target URL. WebKit can
        // report an allowed artifact as a main-frame navigation before it
        // hands the response to WKDownload; retaining the target lets the
        // download callback retire that navigation instead of leaving the
        // controller permanently loading.
        guard decision.route.kind != .artifactDownload else { return }
        if syntheticLoadInFlight, decision.route.kind != .meetingList {
            syntheticMeetingsListURL = nil
            syntheticLoadInFlight = false
        }
        if EmbeddedCabinetNavigationPolicy.isSafeHistoryRequest(request, routePolicy: routePolicy) {
            if !unsafeHistoryURLs.contains(url) {
                safeHistoryURLs.insert(url)
            }
        } else {
            unsafeHistoryURLs.insert(url)
            safeHistoryURLs.remove(url)
        }
    }

    fileprivate func clearPendingNavigation(webView: WKWebView) {
        guard self.webView === webView else { return }
        pendingNavigationURL = nil
    }

    fileprivate func cancelPendingNavigation(webView: WKWebView) {
        guard self.webView === webView else { return }
        invalidateActiveNavigation()
        pendingNavigationURL = nil
        historyFencePending = false
        syntheticMeetingsListURL = nil
        syntheticLoadInFlight = false
        isLoading = false
        syncNavigationState()
    }

    fileprivate func cancelControllerNavigationIfPending(webView: WKWebView) {
        guard self.webView === webView, controllerNavigationPending else { return }
        cancelPendingNavigation(webView: webView)
    }

    private func invalidateActiveNavigation() {
        guard let activeNavigation else { return }
        invalidNavigations.add(activeNavigation)
        self.activeNavigation = nil
        activeNavigationURL = nil
        controllerNavigationPending = false
    }

    @discardableResult
    private func fencePendingHistory() -> Bool {
        guard historyFencePending else { return false }
        historyFencePending = false
        safeHistoryURLs = []
        unsafeHistoryURLs = []
        syntheticMeetingsListURL = nil
        syntheticLoadInFlight = false
        sessionBoundaryID = UUID()
        return true
    }

    private func syncNavigationState() {
        guard let webView, let routePolicy else {
            canGoBack = false
            canGoForward = false
            canReload = false
            return
        }
        let backItem = preferredBackItem(for: webView, routePolicy: routePolicy)
        canGoBack = !(
            syntheticMeetingsListURL == webView.url
        ) && EmbeddedCabinetNavigationPolicy.backDecision(
                currentURL: webView.url,
                backURL: backItem?.url,
                fallbackURL: fallbackRequest?.url,
                routePolicy: routePolicy,
                sessionExpired: sessionExpired
            ) != .unavailable
        if let forwardURL = webView.backForwardList.forwardItem?.url {
            canGoForward = webView.canGoForward
                && syntheticMeetingsListURL != webView.url
                && isSafeHistoryDocument(forwardURL, routePolicy: routePolicy)
                && (!sessionExpired || !isProtectedMeetingRoute(forwardURL, routePolicy: routePolicy))
        } else {
            canGoForward = false
        }
        canReload = !isLoading
            && isSafeHistoryDocument(webView.url, routePolicy: routePolicy)
            && (!sessionExpired || !isProtectedMeetingRoute(webView.url, routePolicy: routePolicy))
    }

    private func beginControllerNavigation(_ navigation: WKNavigation, targetURL: URL?) {
        invalidateActiveNavigation()
        activeNavigation = navigation
        activeNavigationURL = targetURL
        pendingNavigationURL = nil
        controllerNavigationPending = true
        isLoading = true
        syncNavigationState()
    }

    private func isCurrentNavigation(_ navigation: WKNavigation?, expectedURL: URL? = nil) -> Bool {
        if navigation == nil {
            guard let expectedURL else { return activeNavigation == nil }
            guard activeNavigation != nil else { return true }
            return activeNavigationURL == expectedURL
                || pendingNavigationURL == expectedURL
                || isEquivalentArtifactURL(activeNavigationURL, expectedURL)
        }
        guard let activeNavigation else { return false }
        return activeNavigation === navigation
    }

    private func isEquivalentArtifactURL(_ lhs: URL?, _ rhs: URL?) -> Bool {
        guard let lhs, let rhs, let routePolicy else { return false }
        let left = routePolicy.decision(for: lhs)
        let right = routePolicy.decision(for: rhs)
        return left.decision == .allow
            && right.decision == .allow
            && left.route.kind == .artifactDownload
            && right.route.kind == .artifactDownload
            && left.route.path == right.route.path
            && left.route.meetingId == right.route.meetingId
    }

    private func preferredBackItem(
        for webView: WKWebView,
        routePolicy: DesktopCabinetRoutePolicy
    ) -> WKBackForwardListItem? {
        let currentKind = webView.url.map { routePolicy.decision(for: $0).route.kind }
        return webView.backForwardList.backList.reversed().first { item in
            let decision = routePolicy.decision(for: item.url)
            guard decision.decision == .allow,
                  isSafeHistoryDocument(item.url, routePolicy: routePolicy),
                  (!sessionExpired || !isProtectedMeetingRoute(item.url, routePolicy: routePolicy))
            else { return false }
            if isMeetingReviewRoute(currentKind) {
                return isMeetingHistoryRoute(decision.route.kind)
            }
            return true
        }
    }

    private func isSafeHistoryDocument(
        _ url: URL?,
        routePolicy: DesktopCabinetRoutePolicy
    ) -> Bool {
        guard let url,
              !unsafeHistoryURLs.contains(url),
              safeHistoryURLs.contains(url)
        else { return false }
        return EmbeddedCabinetNavigationPolicy.isSafeDocument(url, routePolicy: routePolicy)
    }

    private func isProtectedMeetingRoute(
        _ url: URL?,
        routePolicy: DesktopCabinetRoutePolicy
    ) -> Bool {
        guard let url else { return false }
        let kind = routePolicy.decision(for: url).route.kind
        switch kind {
        case .meetingList, .meetingDetail, .meetingShare, .meetingDeletionReport,
             .settings, .calendarSettings, .meetingDetectionSettings:
            return true
        default:
            return false
        }
    }

    private func isMeetingList(
        _ url: URL?,
        routePolicy: DesktopCabinetRoutePolicy?
    ) -> Bool {
        guard let url, let routePolicy else { return false }
        let decision = routePolicy.decision(for: url)
        return decision.decision == .allow && decision.route.kind == .meetingList
    }

    private func isMeetingReviewRoute(_ kind: DesktopCabinetRouteKind?) -> Bool {
        switch kind {
        case .meetingDetail, .meetingShare, .meetingDeletionReport:
            return true
        default:
            return false
        }
    }

    private func isMeetingHistoryRoute(_ kind: DesktopCabinetRouteKind) -> Bool {
        switch kind {
        case .meetingList, .meetingDetail, .meetingShare, .meetingDeletionReport:
            return true
        default:
            return false
        }
    }

    private func isAuthRoute(_ kind: DesktopCabinetRouteKind?) -> Bool {
        switch kind {
        case .authLogin, .authSignup, .authProvider, .authCallback:
            return true
        default:
            return false
        }
    }
}

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
        case .artifactDownload, .settings, .calendarSettings, .meetingDetectionSettings, .admin, .authLogin, .authSignup,
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
    public typealias OpenMeetingDetectionSettingsAction = @MainActor @Sendable () -> Void

    private let request: URLRequest
    private let routePolicy: DesktopCabinetRoutePolicy
    private let workspaceZoom: WorkspaceZoomPreference
    private let navigationEventLogger: NavigationEventLogger?
    private let showsAppUpdateBadge: Bool
    private let onCheckForUpdates: CheckForUpdatesAction
    private let onOpenMeetingDetectionSettings: OpenMeetingDetectionSettingsAction
    private let supportIncidentBridge: EmbeddedCabinetSupportIncidentBridge?
    private let fallbackRequest: URLRequest
    private let navigationController: EmbeddedCabinetNavigationController
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
        onOpenMeetingDetectionSettings: @escaping OpenMeetingDetectionSettingsAction = {},
        supportIncidentBridge: EmbeddedCabinetSupportIncidentBridge? = nil,
        fallbackRequest: URLRequest,
        navigationController: EmbeddedCabinetNavigationController
    ) {
        self.request = request
        self.routePolicy = routePolicy
        self.workspaceZoom = workspaceZoom
        self.navigationEventLogger = navigationEventLogger
        self.showsAppUpdateBadge = showsAppUpdateBadge
        self.onCheckForUpdates = onCheckForUpdates
        self.onOpenMeetingDetectionSettings = onOpenMeetingDetectionSettings
        self.supportIncidentBridge = supportIncidentBridge
        self.fallbackRequest = fallbackRequest
        self.navigationController = navigationController
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

    /// Provider, callback, and email form navigations are transient WebKit
    /// pages, not SwiftUI-owned document routes. Keeping one as the last
    /// loaded request makes updateNSView replay a one-time navigation as GET.
    public nonisolated static func shouldTrackSwiftUIRequestIdentity(
        for routeKind: DesktopCabinetRouteKind,
        url: URL? = nil
    ) -> Bool {
        guard ![.authProvider, .authCallback].contains(routeKind) else {
            return false
        }
        guard let url else { return true }
        return ![
            "/login/email/start",
            "/login/email/verify",
            "/sign-up/email/start",
            "/sign-up/email/verify"
        ].contains(url.path)
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
        case .meetingList, .meetingDetail, .meetingShare, .meetingDeletionReport, .settings, .calendarSettings, .meetingDetectionSettings:
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
        context.coordinator.activate()
        EmbeddedCabinetZoomBridge.apply(workspaceZoom, to: webView)
        supportIncidentBridge?.attach(webView: webView, routePolicy: routePolicy)
        navigationController.attach(
            webView: webView,
            routePolicy: routePolicy,
            fallbackRequest: fallbackRequest,
            initialRequest: request,
            sessionExpired: cabinetState == .expiredSession
                || cabinetState == .workspaceReselectionRequired
        )
        context.coordinator.update(
            showsAppUpdateBadge: showsAppUpdateBadge,
            onCheckForUpdates: onCheckForUpdates
        )
        let container = WebViewContainer(webView: webView)
        container.lastLoadedRequestIdentity = Self.loadIdentity(for: request)
        let navigation = webView.load(request)
        navigationController.navigationDidStart(
            webView: webView,
            navigation: navigation,
            targetURL: request.url,
            controllerInitiated: true
        )
        return container
    }

    public func updateNSView(_ container: NSView, context: Context) {
        guard let container = container as? WebViewContainer else { return }
        context.coordinator.update(
            showsAppUpdateBadge: showsAppUpdateBadge,
            onCheckForUpdates: onCheckForUpdates
        )
        supportIncidentBridge?.attach(webView: container.webView, routePolicy: routePolicy)
        navigationController.updateConfiguration(
            routePolicy: routePolicy,
            fallbackRequest: fallbackRequest,
            sessionExpired: cabinetState == .expiredSession
                || cabinetState == .workspaceReselectionRequired
        )
        EmbeddedCabinetZoomBridge.apply(workspaceZoom, to: container.webView)
        context.coordinator.applyUpdateVisibility(to: container.webView)
        guard Self.shouldLoad(request: request, lastLoadedRequestIdentity: container.lastLoadedRequestIdentity) else {
            return
        }
        container.lastLoadedRequestIdentity = Self.loadIdentity(for: request)
        navigationController.observeNavigationRequest(request, webView: container.webView)
        let navigation = container.webView.load(request)
        navigationController.navigationDidStart(
            webView: container.webView,
            navigation: navigation,
            targetURL: request.url,
            controllerInitiated: true
        )
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
            onOpenMeetingDetectionSettings: onOpenMeetingDetectionSettings,
            supportIncidentBridge: supportIncidentBridge,
            navigationController: navigationController
        )
    }

    public static func dismantleNSView(_ nsView: NSView, coordinator: Coordinator) {
        guard let container = nsView as? WebViewContainer else { return }
        coordinator.detachSupportIncidentBridge(from: container.webView)
        coordinator.detachNavigationController(from: container.webView)
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
        private let onOpenMeetingDetectionSettings: OpenMeetingDetectionSettingsAction
        private let supportIncidentBridge: EmbeddedCabinetSupportIncidentBridge?
        private let navigationController: EmbeddedCabinetNavigationController
        private weak var downloadHostWindow: NSWindow?
        private var isActive = true
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
            onOpenMeetingDetectionSettings: @escaping OpenMeetingDetectionSettingsAction,
            supportIncidentBridge: EmbeddedCabinetSupportIncidentBridge?,
            navigationController: EmbeddedCabinetNavigationController
        ) {
            self.routePolicy = routePolicy
            navigationRequestPolicy = DesktopCabinetNavigationRequestPolicy(
                routePolicy: routePolicy,
                desktopHeaders: desktopHeaders
            )
            self.navigationEventLogger = navigationEventLogger
            self.showsAppUpdateBadge = showsAppUpdateBadge
            self.onCheckForUpdates = onCheckForUpdates
            self.onOpenMeetingDetectionSettings = onOpenMeetingDetectionSettings
            self.supportIncidentBridge = supportIncidentBridge
            self.navigationController = navigationController
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
        public func activate() {
            isActive = true
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
        public func detachNavigationController(from webView: WKWebView) {
            isActive = false
            navigationController.detach(webView: webView)
        }

        @MainActor
        public func userContentController(
            _: WKUserContentController,
            didReceive message: WKScriptMessage
        ) {
            guard
                isActive,
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
            guard navigationController.isAttached(to: webView) else {
                decisionHandler(.cancel)
                return
            }
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
                navigationController.cancelPendingNavigation(webView: webView)
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

            if navigationAction.navigationType == .backForward,
               !navigationController.shouldAllowBackForwardNavigation(to: url, in: webView) {
                navigationController.cancelControllerNavigationIfPending(webView: webView)
                decisionHandler(.cancel)
                return
            }
            if navigationAction.navigationType == .reload,
               !navigationController.shouldAllowReload(in: webView) {
                navigationController.cancelControllerNavigationIfPending(webView: webView)
                decisionHandler(.cancel)
                return
            }

            navigationController.observeNavigationRequest(
                navigationAction.request,
                webView: webView,
                allowExternalAuthProvider: authContinuationActive || isAuthRoute(webView.url)
            )

            let decision = routePolicy.decision(
                for: url,
                allowExternalAuthProvider: authContinuationActive || isAuthRoute(webView.url)
            )
            if decision.decision == .allow,
               decision.route.kind == .meetingDetectionSettings {
                navigationController.cancelPendingNavigation(webView: webView)
                onOpenMeetingDetectionSettings()
                decisionHandler(.cancel)
                return
            }
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
                        trackPendingRoute(reloadedRequest, webView: webView)
                        navigationController.observeNavigationRequest(
                            reloadedRequest,
                            webView: webView,
                            allowExternalAuthProvider: authContinuationActive || isAuthRoute(webView.url)
                        )
                    }
                    guard let replacementNavigation = webView.load(reloadedRequest) else {
                        navigationController.navigationDidCancel(
                            webView: webView,
                            expectedURL: reloadedRequest.url
                        )
                        decisionHandler(.cancel)
                        return
                    }
                    navigationController.navigationDidStart(
                        webView: webView,
                        navigation: replacementNavigation,
                        targetURL: reloadedRequest.url,
                        controllerInitiated: true
                    )
                    decisionHandler(.cancel)
                    return
                }
                if decision.route.kind != .artifactDownload {
                    cabinetState = .loading
                    trackPendingRoute(navigationAction.request, webView: webView)
                }
                decisionHandler(.allow)
            case .openExternally:
                authContinuationActive = false
                navigationController.clearPendingNavigation(webView: webView)
                guard let sanitizedURL = routePolicy.sanitizedExternalURL(for: url) else {
                    cabinetState = .blockedRoute
                    decisionHandler(.cancel)
                    return
                }
                NSWorkspace.shared.open(sanitizedURL)
                decisionHandler(.cancel)
            case .blockWithMessage:
                authContinuationActive = false
                navigationController.cancelPendingNavigation(webView: webView)
                cabinetState = .blockedRoute
                decisionHandler(.cancel)
            }
        }

        @MainActor
        public func webView(
            _ webView: WKWebView,
            navigationAction: WKNavigationAction,
            didBecome download: WKDownload
        ) {
            guard navigationController.isAttached(to: webView) else { return }
            downloadHostWindow = webView.window
            download.delegate = self
            navigationController.navigationDidFinish(
                webView: webView,
                expectedURL: navigationAction.request.url
            )
        }

        @MainActor
        public func webView(
            _ webView: WKWebView,
            navigationResponse: WKNavigationResponse,
            didBecome download: WKDownload
        ) {
            guard navigationController.isAttached(to: webView) else { return }
            downloadHostWindow = webView.window
            download.delegate = self
            navigationController.navigationDidFinish(
                webView: webView,
                expectedURL: navigationResponse.response.url
            )
        }

        @MainActor
        public func download(
            _ download: WKDownload,
            decideDestinationUsing _: URLResponse,
            suggestedFilename: String,
            completionHandler: @escaping @MainActor @Sendable (URL?) -> Void
        ) {
            guard isActive else {
                completionHandler(nil)
                return
            }
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
                guard let self, self.isActive else {
                    completionHandler(nil)
                    return
                }
                let destination = EmbeddedCabinetWebView.nativeSaveDestination(
                    response: response,
                    selectedURL: panel.url
                )
                self.downloadHostWindow = nil
                if destination == nil {
                    self.logNavigationEvent(
                        "cabinet_download_cancelled",
                        detail: "result=cancelled"
                    )
                } else {
                    self.logNavigationEvent("cabinet_download_started", detail: "result=started")
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
            guard isActive else { return }
            logNavigationEvent("cabinet_download_finished", detail: "result=completed")
        }

        @MainActor
        public func download(
            _: WKDownload,
            didFailWithError error: Error,
            resumeData _: Data?
        ) {
            guard isActive else { return }
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
            guard isActive, navigationController.isAttached(to: webView) else {
                completionHandler(nil)
                return
            }
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

            let complete: (NSApplication.ModalResponse) -> Void = { [weak self] response in
                guard let self, self.isActive else {
                    completionHandler(nil)
                    return
                }
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
        public func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            guard navigationController.isAttached(to: webView) else { return }
            guard navigationController.navigationDidFinish(webView: webView, navigation: navigation) else { return }
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
            if EmbeddedCabinetWebView.shouldTrackSwiftUIRequestIdentity(for: routeDecision.route.kind, url: url),
               let container = webView.superview as? WebViewContainer {
                // Transient auth pages must not replace the stable SwiftUI
                // request while WebKit owns the continuation.
                container.lastLoadedRequestIdentity = EmbeddedCabinetWebView.loadIdentity(url: url)
            }
            if EmbeddedCabinetWebView.shouldTrackSwiftUIRequestIdentity(for: routeDecision.route.kind, url: url) {
                currentRoute = EmbeddedCabinetWebView.trackedRoute(current: currentRoute, loaded: url)
            }
            cabinetState = finishedState
            applyUpdateVisibility(to: webView)
            logNavigationEvent(
                "cabinet_navigation_finished",
                detail: "state=\(finishedState.rawValue) \(urlLogDetail(url))"
            )
        }

        @MainActor
        public func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationResponse: WKNavigationResponse,
            decisionHandler: @escaping @MainActor @Sendable (WKNavigationResponsePolicy) -> Void
        ) {
            guard navigationController.isAttached(to: webView) else {
                decisionHandler(.cancel)
                return
            }
            switch DesktopCabinetNavigationResponsePolicy(routePolicy: routePolicy).decision(
                forNavigationResponse: navigationResponse.response,
                isForMainFrame: navigationResponse.isForMainFrame
            ) {
            case .allow:
                decisionHandler(.allow)
            case .download:
                navigationController.navigationDidFinish(
                    webView: webView,
                    expectedURL: navigationResponse.response.url
                )
                logNavigationEvent(
                    "cabinet_download_response",
                    detail: responseLogDetail(navigationResponse.response, state: .ready)
                )
                decisionHandler(.download)
            case .cancelResource:
                navigationController.navigationDidFinish(
                    webView: webView,
                    expectedURL: navigationResponse.response.url
                )
                logNavigationEvent(
                    "cabinet_download_response_blocked",
                    detail: responseLogDetail(navigationResponse.response, state: cabinetState)
                )
                decisionHandler(.cancel)
            case let .cancel(state):
                navigationController.navigationDidCancel(
                    webView: webView,
                    expectedURL: navigationResponse.response.url
                )
                if state == .expiredSession || state == .workspaceReselectionRequired {
                    navigationController.markSessionExpired(webView: webView)
                }
                cabinetState = state
                logNavigationEvent(
                    "cabinet_navigation_response_blocked",
                    detail: responseLogDetail(navigationResponse.response, state: state)
                )
                decisionHandler(.cancel)
            }
        }

        @MainActor
        public func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            guard navigationController.isAttached(to: webView) else { return }
            guard navigationController.navigationDidFail(webView: webView, navigation: navigation, error: error) else { return }
            transitionAfterNavigationFailure(error, webView: webView, phase: "committed")
        }

        @MainActor
        public func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            guard navigationController.isAttached(to: webView) else { return }
            guard navigationController.navigationDidFail(webView: webView, navigation: navigation, error: error) else { return }
            transitionAfterNavigationFailure(error, webView: webView, phase: "provisional")
        }

        @MainActor
        public func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) {
            guard navigationController.isAttached(to: webView) else { return }
            navigationController.navigationDidStart(webView: webView, navigation: navigation)
        }

        private func transitionAfterNavigationFailure(_ error: Error, webView: WKWebView, phase: String) {
            let previousState = cabinetState
            let nextState = DesktopCabinetState.state(forNavigationError: error, currentState: cabinetState)
            cabinetState = nextState
            if nextState == .expiredSession || nextState == .workspaceReselectionRequired {
                navigationController.markSessionExpired(webView: webView)
            }
            logNavigationEvent(
                "cabinet_navigation_failed",
                detail: errorLogDetail(error, webViewURL: webView.url, phase: phase, from: previousState, to: nextState)
            )
        }

        private func logNavigationEvent(_ event: String, detail: String) {
            navigationEventLogger?(event, detail)
        }

        private func trackPendingRoute(_ request: URLRequest, webView: WKWebView) {
            guard let url = request.url else { return }
            let routeKind = routePolicy.decision(
                for: url,
                allowExternalAuthProvider: authContinuationActive
            ).route.kind
            if EmbeddedCabinetWebView.shouldTrackSwiftUIRequestIdentity(for: routeKind, url: url) {
                currentRoute = url
                if let container = webView.superview as? WebViewContainer {
                    // SwiftUI rebuilds the request from the route as a GET.
                    // Keep its identity in sync so the in-flight WebKit
                    // navigation is not started a second time by updateNSView.
                    container.lastLoadedRequestIdentity = EmbeddedCabinetWebView.loadIdentity(url: url)
                }
            }
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

@MainActor
public final class EmbeddedCabinetNavigationController: ObservableObject {
    @Published public private(set) var canGoBack = false
    @Published public private(set) var canGoForward = false
    @Published public private(set) var canReload = false
    @Published public private(set) var isLoading = false

    @Published public private(set) var sessionBoundaryID = UUID()

    public init() {}

    public func goBack() {}
    public func goForward() {}
    public func reload() {}
}

public struct EmbeddedCabinetWebView: View {
    public typealias NavigationEventLogger = @MainActor @Sendable (_ event: String, _ detail: String) -> Void
    public typealias CheckForUpdatesAction = @MainActor @Sendable () -> Void
    public typealias OpenMeetingDetectionSettingsAction = @MainActor @Sendable () -> Void

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
        onOpenMeetingDetectionSettings _: @escaping OpenMeetingDetectionSettingsAction = {},
        supportIncidentBridge _: EmbeddedCabinetSupportIncidentBridge? = nil,
        fallbackRequest _: URLRequest,
        navigationController _: EmbeddedCabinetNavigationController
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

    public nonisolated static func shouldTrackSwiftUIRequestIdentity(
        for _: DesktopCabinetRouteKind,
        url _: URL? = nil
    ) -> Bool {
        true
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
