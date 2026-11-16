import Foundation
import CryptoKit
import XCTest
@testable import TwoBrainRecAppCore
@testable import TwoBrainRecShared

final class LocalBufferServiceTests: XCTestCase {
    private let root = URL(fileURLWithPath: "/synthetic-recordings")

    func testStorageProbeUsesActualMeasurements() {
        let measurementPolicy = LocalBufferPolicy(
            maxBytesPerDevice: LocalBufferService.defaultPolicy.maxBytesPerDevice,
            warningFraction: LocalBufferService.defaultPolicy.warningFraction,
            criticalFraction: LocalBufferService.defaultPolicy.criticalFraction,
            minimumDiskReserveBytes: 10_000_000,
            retentionDays: 7
        )
        let healthy = LocalRecordingStorageProbe(
            rootURL: root,
            usedBytes: 100,
            policy: measurementPolicy,
            availableBytes: { _ in 1_000_000_000 },
            capacityBytes: { _ in 50_000_000_000 }
        )
        let lowReserve = LocalRecordingStorageProbe(
            rootURL: root,
            usedBytes: 100,
            policy: measurementPolicy,
            availableBytes: { _ in 1 },
            capacityBytes: { _ in 50_000_000_000 }
        )
        let overBudget = LocalRecordingStorageProbe(
            rootURL: root,
            usedBytes: LocalBufferService.defaultPolicy.maxBytesPerDevice,
            policy: measurementPolicy,
            availableBytes: { _ in .max },
            capacityBytes: { _ in 50_000_000_000 }
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

    func testProductBaselineMatchesPRD() {
        let policy = LocalBufferService.defaultPolicy
        XCTAssertEqual(policy.maxBytesPerDevice, 5_000_000_000)
        XCTAssertEqual(policy.warningFraction, 0.8)
        XCTAssertEqual(policy.criticalFraction, 0.95)
        XCTAssertEqual(policy.minimumDiskReserveBytes, 10_000_000_000)
        XCTAssertEqual(policy.retentionDays, 7)
    }

    func testResolvedReserveUsesTheSmallerOfTenGigabytesAndTenPercent() {
        let policy = LocalBufferPolicy.productBaseline
        XCTAssertEqual(
            policy.resolvedMinimumDiskReserveBytes(diskCapacityBytes: 50_000_000_000),
            5_000_000_000
        )
        XCTAssertEqual(
            policy.resolvedMinimumDiskReserveBytes(diskCapacityBytes: 200_000_000_000),
            10_000_000_000
        )
        XCTAssertEqual(
            policy.resolvedMinimumDiskReserveBytes(diskCapacityBytes: nil),
            10_000_000_000
        )
        XCTAssertEqual(
            policy.resolvedMinimumDiskReserveBytes(diskCapacityBytes: 0),
            10_000_000_000
        )
        XCTAssertEqual(
            LocalBufferPolicy(
                maxBytesPerDevice: 1, warningFraction: 0.8, criticalFraction: 0.95,
                minimumDiskReserveBytes: 0, retentionDays: 7
            ).resolvedMinimumDiskReserveBytes(diskCapacityBytes: 100_000_000_000),
            0
        )
    }

    func testStorageProbeResolvesTheDynamicDiskReserve() {
        let policy = LocalBufferPolicy.productBaseline
        let freeAboveReserve = LocalRecordingStorageProbe(
            rootURL: root,
            usedBytes: 4_100_000_000,
            policy: policy,
            availableBytes: { _ in 5_200_000_000 },
            capacityBytes: { _ in 50_000_000_000 }
        )
        let freeBelowReserve = LocalRecordingStorageProbe(
            rootURL: root,
            usedBytes: 4_100_000_000,
            policy: policy,
            availableBytes: { _ in 4_900_000_000 },
            capacityBytes: { _ in 50_000_000_000 }
        )
        let largeDiskKeepsTheTenGigabyteCap = LocalRecordingStorageProbe(
            rootURL: root,
            usedBytes: 4_100_000_000,
            policy: policy,
            availableBytes: { _ in 9_900_000_000 },
            capacityBytes: { _ in 200_000_000_000 }
        )

        XCTAssertEqual(freeAboveReserve.riskState(), .warning)
        XCTAssertEqual(freeBelowReserve.riskState(), .mustDegradeOrStop)
        XCTAssertEqual(largeDiskKeepsTheTenGigabyteCap.riskState(), .mustDegradeOrStop)
    }

    func testCaptureGateBlocksCriticalButAllowsWarning() {
        let service = LocalBufferService()
        let policy = LocalBufferService.defaultPolicy
        let warning = service.riskState(
            usedBytes: Int64(Double(policy.maxBytesPerDevice) * 0.8),
            freeDiskBytes: 100_000_000_000,
            policy: policy
        )
        let critical = service.riskState(
            usedBytes: Int64(Double(policy.maxBytesPerDevice) * 0.95),
            freeDiskBytes: 100_000_000_000,
            policy: policy
        )
        let overBudget = service.riskState(
            usedBytes: policy.maxBytesPerDevice,
            freeDiskBytes: 100_000_000_000,
            policy: policy
        )

        XCTAssertEqual(warning, .warning)
        XCTAssertTrue(warning.allowsRecordingStart)
        XCTAssertEqual(critical, .critical)
        XCTAssertFalse(critical.allowsRecordingStart)
        XCTAssertEqual(overBudget, .mustDegradeOrStop)
        XCTAssertFalse(overBudget.allowsRecordingStart)
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
