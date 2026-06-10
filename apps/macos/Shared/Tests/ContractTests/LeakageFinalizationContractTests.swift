import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LeakageFinalizationContractTests: XCTestCase {
    func testLeakagePackageContractPinsManifestV3AndNoEgress() throws {
        let object = try loadContract("local-recording-package-leakage") as? [String: Any]
        let properties = object?["properties"] as? [String: Any]
        let schemaVersion = properties?["schemaVersion"] as? [String: Any]
        let externalEgress = properties?["externalEgressStarted"] as? [String: Any]

        XCTAssertEqual(schemaVersion?["const"] as? String, LocalRecordingManifest.schemaVersion)
        XCTAssertEqual(externalEgress?["const"] as? Bool, false)
    }

    func testLeakageEventContractContainsAuditEventNames() throws {
        let object = try loadContract("leakage-finalization-events") as? [String: Any]
        let properties = object?["properties"] as? [String: Any]
        let eventName = properties?["eventName"] as? [String: Any]
        let values = Set(eventName?["enum"] as? [String] ?? [])

        XCTAssertTrue(values.contains(AuditEventName.leakageFinalizationCompleted.rawValue))
        XCTAssertTrue(values.contains(AuditEventName.leakageDetected.rawValue))
        XCTAssertTrue(values.contains(AuditEventName.derivedCleanedTrackValidated.rawValue))
    }
}

private func loadContract(_ name: String) throws -> Any {
    let root = try repositoryRoot(startingAt: URL(fileURLWithPath: #filePath))
    let url = root.appendingPathComponent("tests/macos/contract/\(name).json")
    let data = try Data(contentsOf: url)
    return try JSONSerialization.jsonObject(with: data)
}

private func repositoryRoot(startingAt url: URL) throws -> URL {
    var candidate = url.deletingLastPathComponent()
    while candidate.path != "/" {
        if FileManager.default.fileExists(atPath: candidate.appendingPathComponent("apps/macos/Package.swift").path) {
            return candidate
        }
        candidate.deleteLastPathComponent()
    }
    throw NSError(domain: "LeakageFinalizationContractTests", code: 1)
}
#endif
