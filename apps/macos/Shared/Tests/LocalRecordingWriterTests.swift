import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LocalRecordingWriterTests: XCTestCase {
    func testWriterFinalizesTruthfulDegradedManifestWhenNoFramesAreAvailable() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-writer-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            sharedMemoryFactory: { nil },
            recordMicrophone: false
        )

        let directory = try writer.start(
            sessionId: "session",
            startedAt: Date(timeIntervalSince1970: 10)
        )
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.manifestURL.path))
        XCTAssertEqual(manifest.status, .degraded)
        XCTAssertFalse(manifest.isComplete)
        XCTAssertEqual(Set(manifest.tracks.map(\.role)), Set([.localMic, .remoteSpeaker]))
    }
}
#endif
