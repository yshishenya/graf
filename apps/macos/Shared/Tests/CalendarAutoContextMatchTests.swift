import Foundation
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class CalendarAutoContextMatchTests: XCTestCase {
    func testAutomaticResolveRequestUsesExactRecordingStartContract() throws {
        let client = DesktopUploadClient(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.pro")),
            headers: [
                "X-Workspace-Id": "00000000-0000-0000-0000-000000000901",
                "X-User-Id": "00000000-0000-0000-0000-000000000902",
                "X-Device-Id": "00000000-0000-0000-0000-000000000903"
            ],
            cookieHeaderProvider: { _ in nil }
        )
        let body = DesktopCalendarContextResolveRequest(
            recordingStartedAt: CalendarSettingsFixtures.recordingStartedAt,
            decisionIntent: .automatic
        )

        let request = try client.calendarContextResolveRequest(
            localRecordingId: "calendar-package",
            body: body
        )
        let json = try XCTUnwrap(request.httpBody).jsonObject

        XCTAssertEqual(
            request.url?.path,
            "/api/v1/desktop/recordings/calendar-package/calendar-context/resolve"
        )
        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/json")
        XCTAssertEqual(
            request.value(forHTTPHeaderField: "Idempotency-Key"),
            "desktop-calendar-context-resolve:calendar-package"
        )
        XCTAssertEqual(json["recording_started_at"] as? String, "2026-07-14T03:33:20Z")
        XCTAssertEqual(json["decision_intent"] as? String, "automatic")
        XCTAssertEqual(json["contract_version"] as? String, "calendar_auto_context_v1")
        XCTAssertNil(json["event_id"])
        XCTAssertNil(json["provider"])
        XCTAssertNil(json["credential"])
        XCTAssertNil(json["meeting_link"])
    }

    func testResolveResponseDecodesOpaqueAttemptWithoutProviderContent() throws {
        let data = """
        {
          "attempt_id": "00000000-0000-0000-0000-000000000098",
          "context_state": "matched_auto",
          "reason_code": "single_fresh_candidate",
          "context_confidence": "high",
          "candidate_count": 1,
          "matcher_version": "calendar_auto_match_v1",
          "expires_at": "2026-07-15T03:33:20Z"
        }
        """.data(using: .utf8)!
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601

        let response = try decoder.decode(DesktopCalendarContextResolveResponse.self, from: data)

        XCTAssertEqual(response.attemptId, CalendarSettingsFixtures.attemptID)
        XCTAssertEqual(response.contextState, .matchedAuto)
        XCTAssertEqual(response.reasonCode, "single_fresh_candidate")
        XCTAssertEqual(response.contextConfidence, .high)
        XCTAssertEqual(response.candidateCount, 1)
        XCTAssertEqual(response.matcherVersion, CalendarSettingsFixtures.autoContextMatcherVersion)
        XCTAssertEqual(response.expiresAt, CalendarSettingsFixtures.recordingStartedAt.addingTimeInterval(24 * 60 * 60))
    }

    func testResolveCommandRequiresActiveCaptureAndPreservesIntent() throws {
        let inactive = DesktopCalendarResolvePolicy.commandAfterCaptureStarted(
            localRecordingActive: false,
            localRecordingId: "calendar-package",
            recordingStartedAt: CalendarSettingsFixtures.recordingStartedAt,
            decisionIntent: .userSelected,
            eventId: "synthetic-event"
        )
        let active = try XCTUnwrap(
            DesktopCalendarResolvePolicy.commandAfterCaptureStarted(
                localRecordingActive: true,
                localRecordingId: "calendar-package",
                recordingStartedAt: CalendarSettingsFixtures.recordingStartedAt,
                decisionIntent: .userSelected,
                eventId: "synthetic-event"
            )
        )

        XCTAssertNil(inactive)
        XCTAssertEqual(active.localRecordingId, "calendar-package")
        XCTAssertEqual(active.recordingStartedAt, CalendarSettingsFixtures.recordingStartedAt)
        XCTAssertEqual(active.decisionIntent, .userSelected)
        XCTAssertEqual(active.eventId, "synthetic-event")
    }

    // FR-032, FR-049: resolve completion always releases an already queued recording for ordinary upload.
    func testResolveCompletionReleasesOnlyAnExistingQueuedRecording() {
        XCTAssertTrue(
            DesktopCalendarResolvePolicy.shouldProcessQueuedRecording(queueHasRecording: true)
        )
        XCTAssertFalse(
            DesktopCalendarResolvePolicy.shouldProcessQueuedRecording(queueHasRecording: false)
        )
    }
}

private extension Data {
    var jsonObject: [String: Any] {
        get throws {
            try XCTUnwrap(JSONSerialization.jsonObject(with: self) as? [String: Any])
        }
    }
}

#endif
