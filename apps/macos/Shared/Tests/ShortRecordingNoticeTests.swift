import AppKit
import XCTest
@testable import TwoBrainRecAppCore

final class ShortRecordingNoticeTests: XCTestCase {
    @MainActor
    func testPassiveNoticeReplacesDismissesAndExpires() async throws {
        let presenter = DesktopRecordingNoticePresenter()
        defer { presenter.dismiss() }
        presenter.showShortRecordingDiscarded()
        let first = try XCTUnwrap(presenter.panel)
        XCTAssertFalse(first.canBecomeKey)
        XCTAssertFalse(first.canBecomeMain)
        XCTAssertTrue(first.styleMask.contains(.nonactivatingPanel))
        XCTAssertTrue(first.ignoresMouseEvents)
        presenter.showShortRecordingDiscarded()
        XCTAssertFalse(first.isVisible)
        XCTAssertTrue(presenter.panel !== first)
        presenter.dismiss()
        XCTAssertNil(presenter.panel)
        presenter.showShortRecordingDiscarded()
        try await Task.sleep(for: .milliseconds(6_200))
        XCTAssertNil(presenter.panel)
    }
}
