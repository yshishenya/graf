import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class DesktopLocalPurgeTests: XCTestCase {
    func testLocalPurgeTaskDecodesMetadataOnlyPayload() throws {
        let payload = """
        {
          "task_id": "71000000-0000-0000-0000-000000000001",
          "meeting_id": "72000000-0000-0000-0000-000000000001",
          "task_type": "purge_local_buffers",
          "state": "pending",
          "safe_reason": "delete_requested",
          "expires_at": "2026-06-17T00:00:00Z",
          "ack_url": "/api/v1/desktop/local-purge-tasks/71000000-0000-0000-0000-000000000001/ack"
        }
        """.data(using: .utf8)!

        let task = try localPurgeDecoder.decode(DesktopLocalPurgeTask.self, from: payload)

        XCTAssertEqual(task.taskId, "71000000-0000-0000-0000-000000000001")
        XCTAssertEqual(task.meetingId, "72000000-0000-0000-0000-000000000001")
        XCTAssertEqual(task.taskType, .purgeLocalBuffers)
        XCTAssertEqual(task.state, .pending)
        XCTAssertEqual(task.safeReason, "delete_requested")
        XCTAssertTrue(task.ackURL?.path.hasSuffix("/ack") == true)
    }

    func testLocalPurgeTaskDecodesWithoutAckURLAndUsesTaskFallback() throws {
        let payload = """
        {
          "task_id": "71000000-0000-0000-0000-000000000001",
          "meeting_id": "72000000-0000-0000-0000-000000000001",
          "task_type": "purge_local_buffers",
          "state": "pending",
          "safe_reason": "delete_requested",
          "expires_at": "2026-06-17T00:00:00Z",
          "ack_url": null
        }
        """.data(using: .utf8)!

        let task = try localPurgeDecoder.decode(DesktopLocalPurgeTask.self, from: payload)

        XCTAssertNil(task.ackURL)
    }

    func testLocalPurgeAcknowledgementEncodesNoPrivateProofPayload() throws {
        let ack = DesktopLocalPurgeAcknowledgement(
            state: .acknowledged,
            reasonCode: "local_buffers_purged",
            clientVersion: "local-macos-test",
            completedAt: Date(timeIntervalSince1970: 1_781_654_400)
        )

        let data = try localPurgeEncoder.encode(ack)
        let json = String(decoding: data, as: UTF8.self)

        XCTAssertTrue(json.contains("\"state\":\"acknowledged\""))
        XCTAssertTrue(json.contains("\"reason_code\":\"local_buffers_purged\""))
        XCTAssertFalse(json.localizedCaseInsensitiveContains("/Users/"))
        XCTAssertFalse(json.localizedCaseInsensitiveContains("private.wav"))
        XCTAssertFalse(json.localizedCaseInsensitiveContains("sha256"))
        XCTAssertFalse(json.localizedCaseInsensitiveContains("transcript"))
    }

    private var localPurgeDecoder: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }

    private var localPurgeEncoder: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        return encoder
    }
}
#endif
