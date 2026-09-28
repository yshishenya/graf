import Foundation
import UserNotifications

/// The current center is scoped by macOS to this application's bundle. Cleanup
/// runs on every launch so an installation upgraded again also loses old alerts.
/// This boundary has no authorization, delivery, category or response behavior.
@MainActor
enum DesktopNotificationRetirement {
    static func run() {
        let center = UNUserNotificationCenter.current()
        cleanup(removePending: { center.removeAllPendingNotificationRequests() },
                removeDelivered: { center.removeAllDeliveredNotifications() })
    }

    static func cleanup(removePending: () -> Void, removeDelivered: () -> Void) {
        removePending()
        removeDelivered()
    }
}
