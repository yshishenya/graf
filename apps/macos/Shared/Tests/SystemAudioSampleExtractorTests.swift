import Foundation
@testable import TwoBrainRecAppCore

#if canImport(XCTest) && canImport(AudioToolbox)
import AudioToolbox
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

    func testExtractsSignedInt16SamplesAsNormalizedFloats() {
        let format = audioFormat(bitsPerChannel: 16, flags: kAudioFormatFlagIsSignedInteger)
        let data = int16Data([0, Int16.max, Int16.min / 2])

        let samples = SystemAudioSampleExtractor.extractFloatSamples(
            streamDescription: format,
            bufferData: [data]
        )

        XCTAssertEqual(samples.count, 3)
        XCTAssertEqual(samples[0], 0, accuracy: 0.0001)
        XCTAssertEqual(samples[1], 1, accuracy: 0.0001)
        XCTAssertEqual(samples[2], -0.5, accuracy: 0.0001)
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

    private func floatData(_ samples: [Float]) -> Data {
        var data = Data()
        for sample in samples {
            var littleEndian = sample.bitPattern.littleEndian
            data.append(Data(bytes: &littleEndian, count: MemoryLayout<UInt32>.size))
        }
        return data
    }

    private func int16Data(_ samples: [Int16]) -> Data {
        var data = Data()
        for sample in samples {
            var littleEndian = sample.littleEndian
            data.append(Data(bytes: &littleEndian, count: MemoryLayout<Int16>.size))
        }
        return data
    }
}
#endif
