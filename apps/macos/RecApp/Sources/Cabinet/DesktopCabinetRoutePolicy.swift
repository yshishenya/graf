import Foundation

public enum DesktopCabinetRouteKind: String, Equatable, Sendable {
    case meetingList
    case meetingDetail
    case meetingShare
    case meetingDeletionReport
    case artifactDownload
    case settings
    case calendarSettings
    case meetingDetectionSettings
    case admin
    case authLogin
    case authSignup
    case authProvider
    case authCallback
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
    case allowedMeetingShare = "allowed_meeting_share"
    case allowedMeetingDeletionReport = "allowed_meeting_deletion_report"
    case allowedArtifactDownload = "allowed_artifact_download"
    case allowedSettings = "allowed_settings"
    case allowedCalendarSettings = "allowed_calendar_settings"
    case allowedMeetingDetectionSettings = "allowed_meeting_detection_settings"
    case allowedAuthLogin = "allowed_auth_login"
    case allowedAuthSignup = "allowed_auth_signup"
    case allowedAuthProvider = "allowed_auth_provider"
    case allowedAuthCallback = "allowed_auth_callback"
    case blockedFutureGovernance = "blocked_future_governance"
    case blockedNativeCaptureControl = "blocked_native_capture_control"
    case blockedLocalFileOrDiagnostic = "blocked_local_file_or_diagnostic"
    case blockedReviewUnavailable = "blocked_review_unavailable"
    case blockedUnknownRoute = "blocked_unknown_route"
    case openExternalSafeLink = "open_external_safe_link"
    case openBrowserOwnedBilling = "open_browser_owned_billing"
    case openBrowserOwnedAccount = "open_browser_owned_account"
    case openBrowserOwnedAdmin = "open_browser_owned_admin"
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

    public func decision(for url: URL, allowExternalAuthProvider: Bool = false) -> DesktopCabinetRouteDecision {
        guard let scheme = url.scheme?.lowercased(), scheme == "http" || scheme == "https" else {
            return block(path: url.path, kind: .unsupported, reason: .invalidURL, message: "This meeting route cannot be opened.")
        }
        guard sameOrigin(url) else {
            if allowExternalAuthProvider && scheme == "https" {
                return DesktopCabinetRouteDecision(
                    route: DesktopCabinetRoute(path: normalizedPath(url.path), kind: .authProvider),
                    decision: .allow,
                    reason: .allowedAuthProvider,
                    userMessage: "Auth provider"
                )
            }
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
        if isAuthCallbackRoute(components) {
            return DesktopCabinetRouteDecision(
                route: DesktopCabinetRoute(path: path, kind: .authCallback),
                decision: .allow,
                reason: .allowedAuthCallback,
                userMessage: "Auth callback"
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
        if components == ["desktop", "shared-with-me"] {
            return DesktopCabinetRouteDecision(
                route: DesktopCabinetRoute(path: path, kind: .meetingList),
                decision: .allow,
                reason: .allowedMeetingList,
                userMessage: "Shared meeting list"
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
        if components.count == 4,
           components[0] == "desktop",
           components[1] == "meetings",
           isSafeMeetingId(components[2]),
           components[3] == "share" {
            return DesktopCabinetRouteDecision(
                route: DesktopCabinetRoute(path: path, meetingId: components[2], kind: .meetingShare),
                decision: .allow,
                reason: .allowedMeetingShare,
                userMessage: "Meeting sharing"
            )
        }
        if components.count == 5,
           components[0] == "desktop",
           components[1] == "meetings",
           isSafeMeetingId(components[2]),
           components[3] == "calendar-context",
           ["choose", "continue-without", "clear"].contains(components[4]) {
            return DesktopCabinetRouteDecision(
                route: DesktopCabinetRoute(
                    path: path,
                    meetingId: components[2],
                    kind: .meetingDetail
                ),
                decision: .allow,
                reason: .allowedMeetingDetail,
                userMessage: "Meeting calendar context"
            )
        }
        if components.count == 4,
           components[0] == "desktop",
           components[1] == "meetings",
           isSafeMeetingId(components[2]),
           components[3] == "deletion-report" {
            return DesktopCabinetRouteDecision(
                route: DesktopCabinetRoute(path: path, meetingId: components[2], kind: .meetingDeletionReport),
                decision: .allow,
                reason: .allowedMeetingDeletionReport,
                userMessage: "Meeting deletion report"
            )
        }
        if isArtifactDownloadRoute(components) {
            return DesktopCabinetRouteDecision(
                route: DesktopCabinetRoute(
                    path: path,
                    meetingId: components[4],
                    kind: .artifactDownload
                ),
                decision: .allow,
                reason: .allowedArtifactDownload,
                userMessage: "Download meeting artifact"
            )
        }
        if isCalendarSettingsRoute(components) {
            return DesktopCabinetRouteDecision(
                route: DesktopCabinetRoute(path: path, kind: .calendarSettings),
                decision: .allow,
                reason: .allowedCalendarSettings,
                userMessage: "Calendar settings"
            )
        }
        if isMeetingDetectionSettingsRoute(components) {
            return DesktopCabinetRouteDecision(
                route: DesktopCabinetRoute(path: path, kind: .meetingDetectionSettings),
                decision: .allow,
                reason: .allowedMeetingDetectionSettings,
                userMessage: "Meeting detection settings"
            )
        }
        if isSettingsRoute(components) {
            return DesktopCabinetRouteDecision(
                route: DesktopCabinetRoute(path: path, kind: .settings),
                decision: .allow,
                reason: .allowedSettings,
                userMessage: "Settings"
            )
        }
        if isAdminRoute(components) {
            return DesktopCabinetRouteDecision(
                route: DesktopCabinetRoute(path: path, kind: .admin),
                decision: .openExternally,
                reason: .openBrowserOwnedAdmin,
                userMessage: "Open workspace admin in your browser."
            )
        }
        if isBrowserOwnedBillingRoute(components) {
            return DesktopCabinetRouteDecision(
                route: DesktopCabinetRoute(path: path, kind: .external),
                decision: .openExternally,
                reason: .openBrowserOwnedBilling,
                userMessage: "Откройте тариф и оплату в браузере."
            )
        }
        if isBrowserOwnedAccountRoute(components) {
            return DesktopCabinetRouteDecision(
                route: DesktopCabinetRoute(path: path, kind: .external),
                decision: .openExternally,
                reason: .openBrowserOwnedAccount,
                userMessage: "Откройте раздел аккаунта в браузере."
            )
        }
        if isFutureGovernanceRoute(components) {
            return block(path: path, kind: .unsupported, reason: .blockedFutureGovernance, message: "This action opens in a future browser-owned release.")
        }
        if isNativeCaptureControlRoute(components) {
            return block(path: path, kind: .forbiddenAction, reason: .blockedNativeCaptureControl, message: "This local control stays in the app shell.")
        }
        if isLocalFileOrDiagnosticRoute(components) {
            return block(path: path, kind: .forbiddenAction, reason: .blockedLocalFileOrDiagnostic, message: "This local diagnostic stays in the app shell.")
        }
        return block(path: path, kind: .unsupported, reason: .blockedUnknownRoute, message: "This meeting route is not available in the desktop workspace.")
    }

    /// Return only the browser-owned origin/path. Query and fragment values
    /// may contain payment, provider, promo or referral data and never cross
    /// the desktop-to-browser boundary.
    public func sanitizedExternalURL(for url: URL) -> URL? {
        guard decision(for: url).decision == .openExternally else { return nil }
        var components = URLComponents(url: url, resolvingAgainstBaseURL: false)
        components?.query = nil
        components?.fragment = nil
        return components?.url
    }

    public func reviewDecision(
        for url: URL,
        reviewAvailableMeetingIds: Set<String>
    ) -> DesktopCabinetRouteDecision {
        let decision = decision(for: url)
        guard decision.decision == .allow,
              [.meetingDetail, .meetingShare].contains(decision.route.kind),
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

    private func isLoginRoute(_ components: [String]) -> Bool {
        components.first == "login"
    }

    private func isSignupRoute(_ components: [String]) -> Bool {
        components.first == "sign-up"
    }

    private func isAuthCallbackRoute(_ components: [String]) -> Bool {
        components.count == 5 &&
            components[0] == "api" &&
            components[1] == "v1" &&
            components[2] == "auth" &&
            components[3] == "callback" &&
            isSafeProviderId(components[4])
    }

    private func isSafeProviderId(_ value: String) -> Bool {
        !value.isEmpty && value.range(of: #"^[A-Za-z0-9_.-]+$"#, options: .regularExpression) != nil
    }

    private func isCalendarSettingsRoute(_ components: [String]) -> Bool {
        guard components.count >= 4,
              components[0] == "desktop",
              components[1] == "settings",
              components[2] == "integrations",
              components[3] == "calendar"
        else {
            return false
        }
        if components.count == 4 {
            return true
        }
        if components == ["desktop", "settings", "integrations", "calendar", "provider-result"] {
            return true
        }
        if components == ["desktop", "settings", "integrations", "calendar", "preferences"] {
            return true
        }
        if components.count == 7,
           components[4] == "providers",
           isSafeMeetingId(components[5]),
           components[6] == "connect" {
            return true
        }
        if components.count == 7,
           components[4] == "sources",
           isSafeMeetingId(components[5]),
           ["calendars", "sync", "disconnect"].contains(components[6]) {
            return true
        }
        return false
    }

    private func isMeetingDetectionSettingsRoute(_ components: [String]) -> Bool {
        components == ["desktop", "settings", "meeting-detection"]
    }

    private func isSettingsRoute(_ components: [String]) -> Bool {
        if components.count >= 2,
           components[0] == "desktop",
           components[1] == "account" {
            let tail = Array(components.dropFirst(2))
            return tail.isEmpty || (tail.count == 1 && ["profile", "security", "notifications"].contains(tail[0]))
        }
        guard components.count >= 2,
              components[0] == "desktop",
              components[1] == "settings"
        else {
            return false
        }

        let tail = Array(components.dropFirst(2))
        if tail.isEmpty || (tail.count == 1 && ["recording", "summaries", "workspace", "account", "notifications"].contains(tail[0])) {
            return true
        }
        if tail.count == 2,
           tail[0] == "account",
           ["profile", "security", "notifications"].contains(tail[1]) {
            return true
        }
        if tail.count == 4,
           tail[0] == "account",
           tail[1] == "devices",
           tail[3] == "revoke" {
            return isSafeMeetingId(tail[2])
        }
        if tail.count == 4,
           tail[0] == "account",
           tail[1] == "sessions",
           tail[3] == "revoke" {
            return isSafeMeetingId(tail[2])
        }
        if tail.count == 3,
           tail[0] == "account",
           ["devices", "sessions"].contains(tail[1]),
           tail[2] == "revoke-others" {
            return true
        }
        if tail.count == 2, tail[0] == "provider-links" {
            return isSafeMeetingId(tail[1])
        }
        if tail.count == 3, tail[0] == "provider-links" {
            if tail[2] == "start" {
                return isSafeProviderId(tail[1])
            }
            return tail[2] == "confirm" && isSafeMeetingId(tail[1])
        }
        if tail.count == 4,
           tail[0] == "account",
           tail[1] == "providers",
           tail[3] == "unlink" {
            return isSafeMeetingId(tail[2])
        }
        if tail.count == 3, tail[0] == "spaces", tail[2] == "activate" {
            return isSafeMeetingId(tail[1])
        }
        if tail.count == 3, tail[0] == "join-offers", ["accept", "reject"].contains(tail[2]) {
            return isSafeMeetingId(tail[1])
        }
        return false
    }

    private func isArtifactDownloadRoute(_ components: [String]) -> Bool {
        components.count == 7 &&
            components[0] == "api" &&
            components[1] == "v1" &&
            components[2] == "cabinet" &&
            components[3] == "meetings" &&
            isSafeMeetingId(components[4]) &&
            components[5] == "downloads" &&
            ["audio", "transcript", "summary"].contains(components[6])
    }

    private func isFutureGovernanceRoute(_ components: [String]) -> Bool {
        hasAnySegment(
            components,
            [
                "admin",
                "billing",
                "delete",
                "deletion",
                "download",
                "export",
                "retention",
                "settings",
                "share"
            ]
        )
    }

    private func isAdminRoute(_ components: [String]) -> Bool {
        components.first?.lowercased() == "admin"
    }

    private func isBrowserOwnedBillingRoute(_ components: [String]) -> Bool {
        guard components.first == "billing" else { return false }
        if components.count == 1 { return true }
        if components.count == 2 {
            return ["plans", "usage", "subscription", "payment-method", "checkout", "history", "discounts", "storage"].contains(components[1])
        }
        if components == ["billing", "checkout", "return"] { return true }
        if components.count == 4 && components[1] == "checkout" && components[2] == "status" {
            return isSafeMeetingId(components[3])
        }
        return components.count == 3 && components[1] == "invoices" && isSafeMeetingId(components[2])
    }

    private func isBrowserOwnedAccountRoute(_ components: [String]) -> Bool {
        components == ["referrals"] || components == ["account", "referrals"]
    }

    private func isNativeCaptureControlRoute(_ components: [String]) -> Bool {
        // Keep stale legacy route names denied so an old server link cannot
        // cross the native capture-control trust boundary.
        hasAnySegment(
            components,
            [
                "audio-devices",
                "capture",
                "device",
                "devices",
                "driver",
                "microphone",
                "permission",
                "permissions",
                "record",
                "speaker",
                "stop",
                "system-audio"
            ]
        )
    }

    private func isLocalFileOrDiagnosticRoute(_ components: [String]) -> Bool {
        hasAnySegment(
            components,
            [
                "bundle",
                "diagnostic",
                "diagnostics",
                "file",
                "files",
                "local",
                "picker",
                "purge",
                "upload"
            ]
        )
    }

    private func hasAnySegment(_ components: [String], _ blockedSegments: Set<String>) -> Bool {
        components.contains { blockedSegments.contains($0.lowercased()) }
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
