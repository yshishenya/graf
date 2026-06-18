import TwoBrainRecAppCore
import XCTest

final class NativeCabinetMeetingListTests: XCTestCase {
    func testListURLTargetsCabinetMeetingsAPI() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.pro/desktop/meetings",
            headers: [:]
        ))

        let url = NativeCabinetMeetingListClient.listURL(configuration: configuration, limit: 25)

        XCTAssertEqual(url.scheme, "https")
        XCTAssertEqual(url.host, "rec.2brain.pro")
        XCTAssertEqual(url.path, "/api/v1/cabinet/meetings")
        XCTAssertEqual(url.query, "sort=updated_desc&limit=25")
    }

    func testMeetingListResponseDecodesServerPayload() throws {
        let payload = """
        {
          "items": [
            {
              "meeting_id": "246751b2-038d-4b1d-96b7-a9b1f0adbbe2",
              "title": "Чувство вины и отношения с матерью",
              "started_at": null,
              "duration_seconds": 74,
              "status": "ingested_pending_processing",
              "status_label": "Submitted",
              "primary_action": "wait",
              "transcript_available": false
            }
          ]
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        let response = try decoder.decode(NativeCabinetMeetingListResponse.self, from: payload)

        XCTAssertEqual(response.items.count, 1)
        XCTAssertEqual(response.items[0].meetingId, "246751b2-038d-4b1d-96b7-a9b1f0adbbe2")
        XCTAssertEqual(response.items[0].title, "Чувство вины и отношения с матерью")
        XCTAssertEqual(response.items[0].durationSeconds, 74)
        XCTAssertEqual(response.items[0].statusLabel, "Submitted")
        XCTAssertEqual(response.items[0].primaryAction, .wait)
        XCTAssertEqual(response.items[0].primaryAction.label, "В обработке")
        XCTAssertFalse(response.items[0].transcriptAvailable)
    }

    func testDurationTextMatchesCabinetRows() {
        XCTAssertEqual(NativeCabinetMeetingListClient.durationText(seconds: -5), "0s")
        XCTAssertEqual(NativeCabinetMeetingListClient.durationText(seconds: 59), "59s")
        XCTAssertEqual(NativeCabinetMeetingListClient.durationText(seconds: 74), "1m")
        XCTAssertEqual(NativeCabinetMeetingListClient.durationText(seconds: 3_725), "1h 2m")
    }

    func testShellUsesNativeListOnlyForMeetingsIndexRoute() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.pro",
            headers: [:]
        ))

        XCTAssertTrue(DesktopCabinetWorkspaceView.usesNativeMeetingList(for: nil, configuration: configuration))
        XCTAssertTrue(
            DesktopCabinetWorkspaceView.usesNativeMeetingList(
                for: configuration.meetingsURL(),
                configuration: configuration
            )
        )
        XCTAssertFalse(
            DesktopCabinetWorkspaceView.usesNativeMeetingList(
                for: configuration.meetingDetailURL(meetingId: "meeting-042"),
                configuration: configuration
            )
        )
    }

    func testUserMessagesDistinguishAuthAndServerFailures() {
        XCTAssertEqual(
            NativeCabinetMeetingListClient.userMessage(for: NativeCabinetMeetingListError.httpStatus(401)),
            "Нужен вход, чтобы открыть список встреч."
        )
        XCTAssertEqual(
            NativeCabinetMeetingListClient.userMessage(for: NativeCabinetMeetingListError.httpStatus(403)),
            "Текущая сессия не подтверждает доступ к этому кабинету."
        )
        XCTAssertEqual(
            NativeCabinetMeetingListClient.userMessage(for: NativeCabinetMeetingListError.network),
            "Кабинет встреч недоступен. Проверьте соединение с сервером Rec."
        )
    }
}
