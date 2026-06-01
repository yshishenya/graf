import Foundation

#if canImport(XCTest)
import XCTest

final class LowResourceContractTests: XCTestCase {
    private let repositoryRoot = LowResourceContractTests.findRepositoryRoot()

    func testLowResourceFixturesForbidRawContentAndSecrets() throws {
        for name in [
            "low-resource-validation-evidence",
            "low-resource-route-truth",
            "low-resource-startup-attempt"
        ] {
            let object = try fixtureObject(named: name)
            let forbidden = try XCTUnwrap(object["forbiddenFields"] as? [String], name)

            XCTAssertTrue(forbidden.contains("rawAudio"), name)
            XCTAssertTrue(forbidden.contains("transcriptText"), name)
            XCTAssertTrue(forbidden.contains("meetingContent"), name)
            XCTAssertTrue(forbidden.contains("credentials"), name)
            XCTAssertTrue(forbidden.contains("tokens"), name)
            XCTAssertTrue(forbidden.contains("signedUrls"), name)
            XCTAssertTrue(forbidden.contains("password"), name)
        }
    }

    func testLowResourceValidationFixtureDefinesPromotionThresholds() throws {
        let object = try fixtureObject(named: "low-resource-validation-evidence")
        let thresholds = try XCTUnwrap(object["thresholds"] as? [String: Any])
        let rules = try XCTUnwrap(object["rules"] as? [String: Any])

        XCTAssertEqual(thresholds["startup_timeout_ms"] as? Int, 3000)
        XCTAssertEqual(thresholds["target_surface_usable_within_seconds"] as? Int, 5)
        XCTAssertEqual(thresholds["coreaudiod_sustained_cpu_percent"] as? Int, 10)
        XCTAssertEqual(rules["metadataOnly"] as? Bool, true)
        XCTAssertEqual(rules["failedP1GatePreserves005Fallback"] as? Bool, true)
    }

    func testLowResourceRouteTruthFixtureRequiresSeparatePlanes() throws {
        let object = try fixtureObject(named: "low-resource-route-truth")
        let planes = try XCTUnwrap(object["requiredPlanes"] as? [String])

        XCTAssertEqual(Set(planes), [
            "publication",
            "client_io",
            "app_bridge",
            "physical_devices",
            "recording_trigger"
        ])
    }

    private func fixtureObject(named name: String) throws -> [String: Any] {
        let url = repositoryRoot
            .appendingPathComponent("tests/macos/contract")
            .appendingPathComponent("\(name).json")
        let data = try Data(contentsOf: url)
        return try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
    }

    private static func findRepositoryRoot() -> URL {
        var candidate = URL(fileURLWithPath: #filePath)
        while candidate.path != candidate.deletingLastPathComponent().path {
            let fixture = candidate.appendingPathComponent("tests/macos/contract/low-resource-validation-evidence.json")
            if FileManager.default.fileExists(atPath: fixture.path) {
                return candidate
            }
            candidate.deleteLastPathComponent()
        }
        return URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
    }
}
#endif
