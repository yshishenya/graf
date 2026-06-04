import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LiveAudioSignalMonitorTests: XCTestCase {
    func testPhysicalMicWriteWithoutVirtualClientReadDoesNotRouteMicrophone() {
        let source = FakeLiveAudioSignalSource(
            snapshot: .init(
                micReadIndex: 0,
                micWriteIndex: 4,
                speakerReadIndex: 0,
                speakerWriteIndex: 0,
                captureReadIndex: 0,
                captureWriteIndex: 0,
                checkedAt: Date(timeIntervalSince1970: 10)
            ),
            micSamples: [0.4, 0.4, 0.4, 0.4]
        )
        let monitor = LiveAudioSignalMonitor(sampleSource: source, scratchCapacity: 4)
        let now = Date(timeIntervalSince1970: 10)

        let levels = monitor.currentLevels(routeActive: true, now: now)

        XCTAssertFalse(levels.microphoneIsLive(now: now, staleAfter: 0.45))
        XCTAssertEqual(levels.microphoneLevel, 0)
    }

    func testVirtualMicReadAndWriteEvidenceRoutesMicrophone() {
        let source = FakeLiveAudioSignalSource(
            snapshot: .init(
                micReadIndex: 2,
                micWriteIndex: 4,
                speakerReadIndex: 0,
                speakerWriteIndex: 0,
                captureReadIndex: 0,
                captureWriteIndex: 0,
                checkedAt: Date(timeIntervalSince1970: 10)
            ),
            micSamples: [0.25, 0.25, 0.25, 0.25]
        )
        let monitor = LiveAudioSignalMonitor(sampleSource: source, scratchCapacity: 4)
        let now = Date(timeIntervalSince1970: 10)

        let levels = monitor.currentLevels(routeActive: true, now: now)

        XCTAssertTrue(levels.microphoneIsLive(now: now, staleAfter: 0.45))
        XCTAssertGreaterThan(levels.microphoneLevel, 0)
    }

    func testCaptureWriteEvidenceRoutesIncoming() {
        let source = FakeLiveAudioSignalSource(
            snapshot: .init(
                micReadIndex: 0,
                micWriteIndex: 0,
                speakerReadIndex: 0,
                speakerWriteIndex: 0,
                captureReadIndex: 0,
                captureWriteIndex: 4,
                checkedAt: Date(timeIntervalSince1970: 10)
            ),
            captureSamples: [0.5, 0.5, 0.5, 0.5]
        )
        let monitor = LiveAudioSignalMonitor(sampleSource: source, scratchCapacity: 4)
        let now = Date(timeIntervalSince1970: 10)

        let levels = monitor.currentLevels(routeActive: true, now: now)

        XCTAssertTrue(levels.speakerIsLive(now: now, staleAfter: 0.45))
        XCTAssertGreaterThan(levels.speakerLevel, 0)
    }

    func testSpeakerWriteFallbackRoutesIncomingWhenCaptureDoesNotAdvance() {
        let source = FakeLiveAudioSignalSource(
            snapshot: .init(
                micReadIndex: 0,
                micWriteIndex: 0,
                speakerReadIndex: 0,
                speakerWriteIndex: 4,
                captureReadIndex: 0,
                captureWriteIndex: 0,
                checkedAt: Date(timeIntervalSince1970: 10)
            ),
            speakerSamples: [0.6, 0.6, 0.6, 0.6]
        )
        let monitor = LiveAudioSignalMonitor(sampleSource: source, scratchCapacity: 4)
        let now = Date(timeIntervalSince1970: 10)

        let levels = monitor.currentLevels(routeActive: true, now: now)

        XCTAssertTrue(levels.speakerIsLive(now: now, staleAfter: 0.45))
        XCTAssertGreaterThan(levels.speakerLevel, 0)
    }
}

private final class FakeLiveAudioSignalSource: LiveAudioSignalSampleSource {
    var snapshot: SharedAudioMemory.WriteIndexSnapshot
    var micSamples: [Float]
    var speakerSamples: [Float]
    var captureSamples: [Float]

    init(
        snapshot: SharedAudioMemory.WriteIndexSnapshot,
        micSamples: [Float] = [],
        speakerSamples: [Float] = [],
        captureSamples: [Float] = []
    ) {
        self.snapshot = snapshot
        self.micSamples = micSamples
        self.speakerSamples = speakerSamples
        self.captureSamples = captureSamples
    }

    func writeIndexSnapshot(checkedAt: Date) -> SharedAudioMemory.WriteIndexSnapshot {
        snapshot.checkedAt = checkedAt
        return snapshot
    }

    func peekLatestMic(dst: UnsafeMutablePointer<Float>, count: Int) -> Int {
        copy(samples: micSamples, dst: dst, count: count)
    }

    func peekLatestSpeaker(dst: UnsafeMutablePointer<Float>, count: Int) -> Int {
        copy(samples: speakerSamples, dst: dst, count: count)
    }

    func peekLatestCapture(dst: UnsafeMutablePointer<Float>, count: Int) -> Int {
        copy(samples: captureSamples, dst: dst, count: count)
    }

    private func copy(samples: [Float], dst: UnsafeMutablePointer<Float>, count: Int) -> Int {
        let copyCount = min(samples.count, count)
        guard copyCount > 0 else { return 0 }
        for index in 0..<copyCount {
            dst[index] = samples[index]
        }
        return copyCount
    }
}
#endif
