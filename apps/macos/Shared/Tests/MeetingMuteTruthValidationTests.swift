import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class MeetingMuteTruthValidationTests: XCTestCase {
    func testTargetMatrixResolvesKnownAndUnknownTargets() {
        let service = MeetingMuteTruthService()

        XCTAssertEqual(service.capability(for: "Zoom Workplace").targetId, "zoom_native")
        XCTAssertEqual(service.capability(for: "Google Chrome - Яндекс Телемост").targetId, "chrome_telemost")
        XCTAssertEqual(service.capability(for: "Opera - Telemost").targetId, "opera_telemost")
        XCTAssertEqual(service.capability(for: "Yandex Browser - Telemost").firstMatrixStatus, .deferred)
        XCTAssertEqual(service.capability(for: "Unknown Call").firstMatrixStatus, .unsupported)
    }

    func testTargetMatrixEvidenceIsFailClosedWithoutAdapterSupport() {
        let service = MeetingMuteTruthService()
        let evidence = service.evidence(
            sessionId: "session",
            capability: .chromeTelemost,
            limitationCopyShown: true,
            recordedAt: Date(timeIntervalSince1970: 1)
        )

        XCTAssertEqual(evidence.source, .productPause)
        XCTAssertEqual(evidence.status, .meetingMuteUnproven)
        XCTAssertEqual(evidence.freshness, .unavailable)
        XCTAssertTrue(evidence.limitationCopyShown)
        XCTAssertNil(evidence.adapterId)
    }

    func testFixtureDirectoryContainsRequiredRows() throws {
        let fixtureRoot = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .appendingPathComponent("Fixtures/MeetingMuteTruth", isDirectory: true)
        let required = [
            "pause-validated.json",
            "unsupported.json",
            "deferred.json",
            "unsafe.json"
        ]

        for fileName in required {
            let url = fixtureRoot.appendingPathComponent(fileName)
            XCTAssertTrue(FileManager.default.fileExists(atPath: url.path), "Missing \(fileName)")
        }
    }
}
#endif
