import Foundation
import XCTest
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

@MainActor
final class DesktopNotificationHistoryTests: XCTestCase {
    func testHistoryKeepsFiftyNewestNeutralResultsOnlyInMemory() throws {
        let f = try notificationFixture(self, requiresScreen: false)
        let p = f.presenter()
        var prefs = p.preferences; prefs.quiet = true
        XCTAssertTrue(p.save(prefs))
        let first = f.now
        for _ in 0..<55 {
            XCTAssertFalse(p.presentShortRecording())
            f.now = f.now.addingTimeInterval(1)
        }
        XCTAssertEqual(p.history.count, 50)
        XCTAssertEqual(p.history.first?.occurredAt, first.addingTimeInterval(54))
        XCTAssertEqual(p.history.last?.occurredAt, first.addingTimeInterval(5))
        XCTAssertEqual(Set(p.history.map(\.id)).count, 50)
        XCTAssertTrue(p.history.allSatisfy {
            $0.kind == .shortRecording && $0.message == "Запись не сохранена — короче 30 секунд"
        })
        let restored = f.presenter()
        XCTAssertTrue(restored.history.isEmpty)
        XCTAssertTrue(restored.preferences.quiet)
    }

    func testHistoryClearsForAccountWorkspaceOriginAndLogout() throws {
        let f = try notificationFixture(self, requiresScreen: false)
        let p = f.presenter(screens: [])
        for (user, workspace, origin) in [
            ("other", "workspace", "https://one.test"),
            ("other", "new-workspace", "https://one.test"),
            ("other", "new-workspace", "https://two.test")
        ] {
            _ = p.presentShortRecording()
            XCTAssertEqual(p.history.count, 1)
            let epoch = p.presentationEpoch
            p.updateContext(user: user, workspace: workspace, serverOrigin: origin)
            XCTAssertTrue(p.history.isEmpty)
            XCTAssertGreaterThan(p.presentationEpoch, epoch)
        }
        _ = p.presentShortRecording()
        p.invalidate()
        XCTAssertTrue(p.history.isEmpty)
        XCTAssertFalse(p.canEdit)
    }

    func testQuietIncidentIsRecordedOnceAndRecursOnlyAfterObservedRecovery() async throws {
        let f = try notificationFixture(self, requiresScreen: false)
        let p = f.presenter()
        var prefs = p.preferences; prefs.quiet = true
        XCTAssertTrue(p.save(prefs))
        var item = f.item(); f.bind(item)
        let failed = f.snapshot([item])
        await p.updateSnapshot(failed)?.value
        for _ in 0..<10 { await p.refreshLocal(failed) }
        XCTAssertEqual(p.history.map(\.kind), [.problem])
        XCTAssertEqual(p.history.first?.message, "Запись требует вашего внимания")
        XCTAssertNil(p.card.presentedContent)
        // Disappearance is not evidence of resolution.
        await p.updateSnapshot(f.snapshot([]))?.value
        await p.updateSnapshot(failed)?.value
        XCTAssertEqual(p.history.count, 1)
        item.state = .queued
        await p.updateSnapshot(f.snapshot([item]))?.value
        await p.updateSnapshot(failed)?.value
        XCTAssertEqual(p.history.count, 2)
    }

    func testHistoryHasNoContentFieldsAndNoPreviewOrTicks() async throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        await p.testNotification()
        for _ in 0..<4 { f.now = f.now.addingTimeInterval(1); p.card.refresh() }
        XCTAssertTrue(p.history.isEmpty)
        try notificationClose(p)
        XCTAssertTrue(p.presentShortRecording())
        let entry = try XCTUnwrap(p.history.first)
        XCTAssertEqual(Set(Mirror(reflecting: entry).children.compactMap(\.label)),
                       Set(["id", "occurredAt", "kind"]))
        for fragment in ["Private meeting", "https://", "session", "transcript", "/Users/"] {
            XCTAssertFalse(entry.message.contains(fragment))
        }
    }

    func testFailedPlacementStillRetainsShortAndProblemResults() async throws {
        let f = try notificationFixture(self, requiresScreen: false)
        let p = f.presenter(screens: [])
        XCTAssertFalse(p.presentShortRecording())
        let item = f.item(); f.bind(item)
        await p.updateSnapshot(f.snapshot([item]))?.value
        XCTAssertNil(p.card.presentedContent)
        XCTAssertEqual(p.history.map(\.kind), [.problem, .shortRecording])
        XCTAssertEqual(f.sounds, 0)
    }

    func testRejectedSaveDoesNotChangeActivePreferencesOrInventAnOwner() throws {
        let f = try notificationFixture(self, requiresScreen: false)
        let p = f.presenter()
        p.invalidate()
        var prefs = p.preferences; prefs.quiet = true
        XCTAssertFalse(p.save(prefs))
        XCTAssertTrue(p.saveFailed)
        XCTAssertFalse(p.preferences.quiet)
        XCTAssertTrue(p.draft.quiet)
        XCTAssertFalse(p.canEdit)
    }
}
