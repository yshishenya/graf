@preconcurrency import AVFoundation
import Foundation
import TwoBrainRecShared

/// Errors are intentionally coarse at this boundary: callers must expose a
/// truthful failed/degraded recording, never publish a half-finished package.
public enum CanonicalRecordingWriterError: Error, Equatable {
    case noFrames
    case invalidChunk
    case nonContiguousChunk
    case finalArtifactAlreadyExists
    case conversionFailed
    case finalizationFailed
    case alreadyFinalized
}

public struct CanonicalRecordingArtifact: Equatable, Sendable {
    public let transcriptionAudioURL: URL
    public let reviewAudioURL: URL
    public let canonicalFrameCount: Int64
    public let transcriptionFrameCount: Int64

    public init(
        transcriptionAudioURL: URL,
        reviewAudioURL: URL,
        canonicalFrameCount: Int64,
        transcriptionFrameCount: Int64
    ) {
        self.transcriptionAudioURL = transcriptionAudioURL
        self.reviewAudioURL = reviewAudioURL
        self.canonicalFrameCount = canonicalFrameCount
        self.transcriptionFrameCount = transcriptionFrameCount
    }

    public var transcriptionDurationMs: Int {
        Int((Double(transcriptionFrameCount) / CanonicalRecordingWriter.transcriptionSampleRate) * 1_000)
    }
}

/// Writes the two v5 representations from the same already-mixed 48 kHz
/// timeline. The WAV is the sole ASR input; the M4A is only a playback copy.
public final class CanonicalRecordingWriter: @unchecked Sendable {
    public static let canonicalSampleRate: Double = 48_000
    public static let transcriptionSampleRate: Double = 16_000
    public static let reviewBitRate = 96_000

    private let directory: LocalRecordingDirectory
    private let fileManager: FileManager
    private let partialTranscriptionURL: URL
    private let partialReviewURL: URL
    private let wavWriter: CanonicalPCM16WAVWriter
    private let transcriptionConverter: PTSBoundedPCMConverter
    private let reviewFormat: AVAudioFormat
    private var reviewFile: AVAudioFile?
    private var expectedNextFrameIndex: Int64 = 0
    private var canonicalFrameCount: Int64 = 0
    private var finalized = false

    public init(
        directory: LocalRecordingDirectory,
        fileManager: FileManager = .default
    ) throws {
        self.directory = directory
        self.fileManager = fileManager
        partialTranscriptionURL = directory.directoryURL.appendingPathComponent("meeting-transcription.partial.wav")
        partialReviewURL = directory.directoryURL.appendingPathComponent("meeting-review.partial.m4a")

        guard !fileManager.fileExists(atPath: directory.transcriptionAudioURL.path),
              !fileManager.fileExists(atPath: directory.reviewAudioURL.path)
        else {
            throw CanonicalRecordingWriterError.finalArtifactAlreadyExists
        }

        try? fileManager.removeItem(at: partialTranscriptionURL)
        try? fileManager.removeItem(at: partialReviewURL)
        do {
            wavWriter = try CanonicalPCM16WAVWriter(url: partialTranscriptionURL)
            transcriptionConverter = try PTSBoundedPCMConverter(
                inputSampleRate: Self.canonicalSampleRate,
                outputSampleRate: Self.transcriptionSampleRate
            )
            guard let reviewFormat = AVAudioFormat(
                commonFormat: .pcmFormatFloat32,
                sampleRate: Self.canonicalSampleRate,
                channels: 1,
                interleaved: false
            ) else {
                throw CanonicalRecordingWriterError.finalizationFailed
            }
            self.reviewFormat = reviewFormat
            reviewFile = try AVAudioFile(
                forWriting: partialReviewURL,
                settings: [
                    AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
                    AVSampleRateKey: Self.canonicalSampleRate,
                    AVNumberOfChannelsKey: 1,
                    AVEncoderBitRateKey: Self.reviewBitRate
                ],
                commonFormat: .pcmFormatFloat32,
                interleaved: false
            )
            try LocalCustodyFileProtection.apply(to: partialReviewURL)
        } catch let error as CanonicalRecordingWriterError {
            try? fileManager.removeItem(at: partialTranscriptionURL)
            try? fileManager.removeItem(at: partialReviewURL)
            throw error
        } catch {
            try? fileManager.removeItem(at: partialTranscriptionURL)
            try? fileManager.removeItem(at: partialReviewURL)
            throw CanonicalRecordingWriterError.finalizationFailed
        }
    }

    deinit {
        if !finalized {
            abort()
        }
    }

    /// Adds exactly one contiguous segment of the canonical timeline to both
    /// final representations. A gap here means an upstream timeline bug, not a
    /// request to invent silence in a persisted artifact.
    public func append(_ chunk: RecordingAudioTimelineChunk) throws {
        guard !finalized else { throw CanonicalRecordingWriterError.alreadyFinalized }
        guard chunk.startFrameIndex == expectedNextFrameIndex,
              !chunk.samples.isEmpty,
              chunk.samples.allSatisfy(\.isFinite)
        else {
            if chunk.startFrameIndex != expectedNextFrameIndex {
                throw CanonicalRecordingWriterError.nonContiguousChunk
            }
            throw CanonicalRecordingWriterError.invalidChunk
        }

        do {
            try writeReview(samples: chunk.samples)
            let transcriptionSamples = try transcriptionConverter.convert(chunk.samples)
            try wavWriter.write(transcriptionSamples)
            canonicalFrameCount += Int64(chunk.samples.count)
            expectedNextFrameIndex += Int64(chunk.samples.count)
        } catch let error as CanonicalRecordingWriterError {
            abort()
            throw error
        } catch {
            abort()
            throw CanonicalRecordingWriterError.finalizationFailed
        }
    }

    /// Flushes the native converter, validates both files, then makes the pair
    /// visible together. No finalized file is left behind after a failed step.
    public func finish() throws -> CanonicalRecordingArtifact {
        guard !finalized else { throw CanonicalRecordingWriterError.alreadyFinalized }
        guard canonicalFrameCount > 0 else {
            abort()
            throw CanonicalRecordingWriterError.noFrames
        }

        do {
            let tail = try transcriptionConverter.flush()
            try wavWriter.write(tail)
            try wavWriter.close()
            reviewFile = nil
            try validatePartialArtifacts()
            try publishFinalArtifacts()
            finalized = true
            return CanonicalRecordingArtifact(
                transcriptionAudioURL: directory.transcriptionAudioURL,
                reviewAudioURL: directory.reviewAudioURL,
                canonicalFrameCount: canonicalFrameCount,
                transcriptionFrameCount: Int64(wavWriter.frameCount)
            )
        } catch let error as CanonicalRecordingWriterError {
            abort()
            throw error
        } catch {
            abort()
            throw CanonicalRecordingWriterError.finalizationFailed
        }
    }

    /// Safe to call more than once. It deliberately removes only temporary
    /// files owned by this writer; it never removes a published package.
    public func abort() {
        guard !finalized else { return }
        reviewFile = nil
        wavWriter.abort()
        try? fileManager.removeItem(at: partialTranscriptionURL)
        try? fileManager.removeItem(at: partialReviewURL)
    }

    private func writeReview(samples: [Float]) throws {
        guard let reviewFile,
              samples.count <= Int(UInt32.max),
              let buffer = AVAudioPCMBuffer(
                  pcmFormat: reviewFormat,
                  frameCapacity: AVAudioFrameCount(samples.count)
              ),
              let data = buffer.floatChannelData
        else {
            throw CanonicalRecordingWriterError.finalizationFailed
        }
        buffer.frameLength = AVAudioFrameCount(samples.count)
        data[0].update(from: samples, count: samples.count)
        try reviewFile.write(from: buffer)
    }

    private func validatePartialArtifacts() throws {
        let wav = try Data(contentsOf: partialTranscriptionURL)
        guard wav.count >= 44,
              Array(wav.prefix(4)) == [0x52, 0x49, 0x46, 0x46],
              Array(wav[8..<12]) == [0x57, 0x41, 0x56, 0x45],
              wav.uint16LE(at: 20) == 1,
              wav.uint16LE(at: 22) == 1,
              wav.uint32LE(at: 24) == UInt32(Self.transcriptionSampleRate),
              wav.uint16LE(at: 34) == 16,
              wav.uint32LE(at: 40) == UInt32(wav.count - 44)
        else {
            throw CanonicalRecordingWriterError.finalizationFailed
        }
        let expectedTranscriptionFrames = Int64(
            (Double(canonicalFrameCount) * Self.transcriptionSampleRate / Self.canonicalSampleRate).rounded()
        )
        guard Int64(wav.uint32LE(at: 40) / 2) == expectedTranscriptionFrames else {
            throw CanonicalRecordingWriterError.finalizationFailed
        }
        let review = try AVAudioFile(forReading: partialReviewURL)
        guard abs(review.fileFormat.sampleRate - Self.canonicalSampleRate) < 1,
              review.fileFormat.channelCount == 1,
              (review.fileFormat.settings[AVFormatIDKey] as? NSNumber)?.intValue == Int(kAudioFormatMPEG4AAC),
              abs(review.length - canonicalFrameCount) <= LocalRecordingTrack.maximumAACPresentationDeltaFrames
        else {
            throw CanonicalRecordingWriterError.finalizationFailed
        }
    }

    private func publishFinalArtifacts() throws {
        var published: [URL] = []
        do {
            try fileManager.moveItem(at: partialTranscriptionURL, to: directory.transcriptionAudioURL)
            published.append(directory.transcriptionAudioURL)
            try fileManager.moveItem(at: partialReviewURL, to: directory.reviewAudioURL)
            published.append(directory.reviewAudioURL)
            try LocalCustodyFileProtection.apply(to: directory.transcriptionAudioURL)
            try LocalCustodyFileProtection.apply(to: directory.reviewAudioURL)
        } catch {
            for url in published {
                try? fileManager.removeItem(at: url)
            }
            throw CanonicalRecordingWriterError.finalizationFailed
        }
    }
}

private final class PTSBoundedPCMConverter {
    private let inputSampleRate: Double
    private let outputSampleRate: Double
    private let inputFormat: AVAudioFormat
    private let outputFormat: AVAudioFormat
    private let converter: AVAudioConverter
    private var submittedInputFrameCount: Int64 = 0
    private var deliveredOutputFrameCount: Int64 = 0
    private var pendingConverterOutput: [Float] = []

    init(inputSampleRate: Double, outputSampleRate: Double) throws {
        guard let inputFormat = AVAudioFormat(
            commonFormat: .pcmFormatFloat32,
            sampleRate: inputSampleRate,
            channels: 1,
            interleaved: false
        ), let outputFormat = AVAudioFormat(
            commonFormat: .pcmFormatFloat32,
            sampleRate: outputSampleRate,
            channels: 1,
            interleaved: false
        ), let converter = AVAudioConverter(from: inputFormat, to: outputFormat)
        else {
            throw CanonicalRecordingWriterError.conversionFailed
        }
        self.inputSampleRate = inputSampleRate
        self.outputSampleRate = outputSampleRate
        self.inputFormat = inputFormat
        self.outputFormat = outputFormat
        self.converter = converter
        self.converter.primeMethod = .none
    }

    func convert(_ samples: [Float]) throws -> [Float] {
        guard !samples.isEmpty else { return [] }
        let expectedFrames = Int(ceil(Double(samples.count) * outputSampleRate / inputSampleRate))
        let converted = try runConverter(
            samples: samples,
            outputCapacity: max(1_024, expectedFrames + 1_024),
            endOfStream: false
        )
        submittedInputFrameCount += Int64(samples.count)
        pendingConverterOutput.append(contentsOf: converted)
        return takeOutputWithinPresentationTime()
    }

    func flush() throws -> [Float] {
        let converted = try runConverter(
            samples: nil,
            outputCapacity: 4_096,
            endOfStream: true
        )
        pendingConverterOutput.append(contentsOf: converted)
        let finalSamples = takeOutputWithinPresentationTime()
        pendingConverterOutput.removeAll(keepingCapacity: false)
        return finalSamples
    }

    private func takeOutputWithinPresentationTime() -> [Float] {
        let expectedOutputFrameCount = Int64(
            (Double(submittedInputFrameCount) * outputSampleRate / inputSampleRate).rounded()
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
        samples: [Float]?,
        outputCapacity: Int,
        endOfStream: Bool
    ) throws -> [Float] {
        let inputBuffer: AVAudioPCMBuffer?
        if let samples {
            guard samples.count <= Int(UInt32.max),
                  let buffer = AVAudioPCMBuffer(
                      pcmFormat: inputFormat,
                      frameCapacity: AVAudioFrameCount(samples.count)
                  ), let data = buffer.floatChannelData
            else {
                throw CanonicalRecordingWriterError.conversionFailed
            }
            buffer.frameLength = AVAudioFrameCount(samples.count)
            data[0].update(from: samples, count: samples.count)
            inputBuffer = buffer
        } else {
            inputBuffer = nil
        }
        guard let outputBuffer = AVAudioPCMBuffer(
            pcmFormat: outputFormat,
            frameCapacity: AVAudioFrameCount(outputCapacity)
        ) else {
            throw CanonicalRecordingWriterError.conversionFailed
        }
        let inputState = CanonicalConverterInputState(inputBuffer: inputBuffer)
        var conversionError: NSError?
        let status = converter.convert(to: outputBuffer, error: &conversionError) { _, statusPointer in
            inputState.next(endOfStream: endOfStream, statusPointer: statusPointer)
        }
        guard conversionError == nil, status != .error,
              let outputData = outputBuffer.floatChannelData
        else {
            throw CanonicalRecordingWriterError.conversionFailed
        }
        return Array(UnsafeBufferPointer(
            start: outputData[0],
            count: Int(outputBuffer.frameLength)
        ))
    }
}

private final class CanonicalConverterInputState: @unchecked Sendable {
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

private final class CanonicalPCM16WAVWriter {
    private let url: URL
    private let handle: FileHandle
    private var closed = false
    private(set) var frameCount = 0

    init(url: URL) throws {
        self.url = url
        try LocalCustodyFileProtection.createEmptyFile(at: url)
        handle = try FileHandle(forWritingTo: url)
        try handle.write(contentsOf: Data(repeating: 0, count: 44))
    }

    func write(_ samples: [Float]) throws {
        guard !closed, !samples.isEmpty else { return }
        var data = Data()
        data.reserveCapacity(samples.count * MemoryLayout<Int16>.size)
        for sample in samples {
            var value = Int16(max(-1, min(1, sample)) * Float(Int16.max)).littleEndian
            withUnsafeBytes(of: &value) { data.append(contentsOf: $0) }
        }
        try handle.write(contentsOf: data)
        frameCount += samples.count
    }

    func close() throws {
        guard !closed else { return }
        let dataByteCount = UInt32(frameCount * MemoryLayout<Int16>.size)
        var header = Data()
        header.append(contentsOf: [0x52, 0x49, 0x46, 0x46])
        header.appendLittleEndian(UInt32(36) + dataByteCount)
        header.append(contentsOf: [0x57, 0x41, 0x56, 0x45])
        header.append(contentsOf: [0x66, 0x6d, 0x74, 0x20])
        header.appendLittleEndian(UInt32(16))
        header.appendLittleEndian(UInt16(1))
        header.appendLittleEndian(UInt16(1))
        header.appendLittleEndian(UInt32(CanonicalRecordingWriter.transcriptionSampleRate))
        header.appendLittleEndian(UInt32(CanonicalRecordingWriter.transcriptionSampleRate * 2))
        header.appendLittleEndian(UInt16(2))
        header.appendLittleEndian(UInt16(16))
        header.append(contentsOf: [0x64, 0x61, 0x74, 0x61])
        header.appendLittleEndian(dataByteCount)
        try handle.seek(toOffset: 0)
        try handle.write(contentsOf: header)
        try handle.close()
        closed = true
    }

    func abort() {
        guard !closed else { return }
        try? handle.close()
        closed = true
        try? FileManager.default.removeItem(at: url)
    }
}

private extension Data {
    mutating func appendLittleEndian<T: FixedWidthInteger>(_ value: T) {
        var littleEndianValue = value.littleEndian
        Swift.withUnsafeBytes(of: &littleEndianValue) { append(contentsOf: $0) }
    }

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
