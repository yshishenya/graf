import Foundation
@testable import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

final class RecordingAudioTimelineTests: XCTestCase {
    private func makeTimeline(
        configuration: RecordingAudioTimelineConfiguration = .init(),
        frameSink: @escaping (RecordingAudioTimelineChunk) throws -> Void = { _ in }
    ) -> RecordingAudioTimeline {
        RecordingAudioTimeline(
            configuration: configuration,
            processEchoFrame: { _, microphone in microphone },
            frameSink: frameSink
        )
    }

    func testAECFramingPadsAndTrimsEveryCallbackPartition() throws {
        for sampleCount in [1, 479, 480, 481, 1_024, 4_096] {
            let collector = TimelineCollector()
            let spy = EchoFrameSpy()
            let timeline = RecordingAudioTimeline(
                configuration: .init(reorderWindowFrames: 0),
                processEchoFrame: spy.process,
                frameSink: collector.append
            )

            try timeline.append(
                source: .microphone,
                batch: batch(samples: Array(repeating: 0.4, count: sampleCount), at: 0)
            )
            try timeline.append(
                source: .systemAudio,
                batch: batch(samples: Array(repeating: 0.2, count: sampleCount), at: 0)
            )
            try timeline.finish()

            XCTAssertEqual(spy.frameSizes, Array(repeating: 480, count: (sampleCount + 479) / 480))
            XCTAssertEqual(collector.samples.count, sampleCount)
            XCTAssertTrue(collector.samples.allSatisfy { abs($0 - 0.3) < 0.0001 })
            XCTAssertEqual(timeline.metrics.echoProcessedFrameCount, Int64((sampleCount + 479) / 480))
        }
    }

    func testMissingRenderReferenceAndProcessorFailureKeepOnlyCleanedPrefix() throws {
        var diagnostics: [String] = []
        let missingReference = RecordingAudioTimeline(
            configuration: .init(reorderWindowFrames: 0),
            diagnosticLogger: { diagnostics.append($0) },
            processEchoFrame: { _, microphone in microphone }
        )
        try missingReference.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.4, count: 960), at: 0)
        )
        try missingReference.append(
            source: .systemAudio,
            batch: batch(samples: Array(repeating: 0.2, count: 480), at: 0)
        )
        // A short 10 ms system-audio gap is bridged with silence, not fatal.
        XCTAssertNoThrow(
            try missingReference.append(
                source: .systemAudio,
                batch: batch(samples: Array(repeating: 0.2, count: 480), at: 0.02)
            )
        )
        XCTAssertEqual(missingReference.metrics.outputFrameCount, 960)
        XCTAssertEqual(missingReference.metrics.hostUnderrunCount, 0)
        XCTAssertEqual(missingReference.metrics.continuityGapBridgedFrames, 480)
        XCTAssertEqual(diagnostics, ["recording_timeline_gap source=systemAudio expected_frame=480 requested_frame=960 input_frames=480 converted_frames=480 rate=48000 channels=1 continuous=1"])
        XCTAssertNoThrow(try missingReference.append(
            source: .systemAudio,
            batch: batch(samples: Array(repeating: 0.2, count: 480), at: 0.04)
        ))
        XCTAssertEqual(diagnostics.count, 1)
        XCTAssertTrue(missingReference.finishPreservingAvailableAudio())
        XCTAssertEqual(missingReference.metrics.outputFrameCount, 960)

        let collector = TimelineCollector()
        let spy = EchoFrameSpy(failOnCall: 2)
        let failedProcessor = RecordingAudioTimeline(
            configuration: .init(reorderWindowFrames: 0),
            processEchoFrame: spy.process,
            frameSink: collector.append
        )
        try failedProcessor.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.4, count: 960), at: 0)
        )
        XCTAssertThrowsError(
            try failedProcessor.append(
                source: .systemAudio,
                batch: batch(samples: Array(repeating: 0.2, count: 960), at: 0)
            )
        ) {
            XCTAssertEqual(
                $0 as? RecordingAudioTimelineError,
                .echoProcessingFailed(.captureFailed)
            )
        }
        XCTAssertTrue(failedProcessor.finishPreservingAvailableAudio())
        XCTAssertEqual(collector.samples.count, 480)
        XCTAssertEqual(failedProcessor.metrics.processErrorCount, 1)
    }

    func testSystemAudioGapBeyondBridgeBoundFailsClosed() throws {
        let timeline = makeTimeline(
            configuration: .init(reorderWindowFrames: 0, maximumKnownGapSeconds: 15)
        )
        try timeline.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.4, count: 1_920), at: 0)
        )
        try timeline.append(
            source: .systemAudio,
            batch: batch(samples: Array(repeating: 0.2, count: 480), at: 0)
        )
        XCTAssertThrowsError(
            try timeline.append(
                source: .systemAudio,
                batch: batch(samples: Array(repeating: 0.2, count: 480), at: 1.0)
            )
        ) { error in
            XCTAssertEqual(error as? RecordingAudioTimelineError, .renderReferenceMissing)
        }
        XCTAssertEqual(timeline.metrics.outputFrameCount, 480)
        XCTAssertEqual(timeline.metrics.continuityGapBridgedFrames, 0)
        XCTAssertTrue(timeline.finishPreservingAvailableAudio())
    }

    func testSystemAudioGapAtBridgeBoundaryIsAcceptedAndJustOverIsNot() throws {
        let atBoundary = makeTimeline(
            configuration: .init(reorderWindowFrames: 0, maximumKnownGapSeconds: 15)
        )
        try atBoundary.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.4, count: 19_200), at: 0)
        )
        try atBoundary.append(
            source: .systemAudio,
            batch: batch(samples: Array(repeating: 0.2, count: 4_800), at: 0)
        )
        XCTAssertNoThrow(
            try atBoundary.append(
                source: .systemAudio,
                batch: batch(samples: Array(repeating: 0.2, count: 4_800), at: 0.6)
            )
        )
        XCTAssertEqual(atBoundary.metrics.continuityGapBridgedFrames, 24_000)
        XCTAssertTrue(atBoundary.finishPreservingAvailableAudio())

        let overBoundary = makeTimeline(
            configuration: .init(reorderWindowFrames: 0, maximumKnownGapSeconds: 15)
        )
        try overBoundary.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.4, count: 19_200), at: 0)
        )
        try overBoundary.append(
            source: .systemAudio,
            batch: batch(samples: Array(repeating: 0.2, count: 4_800), at: 0)
        )
        XCTAssertThrowsError(
            try overBoundary.append(
                source: .systemAudio,
                batch: batch(samples: Array(repeating: 0.2, count: 4_800), at: 0.6001)
            )
        ) { error in
            XCTAssertEqual(error as? RecordingAudioTimelineError, .renderReferenceMissing)
        }
        XCTAssertEqual(overBoundary.metrics.continuityGapBridgedFrames, 0)
        XCTAssertTrue(overBoundary.finishPreservingAvailableAudio())
    }

    func testRouteChangeRebasesNewGenerationWithoutLosingFrames() throws {
        let timeline = makeTimeline(
            configuration: .init(reorderWindowFrames: 0, maximumKnownGapSeconds: 15)
        )
        try timeline.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.4, count: 1_920), at: 0)
        )
        try timeline.append(
            source: .systemAudio,
            batch: batch(
                samples: Array(repeating: 0.2, count: 480),
                at: 0,
                routeGeneration: 1
            )
        )
        XCTAssertNoThrow(
            try timeline.append(
                source: .systemAudio,
                batch: RecordingAudioBatch(
                    samples: [],
                    format: RecordingAudioFormat(sampleRate: 48_000, channelCount: 1),
                    presentationTime: RecordingAudioPresentationTimestamp(
                        seconds: 0.01,
                        clockDomain: .wallClock
                    ),
                    discontinuity: .routeChanged,
                    routeGeneration: 1
                )
            )
        )
        // New stream starts its PTS at zero; it must be rebased after the
        // existing 480-frame prefix, not trimmed as negative time.
        XCTAssertNoThrow(
            try timeline.append(
                source: .systemAudio,
                batch: batch(
                    samples: Array(repeating: 0.2, count: 480),
                    at: 0,
                    routeGeneration: 2
                )
            )
        )
        XCTAssertNoThrow(
            try timeline.append(
                source: .systemAudio,
                batch: batch(
                    samples: Array(repeating: 0.2, count: 480),
                    at: 0.01,
                    routeGeneration: 2
                )
            )
        )
        XCTAssertEqual(timeline.metrics.continuityRouteChangeCount, 1)
        XCTAssertEqual(timeline.metrics.outputFrameCount, 1_440)
        XCTAssertTrue(timeline.finishPreservingAvailableAudio())
    }

    func testContinuousRouteChangeDoesNotInsertPreviousBatchDuration() throws {
        let timeline = makeTimeline(
            configuration: .init(reorderWindowFrames: 0, maximumKnownGapSeconds: 15)
        )
        try timeline.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.4, count: 192_000), at: 0)
        )
        try timeline.append(
            source: .systemAudio,
            batch: batch(
                samples: Array(repeating: 0.2, count: 4_800),
                at: 0,
                observedHostTimeSeconds: 100,
                routeGeneration: 1
            )
        )
        XCTAssertNoThrow(
            try timeline.append(
                source: .systemAudio,
                batch: routeMarker(at: 0.01, routeGeneration: 1)
            )
        )
        // The previous system batch lasts 100 ms and ends at host time 100.1.
        // The new stream starts exactly there; no artificial 100 ms silence.
        XCTAssertNoThrow(
            try timeline.append(
                source: .systemAudio,
                batch: batch(
                    samples: Array(repeating: 0.2, count: 480),
                    at: 0,
                    observedHostTimeSeconds: 100.1,
                    routeGeneration: 2
                )
            )
        )
        XCTAssertNoThrow(
            try timeline.append(
                source: .systemAudio,
                batch: batch(
                    samples: Array(repeating: 0.2, count: 480),
                    at: 0.01,
                    observedHostTimeSeconds: 100.11,
                    routeGeneration: 2
                )
            )
        )
        XCTAssertEqual(timeline.metrics.continuityGapBridgedFrames, 0)
        XCTAssertEqual(timeline.metrics.outputFrameCount, 5_760)
        XCTAssertTrue(timeline.finishPreservingAvailableAudio())
    }

    func testContiguousPTSIgnoresCallbackLatency() throws {
        let timeline = makeTimeline(
            configuration: .init(reorderWindowFrames: 0, maximumKnownGapSeconds: 15)
        )
        try timeline.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.4, count: 192_000), at: 0)
        )
        try timeline.append(
            source: .systemAudio,
            batch: batch(
                samples: Array(repeating: 0.2, count: 4_800),
                at: 0,
                observedHostTimeSeconds: 100,
                routeGeneration: 1
            )
        )
        XCTAssertNoThrow(
            try timeline.append(
                source: .systemAudio,
                batch: routeMarker(at: 0.01, routeGeneration: 1)
            )
        )
        // PTS is exactly contiguous at 0.1 s; the callback arrives 100 ms late.
        // Host latency must not manufacture silence in the media timeline.
        XCTAssertNoThrow(
            try timeline.append(
                source: .systemAudio,
                batch: batch(
                    samples: Array(repeating: 0.2, count: 480),
                    at: 0.1,
                    observedHostTimeSeconds: 100.2,
                    routeGeneration: 2
                )
            )
        )
        XCTAssertEqual(timeline.metrics.continuityGapBridgedFrames, 0)
        XCTAssertEqual(timeline.metrics.outputFrameCount, 5_280)
        XCTAssertTrue(timeline.finishPreservingAvailableAudio())
    }

    func testRouteChangeDoesNotCompressMaterialSystemAudioGap() throws {
        let timeline = makeTimeline(
            configuration: .init(reorderWindowFrames: 0, maximumKnownGapSeconds: 15)
        )
        try timeline.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.4, count: 192_000), at: 0)
        )
        try timeline.append(
            source: .systemAudio,
            batch: batch(
                samples: Array(repeating: 0.2, count: 480),
                at: 0,
                observedHostTimeSeconds: 0,
                routeGeneration: 1
            )
        )
        XCTAssertNoThrow(
            try timeline.append(
                source: .systemAudio,
                batch: routeMarker(at: 0.01, routeGeneration: 1)
            )
        )
        // The new stream continues 3 seconds later. The route marker must not
        // compress that gap to zero and shift the system reference.
        XCTAssertThrowsError(
            try timeline.append(
                source: .systemAudio,
                batch: batch(
                    samples: Array(repeating: 0.2, count: 480),
                    at: 3.01,
                    observedHostTimeSeconds: 3.01,
                    routeGeneration: 2
                )
            )
        ) {
            XCTAssertEqual($0 as? RecordingAudioTimelineError, .renderReferenceMissing)
        }
        XCTAssertEqual(timeline.metrics.continuityGapBridgedFrames, 0)
        XCTAssertTrue(timeline.finishPreservingAvailableAudio())
    }

    func testRouteChangeWithResetClockUsesHostGap() throws {
        let timeline = makeTimeline(
            configuration: .init(reorderWindowFrames: 0, maximumKnownGapSeconds: 15)
        )
        try timeline.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.4, count: 192_000), at: 0)
        )
        try timeline.append(
            source: .systemAudio,
            batch: batch(
                samples: Array(repeating: 0.2, count: 480),
                at: 0,
                observedHostTimeSeconds: 0,
                routeGeneration: 1
            )
        )
        XCTAssertNoThrow(
            try timeline.append(
                source: .systemAudio,
                batch: routeMarker(at: 0.01, routeGeneration: 1)
            )
        )
        // A reset PTS alone would look like zero gap. The host clock proves the
        // three-second loss, so the timeline must keep the prefix and fail
        // closed instead of claiming a full recording.
        XCTAssertThrowsError(
            try timeline.append(
                source: .systemAudio,
                batch: batch(
                    samples: Array(repeating: 0.2, count: 480),
                    at: 0,
                    observedHostTimeSeconds: 3.01,
                    routeGeneration: 2
                )
            )
        ) {
            XCTAssertEqual($0 as? RecordingAudioTimelineError, .renderReferenceMissing)
        }
        XCTAssertTrue(timeline.finishPreservingAvailableAudio())
    }

    func testSecondRouteChangeIsAccepted() throws {
        let timeline = makeTimeline(
            configuration: .init(reorderWindowFrames: 0, maximumKnownGapSeconds: 15)
        )
        try timeline.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.4, count: 192_000), at: 0)
        )
        try timeline.append(
            source: .systemAudio,
            batch: batch(samples: Array(repeating: 0.2, count: 480), at: 0, routeGeneration: 1)
        )
        XCTAssertNoThrow(try timeline.append(
            source: .systemAudio,
            batch: routeMarker(at: 0.01, routeGeneration: 1)
        ))
        XCTAssertNoThrow(try timeline.append(
            source: .systemAudio,
            batch: batch(samples: Array(repeating: 0.2, count: 480), at: 0, routeGeneration: 2)
        ))
        XCTAssertNoThrow(try timeline.append(
            source: .systemAudio,
            batch: routeMarker(at: 0.02, routeGeneration: 2)
        ))
        XCTAssertNoThrow(try timeline.append(
            source: .systemAudio,
            batch: batch(samples: Array(repeating: 0.2, count: 480), at: 0, routeGeneration: 3)
        ))
        XCTAssertEqual(timeline.metrics.continuityRouteChangeCount, 2)
        XCTAssertTrue(timeline.finishPreservingAvailableAudio())
    }

    private func routeMarker(
        at seconds: Double,
        routeGeneration: Int
    ) -> RecordingAudioBatch {
        RecordingAudioBatch(
            samples: [],
            format: RecordingAudioFormat(sampleRate: 48_000, channelCount: 1),
            presentationTime: RecordingAudioPresentationTimestamp(
                seconds: seconds,
                clockDomain: .wallClock
            ),
            discontinuity: .routeChanged,
            routeGeneration: routeGeneration
        )
    }

    func testRouteChangeAllowsNewSampleRateAfterRebase() throws {
        let timeline = makeTimeline(configuration: .init(reorderWindowFrames: 0))
        try timeline.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.4, count: 19_200), at: 0)
        )
        try timeline.append(
            source: .systemAudio,
            batch: batch(
                samples: Array(repeating: 0.2, count: 9_600),
                at: 0,
                routeGeneration: 1
            )
        )
        XCTAssertNoThrow(
            try timeline.append(
                source: .systemAudio,
                batch: RecordingAudioBatch(
                    samples: [],
                    format: RecordingAudioFormat(sampleRate: 48_000, channelCount: 1),
                    presentationTime: RecordingAudioPresentationTimestamp(
                        seconds: 0.1,
                        clockDomain: .wallClock
                    ),
                    discontinuity: .routeChanged,
                    routeGeneration: 1
                )
            )
        )

        // A new capture route may negotiate a different native sample rate.
        // The converter must be reset, not treated as a format change.
        let newFormat = RecordingAudioFormat(sampleRate: 44_100, channelCount: 1)
        XCTAssertNoThrow(
            try timeline.append(
                source: .systemAudio,
                batch: RecordingAudioBatch(
                    samples: Array(repeating: 0.2, count: 441),
                    format: newFormat,
                    presentationTime: RecordingAudioPresentationTimestamp(
                        seconds: 0,
                        clockDomain: .wallClock
                    ),
                    discontinuity: .none,
                    routeGeneration: 2
                )
            )
        )
        XCTAssertNoThrow(
            try timeline.append(
                source: .systemAudio,
                batch: RecordingAudioBatch(
                    samples: Array(repeating: 0.2, count: 441),
                    format: newFormat,
                    presentationTime: RecordingAudioPresentationTimestamp(
                        seconds: 0.01,
                        clockDomain: .wallClock
                    ),
                    discontinuity: .none,
                    routeGeneration: 2
                )
            )
        )
        XCTAssertEqual(timeline.metrics.continuityRouteChangeCount, 1)
        XCTAssertGreaterThan(timeline.metrics.outputFrameCount, 9_600)
        XCTAssertTrue(timeline.finishPreservingAvailableAudio())
    }

    func testCommonEpochTrimsUnmatchedStartupPrefix() throws {
        let collector = TimelineCollector()
        let timeline = makeTimeline(
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

        XCTAssertEqual(timeline.metrics.outputFrameCount, 480)
        XCTAssertEqual(timeline.metrics.gapFramesBySource[.systemAudio, default: 0], 0)
        XCTAssertEqual(collector.samples.count, 480)
        XCTAssertEqual(collector.samples[0], 0.3, accuracy: 0.0001)
        XCTAssertEqual(collector.samples[479], 0.3, accuracy: 0.0001)
    }

    func testOverlapIsTrimmedDeterministicallyWithoutMovingOutputClock() throws {
        let collector = TimelineCollector()
        let timeline = makeTimeline(
            configuration: .init(reorderWindowFrames: 0, maximumKnownGapSeconds: 2),
            frameSink: collector.append
        )

        try timeline.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.4, count: 480), at: 0)
        )
        try timeline.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.8, count: 480), at: 0.0095)
        )
        try timeline.append(
            source: .systemAudio,
            batch: batch(samples: Array(repeating: 0.2, count: 720), at: 0)
        )
        try timeline.finish()

        XCTAssertEqual(timeline.metrics.overlapTrimmedFramesBySource[.microphone], 24)
        XCTAssertEqual(timeline.metrics.outputFrameCount, 720)
        XCTAssertEqual(collector.samples[0], 0.3, accuracy: 0.0001)
        XCTAssertEqual(collector.samples[479], 0.3, accuracy: 0.0001)
        XCTAssertEqual(collector.samples[480], 0.5, accuracy: 0.0001)
    }

    func testRejectsUncomparableClockDomainsBeforeWritingFrames() throws {
        let timeline = makeTimeline(configuration: .init(reorderWindowFrames: 0))
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

    func testAdmitsNativeSourcePresentationTimesWithJitteryHostObservation() throws {
        let collector = TimelineCollector()
        let timeline = makeTimeline(configuration: .init(reorderWindowFrames: 0), frameSink: collector.append)

        try timeline.append(
            source: .microphone,
            batch: batch(
                samples: Array(repeating: 0.4, count: 480),
                at: 100,
                clockDomain: .sourcePresentationTime,
                observedHostTimeSeconds: 100.01
            )
        )
        try timeline.append(
            source: .systemAudio,
            batch: batch(
                samples: Array(repeating: 0.2, count: 480),
                at: 100,
                clockDomain: .sourcePresentationTime,
                observedHostTimeSeconds: 100.50
            )
        )
        try timeline.append(
            source: .microphone,
            batch: batch(
                samples: Array(repeating: 0.4, count: 480),
                at: 100.01,
                clockDomain: .sourcePresentationTime,
                observedHostTimeSeconds: 100.01
            )
        )
        try timeline.append(
            source: .systemAudio,
            batch: batch(
                samples: Array(repeating: 0, count: 480),
                at: 100.01,
                clockDomain: .sourcePresentationTime,
                observedHostTimeSeconds: 100.75
            )
        )
        try timeline.finish()

        XCTAssertEqual(timeline.metrics.outputFrameCount, 960)
        XCTAssertEqual(collector.samples[0], 0.3, accuracy: 0.0001)
        XCTAssertEqual(collector.samples[480], 0.2, accuracy: 0.0001)
    }

    func testAdmitsNativeSourcePresentationTimeWithoutCallbackObservation() throws {
        let collector = TimelineCollector()
        let timeline = makeTimeline(
            configuration: .init(reorderWindowFrames: 0),
            frameSink: collector.append
        )
        try timeline.append(
            source: .microphone,
            batch: batch(
                samples: Array(repeating: 0.1, count: 480),
                at: 100,
                clockDomain: .sourcePresentationTime
            )
        )
        try timeline.append(
            source: .systemAudio,
            batch: batch(
                samples: Array(repeating: 0.1, count: 480),
                at: 100,
                clockDomain: .sourcePresentationTime
            )
        )
        try timeline.append(
            source: .microphone,
            batch: batch(
                samples: Array(repeating: 0.1, count: 480),
                at: 100.01,
                clockDomain: .sourcePresentationTime,
                observedHostTimeSeconds: 100.51
            )
        )
        try timeline.append(
            source: .systemAudio,
            batch: batch(
                samples: Array(repeating: 0.1, count: 480),
                at: 100.01,
                clockDomain: .sourcePresentationTime
            )
        )
        try timeline.finish()

        XCTAssertEqual(timeline.metrics.outputFrameCount, 960)
        XCTAssertEqual(collector.samples.count, 960)
    }

    func testReorderedCallbackDoesNotMovePTSMarker() throws {
        let collector = TimelineCollector()
        let timeline = makeTimeline(frameSink: collector.append)

        try timeline.append(
            source: .microphone,
            batch: batch(
                samples: Array(repeating: 0.4, count: 480),
                at: 10,
                clockDomain: .sourcePresentationTime
            )
        )
        try timeline.append(
            source: .systemAudio,
            batch: batch(
                samples: Array(repeating: 0.2, count: 480),
                at: 10,
                clockDomain: .sourcePresentationTime
            )
        )
        try timeline.append(
            source: .microphone,
            batch: batch(
                samples: Array(repeating: 0.8, count: 480),
                at: 10.01,
                clockDomain: .sourcePresentationTime,
                observedHostTimeSeconds: 10.51
            )
        )
        try timeline.append(
            source: .systemAudio,
            batch: batch(
                samples: Array(repeating: 0.2, count: 480),
                at: 10.01,
                clockDomain: .sourcePresentationTime,
                observedHostTimeSeconds: 10.02
            )
        )
        try timeline.finish()

        XCTAssertEqual(timeline.metrics.outputFrameCount, 960)
        XCTAssertEqual(collector.samples[0], 0.3, accuracy: 0.0001)
        XCTAssertEqual(collector.samples[479], 0.3, accuracy: 0.0001)
        XCTAssertEqual(collector.samples[480], 0.5, accuracy: 0.0001)
    }

    func testDelayedSourceBatchArrivingWithinFiveHundredMillisecondsIsNotLate() throws {
        let timeline = makeTimeline()

        try timeline.append(
            source: .microphone,
            batch: batch(
                samples: Array(repeating: 0.4, count: 480),
                at: 0,
                clockDomain: .sourcePresentationTime
            )
        )
        try timeline.append(
            source: .systemAudio,
            batch: batch(
                samples: Array(repeating: 0.2, count: 480),
                at: 0,
                clockDomain: .sourcePresentationTime
            )
        )

        for index in 1...60 {
            try timeline.append(
                source: .microphone,
                batch: batch(
                    samples: Array(repeating: 0.4, count: 480),
                    at: Double(index) * 0.01,
                    clockDomain: .sourcePresentationTime
                )
            )
        }

        XCTAssertNoThrow(
            try timeline.append(
                source: .systemAudio,
                batch: batch(
                    samples: Array(repeating: 0.2, count: 480),
                    at: 0.01,
                    clockDomain: .sourcePresentationTime,
                    observedHostTimeSeconds: 0.51
                )
            )
        )
        XCTAssertNoThrow(try timeline.finish())
    }

    func testSlowerSourceCanArriveAfterReorderWindowWithoutFalseLateBatch() throws {
        let timeline = makeTimeline(
            configuration: .init(reorderWindowFrames: 48_000)
        )

        try timeline.append(
            source: .microphone,
            batch: batch(
                samples: Array(repeating: 0.4, count: 480),
                at: 0,
                clockDomain: .sourcePresentationTime
            )
        )
        try timeline.append(
            source: .systemAudio,
            batch: batch(
                samples: Array(repeating: 0.2, count: 480),
                at: 0,
                clockDomain: .sourcePresentationTime
            )
        )

        for index in 1...220 {
            try timeline.append(
                source: .microphone,
                batch: batch(
                    samples: Array(repeating: 0.4, count: 480),
                    at: Double(index) * 0.01,
                    clockDomain: .sourcePresentationTime
                )
            )
        }

        XCTAssertNoThrow(
            try timeline.append(
                source: .systemAudio,
                batch: batch(
                    samples: Array(repeating: 0.2, count: 480),
                    at: 0.01,
                    clockDomain: .sourcePresentationTime
                )
            )
        )
        XCTAssertNoThrow(try timeline.finish())
        XCTAssertGreaterThan(timeline.metrics.outputFrameCount, 0)
    }

    func testSmallPTSDriftRemainsBoundedAndMeasurable() throws {
        let timeline = makeTimeline(
            configuration: .init(
                reorderWindowFrames: 9_600,
                maximumKnownGapSeconds: 0.1
            )
        )

        for index in 0..<100 {
            let microphoneSeconds = Double(index) * 0.01
            let systemSeconds = microphoneSeconds + 0.0001
            try timeline.append(
                source: .microphone,
                batch: batch(samples: Array(repeating: 0.4, count: 480), at: microphoneSeconds)
            )
            try timeline.append(
                source: .systemAudio,
                batch: batch(samples: Array(repeating: 0.2, count: 480), at: systemSeconds)
            )
        }
        try timeline.finish()

        XCTAssertEqual(timeline.metrics.gapFramesBySource[.systemAudio, default: 0], 0)
        XCTAssertGreaterThanOrEqual(timeline.metrics.outputFrameCount, 47_990)
        XCTAssertLessThanOrEqual(timeline.metrics.outputFrameCount, 48_000)
    }

    func testGradualClockDriftDoesNotCreateFalseMissingReference() throws {
        let timeline = makeTimeline(
            configuration: .init(
                reorderWindowFrames: 9_600,
                maximumKnownGapSeconds: 0.1
            )
        )
        let frame = Array(repeating: Float(0.1), count: 480)

        for index in 0..<1_000 {
            try timeline.append(
                source: .microphone,
                batch: batch(samples: frame, at: Double(index) * 0.010_001)
            )
            try timeline.append(
                source: .systemAudio,
                batch: batch(samples: frame, at: Double(index) * 0.009_999)
            )
        }

        XCTAssertNoThrow(try timeline.finish())
        XCTAssertGreaterThan(timeline.metrics.outputFrameCount, 479_800)
        XCTAssertLessThanOrEqual(timeline.metrics.outputFrameCount, 480_000)
    }

    func testSixtyMinuteClockModelStaysRecoverableAtPlusMinusOneHundredPPM() {
        for ppm in [-100.0, 100.0] {
            let actualRate = RecordingAudioTimeline.canonicalSampleRate * (1 + ppm / 1_000_000)
            let batchDuration = 480 / actualRate
            var presentationSeconds = 0.0
            var expectedStart: Int64 = 0
            var maximumCorrection: Int64 = 0

            while presentationSeconds < 3_600 {
                let requestedStart = Int64(
                    (presentationSeconds * RecordingAudioTimeline.canonicalSampleRate).rounded()
                )
                let correction = RecordingAudioTimeline.recoverableClockDelta(
                    requestedStart: requestedStart,
                    expectedStart: expectedStart,
                    limit: 48
                )
                XCTAssertNotNil(correction)
                maximumCorrection = max(maximumCorrection, abs(correction ?? 0))
                expectedStart = requestedStart + 480
                presentationSeconds += batchDuration
            }

            let recoveredDuration = Double(expectedStart) / RecordingAudioTimeline.canonicalSampleRate
            XCTAssertLessThanOrEqual(maximumCorrection, 1)
            XCTAssertLessThan(abs(recoveredDuration - 3_600), 0.011)
        }
    }

    func testDeterministicRandomPartitionsAndCallbackJitterKeepExactOutput() throws {
        let collector = TimelineCollector()
        let timeline = makeTimeline(
            configuration: .init(reorderWindowFrames: 9_600),
            frameSink: collector.append
        )
        let totalFrames = 48_000
        var offsets: [RecordingAudioInput: Int] = [.microphone: 0, .systemAudio: 0]
        var state: UInt64 = 0x177_AEC3

        while offsets.values.contains(where: { $0 < totalFrames }) {
            state = state &* 6_364_136_223_846_793_005 &+ 1
            let preferred: RecordingAudioInput = state.isMultiple(of: 2) ? .microphone : .systemAudio
            let source = offsets[preferred, default: 0] < totalFrames
                ? preferred
                : (preferred == .microphone ? .systemAudio : .microphone)
            let offset = offsets[source, default: 0]
            let count = min(totalFrames - offset, 1 + Int((state >> 32) % 4_096))
            try timeline.append(
                source: source,
                batch: batch(
                    samples: Array(repeating: source == .microphone ? 0.4 : 0.2, count: count),
                    at: Double(offset) / RecordingAudioTimeline.canonicalSampleRate
                )
            )
            offsets[source] = offset + count
        }

        try timeline.finish()
        XCTAssertEqual(collector.samples.count, totalFrames)
        XCTAssertTrue(collector.samples.allSatisfy { abs($0 - 0.3) < 0.0001 })
    }

    func testBackwardPTSAndExcessiveOverlapFailClosed() throws {
        let backward = makeTimeline()
        try backward.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.1, count: 480), at: 1)
        )
        try backward.append(
            source: .systemAudio,
            batch: batch(samples: Array(repeating: 0.1, count: 480), at: 1)
        )
        XCTAssertThrowsError(
            try backward.append(
                source: .microphone,
                batch: batch(samples: Array(repeating: 0.1, count: 480), at: 0.99)
            )
        ) { error in
            XCTAssertEqual(error as? RecordingAudioTimelineError, .lateBatch)
        }

        let overlap = makeTimeline()
        try overlap.append(
            source: .microphone,
            batch: batch(samples: Array(repeating: 0.1, count: 480), at: 0)
        )
        try overlap.append(
            source: .systemAudio,
            batch: batch(samples: Array(repeating: 0.1, count: 480), at: 0)
        )
        XCTAssertThrowsError(
            try overlap.append(
                source: .microphone,
                batch: batch(samples: Array(repeating: 0.1, count: 480), at: 0.005)
            )
        ) { error in
            XCTAssertEqual(error as? RecordingAudioTimelineError, .lateBatch)
        }
    }

    func testRouteGenerationOrDroppedSourceFailsClosed() throws {
        let timeline = makeTimeline(configuration: .init(reorderWindowFrames: 0))
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

        let droppedTimeline = makeTimeline(configuration: .init(reorderWindowFrames: 0))
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

    func testSourceFormatChangeFailsClosed() throws {
        for changedFormat in [
            RecordingAudioFormat(sampleRate: 44_100, channelCount: 1),
            RecordingAudioFormat(sampleRate: 48_000, channelCount: 2)
        ] {
            let timeline = makeTimeline(configuration: .init(reorderWindowFrames: 0))
            try timeline.append(
                source: .microphone,
                batch: batch(samples: Array(repeating: 0.1, count: 480), at: 0)
            )
            try timeline.append(
                source: .systemAudio,
                batch: batch(samples: Array(repeating: 0.1, count: 480), at: 0)
            )
            let sampleCount = changedFormat.channelCount * (changedFormat.sampleRate == 44_100 ? 441 : 480)
            let changedBatch = RecordingAudioBatch(
                samples: Array(repeating: 0.1, count: sampleCount),
                format: changedFormat,
                presentationTime: RecordingAudioPresentationTimestamp(seconds: 0.01, clockDomain: .wallClock),
                routeGeneration: 0
            )

            XCTAssertThrowsError(try timeline.append(source: .microphone, batch: changedBatch)) { error in
                XCTAssertEqual(error as? RecordingAudioTimelineError, .formatChanged)
            }
        }
    }

    func testClockDeltaOverflowIsNotRecoverable() {
        XCTAssertNil(RecordingAudioTimeline.recoverableClockDelta(
            requestedStart: .max,
            expectedStart: .min,
            limit: 48
        ))
    }

    func testBootstrapCapacityFailsBeforeUnboundedSingleSourceBuffering() throws {
        let timeline = makeTimeline(
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
        let timeline = makeTimeline(configuration: .init(reorderWindowFrames: 0))
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
        let timeline = makeTimeline(
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
        let timeline = makeTimeline(
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
        observedHostTimeSeconds: Double? = nil,
        discontinuity: RecordingAudioDiscontinuity = .none,
        routeGeneration: Int = 0
    ) -> RecordingAudioBatch {
        RecordingAudioBatch(
            samples: samples,
            format: RecordingAudioFormat(sampleRate: 48_000, channelCount: 1),
            presentationTime: RecordingAudioPresentationTimestamp(
                seconds: seconds,
                clockDomain: clockDomain,
                observedHostTimeSeconds: observedHostTimeSeconds
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

private final class EchoFrameSpy: @unchecked Sendable {
    private let failOnCall: Int?
    private(set) var frameSizes: [Int] = []

    init(failOnCall: Int? = nil) {
        self.failOnCall = failOnCall
    }

    func process(render: [Float], microphone: [Float]) throws -> [Float] {
        XCTAssertEqual(render.count, 480)
        XCTAssertEqual(microphone.count, 480)
        frameSizes.append(render.count)
        if frameSizes.count == failOnCall {
            throw RecordingEchoProcessorError.captureFailed
        }
        return microphone
    }
}
#endif
