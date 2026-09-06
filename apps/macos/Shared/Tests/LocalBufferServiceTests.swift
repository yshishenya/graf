import Foundation
import CryptoKit
import XCTest
@testable import TwoBrainRecAppCore
@testable import TwoBrainRecShared

final class LocalBufferServiceTests: XCTestCase {
    private let root = URL(fileURLWithPath: "/synthetic-recordings")

    func testStorageProbeUsesActualMeasurements() {
        let healthy = LocalRecordingStorageProbe(
            rootURL: root,
            usedBytes: 100,
            availableBytes: { _ in 1_000_000_000 }
        )
        let lowReserve = LocalRecordingStorageProbe(
            rootURL: root,
            usedBytes: 100,
            availableBytes: { _ in 1 }
        )
        let overBudget = LocalRecordingStorageProbe(
            rootURL: root,
            usedBytes: LocalBufferService.defaultPolicy.maxBytesPerDevice,
            availableBytes: { _ in .max }
        )

        XCTAssertEqual(healthy.riskState(), .healthy)
        XCTAssertEqual(lowReserve.riskState(), .mustDegradeOrStop)
        XCTAssertEqual(overBudget.riskState(), .mustDegradeOrStop)
    }

    func testStorageProbeFailsClosedWhenMeasurementFails() {
        let probe = LocalRecordingStorageProbe(
            rootURL: root,
            usedBytes: 100,
            availableBytes: { _ in throw CocoaError(.fileReadUnknown) }
        )

        XCTAssertEqual(probe.riskState(), .mustDegradeOrStop)
    }

    func testAESGCMEncryptionKeepsKeyMaterialAndRoundTrips() throws {
        let key = SymmetricKey(data: Data(repeating: 7, count: 32))
        let service = AESGCMBufferEncryptionService(key: key)
        let plaintext = Data("local recording chunk".utf8)

        let encrypted = try service.encrypt(plaintext)
        let sealedBox = try AES.GCM.SealedBox(combined: encrypted)

        XCTAssertEqual(try AES.GCM.open(sealedBox, using: key), plaintext)
        XCTAssertEqual(
            service.keyFingerprint(),
            SHA256.hash(data: Data(repeating: 7, count: 32))
                .compactMap { String(format: "%02x", $0) }
                .joined()
        )
    }
}
