import Foundation

public enum DesktopCabinetRouteKind: String, Equatable, Sendable {
    case meetingList
    case meetingDetail
    case authLogin
    case authSignup
    case unsupported
    case external
    case forbiddenAction
}

public struct DesktopCabinetRoute: Equatable, Sendable {
    public let path: String
    public let meetingId: String?
    public let kind: DesktopCabinetRouteKind

    public init(path: String, meetingId: String? = nil, kind: DesktopCabinetRouteKind) {
        self.path = path
        self.meetingId = meetingId
        self.kind = kind
    }
}

public enum DesktopCabinetRouteAction: String, Equatable, Sendable {
    case allow
    case blockWithMessage
    case openExternally
}

public enum DesktopCabinetRouteDecisionReason: String, Equatable, Sendable {
    case allowedMeetingList = "allowed_meeting_list"
    case allowedMeetingDetail = "allowed_meeting_detail"
    case allowedAuthLogin = "allowed_auth_login"
    case allowedAuthSignup = "allowed_auth_signup"
    case blockedFutureGovernance = "blocked_future_governance"
    case blockedNativeCaptureControl = "blocked_native_capture_control"
    case blockedLocalFileOrDiagnostic = "blocked_local_file_or_diagnostic"
    case blockedReviewUnavailable = "blocked_review_unavailable"
    case blockedUnknownRoute = "blocked_unknown_route"
    case openExternalSafeLink = "open_external_safe_link"
    case invalidURL = "invalid_url"
}

public struct DesktopCabinetRouteDecision: Equatable, Sendable {
    public let route: DesktopCabinetRoute
    public let decision: DesktopCabinetRouteAction
    public let reason: DesktopCabinetRouteDecisionReason
    public let userMessage: String

    public init(
        route: DesktopCabinetRoute,
        decision: DesktopCabinetRouteAction,
        reason: DesktopCabinetRouteDecisionReason,
        userMessage: String
    ) {
        self.route = route
        self.decision = decision
        self.reason = reason
        self.userMessage = userMessage
    }
}

public struct DesktopCabinetRoutePolicy: Equatable, Sendable {
    private let baseURL: URL

    public init(baseURL: URL) {
        self.baseURL = DesktopCabinetConfiguration(baseURL: baseURL).baseURL
    }

    public func decision(for url: URL) -> DesktopCabinetRouteDecision {
        guard let scheme = url.scheme?.lowercased(), scheme == "http" || scheme == "https" else {
            return block(path: url.path, kind: .unsupported, reason: .invalidURL, message: "This meeting route cannot be opened.")
        }
        guard sameOrigin(url) else {
            return externalDecision(for: url)
        }

        let path = normalizedPath(url.path)
        let components = path.split(separator: "/").map(String.init)
        if isLoginRoute(components) {
            return DesktopCabinetRouteDecision(
                route: DesktopCabinetRoute(path: path, kind: .authLogin),
                decision: .allow,
                reason: .allowedAuthLogin,
                userMessage: "Login"
            )
        }
        if isSignupRoute(components) {
            return DesktopCabinetRouteDecision(
                route: DesktopCabinetRoute(path: path, kind: .authSignup),
                decision: .allow,
                reason: .allowedAuthSignup,
                userMessage: "Sign up"
            )
        }
        if components == ["desktop", "meetings"] {
            return DesktopCabinetRouteDecision(
                route: DesktopCabinetRoute(path: path, kind: .meetingList),
                decision: .allow,
                reason: .allowedMeetingList,
                userMessage: "Meeting list"
            )
        }
        if components.count == 3,
           components[0] == "desktop",
           components[1] == "meetings",
           isSafeMeetingId(components[2]) {
            return DesktopCabinetRouteDecision(
                route: DesktopCabinetRoute(path: path, meetingId: components[2], kind: .meetingDetail),
                decision: .allow,
                reason: .allowedMeetingDetail,
                userMessage: "Meeting detail"
            )
        }
        if containsAny(path, ["share", "export", "download", "delete", "retention", "settings", "billing", "admin"]) {
            return block(path: path, kind: .unsupported, reason: .blockedFutureGovernance, message: "This action opens in a future browser-owned release.")
        }
        if containsAny(path, ["capture", "record", "stop", "microphone", "speaker", "device", "permission", "driver", "system-audio"]) {
            return block(path: path, kind: .forbiddenAction, reason: .blockedNativeCaptureControl, message: "This local control stays in the app shell.")
        }
        if containsAny(path, ["diagnostic", "bundle", "file", "picker", "purge", "local", "upload"]) {
            return block(path: path, kind: .forbiddenAction, reason: .blockedLocalFileOrDiagnostic, message: "This local diagnostic stays in the app shell.")
        }
        return block(path: path, kind: .unsupported, reason: .blockedUnknownRoute, message: "This meeting route is not available in the desktop workspace.")
    }

    public func reviewDecision(
        for url: URL,
        reviewAvailableMeetingIds: Set<String>
    ) -> DesktopCabinetRouteDecision {
        let decision = decision(for: url)
        guard decision.decision == .allow,
              decision.route.kind == .meetingDetail,
              let meetingId = decision.route.meetingId
        else {
            return decision
        }
        guard reviewAvailableMeetingIds.contains(meetingId) else {
            return DesktopCabinetRouteDecision(
                route: decision.route,
                decision: .blockWithMessage,
                reason: .blockedReviewUnavailable,
                userMessage: "This meeting review is not available yet."
            )
        }
        return decision
    }

    private func sameOrigin(_ url: URL) -> Bool {
        url.scheme?.lowercased() == baseURL.scheme?.lowercased() &&
            url.host?.lowercased() == baseURL.host?.lowercased() &&
            (url.port ?? defaultPort(for: url.scheme)) == (baseURL.port ?? defaultPort(for: baseURL.scheme))
    }

    private func externalDecision(for url: URL) -> DesktopCabinetRouteDecision {
        let host = url.host?.lowercased() ?? ""
        if host == "docs.2brain.dev" || host == "help.2brain.dev" {
            return DesktopCabinetRouteDecision(
                route: DesktopCabinetRoute(path: normalizedPath(url.path), kind: .external),
                decision: .openExternally,
                reason: .openExternalSafeLink,
                userMessage: "Open help in your browser."
            )
        }
        return block(path: normalizedPath(url.path), kind: .external, reason: .blockedUnknownRoute, message: "External links are not embedded in the desktop workspace.")
    }

    private func block(
        path: String,
        kind: DesktopCabinetRouteKind,
        reason: DesktopCabinetRouteDecisionReason,
        message: String
    ) -> DesktopCabinetRouteDecision {
        DesktopCabinetRouteDecision(
            route: DesktopCabinetRoute(path: path, kind: kind),
            decision: .blockWithMessage,
            reason: reason,
            userMessage: message
        )
    }

    private func normalizedPath(_ path: String) -> String {
        if path.isEmpty { return "/" }
        return path.hasPrefix("/") ? path : "/\(path)"
    }

    private func isSafeMeetingId(_ value: String) -> Bool {
        !value.isEmpty && value.range(of: #"^[A-Za-z0-9_.-]+$"#, options: .regularExpression) != nil
    }

    private func containsAny(_ path: String, _ needles: [String]) -> Bool {
        let lowered = path.lowercased()
        return needles.contains { lowered.contains($0) }
    }

    private func isLoginRoute(_ components: [String]) -> Bool {
        components.first == "login"
    }

    private func isSignupRoute(_ components: [String]) -> Bool {
        components.first == "sign-up"
    }

    private func defaultPort(for scheme: String?) -> Int? {
        switch scheme?.lowercased() {
        case "http":
            return 80
        case "https":
            return 443
        default:
            return nil
        }
    }
}
