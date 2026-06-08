import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioRecordingPackageTests: XCTestCase {
    func testDualIndependentSourcesProduceMicIncomingAndManifest() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("system-audio-package-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let micSource = BufferedLocalRecordingSampleSource()
        let incomingSource = BufferedLocalRecordingSampleSource()
        micSource.append(Array(repeating: 0.12, count: 48_000))
        incomingSource.append(Array(repeating: 0.20, count: 48_000))

        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            microphoneSampleSourceFactory: { micSource },
            incomingSampleSourceFactory: { incomingSource },
            recordMicrophone: true
        )

        let directory = try writer.start(
            sessionId: "session",
            startedAt: Date(timeIntervalSince1970: 10)
        )
        Thread.sleep(forTimeInterval: 0.2)
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.localMicURL.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.remoteSpeakerURL.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.manifestURL.path))
        XCTAssertEqual(Set(manifest.tracks.map(\.role)), Set([.localMic, .remoteSpeaker]))
        XCTAssertEqual(manifest.tracks.first { $0.role == .localMic }?.sourceKind, .microphone)
        XCTAssertEqual(manifest.tracks.first { $0.role == .remoteSpeaker }?.sourceKind, .systemAudio)
        XCTAssertEqual(manifest.status, .saved)
        XCTAssertTrue(manifest.isComplete)
        XCTAssertFalse(manifest.externalEgressStarted)
        XCTAssertFalse(manifest.transcriptionStarted)
    }
}
#endif
