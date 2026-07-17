@preconcurrency import AVFoundation
import Foundation

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
}

public struct RecordingAudioPresentationTimestamp: Equatable, Sendable {
    public let seconds: Double
    public let clockDomain: RecordingAudioClockDomain

    public init(seconds: Double, clockDomain: RecordingAudioClockDomain) {
        self.seconds = seconds
        self.clockDomain = clockDomain
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
    public internal(set) var gapFramesBySource: [RecordingAudioInput: Int64]
    public internal(set) var overlapTrimmedFramesBySource: [RecordingAudioInput: Int64]

    public init(
        outputFrameCount: Int64 = 0,
        gapFramesBySource: [RecordingAudioInput: Int64] = [:],
        overlapTrimmedFramesBySource: [RecordingAudioInput: Int64] = [:]
    ) {
        self.outputFrameCount = outputFrameCount
        self.gapFramesBySource = gapFramesBySource
        self.overlapTrimmedFramesBySource = overlapTrimmedFramesBySource
    }
}

public struct RecordingAudioTimelineConfiguration: Equatable, Sendable {
    /// A small look-behind window permits the two real-time callbacks to arrive
    /// in a different order without moving already-emitted canonical frames.
    public let reorderWindowFrames: Int64
    public let maximumKnownGapSeconds: Double
    public let maximumBufferedFramesPerSource: Int64
    public let outputChunkFrameCount: Int

    public init(
        reorderWindowFrames: Int = 9_600,
        maximumKnownGapSeconds: Double = 15,
        maximumBufferedFramesPerSource: Int = 48_000 * 20,
        outputChunkFrameCount: Int = 4_096
    ) {
        self.reorderWindowFrames = Int64(max(0, reorderWindowFrames))
        self.maximumKnownGapSeconds = maximumKnownGapSeconds
        self.maximumBufferedFramesPerSource = Int64(max(1, maximumBufferedFramesPerSource))
        self.outputChunkFrameCount = max(1, outputChunkFrameCount)
    }
}

public enum RecordingAudioTimelineError: Error, Equatable {
    case invalidTimestamp
    case invalidFormat
    case invalidSamples
    case uncomparablePresentationTimes
    case routeGenerationChanged
    case sourceOverflow
    case gapExceedsBound
    case lateBatch
    case converterFailed
    case alreadyFinished
}

/// One append-only canonical timeline shared by the transcription WAV and the
/// review M4A. A callback owns the output so a long recording never requires a
/// second in-memory copy of its audio.
public final class RecordingAudioTimeline: @unchecked Sendable {
    public static let canonicalSampleRate: Double = 48_000

    public private(set) var metrics = RecordingAudioTimelineMetrics()

    private let configuration: RecordingAudioTimelineConfiguration
    private let frameSink: (RecordingAudioTimelineChunk) throws -> Void
    private var pendingBootstrapBatches: [(source: RecordingAudioInput, batch: RecordingAudioBatch)] = []
    private var states: [RecordingAudioInput: SourceState] = [:]
    private var observedRouteGenerations: [RecordingAudioInput: Int] = [:]
    private var bootstrapSourceEndSeconds: [RecordingAudioInput: Double] = [:]
    private var bootstrapBufferedCanonicalFrames: [RecordingAudioInput: Int64] = [:]
    private var epoch: RecordingAudioPresentationTimestamp?
    private var emittedThroughFrame: Int64 = 0
    private var finished = false

    public init(
        configuration: RecordingAudioTimelineConfiguration = .init(),
        frameSink: @escaping (RecordingAudioTimelineChunk) throws -> Void = { _ in }
    ) {
        self.configuration = configuration
        self.frameSink = frameSink
    }

    /// Adds a source batch without ever deriving time from the drain order.
    public func append(source: RecordingAudioInput, batch: RecordingAudioBatch) throws {
        guard !finished else { throw RecordingAudioTimelineError.alreadyFinished }
        try validate(batch)
        try validateDiscontinuity(batch)
        try validateClockDomain(batch.presentationTime)
        try validateRouteGeneration(source, batch: batch)

        guard epoch != nil else {
            try validateBootstrapContinuity(source, batch: batch)
            try reserveBootstrapCapacity(source, batch: batch)
            pendingBootstrapBatches.append((source, batch))
            if hasBothSourcesInBootstrap {
                try establishEpochAndProcessBootstrapBatches()
            }
            return
        }

        try process(source: source, batch: batch)
        try emitAvailableFrames(final: false)
    }

    /// Flushes converter tails and emits the exact remaining canonical timeline.
    public func finish() throws {
        guard !finished else { return }
        defer { finished = true }

        if epoch == nil, !pendingBootstrapBatches.isEmpty {
            try establishEpochAndProcessBootstrapBatches()
        }

        for source in RecordingAudioInput.allCases {
            guard let state = states[source] else { continue }
            let flushed = try state.converter?.flush() ?? []
            guard !flushed.isEmpty else { continue }
            try appendCanonicalSamples(flushed, for: source, into: state, at: state.lastInputEndFrame ?? 0)
        }
        try emitAvailableFrames(final: true)
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

    private var hasBothSourcesInBootstrap: Bool {
        Set(pendingBootstrapBatches.map(\.source)).count == RecordingAudioInput.allCases.count
    }

    private func establishEpochAndProcessBootstrapBatches() throws {
        guard !pendingBootstrapBatches.isEmpty else { return }
        guard let first = pendingBootstrapBatches.first?.batch.presentationTime else { return }
        guard pendingBootstrapBatches.allSatisfy({ $0.batch.presentationTime.clockDomain == first.clockDomain }) else {
            throw RecordingAudioTimelineError.uncomparablePresentationTimes
        }
        guard let earliest = pendingBootstrapBatches
            .map(\.batch.presentationTime)
            .min(by: { $0.seconds < $1.seconds })
        else { return }

        epoch = earliest
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

    private func validateDiscontinuity(_ batch: RecordingAudioBatch) throws {
        switch batch.discontinuity {
        case .none, .knownGap:
            return
        case .dropped:
            throw RecordingAudioTimelineError.sourceOverflow
        case .routeChanged:
            throw RecordingAudioTimelineError.routeGenerationChanged
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

        let canonicalSamples = try state.convert(batch: batch)
        guard !canonicalSamples.isEmpty else { return }
        let requestedStart = try Self.canonicalFrameIndex(
            for: batch.presentationTime,
            relativeTo: epoch
        )
        guard requestedStart >= 0 else {
            throw RecordingAudioTimelineError.lateBatch
        }
        try appendCanonicalSamples(canonicalSamples, for: source, into: state, at: requestedStart)
    }

    private func appendCanonicalSamples(
        _ samples: [Float],
        for source: RecordingAudioInput,
        into state: SourceState,
        at requestedStart: Int64
    ) throws {
        var start = requestedStart
        var values = samples
        let expectedStart = state.lastInputEndFrame ?? 0
        if start > expectedStart {
            let gapFrames = start - expectedStart
            guard gapFrames <= maximumKnownGapFrames else {
                throw RecordingAudioTimelineError.gapExceedsBound
            }
            metrics.gapFramesBySource[source, default: 0] += gapFrames
        } else if start < expectedStart {
            let overlapFrames = expectedStart - start
            let trimCount = min(overlapFrames, Int64(values.count))
            metrics.overlapTrimmedFramesBySource[source, default: 0] += trimCount
            start += trimCount
            if trimCount == Int64(values.count) {
                return
            }
            values.removeFirst(Int(trimCount))
        }

        guard start >= emittedThroughFrame else {
            throw RecordingAudioTimelineError.lateBatch
        }
        guard Int64(state.bufferedFrameCount) + Int64(values.count) <= configuration.maximumBufferedFramesPerSource else {
            throw RecordingAudioTimelineError.sourceOverflow
        }

        state.segments.append(TimelineSegment(startFrameIndex: start, samples: values))
        state.lastInputEndFrame = start + Int64(values.count)
    }

    private var maximumKnownGapFrames: Int64 {
        Int64((configuration.maximumKnownGapSeconds * Self.canonicalSampleRate).rounded(.down))
    }

    private func emitAvailableFrames(final: Bool) throws {
        let highWaterFrame = states.values.compactMap(\.lastInputEndFrame).max() ?? 0
        let targetFrame: Int64
        if final {
            targetFrame = highWaterFrame
        } else {
            targetFrame = max(emittedThroughFrame, highWaterFrame - configuration.reorderWindowFrames)
        }

        while emittedThroughFrame < targetFrame {
            let frameCount = Int(min(Int64(configuration.outputChunkFrameCount), targetFrame - emittedThroughFrame))
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
            let mixed = zip(microphone, systemAudio).map { microphoneSample, systemSample in
                let value = 0.5 * (microphoneSample + systemSample)
                return value.isFinite ? value : 0
            }
            try frameSink(RecordingAudioTimelineChunk(
                startFrameIndex: emittedThroughFrame,
                samples: mixed
            ))
            emittedThroughFrame += Int64(frameCount)
            metrics.outputFrameCount = emittedThroughFrame
            states.values.forEach { $0.discardSamples(through: emittedThroughFrame) }
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
    var lastInputEndFrame: Int64?
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
