import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

enum CalendarSettingsFixtures {
    static func cabinetConfiguration() -> DesktopCabinetConfiguration {
        DesktopCabinetConfiguration(baseURL: URL(string: "https://rec.2brain.dev")!)
    }

    static func embeddedCalendarSettingsURL() -> URL {
        cabinetConfiguration().calendarSettingsURL()
    }

    static func overlappingPromptEvents(now: Date = Date(timeIntervalSince1970: 1_000)) -> [DesktopCalendarPromptEvent] {
        [
            DesktopCalendarPromptEvent(
                eventId: "event-1200-1300",
                startsAt: now.addingTimeInterval(-1_800),
                endsAt: now.addingTimeInterval(1_800),
                title: "Первая встреча",
                titleState: .available,
                meetingLinkPresent: true,
                recordPromptDueAt: now.addingTimeInterval(-1)
            ),
            DesktopCalendarPromptEvent(
                eventId: "event-1230-1330",
                startsAt: now.addingTimeInterval(-900),
                endsAt: now.addingTimeInterval(2_700),
                title: "Вторая встреча",
                titleState: .available,
                meetingLinkPresent: true,
                recordPromptDueAt: now.addingTimeInterval(-1)
            )
        ]
    }

    static func activeRecordingInvariant(embeddedLoaded: Bool = true) -> NativeShellInvariant {
        NativeShellInvariant(
            recordVisible: true,
            stopVisible: true,
            uploadTruthVisible: true,
            focusCanReachStop: true,
            embeddedSurfaceLoaded: embeddedLoaded
        )
    }
}
