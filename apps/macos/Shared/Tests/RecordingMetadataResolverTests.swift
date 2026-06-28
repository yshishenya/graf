import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class RecordingMetadataResolverTests: XCTestCase {
    func testResolvesApprovedAppTitleAndSafeBasenameWithinBudget() throws {
        let startedAt = utcDate(year: 2026, month: 6, day: 26, hour: 11, minute: 30)
        let generatedAt = utcDate(year: 2026, month: 6, day: 26, hour: 11, minute: 31)
        let resolver = RecordingMetadataResolver(clock: { generatedAt }, displayTimeZone: utcTimeZone)

        let metadata = resolver.resolve(
            startedAt: startedAt,
            stoppedAt: utcDate(year: 2026, month: 6, day: 26, hour: 12, minute: 15),
            directoryId: "recording-directory",
            sessionId: "session-id",
            approvedAppName: "Zoom"
        )

        XCTAssertEqual(metadata.recordingStartedAt, startedAt)
        XCTAssertEqual(metadata.recordingStoppedAt, utcDate(year: 2026, month: 6, day: 26, hour: 12, minute: 15))
        XCTAssertEqual(metadata.recordingDisplayTimeZoneOffsetMinutes, 0)
        XCTAssertEqual(metadata.title, "Zoom - 2026-06-26 11:30")
        XCTAssertEqual(metadata.titleStatus, .generated)
        XCTAssertEqual(metadata.titleSource, .appContext)
        XCTAssertEqual(metadata.titleConfidence, .high)
        XCTAssertEqual(metadata.titleGeneratedAt, generatedAt)
        XCTAssertTrue(metadata.safeFileBasename.hasPrefix("2026-06-26_11-30_zoom-2026-06-26-11-30_"))
        XCTAssertFalse(metadata.safeFileBasename.contains("/"))
        XCTAssertFalse(metadata.safeFileBasename.contains("\\"))
        XCTAssertFalse(metadata.safeFileBasename.contains(":"))
    }

    func testFallsBackToGenericTitleWhenAppContextIsMissingOrUnsafe() throws {
        let resolver = RecordingMetadataResolver(clock: { Date(timeIntervalSince1970: 1) }, displayTimeZone: utcTimeZone)
        let startedAt = utcDate(year: 2026, month: 6, day: 26, hour: 11, minute: 30)

        let missingApp = resolver.resolve(
            startedAt: startedAt,
            stoppedAt: nil,
            directoryId: "recording-directory",
            sessionId: "session-id",
            approvedAppName: nil
        )
        XCTAssertEqual(missingApp.title, "Meeting - 2026-06-26 11:30")
        XCTAssertEqual(missingApp.titleSource, .generic)
        XCTAssertEqual(missingApp.titleConfidence, .medium)

        let unsafeAppName = "https" + "://meet." + "example" + ".com/private?" + "token" + "=secret"
        let unsafeApp = resolver.resolve(
            startedAt: startedAt,
            stoppedAt: nil,
            directoryId: "recording-directory",
            sessionId: "session-id",
            approvedAppName: unsafeAppName
        )
        XCTAssertEqual(unsafeApp.title, "Meeting - 2026-06-26 11:30")
        XCTAssertEqual(unsafeApp.titleSource, .generic)
        XCTAssertEqual(unsafeApp.suppressedSources, [
            RecordingTitleSuppression(source: .appContext, reason: "unsafe_pattern")
        ])
        XCTAssertFalse(unsafeApp.title.contains("https" + "://"))
        XCTAssertFalse(unsafeApp.safeFileBasename.contains("token"))

        let ordinarySkDash = resolver.resolve(
            startedAt: startedAt,
            stoppedAt: nil,
            directoryId: "recording-directory",
            sessionId: "session-id",
            approvedAppName: "Risk-review"
        )
        XCTAssertEqual(ordinarySkDash.title, "Risk-review - 2026-06-26 11:30")
        XCTAssertEqual(ordinarySkDash.titleSource, .appContext)

        let bareMeetingLink = resolver.resolve(
            startedAt: startedAt,
            stoppedAt: nil,
            directoryId: "recording-directory",
            sessionId: "session-id",
            approvedAppName: "meet.example.test/abc-defg-hij"
        )
        XCTAssertEqual(bareMeetingLink.title, "Meeting - 2026-06-26 11:30")
        XCTAssertEqual(bareMeetingLink.titleSource, .generic)
        XCTAssertEqual(bareMeetingLink.suppressedSources, [
            RecordingTitleSuppression(source: .appContext, reason: "unsafe_pattern")
        ])
    }

    func testUserConfirmedTitleWinsWithoutChangingStableSuffix() throws {
        let resolver = RecordingMetadataResolver(clock: { Date(timeIntervalSince1970: 1) }, displayTimeZone: utcTimeZone)
        let startedAt = utcDate(year: 2026, month: 6, day: 26, hour: 11, minute: 30)

        let generated = resolver.resolve(
            startedAt: startedAt,
            stoppedAt: nil,
            directoryId: "recording-directory",
            sessionId: "session-id",
            approvedAppName: "Zoom"
        )
        let userConfirmed = resolver.resolve(
            startedAt: startedAt,
            stoppedAt: nil,
            directoryId: "recording-directory",
            sessionId: "session-id",
            approvedAppName: "Zoom",
            userConfirmedTitle: "Weekly Product Sync"
        )

        XCTAssertEqual(userConfirmed.title, "Weekly Product Sync")
        XCTAssertEqual(userConfirmed.titleStatus, .userConfirmed)
        XCTAssertEqual(userConfirmed.titleSource, .userConfirmed)
        XCTAssertEqual(generated.stableSuffix, userConfirmed.stableSuffix)
        XCTAssertTrue(userConfirmed.safeFileBasename.contains("weekly-product-sync"))
    }

    func testSafeBasenameUsesStableSuffixForDuplicateAndLongTitles() throws {
        let resolver = RecordingMetadataResolver(clock: { Date(timeIntervalSince1970: 1) }, displayTimeZone: utcTimeZone)
        let startedAt = utcDate(year: 2026, month: 6, day: 26, hour: 11, minute: 30)
        let longTitle = "Weekly Product Sync " + String(repeating: "Roadmap ", count: 30)

        let first = resolver.resolve(
            startedAt: startedAt,
            stoppedAt: nil,
            directoryId: "recording-directory-a",
            sessionId: "session-id-a",
            approvedAppName: nil,
            userConfirmedTitle: longTitle
        )
        let second = resolver.resolve(
            startedAt: startedAt,
            stoppedAt: nil,
            directoryId: "recording-directory-b",
            sessionId: "session-id-b",
            approvedAppName: nil,
            userConfirmedTitle: longTitle
        )
        let cyrillic = resolver.resolve(
            startedAt: startedAt,
            stoppedAt: nil,
            directoryId: "recording-directory-c",
            sessionId: "session-id-c",
            approvedAppName: nil,
            userConfirmedTitle: "Продуктовый синк"
        )

        XCTAssertEqual(first.title, second.title)
        XCTAssertNotEqual(first.stableSuffix, second.stableSuffix)
        XCTAssertNotEqual(first.safeFileBasename, second.safeFileBasename)
        XCTAssertLessThanOrEqual(first.title.count, 500)
        XCTAssertLessThanOrEqual(first.safeFileBasename.count, 110)
        XCTAssertTrue(first.safeFileBasename.hasPrefix("2026-06-26_11-30_weekly-product-sync-roadmap"))
        XCTAssertTrue(cyrillic.safeFileBasename.contains("_recording_"))
        for basename in [first.safeFileBasename, second.safeFileBasename, cyrillic.safeFileBasename] {
            XCTAssertFalse(basename.contains("/"))
            XCTAssertFalse(basename.contains("\\"))
            XCTAssertFalse(basename.contains(":"))
            XCTAssertFalse(basename.contains("@"))
        }
    }

    func testSuppressesUnsafeUserTitleAndDoesNotExposeCalendarOrWindowSources() throws {
        let resolver = RecordingMetadataResolver(clock: { Date(timeIntervalSince1970: 1) }, displayTimeZone: utcTimeZone)
        let unsafeEmail = "john" + "@example" + ".com"
        let unsafeURL = "https" + "://meet." + "example" + ".com"
        let metadata = resolver.resolve(
            startedAt: utcDate(year: 2026, month: 6, day: 26, hour: 11, minute: 30),
            stoppedAt: nil,
            directoryId: "recording-directory",
            sessionId: "session-id",
            approvedAppName: nil,
            userConfirmedTitle: "Invite \(unsafeEmail) / \(unsafeURL)"
        )

        XCTAssertEqual(metadata.title, "Meeting - 2026-06-26 11:30")
        XCTAssertEqual(metadata.suppressedSources, [
            RecordingTitleSuppression(source: .userConfirmed, reason: "unsafe_pattern")
        ])
        XCTAssertFalse(metadata.title.contains("@"))
        XCTAssertFalse(metadata.safeFileBasename.contains("/"))

        let encoded = String(data: try JSONEncoder().encode(metadata), encoding: .utf8)
        XCTAssertFalse(encoded?.contains("calendar") ?? true)
        XCTAssertFalse(encoded?.contains("window") ?? true)
    }

    func testGeneratedAppTitlesUseDisplayTimezoneAndClampAfterDateSuffix() throws {
        let resolver = RecordingMetadataResolver(
            clock: { Date(timeIntervalSince1970: 1) },
            displayTimeZone: TimeZone(secondsFromGMT: 3 * 60 * 60)!
        )
        let startedAt = utcDate(year: 2026, month: 6, day: 26, hour: 20, minute: 30)
        let longAppName = String(repeating: "A", count: 600)

        let metadata = resolver.resolve(
            startedAt: startedAt,
            stoppedAt: nil,
            directoryId: "recording-directory",
            sessionId: "session-id",
            approvedAppName: longAppName
        )

        XCTAssertEqual(metadata.title.count, 500)
        XCTAssertEqual(metadata.recordingDisplayTimeZoneOffsetMinutes, 180)
        XCTAssertTrue(metadata.title.hasSuffix(" - 2026-06-26 23:30"))
        XCTAssertTrue(metadata.safeFileBasename.hasPrefix("2026-06-26_23-30_"))
    }

    private var utcTimeZone: TimeZone {
        TimeZone(secondsFromGMT: 0)!
    }

    private func utcDate(year: Int, month: Int, day: Int, hour: Int, minute: Int) -> Date {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        var components = DateComponents()
        components.timeZone = calendar.timeZone
        components.year = year
        components.month = month
        components.day = day
        components.hour = hour
        components.minute = minute
        return calendar.date(from: components)!
    }
}
#endif
