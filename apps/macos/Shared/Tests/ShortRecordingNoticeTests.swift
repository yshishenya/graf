import AppKit
import XCTest
@testable import TwoBrainRecAppCore

final class ShortRecordingNoticeTests: XCTestCase {
    @MainActor
    func testPassiveNoticeUsesTheSharedCardAndExpires() async throws {
        let presenter = DesktopRecordingNoticePresenter()
        defer { presenter.dismiss() }
        presenter.showShortRecordingDiscarded()
        let window = try XCTUnwrap(presenter.window)
        XCTAssertFalse(window.canBecomeKey)
        XCTAssertFalse(window.canBecomeMain)
        XCTAssertTrue(window.styleMask.contains(.nonactivatingPanel))
        // Сообщение показывается той же поверхностью, что и остальные
        // уведомления: одна карточка шириной 448 точек.
        XCTAssertEqual(window.frame.width, DesktopNotificationCardPresenter.windowWidth)
        XCTAssertEqual(window.frame.height, DesktopNotificationCardPresenter.windowHeight)
        XCTAssertEqual(window.identifier?.rawValue, "graf-notification-card")
        // На экране всегда одно окно уведомления: повторный показ заменяет
        // предыдущее сообщение, а не добавляет второе окно.
        presenter.showShortRecordingDiscarded()
        let second = try XCTUnwrap(presenter.window)
        XCTAssertTrue(second.isVisible)
        XCTAssertFalse(window.isVisible)
        presenter.dismiss()
        XCTAssertNil(presenter.window)
    }
}
