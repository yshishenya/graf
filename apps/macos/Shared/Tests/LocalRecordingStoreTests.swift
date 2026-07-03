import Foundation
import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

final class LocalRecordingStoreTests: XCTestCase {
    func testBuildsCurrentAndLegacyRecordingRootsFromSameBase() {
        let base = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-store-roots-\(UUID().uuidString)", isDirectory: true)

        XCTAssertEqual(
            LocalRecordingStore.currentRootURL(baseURL: base).path,
            base.appendingPathComponent("GRAF/Recordings", isDirectory: true).path
        )
        XCTAssertEqual(
            LocalRecordingStore.legacyRootURL(baseURL: base).path,
            base.appendingPathComponent("2brain Rec/Recordings", isDirectory: true).path
        )
    }

    func testCreatesSafeSessionDirectoryAndArtifactURLs() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-store-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let directory = try LocalRecordingStore(rootURL: root)
            .createDirectory(sessionId: "session/with unsafe spaces")

        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.directoryURL.path))
        XCTAssertFalse(directory.directoryId.contains("/"))
        XCTAssertEqual(directory.manifestURL.lastPathComponent, "manifest.json")
        XCTAssertEqual(directory.localMicURL.lastPathComponent, "mic.wav")
        XCTAssertEqual(directory.remoteSpeakerURL.lastPathComponent, "incoming.wav")
    }
}
#endif
