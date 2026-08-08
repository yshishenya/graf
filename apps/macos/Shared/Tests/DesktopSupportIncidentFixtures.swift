import Foundation

#if canImport(XCTest)
import XCTest
#endif

struct DesktopSupportIncidentFixture {
    static let schemaVersion = "desktop-support-incident.v2"
    static let successMessage = "Запрос принят и передан в поддержку. Номер: CUST-123"
    static let failureMessage = "Запрос не принят. Проверьте подключение или скопируйте безопасную сводку."
    static let supportTitle = "Связаться с поддержкой"

    static func incidentNumber(_ issueNumber: Int = 123) -> String {
        "CUST-\(issueNumber)"
    }

    static func safeReport(
        problemCode: String = "custody.retention_expired.local_retained",
        localMediaRetained: Bool = true
    ) -> [String: Any] {
        [
            "schema_version": schemaVersion,
            "app_name": "GRAF",
            "bundle_id": "pro.2brain.graf",
            "app_version": "2026.06.26",
            "build_version": "1234",
            "environment_base_url_identity": "rec.2brain.pro",
            "workspace_fingerprint": "ws_fpr_7b2e",
            "user_fingerprint": "usr_fpr_01af",
            "device_fingerprint": "dev_fpr_41dd",
            "safe_recording_identity": "local:rec_fpr_18ce",
            "local_recording_id_fingerprint": "rec_fpr_18ce",
            "custody_lifecycle_state": "terminal_undelivered",
            "upload_queue_item_state": "failed",
            "retry_class": "terminal",
            "retry_mode": "not_retryable",
            "normal_user_action": "send_support_report",
            "failure_category": "retention_expired",
            "problem_code": problemCode,
            "server_identity_present": false,
            "local_media_retained": localMediaRetained,
            "data_loss_risk": "possible",
            "server_copy_known": false,
            "upload_attempt_count": 3,
            "local_file_completeness_profile": [
                "manifest_present": true,
                "audio_files_present": true,
                "missing_file_count": 0,
                "corrupt_file_count": 0,
                "total_size_bucket": "100mb_1gb",
                "duration_bucket": "30m_2h"
            ],
            "redaction_state": "metadata_only",
            "client_report_fingerprint": "report_fpr_18ce",
            "client_dedupe_key": "support_dedupe_18ce",
            "canonical_stage": "retention",
            "custody_owner": "policy_lifecycle",
            "upload_state": "terminal",
            "deletion_state": "retention_expired",
            "local_copy_state": "retained",
            "server_copy_state": "unknown",
            "server_deletion_state": "none",
            "server_access_state": "owner",
            "server_status": "unknown",
            "server_upload_status": "unknown",
            "server_processing_status": "not_submitted",
            "server_review_available": false,
            "server_review_status": "unavailable",
            "last_reconciled_at": "unknown",
            "server_conflict_reason": "unknown",
            "server_next_action": "send_support_report",
            "timeline": [["event": "created", "at": "2026-06-26T10:00:00Z", "source": "local_queue"]],
            "retry_history": []
        ]
    }

    static func safeReportJSON() throws -> String {
        let data = try JSONSerialization.data(withJSONObject: safeReport(), options: [.sortedKeys])
        return String(decoding: data, as: UTF8.self)
    }
}

#if canImport(XCTest)
final class DesktopSupportIncidentFixturesTests: XCTestCase {
    func testSafeReportFixtureIsMetadataOnly() throws {
        let json = try DesktopSupportIncidentFixture.safeReportJSON()

        XCTAssertTrue(json.contains("\"redaction_state\":\"metadata_only\""))
        XCTAssertFalse(json.contains("/Users/"))
        XCTAssertFalse(json.localizedCaseInsensitiveContains("token="))
    }
}
#endif
