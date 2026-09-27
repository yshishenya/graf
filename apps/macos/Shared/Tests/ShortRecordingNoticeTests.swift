import AppKit
import XCTest
@testable import TwoBrainRecAppCore

final class ShortRecordingNoticeTests: XCTestCase {
    @MainActor
    func testShortRecordingUsesTheSingleSharedSurfaceAndCanBeClosed() throws {
        let suite = "F277-short-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        let presenter = DesktopNotificationPresenter(store: .init(defaults: defaults), model: DesktopControlModel())
        presenter.updateContext(user: "synthetic", workspace: "synthetic")
        defer {
            presenter.invalidate()
            defaults.removePersistentDomain(forName: suite)
        }
        XCTAssertTrue(presenter.presentShortRecording())
        let window = try XCTUnwrap(presenter.card.window)
        XCTAssertFalse(window.canBecomeMain)
        XCTAssertTrue(window.styleMask.contains(.nonactivatingPanel))
        XCTAssertEqual(window.identifier?.rawValue, "graf-notification-card")
        XCTAssertEqual(DesktopNotificationCardPresenter.noticeDisplayDuration, 20)
        XCTAssertEqual(presenter.card.presentedContent, .shortRecording)
        XCTAssertTrue(presenter.history.contains { $0.kind == .shortRecording })
        presenter.dismissShortRecording()
        XCTAssertFalse(window.isVisible)
        XCTAssertNil(presenter.card.window)
    }
}
