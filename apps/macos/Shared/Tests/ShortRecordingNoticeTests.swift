import AppKit
import XCTest
import TwoBrainRecShared
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
        // This is the same stopped + absent-manifest presentation used after discard.
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 20) },
            idFactory: { "synthetic-short" },
            policySnapshotProvider: { "synthetic" }
        )
        _ = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
        _ = try controller.markReady()
        _ = try controller.start()
        _ = try controller.markCapturing()
        _ = try controller.requestStop(reason: .userRequested)
        let stopped = try controller.completeStop()
        XCTAssertEqual(CaptureStatusItem.statusLabel(for: stopped), "Запись остановлена")
        XCTAssertEqual(CaptureControlView.primaryStatus(for: stopped, blockedReason: nil,
                                                       localRecordingStatus: nil), "Запись остановлена")
        presenter.dismissShortRecording()
        XCTAssertFalse(window.isVisible)
        XCTAssertNil(presenter.card.window)
        XCTAssertTrue(presenter.history.contains { $0.kind == .shortRecording })
    }
}
