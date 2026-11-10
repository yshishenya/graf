import Foundation

public struct AccountSwitchResetPlan: Equatable, Sendable {
    public let resetCabinetRoute: Bool
    public let clearCalendarPrompt: Bool
    public let clearPendingCalendarState: Bool
    public let closeLocalPlayer: Bool
    public let clearSelectedRecording: Bool
    public let clearWebBridges: Bool
    public let reloadCabinet: Bool
    public let clearWebStorage: Bool

    public init(
        resetCabinetRoute: Bool = true,
        clearCalendarPrompt: Bool = true,
        clearPendingCalendarState: Bool = true,
        closeLocalPlayer: Bool = true,
        clearSelectedRecording: Bool = true,
        clearWebBridges: Bool = true,
        reloadCabinet: Bool = true,
        clearWebStorage: Bool = true
    ) {
        self.resetCabinetRoute = resetCabinetRoute
        self.clearCalendarPrompt = clearCalendarPrompt
        self.clearPendingCalendarState = clearPendingCalendarState
        self.closeLocalPlayer = closeLocalPlayer
        self.clearSelectedRecording = clearSelectedRecording
        self.clearWebBridges = clearWebBridges
        self.reloadCabinet = reloadCabinet
        self.clearWebStorage = clearWebStorage
    }

    public static let standard = AccountSwitchResetPlan()
}

public enum AccountSwitchResetPolicy {
    public static let storageCleanupTypes: Set<String> = [
        "WKWebsiteDataTypeLocalStorage",
        "WKWebsiteDataTypeSessionStorage"
    ]

    /// Clears only in-page storage for the old document. Cookie reconciliation is
    /// owned by `DesktopCabinetSessionBridge`; the native cookie store remains
    /// authoritative for the new session.
    public static let storageCleanupScript = """
    (() => {
      try { window.localStorage.clear(); } catch (_) {}
      try { window.sessionStorage.clear(); } catch (_) {}
    })();
    """
}
