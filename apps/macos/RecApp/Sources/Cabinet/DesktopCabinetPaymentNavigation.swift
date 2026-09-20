import Foundation

/// Outcome of one loaded page inside a payment confirmation chain.
public enum DesktopCabinetPaymentNavigationReport: Equatable, Sendable {
    /// The confirmation chain is still running; keep allowing external hops.
    case continueSession
    /// The chain is over; normal cabinet route rules apply again.
    case stopSession
}

/// Tracks the interactive card payment confirmation chain inside the embedded
/// cabinet.
///
/// A card payment confirmed by redirect is not one navigation but a chain of
/// full-page main-frame navigations: the cabinet checkout page hands the
/// web view over to the payment provider, the provider shows its own pages,
/// the cardholder's bank runs the 3-D Secure step on its own domain, and the
/// chain finally returns to the cabinet. Every hop happens on a different host,
/// so a one-hop allowance cannot cover the chain, and the set of issuer bank
/// domains cannot be enumerated in advance.
///
/// The chain therefore gets a single session with three boundaries:
///
/// * it opens only when a cabinet billing document hands the web view over to a
///   host the server already approved as a payment provider;
/// * it stays open while the web view is off the cabinet origin, so whichever
///   bank domain the card issuer chooses can complete the confirmation;
/// * it closes as soon as the web view loads a cabinet document again, or when
///   its time window expires, so ordinary browsing keeps the strict sandbox.
public struct DesktopCabinetPaymentNavigation: Equatable, Sendable {
    /// Hosts of the payment provider itself. The server validates the
    /// confirmation URL against the same set before handing it to the app.
    public static let allowedProviderHosts: Set<String> = [
        "api.yookassa.ru",
        "api.yookassa.test",
        "yookassa.ru",
        "yookassa.test",
        "yoomoney.ru"
    ]

    /// Upper bound on one confirmation chain. Someone who abandons the payment
    /// page and comes back much later must not resume with a standing
    /// allowance, even if the cabinet document never loaded again.
    public static let defaultTimeLimit: TimeInterval = 15 * 60

    public let sessionOrigin: URL?
    public let timeLimit: TimeInterval
    private let startedAt: Date?

    public init(
        sessionOrigin: URL? = nil,
        startedAt: Date? = nil,
        timeLimit: TimeInterval = defaultTimeLimit
    ) {
        self.sessionOrigin = sessionOrigin
        self.startedAt = startedAt
        self.timeLimit = timeLimit
    }

    /// A chain is live exactly while it has a start time.
    public var isActive: Bool {
        startedAt != nil
    }

    /// External hops are allowed only while a chain is live and within its
    /// bounded confirmation window. Callers evaluate this at the moment they
    /// decide a navigation, before WebKit is allowed to load the next page.
    public func externalProviderNavigationAllowed(at now: Date = Date()) -> Bool {
        guard let startedAt else { return false }
        return now.timeIntervalSince(startedAt) < timeLimit
    }

    /// Open a chain. `isBillingCheckoutDocument` must come from the route
    /// policy alone, and `destination` is the host the cabinet hands over to.
    /// Subdomains are never accepted implicitly: only the exact provider hosts
    /// the server can return as a confirmation URL open a chain.
    public func begin(
        isBillingCheckoutDocument: Bool,
        destination: URL,
        now: Date = Date()
    ) -> Self {
        guard isBillingCheckoutDocument,
              destination.scheme?.lowercased() == "https",
              let host = destination.host?.lowercased(),
              Self.allowedProviderHosts.contains(host)
        else { return self }
        return Self(sessionOrigin: sessionOrigin, startedAt: now, timeLimit: timeLimit)
    }

    /// Decide what a page the cabinet just loaded means for the chain.
    public func report(loadedURL: URL, now: Date = Date()) -> DesktopCabinetPaymentNavigationReport {
        guard let startedAt, now.timeIntervalSince(startedAt) < timeLimit else {
            return .stopSession
        }
        // Off the cabinet origin a live chain keeps running: that is exactly the
        // bank confirmation step, whose domain differs for every card issuer.
        // Any cabinet document means the flow came back, so the chain ends here
        // and the ordinary route sandbox applies again.
        return isOnSessionOrigin(loadedURL) ? .stopSession : .continueSession
    }

    /// Close the chain without changing anything else.
    public func stopped() -> Self {
        Self(sessionOrigin: sessionOrigin, startedAt: nil, timeLimit: timeLimit)
    }

    private func isOnSessionOrigin(_ url: URL) -> Bool {
        guard let sessionOrigin else { return false }
        return DesktopCabinetRoutePolicy(baseURL: sessionOrigin).sharesSessionOrigin(with: url)
    }
}
