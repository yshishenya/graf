import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LocalRecordingWriterSystemAudioTests: XCTestCase {
    func testWriterAcceptsIndependentIncomingSampleSourceWithoutSharedMemory() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("system-audio-writer-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let source = FixtureSampleSource(samples: Array(repeating: 0.25, count: 9_600))
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            incomingSampleSourceFactory: { source },
            recordMicrophone: false
        )

        _ = try writer.start(
            sessionId: "session",
            startedAt: Date(timeIntervalSince1970: 10)
        )
        Thread.sleep(forTimeInterval: 0.15)
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        let incoming = try XCTUnwrap(manifest.tracks.first { $0.role == .remoteSpeaker })
        XCTAssertEqual(incoming.sourceKind, .systemAudio)
        XCTAssertEqual(incoming.fileName, "incoming.wav")
        XCTAssertEqual(incoming.mediaScribeField, .incomingFile)
        XCTAssertEqual(incoming.status, .saved)
        XCTAssertGreaterThan(incoming.frameCount, 0)
    }

    func testWriterReportsIncomingRecorderLevelFromSystemAudioSource() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("system-audio-writer-level-tests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let source = FixtureSampleSource(samples: Array(repeating: 0.5, count: 2_048))
        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            incomingSampleSourceFactory: { source },
            recordMicrophone: false
        )

        _ = try writer.start(
            sessionId: "session",
            startedAt: Date(timeIntervalSince1970: 10)
        )
        Thread.sleep(forTimeInterval: 0.15)
        let now = Date(timeIntervalSince1970: 10.2)
        let levels = writer.currentLevels(now: now)
        _ = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        XCTAssertTrue(levels.isRecording)
        XCTAssertGreaterThan(levels.incomingLevel, 0)
        XCTAssertTrue(levels.incomingIsLive(now: now, staleAfter: 2))
    }
}

private final class FixtureSampleSource: LocalRecordingSampleSource, @unchecked Sendable {
    private var samples: [Float]

    init(samples: [Float]) {
        self.samples = samples
    }

    func readSamples(into destination: UnsafeMutablePointer<Float>, capacity: Int) -> Int {
        guard !samples.isEmpty else { return 0 }
        let count = min(capacity, samples.count)
        for index in 0..<count {
            destination[index] = samples[index]
        }
        samples.removeFirst(count)
        return count
    }
}
#endif
