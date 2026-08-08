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
        XCTAssertEqual(directory.transcriptionAudioURL.lastPathComponent, "meeting-transcription.wav")
        XCTAssertEqual(directory.reviewAudioURL.lastPathComponent, "meeting-review.m4a")
    }

    func testDefaultRootKeepsExistingLegacyRecordingLibraryReadable() throws {
        let applicationSupport = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-root-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: applicationSupport) }
        let legacyRoot = applicationSupport
            .appendingPathComponent(LocalRecordingStore.legacyAppSupportFolderName, isDirectory: true)
            .appendingPathComponent("Recordings", isDirectory: true)
        try FileManager.default.createDirectory(at: legacyRoot, withIntermediateDirectories: true)

        let resolved = LocalRecordingStore.defaultRootURL(
            fileManager: .default,
            applicationSupportURL: applicationSupport
        )

        XCTAssertEqual(resolved.standardizedFileURL, legacyRoot.standardizedFileURL)
    }

    func testDefaultRootPrefersCurrentLibraryWhenBothRootsExist() throws {
        let applicationSupport = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-root-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: applicationSupport) }
        let currentRoot = applicationSupport
            .appendingPathComponent(LocalRecordingStore.appSupportFolderName, isDirectory: true)
            .appendingPathComponent("Recordings", isDirectory: true)
        let legacyRoot = applicationSupport
            .appendingPathComponent(LocalRecordingStore.legacyAppSupportFolderName, isDirectory: true)
            .appendingPathComponent("Recordings", isDirectory: true)
        try FileManager.default.createDirectory(at: currentRoot, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: legacyRoot, withIntermediateDirectories: true)

        let resolved = LocalRecordingStore.defaultRootURL(
            fileManager: .default,
            applicationSupportURL: applicationSupport
        )

        XCTAssertEqual(resolved.standardizedFileURL, currentRoot.standardizedFileURL)
    }
}
#endif
