import Foundation
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class CaptureRecoveryServiceTests: XCTestCase {
    func testRecoveryRepairsCheckpointedWAVRebuildsPlaybackAndIsIdempotent() throws {
        let root = recoveryRoot("repair")
        defer { try? FileManager.default.removeItem(at: root) }
        let directory = try LocalRecordingStore(rootURL: root).createDirectory(sessionId: "repair")
        let service = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
        try service.write(
            service.activeV5Manifest(
                sessionId: "repair",
                directoryId: directory.directoryId,
                startedAt: Date(timeIntervalSince1970: 10),
                scopeApproval: recoveryScopeApproval(),
                permissions: recoveryPermissions()
            ),
            to: directory.manifestURL
        )
        try writeInterruptedPCM16WAV(
            to: directory.directoryURL.appendingPathComponent("meeting-transcription.partial.wav"),
            frameCount: 16_000,
            declaredFrameCount: 0
        )
        let recovery = CaptureRecoveryService(clock: { Date(timeIntervalSince1970: 40) })

        let first = recovery.recoverIncompleteRecordings(in: root, manifestService: service)
        let second = recovery.recoverIncompleteRecordings(in: root, manifestService: service)

        let outcome = try XCTUnwrap(first.first)
        XCTAssertEqual(first.count, 1)
        XCTAssertEqual(second.count, 0)
        XCTAssertEqual(outcome.disposition, .ready)
        XCTAssertEqual(outcome.manifest.status, .saved)
        XCTAssertEqual(outcome.manifest.captureFailureCode, "recording_recovered_after_interruption")
        XCTAssertTrue(outcome.manifest.isComplete)
        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.transcriptionAudioURL.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.reviewAudioURL.path))
        XCTAssertFalse(FileManager.default.fileExists(
            atPath: directory.directoryURL.appendingPathComponent("meeting-transcription.partial.wav").path
        ))
    }

    func testRecoveryClassifiesEmptyInterruptedPackageAsDamagedOnce() throws {
        let root = recoveryRoot("damaged")
        defer { try? FileManager.default.removeItem(at: root) }
        let directory = try LocalRecordingStore(rootURL: root).createDirectory(sessionId: "damaged")
        let service = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
        try service.write(
            service.activeV5Manifest(
                sessionId: "damaged",
                directoryId: directory.directoryId,
                startedAt: Date(timeIntervalSince1970: 10),
                scopeApproval: recoveryScopeApproval(),
                permissions: recoveryPermissions()
            ),
            to: directory.manifestURL
        )
        try Data(repeating: 0, count: 44).write(
            to: directory.directoryURL.appendingPathComponent("meeting-transcription.partial.wav")
        )
        let recovery = CaptureRecoveryService(clock: { Date(timeIntervalSince1970: 40) })

        let first = recovery.recoverIncompleteRecordings(in: root, manifestService: service)
        let second = recovery.recoverIncompleteRecordings(in: root, manifestService: service)

        let outcome = try XCTUnwrap(first.first)
        XCTAssertEqual(first.count, 1)
        XCTAssertEqual(second.count, 0)
        XCTAssertEqual(outcome.disposition, .damaged)
        XCTAssertEqual(outcome.manifest.status, .failed)
        XCTAssertEqual(outcome.manifest.captureFailureCode, "recording_recovery_not_possible")
        XCTAssertEqual(outcome.manifest.transcriptionReadiness, .failed)
    }
}

private func recoveryRoot(_ name: String) -> URL {
    FileManager.default.temporaryDirectory
        .appendingPathComponent("capture-recovery-\(name)-\(UUID().uuidString)", isDirectory: true)
}

private func writeInterruptedPCM16WAV(
    to url: URL,
    frameCount: Int,
    declaredFrameCount: Int
) throws {
    var data = Data(repeating: 0, count: 44)
    for _ in 0..<frameCount {
        var sample = Int16(2_000).littleEndian
        withUnsafeBytes(of: &sample) { data.append(contentsOf: $0) }
    }
    let declaredBytes = UInt32(declaredFrameCount * 2)
    data.replaceSubrange(0..<44, with: recoveryWAVHeader(dataByteCount: declaredBytes))
    try data.write(to: url)
}

private func recoveryWAVHeader(dataByteCount: UInt32) -> Data {
    var data = Data()
    data.append(contentsOf: [0x52, 0x49, 0x46, 0x46])
    data.recoveryAppendLE(UInt32(36) + dataByteCount)
    data.append(contentsOf: [0x57, 0x41, 0x56, 0x45])
    data.append(contentsOf: [0x66, 0x6d, 0x74, 0x20])
    data.recoveryAppendLE(UInt32(16))
    data.recoveryAppendLE(UInt16(1))
    data.recoveryAppendLE(UInt16(1))
    data.recoveryAppendLE(UInt32(16_000))
    data.recoveryAppendLE(UInt32(32_000))
    data.recoveryAppendLE(UInt16(2))
    data.recoveryAppendLE(UInt16(16))
    data.append(contentsOf: [0x64, 0x61, 0x74, 0x61])
    data.recoveryAppendLE(dataByteCount)
    return data
}

private extension Data {
    mutating func recoveryAppendLE<T: FixedWidthInteger>(_ value: T) {
        var value = value.littleEndian
        Swift.withUnsafeBytes(of: &value) { append(contentsOf: $0) }
    }
}

private func recoveryScopeApproval() -> CaptureScopeApproval {
    CaptureScopeApproval(
        scopeApprovalId: "recovery-scope",
        scopeKind: .display,
        sourceDisplayName: "Synthetic Meeting",
        approvedAt: Date(timeIntervalSince1970: 9),
        approvalMode: .userConfirmedSuggestedScope,
        eligibleReason: .manualMeetingScope
    )
}

private func recoveryPermissions() -> SystemAudioPermissionSnapshot {
    SystemAudioPermissionSnapshot(
        microphone: .granted,
        systemAudio: .granted,
        evaluatedAt: Date(timeIntervalSince1970: 9)
    )
}
#endif
