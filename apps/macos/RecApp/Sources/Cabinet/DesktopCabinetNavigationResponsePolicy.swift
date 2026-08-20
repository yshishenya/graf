import Foundation

public enum DesktopCabinetNavigationResponseDecision: Equatable {
    case allow
    case download
    /// The resource failed, but the document that initiated it remains usable.
    case cancelResource
    case cancel(DesktopCabinetState)
}

public struct DesktopCabinetNavigationResponsePolicy: Equatable {
    private let routePolicy: DesktopCabinetRoutePolicy?

    public init(routePolicy: DesktopCabinetRoutePolicy? = nil) {
        self.routePolicy = routePolicy
    }

    public func decision(forNavigationResponse response: URLResponse, isForMainFrame: Bool) -> DesktopCabinetNavigationResponseDecision {
        guard isForMainFrame else { return .allow }
        guard let httpResponse = response as? HTTPURLResponse else {
            if isArtifactDownload(response.url) {
                return .cancelResource
            }
            return .cancel(.malformedResponse)
        }
        let state = DesktopCabinetState.state(forHTTPResponse: httpResponse)
        if isInteractiveFormDocument(httpResponse, state: state) {
            return .allow
        }
        let isArtifact = isArtifactDownload(httpResponse.url)
        guard let state else {
            guard isArtifact else {
                return .allow
            }
            return Self.isAttachmentResponse(httpResponse) ? .download : .cancelResource
        }
        if isArtifact {
            switch state {
            case .expiredSession, .workspaceReselectionRequired:
                return .cancel(state)
            default:
                return .cancelResource
            }
        }
        return .cancel(state)
    }

    private func isArtifactDownload(_ url: URL?) -> Bool {
        guard let url, let routePolicy else { return false }
        let decision = routePolicy.decision(for: url)
        return decision.decision == .allow && decision.route.kind == .artifactDownload
    }

    private func isInteractiveFormDocument(
        _ response: HTTPURLResponse,
        state: DesktopCabinetState?
    ) -> Bool {
        guard let url = response.url, let routePolicy else { return false }
        let decision = routePolicy.decision(for: url)
        guard decision.decision == .allow else { return false }
        if [.authLogin, .authSignup].contains(decision.route.kind) {
            return true
        }
        guard decision.route.kind == .settings,
              EmbeddedCabinetNavigationPolicy.isEmailLinkFormDocument(url),
              response.mimeType == "text/html",
              state != .expiredSession,
              state != .workspaceReselectionRequired
        else { return false }
        return state == nil
            || [400, 429, 503].contains(response.statusCode)
    }

    private static func isAttachmentResponse(_ response: HTTPURLResponse) -> Bool {
        guard let value = response.value(forHTTPHeaderField: "Content-Disposition") else {
            return false
        }
        return value.split(separator: ";", maxSplits: 1, omittingEmptySubsequences: true)
            .first?
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .caseInsensitiveCompare("attachment") == .orderedSame
    }
}
