@preconcurrency import AVFoundation
import Foundation

enum RecordingAudioRouteGeneration {
    private static let lock = NSLock()
    nonisolated(unsafe) private static var value = 0

    static func next() -> Int {
        lock.lock()
        defer { lock.unlock() }
        value &+= 1
        return value
    }
}

/// The two capture origins that make up a newly recorded meeting.
///
/// These names intentionally describe origin, not a persisted package role. New
/// packages contain only the canonical mixed timeline produced from both inputs.
public enum RecordingAudioInput: String, CaseIterable, Hashable, Sendable {
    case microphone
    case systemAudio
}

/// A timestamp is comparable only to another timestamp from the same clock.
/// Mixing host-time and wall-clock values would manufacture an offset, so it is
/// rejected before any canonical frame is written.
public enum RecordingAudioClockDomain: String, Equatable, Sendable {
    case hostTime
    case wallClock
    /// A producer-owned media PTS. The active native capture path treats this
    /// media timestamp as the source position; callback-time host-clock
    /// observations are optional telemetry and never redefine that position.
    case sourcePresentationTime
}

public struct RecordingAudioPresentationTimestamp: Equatable, Sendable {
    public let seconds: Double
    public let clockDomain: RecordingAudioClockDomain
    public let observedHostTimeSeconds: Double?

    public init(
        seconds: Double,
        clockDomain: RecordingAudioClockDomain,
        observedHostTimeSeconds: Double? = nil
    ) {
        self.seconds = seconds
        self.clockDomain = clockDomain
        self.observedHostTimeSeconds = observedHostTimeSeconds
    }
}

public struct RecordingAudioFormat: Equatable, Sendable {
    public let sampleRate: Double
    public let channelCount: Int

    public init(sampleRate: Double, channelCount: Int) {
        self.sampleRate = sampleRate
        self.channelCount = channelCount
    }
}

/// A capture boundary must make loss and route changes explicit. The timeline
/// never attempts to conceal those conditions with inferred samples.
public enum RecordingAudioDiscontinuity: Equatable, Sendable {
    case none
    case knownGap
    case dropped
    case routeChanged
    case sourceStopped
}

public struct RecordingAudioBatch: Sendable {
    public let samples: [Float]
    public let format: RecordingAudioFormat
    public let presentationTime: RecordingAudioPresentationTimestamp
    public let discontinuity: RecordingAudioDiscontinuity
    public let routeGeneration: Int

    public init(
        samples: [Float],
        format: RecordingAudioFormat,
        presentationTime: RecordingAudioPresentationTimestamp,
        discontinuity: RecordingAudioDiscontinuity = .none,
        routeGeneration: Int = 0
    ) {
        self.samples = samples
        self.format = format
        self.presentationTime = presentationTime
        self.discontinuity = discontinuity
        self.routeGeneration = routeGeneration
    }
}

public struct RecordingAudioTimelineChunk: Sendable {
    public let startFrameIndex: Int64
    public let samples: [Float]

    public init(startFrameIndex: Int64, samples: [Float]) {
        self.startFrameIndex = startFrameIndex
        self.samples = samples
    }
}

public struct RecordingAudioTimelineMetrics: Equatable, Sendable {
    public internal(set) var outputFrameCount: Int64
    public internal(set) var echoProcessedFrameCount: Int64
    public internal(set) var processErrorCount: Int
    public internal(set) var ptsGapCount: Int
    public internal(set) var hostUnderrunCount: Int
    public internal(set) var hostOverrunCount: Int
    public internal(set) var clippedSampleCount: Int64
    public internal(set) var nonFiniteSampleCount: Int64
    public internal(set) var processingTimeP95Ms: Double?
    public internal(set) var gapFramesBySource: [RecordingAudioInput: Int64]
    public internal(set) var overlapTrimmedFramesBySource: [RecordingAudioInput: Int64]

    public init(
        outputFrameCount: Int64 = 0,
        echoProcessedFrameCount: Int64 = 0,
        processErrorCount: Int = 0,
        ptsGapCount: Int = 0,
        hostUnderrunCount: Int = 0,
        hostOverrunCount: Int = 0,
        clippedSampleCount: Int64 = 0,
        nonFiniteSampleCount: Int64 = 0,
        processingTimeP95Ms: Double? = nil,
        gapFramesBySource: [RecordingAudioInput: Int64] = [:],
        overlapTrimmedFramesBySource: [RecordingAudioInput: Int64] = [:]
    ) {
        self.outputFrameCount = outputFrameCount
        self.echoProcessedFrameCount = echoProcessedFrameCount
        self.processErrorCount = processErrorCount
        self.ptsGapCount = ptsGapCount
        self.hostUnderrunCount = hostUnderrunCount
        self.hostOverrunCount = hostOverrunCount
        self.clippedSampleCount = clippedSampleCount
        self.nonFiniteSampleCount = nonFiniteSampleCount
        self.processingTimeP95Ms = processingTimeP95Ms
        self.gapFramesBySource = gapFramesBySource
        self.overlapTrimmedFramesBySource = overlapTrimmedFramesBySource
    }
}

public struct RecordingAudioTimelineConfiguration: Equatable, Sendable {
    /// A bounded one-second look-behind window covers the accepted 500 ms
    /// callback-delay scenario plus scheduling margin without deriving time
    /// from callback order or retaining an unbounded source queue.
    public let reorderWindowFrames: Int64
    public let maximumKnownGapSeconds: Double
    public let maximumBufferedFramesPerSource: Int64
    public let maximumClockRecoveryFramesPerBatch: Int64

    public init(
        reorderWindowFrames: Int = 48_000,
        maximumKnownGapSeconds: Double = 15,
        maximumBufferedFramesPerSource: Int = 48_000 * 20,
        maximumClockRecoveryFramesPerBatch: Int = 48
    ) {
        self.reorderWindowFrames = Int64(max(0, reorderWindowFrames))
        self.maximumKnownGapSeconds = maximumKnownGapSeconds
        self.maximumBufferedFramesPerSource = Int64(max(1, maximumBufferedFramesPerSource))
        self.maximumClockRecoveryFramesPerBatch = Int64(max(0, maximumClockRecoveryFramesPerBatch))
    }
}

public enum RecordingAudioTimelineError: Error, Equatable {
    case invalidTimestamp
    case invalidFormat
    case invalidSamples
    case formatChanged
    case uncomparablePresentationTimes
    case routeGenerationChanged
    case sourceOverflow
    case gapExceedsBound
    case lateBatch
    case missingRequiredSource
    case converterFailed
    case renderReferenceMissing
    case echoProcessingFailed(RecordingEchoProcessorError)
    case echoProcessingOutputInvalid
    case sourceStopped
    case alreadyFinished
}

/// One append-only canonical timeline shared by the transcription WAV and the
/// review M4A. A callback owns the output so a long recording never requires a
/// second in-memory copy of its audio.
public final class RecordingAudioTimeline: @unchecked Sendable {
    public static let canonicalSampleRate: Double = 48_000

    public private(set) var metrics = RecordingAudioTimelineMetrics()

    private let configuration: RecordingAudioTimelineConfiguration
    private let processEchoFrame: ([Float], [Float]) throws -> [Float]
    private let frameSink: (RecordingAudioTimelineChunk) throws -> Void
    private var pendingBootstrapBatches: [(source: RecordingAudioInput, batch: RecordingAudioBatch)] = []
    private var states: [RecordingAudioInput: SourceState] = [:]
    private var observedRouteGenerations: [RecordingAudioInput: Int] = [:]
    private var bootstrapSourceEndSeconds: [RecordingAudioInput: Double] = [:]
    private var bootstrapBufferedCanonicalFrames: [RecordingAudioInput: Int64] = [:]
    private var epoch: RecordingAudioPresentationTimestamp?
    private var emittedThroughFrame: Int64 = 0
    private var finished = false
    private var processingTimeHistogram = [Int64](repeating: 0, count: 12)
    private static let processingTimeBoundsMs = [0.1, 0.25, 0.5, 1, 2, 3, 5, 7.5, 10, 15, 25]

    public init(
        configuration: RecordingAudioTimelineConfiguration = .init(),
        echoProcessor: RecordingEchoProcessor,
        frameSink: @escaping (RecordingAudioTimelineChunk) throws -> Void = { _ in }
    ) {
        self.configuration = configuration
        self.processEchoFrame = echoProcessor.process
        self.frameSink = frameSink
    }

    init(
        configuration: RecordingAudioTimelineConfiguration = .init(),
        processEchoFrame: @escaping ([Float], [Float]) throws -> [Float],
        frameSink: @escaping (RecordingAudioTimelineChunk) throws -> Void = { _ in }
    ) {
        self.configuration = configuration
        self.processEchoFrame = processEchoFrame
        self.frameSink = frameSink
    }

    /// Adds a source batch without ever deriving time from the drain order.
    public func append(source: RecordingAudioInput, batch: RecordingAudioBatch) throws {
        guard !finished else { throw RecordingAudioTimelineError.alreadyFinished }
        if source == .microphone {
            metrics.nonFiniteSampleCount += Int64(batch.samples.lazy.filter { !$0.isFinite }.count)
            metrics.clippedSampleCount += Int64(batch.samples.lazy.filter { $0.isFinite && abs($0) >= 1 }.count)
        }
        try validate(batch)
        try validateDiscontinuity(batch)
        let normalizedBatch = normalizePresentationTime(batch: batch)
        try validateClockDomain(normalizedBatch.presentationTime)
        try validateRouteGeneration(source, batch: normalizedBatch)

        guard epoch != nil else {
            try validateBootstrapContinuity(source, batch: normalizedBatch)
            try reserveBootstrapCapacity(source, batch: normalizedBatch)
            pendingBootstrapBatches.append((source, normalizedBatch))
            if hasBothSourcesInBootstrap {
                try establishEpochAndProcessBootstrapBatches()
            }
            return
        }

        try process(source: source, batch: normalizedBatch)
        try emitAvailableFrames(final: false)
    }

    /// Flushes converter tails and emits the exact remaining canonical timeline.
    public func finish() throws {
        guard !finished else { return }

        if epoch == nil, !pendingBootstrapBatches.isEmpty {
            guard hasBothSourcesInBootstrap else {
                throw RecordingAudioTimelineError.missingRequiredSource
            }
            try establishEpochAndProcessBootstrapBatches()
        }

        guard RecordingAudioInput.allCases.allSatisfy({ states[$0]?.lastInputEndFrame != nil }) else {
            throw RecordingAudioTimelineError.missingRequiredSource
        }

        for source in RecordingAudioInput.allCases {
            guard let state = states[source] else { continue }
            let flushed = try state.converter?.flush() ?? []
            guard !flushed.isEmpty else { continue }
            try appendCanonicalSamples(
                flushed,
                for: source,
                into: state,
                at: state.lastInputEndFrame ?? 0,
                allowsClockRecovery: false
            )
        }
        try emitAvailableFrames(final: true)
        finished = true
    }

    /// Keeps only frames already processed and written before an integrity
    /// failure. Pending source buffers may contain raw microphone samples and
    /// therefore must never be drained through a salvage path.
    @discardableResult
    public func finishPreservingAvailableAudio() -> Bool {
        guard !finished else { return metrics.outputFrameCount > 0 }

        pendingBootstrapBatches.removeAll(keepingCapacity: false)
        bootstrapBufferedCanonicalFrames.removeAll(keepingCapacity: false)
        states.removeAll(keepingCapacity: false)
        finished = true
        return metrics.outputFrameCount > 0
    }

    /// Converts a timestamp to the stable 48 kHz integer timeline. The integer
    /// frame index is the only persistent timing representation used downstream.
    public static func canonicalFrameIndex(
        for timestamp: RecordingAudioPresentationTimestamp,
        relativeTo epoch: RecordingAudioPresentationTimestamp
    ) throws -> Int64 {
        guard timestamp.clockDomain == epoch.clockDomain else {
            throw RecordingAudioTimelineError.uncomparablePresentationTimes
        }
        guard timestamp.seconds.isFinite, epoch.seconds.isFinite else {
            throw RecordingAudioTimelineError.invalidTimestamp
        }
        let frames = (timestamp.seconds - epoch.seconds) * canonicalSampleRate
        guard frames.isFinite,
              frames >= Double(Int64.min),
              frames <= Double(Int64.max)
        else {
            throw RecordingAudioTimelineError.invalidTimestamp
        }
        return Int64(frames.rounded())
    }

    static func recoverableClockDelta(
        requestedStart: Int64,
        expectedStart: Int64,
        limit: Int64
    ) -> Int64? {
        let (delta, overflow) = requestedStart.subtractingReportingOverflow(expectedStart)
        guard !overflow else { return nil }
        return delta >= -limit && delta <= limit ? delta : nil
    }

    private var hasBothSourcesInBootstrap: Bool {
        Set(pendingBootstrapBatches.map(\.source)).count == RecordingAudioInput.allCases.count
    }

    private func establishEpochAndProcessBootstrapBatches() throws {
        guard !pendingBootstrapBatches.isEmpty else { return }
        guard let first = pendingBootstrapBatches.first?.batch.presentationTime else { return }
        guard pendingBootstrapBatches.allSatisfy({ $0.batch.presentationTime.clockDomain == first.clockDomain }) else {
            throw RecordingAudioTimelineError.uncomparablePresentationTimes
        }
        let firstBySource = RecordingAudioInput.allCases.compactMap { source in
            pendingBootstrapBatches
                .filter { $0.source == source }
                .map(\.batch.presentationTime)
                .min(by: { $0.seconds < $1.seconds })
        }
        guard firstBySource.count == RecordingAudioInput.allCases.count,
              let commonStart = firstBySource.max(by: { $0.seconds < $1.seconds })
        else { return }

        epoch = commonStart
        let batches = pendingBootstrapBatches
        pendingBootstrapBatches.removeAll(keepingCapacity: true)
        bootstrapBufferedCanonicalFrames.removeAll(keepingCapacity: false)
        for item in batches {
            try process(source: item.source, batch: item.batch)
        }
        try emitAvailableFrames(final: false)
    }

    private func validate(_ batch: RecordingAudioBatch) throws {
        guard batch.presentationTime.seconds.isFinite else {
            throw RecordingAudioTimelineError.invalidTimestamp
        }
        if let observedHostTimeSeconds = batch.presentationTime.observedHostTimeSeconds,
           !observedHostTimeSeconds.isFinite {
            throw RecordingAudioTimelineError.invalidTimestamp
        }
        guard batch.format.sampleRate.isFinite,
              batch.format.sampleRate > 0,
              batch.format.channelCount > 0
        else {
            throw RecordingAudioTimelineError.invalidFormat
        }
        guard batch.samples.count.isMultiple(of: batch.format.channelCount),
              batch.samples.allSatisfy(\.isFinite)
        else {
            throw RecordingAudioTimelineError.invalidSamples
        }
        guard configuration.maximumKnownGapSeconds.isFinite,
              configuration.maximumKnownGapSeconds >= 0
        else {
            throw RecordingAudioTimelineError.invalidFormat
        }
    }

    /// CoreMedia's PTS is the position of the captured media. The callback host
    /// clock is sampled after delivery and therefore includes queue latency;
    /// using it as a per-batch clock mapping would move audio whenever the
    /// callback queue is delayed. Normalize the native producer label without
    /// changing its seconds, while retaining the optional observation for
    /// metadata-only diagnostics.
    private func normalizePresentationTime(
        batch: RecordingAudioBatch
    ) -> RecordingAudioBatch {
        guard batch.presentationTime.clockDomain == .sourcePresentationTime else {
            return batch
        }
        return RecordingAudioBatch(
            samples: batch.samples,
            format: batch.format,
            presentationTime: RecordingAudioPresentationTimestamp(
                seconds: batch.presentationTime.seconds,
                clockDomain: .hostTime,
                observedHostTimeSeconds: batch.presentationTime.observedHostTimeSeconds
            ),
            discontinuity: batch.discontinuity,
            routeGeneration: batch.routeGeneration
        )
    }

    private func validateDiscontinuity(_ batch: RecordingAudioBatch) throws {
        switch batch.discontinuity {
        case .none, .knownGap:
            return
        case .dropped:
            metrics.hostOverrunCount += 1
            throw RecordingAudioTimelineError.sourceOverflow
        case .routeChanged:
            throw RecordingAudioTimelineError.routeGenerationChanged
        case .sourceStopped:
            throw RecordingAudioTimelineError.sourceStopped
        }
    }

    private func validateClockDomain(_ timestamp: RecordingAudioPresentationTimestamp) throws {
        if let epoch, epoch.clockDomain != timestamp.clockDomain {
            throw RecordingAudioTimelineError.uncomparablePresentationTimes
        }
        if let bootstrapClockDomain = pendingBootstrapBatches.first?.batch.presentationTime.clockDomain,
           bootstrapClockDomain != timestamp.clockDomain {
            throw RecordingAudioTimelineError.uncomparablePresentationTimes
        }
    }

    private func validateRouteGeneration(
        _ source: RecordingAudioInput,
        batch: RecordingAudioBatch
    ) throws {
        if let routeGeneration = observedRouteGenerations[source], routeGeneration != batch.routeGeneration {
            throw RecordingAudioTimelineError.routeGenerationChanged
        }
        observedRouteGenerations[source] = batch.routeGeneration
    }

    /// Before the common epoch is known, validate each source's own timing so a
    /// large loss cannot be hidden merely because the other source has not yet
    /// produced its first callback.
    private func validateBootstrapContinuity(
        _ source: RecordingAudioInput,
        batch: RecordingAudioBatch
    ) throws {
        let sourceFrameCount = batch.samples.count / batch.format.channelCount
        let batchEndSeconds = batch.presentationTime.seconds + Double(sourceFrameCount) / batch.format.sampleRate
        if let previousEndSeconds = bootstrapSourceEndSeconds[source] {
            let gapFrames = Int64(((batch.presentationTime.seconds - previousEndSeconds) * Self.canonicalSampleRate).rounded())
            if gapFrames > maximumKnownGapFrames {
                throw RecordingAudioTimelineError.gapExceedsBound
            }
        }
        bootstrapSourceEndSeconds[source] = max(bootstrapSourceEndSeconds[source] ?? batchEndSeconds, batchEndSeconds)
    }

    private func reserveBootstrapCapacity(
        _ source: RecordingAudioInput,
        batch: RecordingAudioBatch
    ) throws {
        let inputFrameCount = batch.samples.count / batch.format.channelCount
        let canonicalFrameCount = Int64(
            (Double(inputFrameCount) * Self.canonicalSampleRate / batch.format.sampleRate).rounded(.up)
        )
        let reserved = bootstrapBufferedCanonicalFrames[source, default: 0] + canonicalFrameCount
        guard reserved <= configuration.maximumBufferedFramesPerSource else {
            metrics.hostOverrunCount += 1
            throw RecordingAudioTimelineError.sourceOverflow
        }
        bootstrapBufferedCanonicalFrames[source] = reserved
    }

    private func process(source: RecordingAudioInput, batch: RecordingAudioBatch) throws {
        guard let epoch else { return }
        let state: SourceState
        if let existing = states[source] {
            state = existing
        } else {
            state = SourceState()
            states[source] = state
        }

        state.routeGeneration = batch.routeGeneration

        var canonicalSamples = try state.convert(batch: batch)
        guard !canonicalSamples.isEmpty else { return }
        var requestedStart = try Self.canonicalFrameIndex(
            for: batch.presentationTime,
            relativeTo: epoch
        )
        if let previousStart = state.lastRequestedStartFrame,
           requestedStart <= previousStart {
            throw RecordingAudioTimelineError.lateBatch
        }
        if requestedStart < 0 {
            guard requestedStart != .min else {
                throw RecordingAudioTimelineError.invalidTimestamp
            }
            let trimCount = min(Int64(canonicalSamples.count), -requestedStart)
            canonicalSamples.removeFirst(Int(trimCount))
            requestedStart += trimCount
            if canonicalSamples.isEmpty {
                state.lastInputEndFrame = max(state.lastInputEndFrame ?? 0, 0)
                return
            }
        }
        try appendCanonicalSamples(
            canonicalSamples,
            for: source,
            into: state,
            at: requestedStart,
            allowsClockRecovery: batch.discontinuity == .none
        )
    }

    private func appendCanonicalSamples(
        _ samples: [Float],
        for source: RecordingAudioInput,
        into state: SourceState,
        at requestedStart: Int64,
        allowsClockRecovery: Bool
    ) throws {
        var start = requestedStart
        var values = samples
        let expectedStart = state.lastInputEndFrame ?? 0
        let (clockDelta, clockDeltaOverflow) = requestedStart.subtractingReportingOverflow(expectedStart)
        guard !clockDeltaOverflow, clockDelta != .min else {
            throw RecordingAudioTimelineError.invalidTimestamp
        }
        // Real capture clocks differ slightly. Correct at most one millisecond
        // at each batch boundary; larger discontinuities remain fail-closed.
        let recoverableClockDelta = allowsClockRecovery
            ? Self.recoverableClockDelta(
                requestedStart: requestedStart,
                expectedStart: expectedStart,
                limit: configuration.maximumClockRecoveryFramesPerBatch
            )
            : nil
        if clockDelta > 0 {
            let gapFrames = clockDelta
            guard gapFrames <= maximumKnownGapFrames else {
                throw RecordingAudioTimelineError.gapExceedsBound
            }
            metrics.gapFramesBySource[source, default: 0] += gapFrames
            metrics.ptsGapCount += 1
            if recoverableClockDelta != nil,
               let previousSample = state.lastSample,
               let nextSample = values.first {
                let denominator = Float(gapFrames + 1)
                let recovered = (1...Int(gapFrames)).map { index in
                    previousSample + (nextSample - previousSample) * Float(index) / denominator
                }
                values.insert(contentsOf: recovered, at: 0)
                start = expectedStart
            }
        } else if clockDelta < 0 {
            let overlapFrames = -clockDelta
            guard recoverableClockDelta != nil
            else {
                throw RecordingAudioTimelineError.lateBatch
            }
            let trimCount = min(overlapFrames, Int64(values.count))
            metrics.overlapTrimmedFramesBySource[source, default: 0] += trimCount
            start += trimCount
            if trimCount == Int64(values.count) {
                throw RecordingAudioTimelineError.lateBatch
            }
            values.removeFirst(Int(trimCount))
        }

        guard start >= emittedThroughFrame else {
            throw RecordingAudioTimelineError.lateBatch
        }
        guard Int64(state.bufferedFrameCount) + Int64(values.count) <= configuration.maximumBufferedFramesPerSource else {
            metrics.hostOverrunCount += 1
            throw RecordingAudioTimelineError.sourceOverflow
        }

        state.segments.append(TimelineSegment(startFrameIndex: start, samples: values))
        state.lastInputEndFrame = start + Int64(values.count)
        state.lastRequestedStartFrame = requestedStart
        state.lastSample = values.last
    }

    private var maximumKnownGapFrames: Int64 {
        Int64((configuration.maximumKnownGapSeconds * Self.canonicalSampleRate).rounded(.down))
    }

    private func emitAvailableFrames(final: Bool) throws {
        // A mixed frame is final only after both sources have reached it. Using
        // the fastest source as the watermark makes the slower callback look
        // late once the reorder window expires, even when its PTS is valid.
        // That false lateBatch was then surfaced as timeline_misaligned and
        // caused otherwise recoverable recordings to fail at stop.
        let sourceWatermarks = RecordingAudioInput.allCases.compactMap {
            states[$0]?.lastInputEndFrame
        }
        let highWaterFrame: Int64
        if sourceWatermarks.count == RecordingAudioInput.allCases.count {
            highWaterFrame = sourceWatermarks.min() ?? 0
        } else {
            highWaterFrame = 0
        }
        let targetFrame: Int64
        if final {
            targetFrame = highWaterFrame
        } else {
            targetFrame = max(emittedThroughFrame, highWaterFrame - configuration.reorderWindowFrames)
        }

        while emittedThroughFrame < targetFrame {
            let frameCount = Int(min(Int64(RecordingEchoProcessor.frameSamples), targetFrame - emittedThroughFrame))
            guard states[.systemAudio]?.hasCoverage(
                timelineStartFrame: emittedThroughFrame,
                frameCount: frameCount
            ) == true else {
                metrics.hostUnderrunCount += 1
                metrics.ptsGapCount += 1
                throw RecordingAudioTimelineError.renderReferenceMissing
            }
            guard states[.microphone]?.hasCoverage(
                timelineStartFrame: emittedThroughFrame,
                frameCount: frameCount
            ) == true else {
                throw RecordingAudioTimelineError.missingRequiredSource
            }
            var microphone = [Float](repeating: 0, count: frameCount)
            var systemAudio = [Float](repeating: 0, count: frameCount)
            states[.microphone]?.copySamples(
                into: &microphone,
                timelineStartFrame: emittedThroughFrame
            )
            states[.systemAudio]?.copySamples(
                into: &systemAudio,
                timelineStartFrame: emittedThroughFrame
            )
            let paddingCount = RecordingEchoProcessor.frameSamples - frameCount
            if paddingCount > 0 {
                microphone.append(contentsOf: repeatElement(0, count: paddingCount))
                systemAudio.append(contentsOf: repeatElement(0, count: paddingCount))
            }
            let cleanedMicrophone: [Float]
            let processingStartedAt = ProcessInfo.processInfo.systemUptime
            do {
                cleanedMicrophone = try processEchoFrame(systemAudio, microphone)
            } catch let error as RecordingEchoProcessorError {
                metrics.processErrorCount += 1
                throw RecordingAudioTimelineError.echoProcessingFailed(error)
            } catch {
                metrics.processErrorCount += 1
                throw RecordingAudioTimelineError.echoProcessingFailed(.internalFailure)
            }
            recordProcessingTime((ProcessInfo.processInfo.systemUptime - processingStartedAt) * 1_000)
            guard cleanedMicrophone.count == RecordingEchoProcessor.frameSamples,
                  cleanedMicrophone.allSatisfy(\.isFinite)
            else {
                metrics.processErrorCount += 1
                throw RecordingAudioTimelineError.echoProcessingOutputInvalid
            }
            let mixed = zip(cleanedMicrophone.prefix(frameCount), systemAudio.prefix(frameCount)).map { microphoneSample, systemSample in
                let value = 0.5 * (microphoneSample + systemSample)
                return value.isFinite ? value : 0
            }
            try frameSink(RecordingAudioTimelineChunk(
                startFrameIndex: emittedThroughFrame,
                samples: mixed
            ))
            emittedThroughFrame += Int64(frameCount)
            metrics.outputFrameCount = emittedThroughFrame
            metrics.echoProcessedFrameCount += 1
            states.values.forEach { $0.discardSamples(through: emittedThroughFrame) }
        }
    }

    private func recordProcessingTime(_ milliseconds: Double) {
        let bucket = Self.processingTimeBoundsMs.firstIndex { milliseconds <= $0 }
            ?? Self.processingTimeBoundsMs.count
        processingTimeHistogram[bucket] += 1
        let total = processingTimeHistogram.reduce(0, +)
        let percentileRank = max(1, Int64((Double(total) * 0.95).rounded(.up)))
        var cumulative: Int64 = 0
        for (index, count) in processingTimeHistogram.enumerated() {
            cumulative += count
            if cumulative >= percentileRank {
                metrics.processingTimeP95Ms = index < Self.processingTimeBoundsMs.count
                    ? Self.processingTimeBoundsMs[index]
                    : 25
                return
            }
        }
    }
}

private struct TimelineSegment {
    let startFrameIndex: Int64
    let samples: [Float]

    var endFrameIndex: Int64 {
        startFrameIndex + Int64(samples.count)
    }
}

private final class SourceState {
    var routeGeneration: Int?
    var inputFormat: RecordingAudioFormat?
    var lastInputEndFrame: Int64?
    var lastRequestedStartFrame: Int64?
    var lastSample: Float?
    var segments: [TimelineSegment] = []
    var firstRetainedSegmentIndex = 0
    var converter: StatefulCanonicalAudioConverter?

    var bufferedFrameCount: Int {
        guard firstRetainedSegmentIndex < segments.count else { return 0 }
        return segments[firstRetainedSegmentIndex...].reduce(into: 0) { partialResult, segment in
            partialResult += segment.samples.count
        }
    }

    func convert(batch: RecordingAudioBatch) throws -> [Float] {
        if let inputFormat, inputFormat != batch.format {
            throw RecordingAudioTimelineError.formatChanged
        }
        inputFormat = batch.format

        let monoSamples: [Float]
        if batch.format.channelCount == 1 {
            monoSamples = batch.samples
        } else {
            monoSamples = stride(from: 0, to: batch.samples.count, by: batch.format.channelCount).map { offset in
                let sum = batch.samples[offset..<(offset + batch.format.channelCount)].reduce(Float.zero, +)
                return sum / Float(batch.format.channelCount)
            }
        }

        if batch.format.sampleRate == RecordingAudioTimeline.canonicalSampleRate {
            return monoSamples
        }
        if let converter, converter.inputSampleRate != batch.format.sampleRate {
            throw RecordingAudioTimelineError.routeGenerationChanged
        }
        let resolvedConverter: StatefulCanonicalAudioConverter
        if let converter {
            resolvedConverter = converter
        } else {
            let created = try StatefulCanonicalAudioConverter(inputSampleRate: batch.format.sampleRate)
            converter = created
            resolvedConverter = created
        }
        return try resolvedConverter.convert(monoSamples)
    }

    func copySamples(into destination: inout [Float], timelineStartFrame: Int64) {
        let timelineEndFrame = timelineStartFrame + Int64(destination.count)
        var index = firstRetainedSegmentIndex
        while index < segments.count {
            let segment = segments[index]
            if segment.endFrameIndex <= timelineStartFrame {
                index += 1
                continue
            }
            if segment.startFrameIndex >= timelineEndFrame {
                break
            }
            let intersectionStart = max(segment.startFrameIndex, timelineStartFrame)
            let intersectionEnd = min(segment.endFrameIndex, timelineEndFrame)
            let sourceOffset = Int(intersectionStart - segment.startFrameIndex)
            let destinationOffset = Int(intersectionStart - timelineStartFrame)
            let frameCount = Int(intersectionEnd - intersectionStart)
            destination.replaceSubrange(
                destinationOffset..<(destinationOffset + frameCount),
                with: segment.samples[sourceOffset..<(sourceOffset + frameCount)]
            )
            index += 1
        }
    }

    func hasCoverage(timelineStartFrame: Int64, frameCount: Int) -> Bool {
        let timelineEndFrame = timelineStartFrame + Int64(frameCount)
        var coveredThrough = timelineStartFrame
        var index = firstRetainedSegmentIndex
        while index < segments.count, coveredThrough < timelineEndFrame {
            let segment = segments[index]
            if segment.endFrameIndex <= coveredThrough {
                index += 1
                continue
            }
            if segment.startFrameIndex > coveredThrough {
                return false
            }
            coveredThrough = max(coveredThrough, segment.endFrameIndex)
            index += 1
        }
        return coveredThrough >= timelineEndFrame
    }

    func discardSamples(through frameIndex: Int64) {
        while firstRetainedSegmentIndex < segments.count,
              segments[firstRetainedSegmentIndex].endFrameIndex <= frameIndex {
            firstRetainedSegmentIndex += 1
        }
        if firstRetainedSegmentIndex > 1,
           firstRetainedSegmentIndex >= segments.count / 2 {
            segments.removeFirst(firstRetainedSegmentIndex)
            firstRetainedSegmentIndex = 0
        }
    }
}

private final class StatefulCanonicalAudioConverter {
    let inputSampleRate: Double

    private let converter: AVAudioConverter
    private let inputFormat: AVAudioFormat
    private let outputFormat: AVAudioFormat
    private var submittedInputFrameCount: Int64 = 0
    private var deliveredOutputFrameCount: Int64 = 0
    private var pendingConverterOutput: [Float] = []

    init(inputSampleRate: Double) throws {
        guard inputSampleRate.isFinite, inputSampleRate > 0,
              let inputFormat = AVAudioFormat(
                  commonFormat: .pcmFormatFloat32,
                  sampleRate: inputSampleRate,
                  channels: 1,
                  interleaved: false
              ),
              let outputFormat = AVAudioFormat(
                  commonFormat: .pcmFormatFloat32,
                  sampleRate: RecordingAudioTimeline.canonicalSampleRate,
                  channels: 1,
                  interleaved: false
              ),
              let converter = AVAudioConverter(from: inputFormat, to: outputFormat)
        else {
            throw RecordingAudioTimelineError.converterFailed
        }
        self.inputSampleRate = inputSampleRate
        self.inputFormat = inputFormat
        self.outputFormat = outputFormat
        self.converter = converter
        self.converter.primeMethod = .none
    }

    func convert(_ samples: [Float]) throws -> [Float] {
        guard !samples.isEmpty else { return [] }
        guard samples.count <= Int(UInt32.max),
              let inputBuffer = AVAudioPCMBuffer(
                  pcmFormat: inputFormat,
                  frameCapacity: AVAudioFrameCount(samples.count)
              ),
              let inputData = inputBuffer.floatChannelData
        else {
            throw RecordingAudioTimelineError.converterFailed
        }
        inputBuffer.frameLength = AVAudioFrameCount(samples.count)
        inputData[0].update(from: samples, count: samples.count)

        let expectedFrames = Int(ceil(Double(samples.count) * RecordingAudioTimeline.canonicalSampleRate / inputSampleRate))
        let converted = try runConverter(
            inputBuffer: inputBuffer,
            outputCapacity: max(1_024, expectedFrames + 1_024),
            endOfStream: false
        )
        submittedInputFrameCount += Int64(samples.count)
        pendingConverterOutput.append(contentsOf: converted)
        return takeOutputWithinPresentationTime()
    }

    func flush() throws -> [Float] {
        let converted = try runConverter(
            inputBuffer: nil,
            outputCapacity: 4_096,
            endOfStream: true
        )
        pendingConverterOutput.append(contentsOf: converted)
        let finalSamples = takeOutputWithinPresentationTime()
        // AVAudioConverter may expose filter-ring tail samples after EOS. They
        // are outside the PTS duration of the source batch and must not extend
        // the meeting timeline or create cumulative drift.
        pendingConverterOutput.removeAll(keepingCapacity: false)
        return finalSamples
    }

    private func takeOutputWithinPresentationTime() -> [Float] {
        let expectedOutputFrameCount = Int64(
            (Double(submittedInputFrameCount) * RecordingAudioTimeline.canonicalSampleRate / inputSampleRate)
                .rounded()
        )
        let allowedFrameCount = max(0, expectedOutputFrameCount - deliveredOutputFrameCount)
        let count = min(Int64(pendingConverterOutput.count), allowedFrameCount)
        guard count > 0 else { return [] }
        let result = Array(pendingConverterOutput.prefix(Int(count)))
        pendingConverterOutput.removeFirst(Int(count))
        deliveredOutputFrameCount += count
        return result
    }

    private func runConverter(
        inputBuffer: AVAudioPCMBuffer?,
        outputCapacity: Int,
        endOfStream: Bool
    ) throws -> [Float] {
        guard let outputBuffer = AVAudioPCMBuffer(
            pcmFormat: outputFormat,
            frameCapacity: AVAudioFrameCount(outputCapacity)
        ) else {
            throw RecordingAudioTimelineError.converterFailed
        }
        let inputState = ConverterInputState(inputBuffer: inputBuffer)
        var conversionError: NSError?
        let status = converter.convert(to: outputBuffer, error: &conversionError) { _, statusPointer in
            inputState.next(endOfStream: endOfStream, statusPointer: statusPointer)
        }
        guard conversionError == nil, status != .error,
              let outputData = outputBuffer.floatChannelData
        else {
            throw RecordingAudioTimelineError.converterFailed
        }
        return Array(UnsafeBufferPointer(
            start: outputData[0],
            count: Int(outputBuffer.frameLength)
        ))
    }
}

private final class ConverterInputState: @unchecked Sendable {
    private let inputBuffer: AVAudioPCMBuffer?
    private var suppliedInput = false

    init(inputBuffer: AVAudioPCMBuffer?) {
        self.inputBuffer = inputBuffer
    }

    func next(
        endOfStream: Bool,
        statusPointer: UnsafeMutablePointer<AVAudioConverterInputStatus>
    ) -> AVAudioBuffer? {
        if let inputBuffer, !suppliedInput {
            suppliedInput = true
            statusPointer.pointee = .haveData
            return inputBuffer
        }
        statusPointer.pointee = endOfStream ? .endOfStream : .noDataNow
        return nil
    }
}
