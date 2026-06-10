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

    func testStaleIncomingLevelResetsInsteadOfHoldingLastBar() {
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
            captureSamples: [0.7, 0.7, 0.7, 0.7]
        )
        let monitor = LiveAudioSignalMonitor(sampleSource: source, scratchCapacity: 4)
        let first = monitor.currentLevels(routeActive: true, now: Date(timeIntervalSince1970: 10))
        source.snapshot.captureWriteIndex = 4
        source.captureSamples = []

        let stale = monitor.currentLevels(routeActive: true, now: Date(timeIntervalSince1970: 10.6))

        XCTAssertGreaterThan(first.speakerLevel, 0)
        XCTAssertFalse(stale.speakerIsLive(now: Date(timeIntervalSince1970: 10.6), staleAfter: 0.45))
        XCTAssertEqual(stale.speakerLevel, 0)
    }

    func testStaleMicrophoneLevelResetsInsteadOfHoldingLastBar() {
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
            micSamples: [0.4, 0.4, 0.4, 0.4]
        )
        let monitor = LiveAudioSignalMonitor(sampleSource: source, scratchCapacity: 4)
        let first = monitor.currentLevels(routeActive: true, now: Date(timeIntervalSince1970: 10))
        source.snapshot.micReadIndex = 2
        source.snapshot.micWriteIndex = 4
        source.micSamples = []

        let stale = monitor.currentLevels(routeActive: true, now: Date(timeIntervalSince1970: 10.6))

        XCTAssertGreaterThan(first.microphoneLevel, 0)
        XCTAssertFalse(stale.microphoneIsLive(now: Date(timeIntervalSince1970: 10.6), staleAfter: 0.45))
        XCTAssertEqual(stale.microphoneLevel, 0)
    }

    func testFutureMonitorFrameTimestampResetsInsteadOfHoldingFalseLiveBars() {
        let source = FakeLiveAudioSignalSource(
            snapshot: .init(
                micReadIndex: 2,
                micWriteIndex: 4,
                speakerReadIndex: 0,
                speakerWriteIndex: 0,
                captureReadIndex: 0,
                captureWriteIndex: 4,
                checkedAt: Date(timeIntervalSince1970: 11)
            ),
            micSamples: [0.4, 0.4, 0.4, 0.4],
            captureSamples: [0.7, 0.7, 0.7, 0.7]
        )
        let monitor = LiveAudioSignalMonitor(sampleSource: source, scratchCapacity: 4)
        let future = monitor.currentLevels(routeActive: true, now: Date(timeIntervalSince1970: 11))
        source.snapshot.micReadIndex = 2
        source.snapshot.micWriteIndex = 4
        source.snapshot.captureWriteIndex = 4
        source.micSamples = []
        source.captureSamples = []

        let skewed = monitor.currentLevels(routeActive: true, now: Date(timeIntervalSince1970: 10))

        XCTAssertGreaterThan(future.microphoneLevel, 0)
        XCTAssertGreaterThan(future.speakerLevel, 0)
        XCTAssertFalse(skewed.microphoneIsLive(now: Date(timeIntervalSince1970: 10), staleAfter: 0.45))
        XCTAssertFalse(skewed.speakerIsLive(now: Date(timeIntervalSince1970: 10), staleAfter: 0.45))
        XCTAssertEqual(skewed.microphoneLevel, 0)
        XCTAssertEqual(skewed.speakerLevel, 0)
    }

    func testFutureSignalTimestampIsNotTreatedAsLive() {
        let levels = LiveRouteSignalLevels(
            isActive: true,
            microphoneLevel: 0.8,
            speakerLevel: 0.8,
            microphoneUpdatedAt: Date(timeIntervalSince1970: 11),
            speakerUpdatedAt: Date(timeIntervalSince1970: 11)
        )

        XCTAssertFalse(levels.microphoneIsLive(now: Date(timeIntervalSince1970: 10), staleAfter: 2))
        XCTAssertFalse(levels.speakerIsLive(now: Date(timeIntervalSince1970: 10), staleAfter: 2))
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
