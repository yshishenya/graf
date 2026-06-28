import Foundation

#if canImport(XCTest)
import XCTest
#endif

struct DesktopSupportIncidentFixture {
    static let schemaVersion = "desktop-support-incident.v1"
    static let successMessage = "Отчет отправлен. Мы разберемся. Номер: CUST-123"
    static let failureMessage = "Не удалось отправить. Скопируйте отчет и отправьте в поддержку."
    static let copyFallbackTitle = "Скопировать отчет"
    static let sendReportTitle = "Отправить отчет"

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
            "redaction_state": "metadata_only"
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
