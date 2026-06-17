import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

final class WorkspaceZoomTests: XCTestCase {
    func testDefaultBoundsAndStepAreConservative() {
        XCTAssertEqual(WorkspaceZoomPreference.defaultValue, 1.0, accuracy: 0.000_1)
        XCTAssertEqual(WorkspaceZoomPreference.minimumValue, 0.8, accuracy: 0.000_1)
        XCTAssertEqual(WorkspaceZoomPreference.maximumValue, 1.4, accuracy: 0.000_1)
        XCTAssertEqual(WorkspaceZoomPreference.step, 0.1, accuracy: 0.000_1)
        XCTAssertEqual(WorkspaceZoomPreference.default.value, 1.0, accuracy: 0.000_1)
    }

    func testZoomCommandsStepAndClampToSupportedRange() {
        var preference = WorkspaceZoomPreference.default

        preference = preference.applying(.increase)
        XCTAssertEqual(preference.value, 1.1, accuracy: 0.000_1)

        preference = preference.applying(.decrease)
        XCTAssertEqual(preference.value, 1.0, accuracy: 0.000_1)

        for _ in 0..<10 {
            preference = preference.applying(.decrease)
        }
        XCTAssertEqual(preference.value, WorkspaceZoomPreference.minimumValue, accuracy: 0.000_1)

        for _ in 0..<20 {
            preference = preference.applying(.increase)
        }
        XCTAssertEqual(preference.value, WorkspaceZoomPreference.maximumValue, accuracy: 0.000_1)
    }

    func testResetReturnsDefaultZoom() {
        let preference = WorkspaceZoomPreference(value: 1.3).applying(.reset)

        XCTAssertEqual(preference.value, WorkspaceZoomPreference.defaultValue, accuracy: 0.000_1)
    }

    func testMenuMetadataUsesStandardMacZoomShortcuts() {
        let increaseKeys = WorkspaceZoomMenu.items
            .filter { $0.command == .increase }
            .map(\.keyEquivalent)
        let decreaseKeys = WorkspaceZoomMenu.items
            .filter { $0.command == .decrease }
            .map(\.keyEquivalent)
        let resetKeys = WorkspaceZoomMenu.items
            .filter { $0.command == .reset }
            .map(\.keyEquivalent)

        XCTAssertEqual(Set(increaseKeys), Set(["+", "="]))
        XCTAssertEqual(decreaseKeys, ["-"])
        XCTAssertEqual(resetKeys, ["0"])
        XCTAssertFalse(WorkspaceZoomMenu.items.map(\.title).joined(separator: " ").localizedCaseInsensitiveContains("web view"))
        XCTAssertFalse(WorkspaceZoomMenu.items.map(\.title).joined(separator: " ").localizedCaseInsensitiveContains("webkit"))
    }

    func testStorePersistsSupportedZoomChanges() {
        let defaults = isolatedDefaults()
        defer { defaults.removePersistentDomain(forName: defaultsSuiteName) }

        let store = WorkspaceZoomStore(defaults: defaults)
        store.apply(.increase)
        store.apply(.increase)

        let restored = WorkspaceZoomStore(defaults: defaults)
        XCTAssertEqual(restored.preference.value, 1.2, accuracy: 0.000_1)
    }

    func testStoreFallsBackToDefaultForInvalidSavedValues() {
        let defaults = isolatedDefaults()
        defer { defaults.removePersistentDomain(forName: defaultsSuiteName) }

        defaults.set(4.2, forKey: WorkspaceZoomStore.preferenceKey)

        let store = WorkspaceZoomStore(defaults: defaults)

        XCTAssertEqual(store.preference.value, WorkspaceZoomPreference.defaultValue, accuracy: 0.000_1)
    }

    private var defaultsSuiteName: String {
        "WorkspaceZoomTests.\(name)"
    }

    private func isolatedDefaults() -> UserDefaults {
        let defaults = UserDefaults(suiteName: defaultsSuiteName)!
        defaults.removePersistentDomain(forName: defaultsSuiteName)
        return defaults
    }
}
#endif
