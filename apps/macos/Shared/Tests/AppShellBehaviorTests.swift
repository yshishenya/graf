import AppKit
import XCTest
import TwoBrainRecShared
@testable import TwoBrainRecAppCore

@MainActor
final class AppShellBehaviorTests: XCTestCase {
    func testLocalSettingsSectionsExplainWhatNeedsTheCabinet() {
        XCTAssertEqual(
            LocalSettingsSection.allCases,
            [.account, .recording, .notifications, .calendar, .billing]
        )
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
        store.saveWindowFrame(NSRect(x: 0, y: 0, width: 320, height: 240))
        XCTAssertNotEqual(store.windowFrame, NSRect(x: 0, y: 0, width: 320, height: 240))

        store.saveInspectorExpanded(true)
        XCTAssertTrue(store.inspectorExpanded)
        store.saveSelectedMicrophoneDeviceID("mic-1")
        XCTAssertEqual(store.selectedMicrophoneDeviceID, "mic-1")
        store.saveSelectedMicrophoneDeviceID(nil)
        XCTAssertNil(store.selectedMicrophoneDeviceID)
    }

    func testMicrophoneDisconnectDegradesOnlySelectedDeviceDuringRecording() {
        XCTAssertTrue(RecordingMicrophoneDisconnectPolicy.shouldMarkDegraded(
            disconnectedDeviceID: "mic-selected",
            selectedDeviceID: "mic-selected",
            sessionState: .active
        ))
        XCTAssertTrue(RecordingMicrophoneDisconnectPolicy.shouldMarkDegraded(
            disconnectedDeviceID: "mic-selected",
            selectedDeviceID: "mic-selected",
            sessionState: .paused
        ))
        XCTAssertFalse(RecordingMicrophoneDisconnectPolicy.shouldMarkDegraded(
            disconnectedDeviceID: "mic-other",
            selectedDeviceID: "mic-selected",
            sessionState: .active
        ))
        XCTAssertFalse(RecordingMicrophoneDisconnectPolicy.shouldMarkDegraded(
            disconnectedDeviceID: "mic-selected",
            selectedDeviceID: nil,
            sessionState: .active
        ))
        XCTAssertFalse(RecordingMicrophoneDisconnectPolicy.shouldMarkDegraded(
            disconnectedDeviceID: "mic-selected",
            selectedDeviceID: "mic-selected",
            sessionState: .starting
        ))
    }

    func testTrayStateDistinguishesDegradedAndFailed() {
        XCTAssertEqual(
            GrafTrayRecordingState.resolve(sessionState: .degraded, writerActive: true, stopping: false),
            .degraded
        )
        XCTAssertEqual(
            GrafTrayRecordingState.resolve(sessionState: .failed, writerActive: true, stopping: false),
            .failed
        )
        XCTAssertEqual(GrafTrayRecordingState.degraded.label, "Запись с ограничением")
        XCTAssertEqual(GrafTrayRecordingState.failed.label, "Нужна помощь")
    }

    func testWindowFrameClampsOffscreenAndSmallFrames() {
        let visible = NSRect(x: 0, y: 0, width: 1440, height: 900)
        let offscreen = InterfacePreferencesStore.clampedFrame(
            NSRect(x: 5000, y: 5000, width: 2000, height: 1000),
            to: visible
        )
        XCTAssertEqual(offscreen, NSRect(x: 0, y: 0, width: 1440, height: 900))

        let tooSmall = InterfacePreferencesStore.clampedFrame(
            NSRect(x: 10, y: 20, width: 320, height: 240),
            to: visible
        )
        XCTAssertEqual(tooSmall.size, InterfacePreferencesStore.minimumWindowSize)
        XCTAssertTrue(visible.contains(tooSmall))
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
