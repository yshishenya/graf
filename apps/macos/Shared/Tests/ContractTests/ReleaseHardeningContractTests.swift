import Foundation

#if canImport(XCTest)
import XCTest

final class ReleaseHardeningContractTests: XCTestCase {
    private let repositoryRoot = ReleaseHardeningContractTests.findRepositoryRoot()

    func testReleaseHardeningFixturesDeclareMetadataOnlyForbiddenFields() throws {
        for name in [
            "release-hardening-evidence",
            "core-audio-no-hang-evidence",
            "route-recovery-evidence",
            "installer-lifecycle-evidence",
            "ux-readiness-evidence"
        ] {
            let object = try fixtureObject(named: name)
            let forbidden = try XCTUnwrap(object["forbiddenFields"] as? [String], name)

            XCTAssertTrue(forbidden.contains("rawAudio"), name)
            XCTAssertTrue(forbidden.contains("transcriptText"), name)
            XCTAssertTrue(forbidden.contains("meetingContent"), name)
            XCTAssertTrue(forbidden.contains("credentials"), name)
            XCTAssertTrue(forbidden.contains("tokens"), name)
            XCTAssertTrue(forbidden.contains("signedUrls"), name)
        }
    }

    func testReleaseHardeningFixturesUseCommonResultValues() throws {
        for name in [
            "release-hardening-evidence",
            "core-audio-no-hang-evidence",
            "route-recovery-evidence",
            "installer-lifecycle-evidence",
            "ux-readiness-evidence"
        ] {
            let object = try fixtureObject(named: name)
            let resultValues = try XCTUnwrap(object["allowedResult"] as? [String], name)

            XCTAssertEqual(Set(resultValues), ["passed", "blocked", "not_accepted"], name)
        }
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
            let fixture = candidate.appendingPathComponent("tests/macos/contract/release-hardening-evidence.json")
            if FileManager.default.fileExists(atPath: fixture.path) {
                return candidate
            }
            candidate.deleteLastPathComponent()
        }
        return URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
    }
}
#endif
