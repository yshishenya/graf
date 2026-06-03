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
        XCTAssertEqual(directory.localMicURL.lastPathComponent, "mic.wav")
        XCTAssertEqual(directory.remoteSpeakerURL.lastPathComponent, "incoming.wav")
        XCTAssertEqual(manifest.status, .degraded)
        XCTAssertEqual(manifest.transcriptionReadiness, .degraded)
        XCTAssertFalse(manifest.isComplete)
        XCTAssertEqual(Set(manifest.tracks.map(\.role)), Set([.localMic, .remoteSpeaker]))
    }

    func testWriterCreatesIncomingWavHeaderInMediaScribeReadyFormat() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-writer-format-tests-\(UUID().uuidString)", isDirectory: true)
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
        _ = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        let header = try WAVHeader(url: directory.remoteSpeakerURL)
        XCTAssertEqual(header.audioFormat, 1)
        XCTAssertEqual(header.channelCount, 1)
        XCTAssertEqual(header.sampleRate, 16_000)
        XCTAssertEqual(header.bitsPerSample, 16)
    }
}

private struct WAVHeader {
    let audioFormat: UInt16
    let channelCount: UInt16
    let sampleRate: UInt32
    let bitsPerSample: UInt16

    init(url: URL) throws {
        let data = try Data(contentsOf: url)
        XCTAssertGreaterThanOrEqual(data.count, 44)
        audioFormat = data.uint16LE(at: 20)
        channelCount = data.uint16LE(at: 22)
        sampleRate = data.uint32LE(at: 24)
        bitsPerSample = data.uint16LE(at: 34)
    }
}

private extension Data {
    func uint16LE(at offset: Int) -> UInt16 {
        UInt16(self[offset]) | (UInt16(self[offset + 1]) << 8)
    }

    func uint32LE(at offset: Int) -> UInt32 {
        UInt32(self[offset]) |
            (UInt32(self[offset + 1]) << 8) |
            (UInt32(self[offset + 2]) << 16) |
            (UInt32(self[offset + 3]) << 24)
    }
}
#endif
