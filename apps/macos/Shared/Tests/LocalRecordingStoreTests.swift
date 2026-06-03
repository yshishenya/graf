import Foundation
import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

final class LocalRecordingStoreTests: XCTestCase {
    func testCreatesSafeSessionDirectoryAndArtifactURLs() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-store-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let directory = try LocalRecordingStore(rootURL: root)
            .createDirectory(sessionId: "session/with unsafe spaces")

        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.directoryURL.path))
        XCTAssertFalse(directory.directoryId.contains("/"))
        XCTAssertEqual(directory.manifestURL.lastPathComponent, "manifest.json")
        XCTAssertEqual(directory.localMicURL.lastPathComponent, "local-mic.wav")
        XCTAssertEqual(directory.remoteSpeakerURL.lastPathComponent, "remote-speaker.wav")
    }
}
#endif
