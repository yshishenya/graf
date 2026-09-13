import Foundation
@testable import TwoBrainRecAppCore

#if canImport(XCTest) && canImport(AudioToolbox)
import AudioToolbox
import CoreMedia
import XCTest

final class SystemAudioSampleExtractorTests: XCTestCase {
    func testExtractsInterleavedFloatSamplesFromContiguousBuffer() {
        let format = audioFormat(bitsPerChannel: 32, flags: kAudioFormatFlagIsFloat)
        let data = floatData([0.1, -0.1, 0.4, -0.4])

        let samples = SystemAudioSampleExtractor.extractFloatSamples(
            streamDescription: format,
            bufferData: [data]
        )

        XCTAssertEqual(samples.count, 4)
        XCTAssertEqual(samples[0], 0.1, accuracy: 0.0001)
        XCTAssertEqual(samples[1], -0.1, accuracy: 0.0001)
        XCTAssertEqual(samples[2], 0.4, accuracy: 0.0001)
        XCTAssertEqual(samples[3], -0.4, accuracy: 0.0001)
    }

    func testInterleavesNonInterleavedAudioBufferListStyleFloatBuffers() {
        let format = audioFormat(
            bitsPerChannel: 32,
            flags: kAudioFormatFlagIsFloat | kAudioFormatFlagIsNonInterleaved
        )
        let left = floatData([0.1, 0.2, 0.3])
        let right = floatData([-0.1, -0.2, -0.3])

        let samples = SystemAudioSampleExtractor.extractFloatSamples(
            streamDescription: format,
            bufferData: [left, right]
        )

        XCTAssertEqual(samples.count, 6)
        XCTAssertEqual(samples[0], 0.1, accuracy: 0.0001)
        XCTAssertEqual(samples[1], -0.1, accuracy: 0.0001)
        XCTAssertEqual(samples[2], 0.2, accuracy: 0.0001)
        XCTAssertEqual(samples[3], -0.2, accuracy: 0.0001)
        XCTAssertEqual(samples[4], 0.3, accuracy: 0.0001)
        XCTAssertEqual(samples[5], -0.3, accuracy: 0.0001)
    }

    func testDownmixesInterleavedStereoSamplesToMonoForSystemAudioWriter() {
        let mono = SystemAudioSampleExtractor.downmixInterleavedSamples(
            [0.2, 0.6, -0.8, 0.2],
            channelCount: 2
        )

        XCTAssertEqual(mono.count, 2)
        XCTAssertEqual(mono[0], 0.4, accuracy: 0.0001)
        XCTAssertEqual(mono[1], -0.3, accuracy: 0.0001)
    }

    func testDownmixLeavesMonoSamplesUnchanged() {
        let samples: [Float] = [0.1, -0.2, 0.3]

        XCTAssertEqual(
            SystemAudioSampleExtractor.downmixInterleavedSamples(samples, channelCount: 1),
            samples
        )
    }

    func testExtractsSignedInt16SamplesAsNormalizedFloats() {
        let format = audioFormat(bitsPerChannel: 16, flags: kAudioFormatFlagIsSignedInteger)
        let data = int16Data([0, Int16.max, Int16.min / 2, Int16.min])

        let samples = SystemAudioSampleExtractor.extractFloatSamples(
            streamDescription: format,
            bufferData: [data]
        )

        XCTAssertEqual(samples.count, 4)
        XCTAssertEqual(samples[0], 0, accuracy: 0.0001)
        XCTAssertEqual(samples[1], 1, accuracy: 0.0001)
        XCTAssertEqual(samples[2], -0.5, accuracy: 0.0001)
        XCTAssertEqual(samples[3], -1, accuracy: 0.0001)
    }

    func testExtractsBigEndianFloatSamples() {
        let format = audioFormat(
            bitsPerChannel: 32,
            flags: kAudioFormatFlagIsFloat | kAudioFormatFlagIsBigEndian
        )
        let data = floatData([0.25, -0.75], endian: .big)

        let samples = SystemAudioSampleExtractor.extractFloatSamples(
            streamDescription: format,
            bufferData: [data]
        )

        XCTAssertEqual(samples.count, 2)
        XCTAssertEqual(samples[0], 0.25, accuracy: 0.0001)
        XCTAssertEqual(samples[1], -0.75, accuracy: 0.0001)
    }

    func testExtractsBigEndianSignedInt16Samples() {
        let format = audioFormat(
            bitsPerChannel: 16,
            flags: kAudioFormatFlagIsSignedInteger | kAudioFormatFlagIsBigEndian
        )
        let data = int16Data([Int16.max, Int16.min / 4], endian: .big)

        let samples = SystemAudioSampleExtractor.extractFloatSamples(
            streamDescription: format,
            bufferData: [data]
        )

        XCTAssertEqual(samples.count, 2)
        XCTAssertEqual(samples[0], 1, accuracy: 0.0001)
        XCTAssertEqual(samples[1], -0.25, accuracy: 0.0001)
    }

    func testTimingDiagnosticDistinguishesOutputPTSWithoutChangingExtractedBatch() throws {
        let previous = try sampleBuffer(pts: CMTime(value: 480_000, timescale: 48_000))
        let current = try sampleBuffer(pts: CMTime(value: 481_701, timescale: 48_000))
        XCTAssertEqual(CMSampleBufferSetOutputPresentationTimeStamp(current,
            newValue: CMTime(value: 480_960, timescale: 48_000)), noErr)
        let previousTiming = SystemAudioBatchTiming(sampleBuffer: previous,
            decodedFrames: 960, rate: 48_000, arrival: 100)
        let timing = SystemAudioBatchTiming(sampleBuffer: current,
            decodedFrames: 960, rate: 48_000, arrival: 100.021)
        let fields = Dictionary(uniqueKeysWithValues: timing.relativeDiagnostic(
            previous: previousTiming, maxCompletedCallbackDuration: 0.002)
            .split(separator: " ").map { field in
                let pair = field.split(separator: "=")
                return (String(pair[0]), Double(pair[1])!)
            })
        XCTAssertEqual(fields["output_gap_ms"]!, 0, accuracy: 0.000001)
        XCTAssertEqual(fields["raw_duration_gap_ms"]!, 15.4375, accuracy: 0.000001)
        XCTAssertEqual(fields["output_minus_raw_ms"]!, -15.4375, accuracy: 0.000001)
        XCTAssertEqual(fields["previous_duration_ms"]!, 20, accuracy: 0.000001)
        XCTAssertEqual(fields["arrival_gap_ms"]!, 21, accuracy: 0.000001)
        XCTAssertEqual(fields["max_completed_callback_ms"]!, 2, accuracy: 0.000001)
        let batch = try XCTUnwrap(SystemAudioSampleExtractor.extractRecordingAudioBatch(from: current))
        XCTAssertEqual(batch.presentationTime.seconds, 481_701.0 / 48_000, accuracy: 0.000000001)
        XCTAssertEqual(batch.samples.count, 1_920)
        XCTAssertEqual(batch.samples.first, 0.25)

        for invalidDuration in [CMTime.invalid, .indefinite, .positiveInfinity] {
            let invalid = try sampleBuffer(pts: .zero, duration: invalidDuration)
            let snapshot = SystemAudioBatchTiming(sampleBuffer: invalid,
                decodedFrames: 960, rate: 48_000, arrival: 101)
            XCTAssertTrue(snapshot.duration.isNaN)
            XCTAssertTrue(snapshot.outputDuration.isNaN)
        }
    }

    private func sampleBuffer(pts: CMTime,
        duration: CMTime = CMTime(value: 1, timescale: 48_000)) throws -> CMSampleBuffer {
        var format = audioFormat(bitsPerChannel: 32,
            flags: kAudioFormatFlagIsFloat | kAudioFormatFlagIsPacked)
        var description: CMAudioFormatDescription?
        XCTAssertEqual(CMAudioFormatDescriptionCreate(allocator: kCFAllocatorDefault,
            asbd: &format, layoutSize: 0, layout: nil, magicCookieSize: 0,
            magicCookie: nil, extensions: nil, formatDescriptionOut: &description), noErr)
        let data = floatData(Array(repeating: 0.25, count: 1_920))
        var block: CMBlockBuffer?
        XCTAssertEqual(CMBlockBufferCreateWithMemoryBlock(allocator: kCFAllocatorDefault,
            memoryBlock: nil, blockLength: data.count, blockAllocator: kCFAllocatorDefault,
            customBlockSource: nil, offsetToData: 0, dataLength: data.count,
            flags: 0, blockBufferOut: &block), noErr)
        let buffer = try XCTUnwrap(block)
        XCTAssertEqual(data.withUnsafeBytes { bytes in
            CMBlockBufferReplaceDataBytes(with: bytes.baseAddress!, blockBuffer: buffer,
                offsetIntoDestination: 0, dataLength: data.count)
        }, noErr)
        var sampleTiming = CMSampleTimingInfo(duration: duration,
            presentationTimeStamp: pts, decodeTimeStamp: .invalid)
        var sampleSize = 8
        var sample: CMSampleBuffer?
        XCTAssertEqual(CMSampleBufferCreateReady(allocator: kCFAllocatorDefault,
            dataBuffer: buffer, formatDescription: description, sampleCount: 960,
            sampleTimingEntryCount: 1, sampleTimingArray: &sampleTiming,
            sampleSizeEntryCount: 1, sampleSizeArray: &sampleSize, sampleBufferOut: &sample), noErr)
        return try XCTUnwrap(sample)
    }

    private func audioFormat(
        bitsPerChannel: UInt32,
        flags: AudioFormatFlags
    ) -> AudioStreamBasicDescription {
        let bytesPerSample = bitsPerChannel / 8
        return AudioStreamBasicDescription(
            mSampleRate: 48_000,
            mFormatID: kAudioFormatLinearPCM,
            mFormatFlags: flags,
            mBytesPerPacket: bytesPerSample * 2,
            mFramesPerPacket: 1,
            mBytesPerFrame: bytesPerSample * 2,
            mChannelsPerFrame: 2,
            mBitsPerChannel: bitsPerChannel,
            mReserved: 0
        )
    }

    private enum Endian {
        case little
        case big
    }

    private func floatData(_ samples: [Float], endian: Endian = .little) -> Data {
        var data = Data()
        for sample in samples {
            var bits = switch endian {
            case .little:
                sample.bitPattern.littleEndian
            case .big:
                sample.bitPattern.bigEndian
            }
            data.append(Data(bytes: &bits, count: MemoryLayout<UInt32>.size))
        }
        return data
    }

    private func int16Data(_ samples: [Int16], endian: Endian = .little) -> Data {
        var data = Data()
        for sample in samples {
            var encoded = switch endian {
            case .little:
                sample.littleEndian
            case .big:
                sample.bigEndian
            }
            data.append(Data(bytes: &encoded, count: MemoryLayout<Int16>.size))
        }
        return data
    }
}
#endif
