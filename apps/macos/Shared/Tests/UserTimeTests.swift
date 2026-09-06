import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared
import XCTest

final class UserTimeTests: XCTestCase {
    func testDeviceDatesAcrossMidnightYearAndDST() throws {
        let instant = try XCTUnwrap(ISO8601DateFormatter().date(from: "2026-09-05T21:30:00Z"))
        let zone = try XCTUnwrap(TimeZone(identifier: "Asia/Yekaterinburg"))
        XCTAssertEqual(UserTime.format(instant, timeZone: zone), "06.09.2026, 02:30")
        XCTAssertEqual(UserTime.format(instant, showZone: true, timeZone: zone), "06.09.2026, 02:30 (UTC+05:00)")
        XCTAssertEqual(UserTime.format(instant, dateOnly: true, timeZone: zone), "06.09.2026")
        XCTAssertEqual(UserTime.format(instant, timeOnly: true, timeZone: zone), "02:30")
        let kathmandu = try XCTUnwrap(TimeZone(identifier: "Asia/Kathmandu"))
        XCTAssertEqual(UserTime.format(instant, timeZone: kathmandu), "06.09.2026, 03:15")
        let yearEnd = try XCTUnwrap(ISO8601DateFormatter().date(from: "2026-12-31T21:30:00Z"))
        XCTAssertEqual(UserTime.format(yearEnd, timeZone: zone), "01.01.2027, 02:30")
        let newYork = try XCTUnwrap(TimeZone(identifier: "America/New_York"))
        let before = try XCTUnwrap(ISO8601DateFormatter().date(from: "2026-03-08T06:30:00Z"))
        XCTAssertEqual(UserTime.format(before, timeZone: newYork), "08.03.2026, 01:30")
        XCTAssertEqual(UserTime.format(before.addingTimeInterval(3600), timeZone: newYork), "08.03.2026, 03:30")
        let repeated = try XCTUnwrap(ISO8601DateFormatter().date(from: "2026-11-01T05:30:00Z"))
        XCTAssertEqual(UserTime.format(repeated, showZone: true, timeZone: newYork), "01.11.2026, 01:30 (UTC-04:00)")
        XCTAssertEqual(UserTime.format(repeated.addingTimeInterval(3600), showZone: true, timeZone: newYork), "01.11.2026, 01:30 (UTC-05:00)")
        XCTAssertEqual(UserTime.format(repeated, showZone: true, timeZone: TimeZone(secondsFromGMT: 0)!), "01.11.2026, 05:30 (UTC)")
        for identifier in ["UTC", "GMT", "Etc/UTC", "Etc/GMT"] {
            let utc = try XCTUnwrap(TimeZone(identifier: identifier))
            XCTAssertEqual(UserTime.format(repeated, timeZone: utc), "01.11.2026, 05:30 (UTC)")
        }
        let london = try XCTUnwrap(TimeZone(identifier: "Europe/London"))
        XCTAssertEqual(UserTime.format(repeated, timeZone: london), "01.11.2026, 05:30")
        XCTAssertEqual(UserTime.interval(start: instant, end: instant.addingTimeInterval(86400), timeZone: zone), "06.09.2026, 02:30 — 07.09.2026, 02:30")
        XCTAssertEqual(UserTime.interval(start: instant, end: instant.addingTimeInterval(3600), timeZone: zone), "06.09.2026, 02:30 — 03:30")
    }

    func testRecoveredRowsUseStartAndStableIdentityDespiteProgressUpdates() {
        var old = custodyFixtureQueueItem(id: "a", state: .queued)
        old.recordingMetadata = metadata(start: Date(timeIntervalSince1970: 10))
        old.createdAt = Date(timeIntervalSince1970: 1000)
        var recent = custodyFixtureQueueItem(id: "b", state: .queued)
        recent.createdAt = Date(timeIntervalSince1970: 20)
        XCTAssertEqual(DesktopMeetingShellLocalQueuePolicy.allRowsForLocalMode([old, recent]).map(\.id), ["b", "a"])
        recent.recordingMetadata = old.recordingMetadata
        recent.updatedAt = Date(timeIntervalSince1970: 9000)
        XCTAssertEqual(DesktopMeetingShellLocalQueuePolicy.allRowsForLocalMode([recent, old]).map(\.id), ["a", "b"])
        XCTAssertEqual(old.displayStartedAt, Date(timeIntervalSince1970: 10))
    }

    func testGeneratedTitleUsesViewingZoneAndCustomTitleIsPreserved() throws {
        let start = try XCTUnwrap(ISO8601DateFormatter().date(from: "2026-09-05T21:30:00Z"))
        var value = metadata(start: start)
        let zone = try XCTUnwrap(TimeZone(identifier: "Asia/Yekaterinburg"))
        XCTAssertEqual(value.displayTitle(timeZone: zone), "Zoom — 06.09.2026, 02:30")
        value.titleStatus = .userConfirmed
        XCTAssertEqual(value.displayTitle(timeZone: zone), "Zoom - 2026-09-05 21:30")
        value.titleStatus = .generated
        value.titleSource = .generic
        value.title = "Meeting - 2026-09-05 21:30"
        XCTAssertEqual(value.displayTitle(timeZone: zone), "Запись 06.09.2026, 02:30")
        value.title = "Проект: запуск 2026"
        XCTAssertEqual(value.displayTitle(timeZone: zone), value.title)
        var item = custodyFixtureQueueItem()
        item.recordingMetadata = value
        let row = try XCTUnwrap(EmbeddedCabinetLocalRecordingRow.rows(for: [item], recordingsRootURL: URL(fileURLWithPath: "/tmp/synthetic-user-time")).first)
        XCTAssertEqual(row.startedAt, start)
        XCTAssertEqual(row.title, value.title)
    }

    func testRetentionDeadlineContainsTimeAndZone() {
        let deadline = Date(timeIntervalSince1970: 1_800_000_000)
        let detail = DesktopUploadCustodyCopy.detail(copyKey: "custody.retention_warning", count: 1, deadline: deadline)
        XCTAssertTrue(detail.contains(UserTime.format(deadline, showZone: true)))
    }

    func testBridgeMarksOnlyGeneratedTitleForViewerLocalization() throws {
        var item = custodyFixtureQueueItem()
        item.recordingMetadata = metadata(start: Date(timeIntervalSince1970: 1_800_000_000))
        let row = try XCTUnwrap(EmbeddedCabinetLocalRecordingRow.rows(for: [item], recordingsRootURL: URL(fileURLWithPath: "/tmp/synthetic-user-time")).first)
        XCTAssertEqual(row.generatedTitlePrefix, "Zoom — ")
        item.recordingMetadata?.titleSource = .userConfirmed
        XCTAssertNil(item.recordingMetadata?.generatedDisplayTitlePrefix)
    }

    func testCompactDurationMatchesWebWithoutChangingElapsedSeconds() {
        for (seconds, expected) in [(-1, "0 с"), (0, "0 с"), (40, "40 с"),
                                    (60, "1 мин"), (61, "1 мин"), (3599, "59 мин"),
                                    (3600, "1 ч"), (3661, "1 ч 1 мин")] {
            XCTAssertEqual(UserTime.formatDuration(seconds), expected)
        }
    }

    private func metadata(start: Date) -> RecordingDisplayMetadata {
        RecordingDisplayMetadata(recordingStartedAt: start, recordingStoppedAt: nil,
            title: "Zoom - 2026-09-05 21:30", titleStatus: .generated,
            titleSource: .appContext, titleConfidence: .high, titleGeneratedAt: start,
            safeFileBasename: "recording", stableSuffix: "123456")
    }
}
