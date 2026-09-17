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
        XCTAssertNotNil(presenter.panel)
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(10))
        while presenter.panel != nil && clock.now < deadline {
            try await Task.sleep(for: .milliseconds(20))
        }
        XCTAssertNil(presenter.panel)
    }
}
