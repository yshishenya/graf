import Foundation
@testable import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

final class RecordingAudioTimelineTests: XCTestCase {
    func testCommonEpochPlacesLaterSourceAfterExactSilenceGap() throws {
        let collector = TimelineCollector()
        let timeline = RecordingAudioTimeline(
            configuration: .init(reorderWindowFrames: 0, maximumKnownGapSeconds: 2),
            frameSink: collector.append
        )

        try timeline.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.4, count: 960), at: 10.0)
        )
        try timeline.append(
            source: .systemAudio,
            batch: batch(samples: Array(repeating: 0.2, count: 480), at: 10.01)
        )
        try timeline.finish()

        XCTAssertEqual(timeline.metrics.outputFrameCount, 960)
        XCTAssertEqual(timeline.metrics.gapFramesBySource[.systemAudio], 480)
        XCTAssertEqual(collector.samples.count, 960)
        XCTAssertEqual(collector.samples[0], 0.2, accuracy: 0.0001)
        XCTAssertEqual(collector.samples[479], 0.2, accuracy: 0.0001)
        XCTAssertEqual(collector.samples[480], 0.3, accuracy: 0.0001)
    }

    func testOverlapIsTrimmedDeterministicallyWithoutMovingOutputClock() throws {
        let collector = TimelineCollector()
        let timeline = RecordingAudioTimeline(
            configuration: .init(reorderWindowFrames: 0, maximumKnownGapSeconds: 2),
            frameSink: collector.append
        )

        try timeline.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.4, count: 480), at: 0)
        )
        try timeline.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.8, count: 480), at: 0.005)
        )
        try timeline.append(
            source: .systemAudio,
            batch: batch(samples: Array(repeating: 0.2, count: 720), at: 0)
        )
        try timeline.finish()

        XCTAssertEqual(timeline.metrics.overlapTrimmedFramesBySource[.microphone], 240)
        XCTAssertEqual(timeline.metrics.outputFrameCount, 720)
        XCTAssertEqual(collector.samples[0], 0.3, accuracy: 0.0001)
        XCTAssertEqual(collector.samples[479], 0.3, accuracy: 0.0001)
        XCTAssertEqual(collector.samples[480], 0.5, accuracy: 0.0001)
    }

    func testRejectsUncomparableClockDomainsBeforeWritingFrames() throws {
        let timeline = RecordingAudioTimeline(configuration: .init(reorderWindowFrames: 0))
        try timeline.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.1, count: 480), at: 10, clockDomain: .hostTime)
        )

        XCTAssertThrowsError(
            try timeline.append(
                source: .systemAudio,
                batch: batch(samples: Array(repeating: 0.1, count: 480), at: 10, clockDomain: .wallClock)
            )
        ) { error in
            XCTAssertEqual(error as? RecordingAudioTimelineError, .uncomparablePresentationTimes)
        }
        XCTAssertEqual(timeline.metrics.outputFrameCount, 0)
    }

    func testRouteGenerationOrDroppedSourceFailsClosed() throws {
        let timeline = RecordingAudioTimeline(configuration: .init(reorderWindowFrames: 0))
        try timeline.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.1, count: 480), at: 0, routeGeneration: 1)
        )

        XCTAssertThrowsError(
            try timeline.append(
                source: .microphone,
                batch: batch(samples: Array(repeating: 0.1, count: 480), at: 0.01, routeGeneration: 2)
            )
        ) { error in
            XCTAssertEqual(error as? RecordingAudioTimelineError, .routeGenerationChanged)
        }

        let droppedTimeline = RecordingAudioTimeline(configuration: .init(reorderWindowFrames: 0))
        XCTAssertThrowsError(
            try droppedTimeline.append(
                source: .systemAudio,
                batch: batch(
                    samples: Array(repeating: 0.1, count: 480),
                    at: 0,
                    discontinuity: .dropped
                )
            )
        ) { error in
            XCTAssertEqual(error as? RecordingAudioTimelineError, .sourceOverflow)
        }
    }

    func testBootstrapCapacityFailsBeforeUnboundedSingleSourceBuffering() throws {
        let timeline = RecordingAudioTimeline(
            configuration: .init(
                reorderWindowFrames: 0,
                maximumBufferedFramesPerSource: 100
            )
        )

        XCTAssertThrowsError(
            try timeline.append(
                source: .microphone,
                batch: batch(samples: Array(repeating: 0.1, count: 480), at: 0)
            )
        ) { error in
            XCTAssertEqual(error as? RecordingAudioTimelineError, .sourceOverflow)
        }
    }

    func testFinishRejectsARecordingMissingEitherRequiredInput() throws {
        let timeline = RecordingAudioTimeline(configuration: .init(reorderWindowFrames: 0))
        try timeline.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.1, count: 480), at: 0)
        )

        XCTAssertThrowsError(try timeline.finish()) { error in
            XCTAssertEqual(error as? RecordingAudioTimelineError, .missingRequiredSource)
        }
        XCTAssertEqual(timeline.metrics.outputFrameCount, 0)
    }

    func testRejectsGapBeyondConfiguredBound() throws {
        let timeline = RecordingAudioTimeline(
            configuration: .init(reorderWindowFrames: 0, maximumKnownGapSeconds: 0.1)
        )
        try timeline.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.1, count: 480), at: 0)
        )

        XCTAssertThrowsError(
            try timeline.append(
                source: .microphone,
                batch: batch(samples: Array(repeating: 0.1, count: 480), at: 1)
            )
        ) { error in
            XCTAssertEqual(error as? RecordingAudioTimelineError, .gapExceedsBound)
        }
    }

    func testCanonicalFrameIndexRemainsExactAtSixtyMinuteBoundary() throws {
        let frameIndex = try RecordingAudioTimeline.canonicalFrameIndex(
            for: RecordingAudioPresentationTimestamp(seconds: 3_600, clockDomain: .wallClock),
            relativeTo: RecordingAudioPresentationTimestamp(seconds: 0, clockDomain: .wallClock)
        )

        XCTAssertEqual(frameIndex, 172_800_000)
    }

    func testStatefulConverterNormalizesFortyFourPointOneKilohertzToCanonicalRate() throws {
        let collector = TimelineCollector()
        let timeline = RecordingAudioTimeline(
            configuration: .init(reorderWindowFrames: 0, maximumKnownGapSeconds: 2),
            frameSink: collector.append
        )
        try timeline.append(
            source: .microphone,
            batch: RecordingAudioBatch(
                samples: Array(repeating: 0.4, count: 441),
                format: RecordingAudioFormat(sampleRate: 44_100, channelCount: 1),
                presentationTime: RecordingAudioPresentationTimestamp(seconds: 0, clockDomain: .wallClock),
                discontinuity: .none,
                routeGeneration: 0
            )
        )
        try timeline.append(
            source: .systemAudio,
            batch: batch(samples: Array(repeating: 0.2, count: 480), at: 0)
        )
        try timeline.finish()

        XCTAssertEqual(timeline.metrics.outputFrameCount, 480)
        XCTAssertEqual(collector.samples.count, 480)
        XCTAssertTrue(collector.samples.allSatisfy(\.isFinite))
    }

    private func batch(
        samples: [Float],
        at seconds: Double,
        clockDomain: RecordingAudioClockDomain = .wallClock,
        discontinuity: RecordingAudioDiscontinuity = .none,
        routeGeneration: Int = 0
    ) -> RecordingAudioBatch {
        RecordingAudioBatch(
            samples: samples,
            format: RecordingAudioFormat(sampleRate: 48_000, channelCount: 1),
            presentationTime: RecordingAudioPresentationTimestamp(
                seconds: seconds,
                clockDomain: clockDomain
            ),
            discontinuity: discontinuity,
            routeGeneration: routeGeneration
        )
    }
}

private final class TimelineCollector: @unchecked Sendable {
    private(set) var samples: [Float] = []

    func append(_ chunk: RecordingAudioTimelineChunk) throws {
        samples.append(contentsOf: chunk.samples)
    }
}
#endif
