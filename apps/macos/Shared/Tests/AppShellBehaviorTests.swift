import AppKit
import XCTest
import TwoBrainRecShared
@testable import TwoBrainRecAppCore

@MainActor
final class AppShellBehaviorTests: XCTestCase {
    func testLocalSettingsSectionsExplainWhatNeedsTheCabinet() {
        XCTAssertTrue(LocalSettingsSection.recording.isAvailableLocally)
        XCTAssertTrue(LocalSettingsSection.notifications.isAvailableLocally)
        XCTAssertFalse(LocalSettingsSection.account.isAvailableLocally)
        XCTAssertFalse(LocalSettingsSection.calendar.isAvailableLocally)
        XCTAssertFalse(LocalSettingsSection.billing.isAvailableLocally)
        XCTAssertTrue(LocalSettingsSection.account.unavailableMessage.contains("кабинет"))
        XCTAssertTrue(LocalSettingsSection.calendar.unavailableMessage.contains("кабинет"))
        XCTAssertTrue(LocalSettingsSection.billing.unavailableMessage.contains("кабинет"))
    }

    func testInterfacePreferencesRoundTripAndRejectInvalidFrame() throws {
        let suite = "interface-preferences-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let store = InterfacePreferencesStore(defaults: defaults)

        store.saveWindowFrame(NSRect(x: 10, y: 20, width: 1200, height: 800))
        XCTAssertEqual(store.windowFrame, NSRect(x: 10, y: 20, width: 1200, height: 800))
        store.saveWindowFrame(NSRect(x: 0, y: 0, width: 10, height: 10))
        XCTAssertNotEqual(store.windowFrame, NSRect(x: 0, y: 0, width: 10, height: 10))

        store.saveInspectorExpanded(true)
        XCTAssertTrue(store.inspectorExpanded)
        store.saveSelectedMicrophoneDeviceID("mic-1")
        XCTAssertEqual(store.selectedMicrophoneDeviceID, "mic-1")
        store.saveSelectedMicrophoneDeviceID(nil)
        XCTAssertNil(store.selectedMicrophoneDeviceID)
    }

    func testSelectedMicrophoneClearsWhenDeviceUnavailable() {
        let selection = RecordingMicrophoneSelection(
            selectionId: "synthetic",
            mode: .userSelected,
            inputDeviceId: "missing",
            inputDisplayName: "Missing",
            selectionResult: .unavailable,
            rejectionReason: .deviceUnavailable,
            resolvedAt: Date()
        )
        XCTAssertFalse(selection.isAccepted)
        XCTAssertEqual(selection.rejectionReason, .deviceUnavailable)
    }
}
