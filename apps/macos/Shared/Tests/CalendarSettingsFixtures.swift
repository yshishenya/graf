import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest
#endif

enum CalendarSettingsFixtures {
    static let autoContextContractVersion = "calendar_auto_context_v1"
    static let autoContextMatcherVersion = "calendar_auto_match_v1"
    static let recordingStartedAt = Date(timeIntervalSince1970: 1_784_000_000)
    static let selectedEventID = "00000000-0000-0000-0000-000000000981"
    static let alternateEventID = "00000000-0000-0000-0000-000000000982"
    static let attemptID = "00000000-0000-0000-0000-000000000098"

    struct ResolveRequestFixture: Codable, Equatable, Sendable {
        var recordingStartedAt: Date
        var decisionIntent: String
        var eventID: String?
        var contractVersion: String

        private enum CodingKeys: String, CodingKey {
            case recordingStartedAt = "recording_started_at"
            case decisionIntent = "decision_intent"
            case eventID = "event_id"
            case contractVersion = "contract_version"
        }
    }

    struct ResolveResponseFixture: Codable, Equatable, Sendable {
        var attemptID: String
        var contextState: String
        var reasonCode: String
        var contextConfidence: String
        var candidateCount: Int
        var matcherVersion: String
        var expiresAt: Date

        private enum CodingKeys: String, CodingKey {
            case attemptID = "attempt_id"
            case contextState = "context_state"
            case reasonCode = "reason_code"
            case contextConfidence = "context_confidence"
            case candidateCount = "candidate_count"
            case matcherVersion = "matcher_version"
            case expiresAt = "expires_at"
        }
    }

    enum ResolveFailureFixture: Error, Equatable, Sendable {
        case transportUnavailable
    }

    static func cabinetConfiguration() -> DesktopCabinetConfiguration {
        DesktopCabinetConfiguration(baseURL: URL(string: "https://rec.2brain.dev")!)
    }

    static func embeddedCalendarSettingsURL() -> URL {
        cabinetConfiguration().calendarSettingsURL()
    }

    static func resolveRequest(
        recordingStartedAt: Date = recordingStartedAt,
        decisionIntent: String = "automatic",
        eventID: String? = nil,
        contractVersion: String = autoContextContractVersion
    ) -> ResolveRequestFixture {
        ResolveRequestFixture(
            recordingStartedAt: recordingStartedAt,
            decisionIntent: decisionIntent,
            eventID: eventID,
            contractVersion: contractVersion
        )
    }

    static func selectedResolveRequest(
        recordingStartedAt: Date = recordingStartedAt,
        eventID: String = selectedEventID
    ) -> ResolveRequestFixture {
        resolveRequest(
            recordingStartedAt: recordingStartedAt,
            decisionIntent: "user_selected",
            eventID: eventID
        )
    }

    static func declinedResolveRequest(
        recordingStartedAt: Date = recordingStartedAt
    ) -> ResolveRequestFixture {
        resolveRequest(
            recordingStartedAt: recordingStartedAt,
            decisionIntent: "user_declined"
        )
    }

    static func resolveResponse(
        attemptID: String = attemptID,
        contextState: String = "matched_auto",
        reasonCode: String = "single_fresh_candidate",
        contextConfidence: String = "high",
        candidateCount: Int = 1,
        matcherVersion: String = autoContextMatcherVersion,
        expiresAt: Date = recordingStartedAt.addingTimeInterval(24 * 60 * 60)
    ) -> ResolveResponseFixture {
        ResolveResponseFixture(
            attemptID: attemptID,
            contextState: contextState,
            reasonCode: reasonCode,
            contextConfidence: contextConfidence,
            candidateCount: candidateCount,
            matcherVersion: matcherVersion,
            expiresAt: expiresAt
        )
    }

    static func overlappingResolveResponse(
        attemptID: String = attemptID,
        candidateCount: Int = 2
    ) -> ResolveResponseFixture {
        resolveResponse(
            attemptID: attemptID,
            contextState: "ambiguous",
            reasonCode: "multiple_time_candidates",
            contextConfidence: "ambiguous",
            candidateCount: candidateCount
        )
    }

    static func failedResolveResult() -> Result<ResolveResponseFixture, ResolveFailureFixture> {
        .failure(.transportUnavailable)
    }

    static func jsonData<Value: Encodable>(for value: Value) throws -> Data {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }

    static func overlappingPromptEvents(now: Date = Date(timeIntervalSince1970: 1_000)) -> [DesktopCalendarPromptEvent] {
        [
            DesktopCalendarPromptEvent(
                eventId: selectedEventID,
                startsAt: now.addingTimeInterval(-1_800),
                endsAt: now.addingTimeInterval(1_800),
                title: "Первая встреча",
                titleState: .available,
                meetingLinkPresent: true,
                recordPromptDueAt: now.addingTimeInterval(-1)
            ),
            DesktopCalendarPromptEvent(
                eventId: alternateEventID,
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

    static func recoveredQueueItem(
        id: String = "calendar-recovered-item",
        state: UploadItemState = .queued,
        calendarContextEventID: String? = nil,
        now: Date = recordingStartedAt
    ) -> DesktopUploadQueueItem {
        var item = custodyFixtureQueueItem(
            id: id,
            state: state,
            retentionDeadline: now.addingTimeInterval(7 * 24 * 60 * 60),
            updatedAt: now
        )
        item.calendarContextEventId = calendarContextEventID
        return item
    }
}

#if canImport(XCTest)
final class CalendarSettingsFixturesTests: XCTestCase {
    func testResolveDecisionBuildersPreserveExplicitIntent() {
        let automatic = CalendarSettingsFixtures.resolveRequest()
        let selected = CalendarSettingsFixtures.selectedResolveRequest()
        let declined = CalendarSettingsFixtures.declinedResolveRequest()

        XCTAssertEqual(automatic.decisionIntent, "automatic")
        XCTAssertNil(automatic.eventID)
        XCTAssertEqual(selected.decisionIntent, "user_selected")
        XCTAssertEqual(selected.eventID, CalendarSettingsFixtures.selectedEventID)
        XCTAssertEqual(declined.decisionIntent, "user_declined")
        XCTAssertNil(declined.eventID)
    }

    func testResolveFixturesUseContractShapeAndBoundedExpiry() throws {
        let requestJSON = String(
            decoding: try CalendarSettingsFixtures.jsonData(for: CalendarSettingsFixtures.selectedResolveRequest()),
            as: UTF8.self
        )
        let response = CalendarSettingsFixtures.resolveResponse()

        XCTAssertTrue(requestJSON.contains("\"decision_intent\":\"user_selected\""))
        XCTAssertTrue(requestJSON.contains("\"event_id\":\"\(CalendarSettingsFixtures.selectedEventID)\""))
        XCTAssertFalse(requestJSON.contains("meeting_link"))
        XCTAssertEqual(
            response.expiresAt.timeIntervalSince(CalendarSettingsFixtures.recordingStartedAt),
            24 * 60 * 60
        )
    }

    func testOverlapFailureAndRecoveryFixturesRemainFailSoft() {
        let overlap = CalendarSettingsFixtures.overlappingResolveResponse()
        let events = CalendarSettingsFixtures.overlappingPromptEvents()
        let recovered = CalendarSettingsFixtures.recoveredQueueItem()

        XCTAssertEqual(overlap.contextState, "ambiguous")
        XCTAssertEqual(overlap.candidateCount, 2)
        XCTAssertEqual(events.map(\.eventId), [
            CalendarSettingsFixtures.selectedEventID,
            CalendarSettingsFixtures.alternateEventID
        ])
        XCTAssertNil(recovered.calendarContextEventId)
        guard case .failure(.transportUnavailable) = CalendarSettingsFixtures.failedResolveResult() else {
            return XCTFail("Expected a synthetic transport failure")
        }
    }
}
#endif
