import Foundation

public struct LeakageWAVInfo: Equatable, Sendable {
    public var sampleRate: Int
    public var channelCount: Int
    public var bitsPerSample: Int
    public var frameCount: Int
    public var durationMs: Int
    public var dataOffset: Int
    public var dataByteCount: Int
}

public enum LeakageWAVReaderError: Error {
    case unsupportedFormat
    case unreadable
}

public struct LeakageWAVReader: Sendable {
    private static let expectedSampleRate = 16_000
    private static let expectedChannelCount = 1
    private static let expectedBitsPerSample = 16

    private let maxSamples: Int

    public init(maxSamples: Int = 960_000) {
        self.maxSamples = maxSamples
    }

    public func readInfo(url: URL) throws -> LeakageWAVInfo {
        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }
        let fileSize = try Self.fileSize(url: url)
        let header = try Self.readData(handle: handle, offset: 0, count: 12)
        guard fileSize >= 44,
              String(data: header[0..<4], encoding: .ascii) == "RIFF",
              String(data: header[8..<12], encoding: .ascii) == "WAVE"
        else {
            throw LeakageWAVReaderError.unreadable
        }

        var offset: UInt64 = 12
        var sampleRate: Int?
        var channelCount: Int?
        var bitsPerSample: Int?
        var dataOffset: Int?
        var dataByteCount: Int?

        while offset + 8 <= UInt64(fileSize) {
            let chunkHeader = try Self.readData(handle: handle, offset: offset, count: 8)
            let chunkId = String(data: chunkHeader[0..<4], encoding: .ascii)
            let chunkSize = UInt64(chunkHeader.uint32LE(at: 4))
            let chunkDataOffset = offset + 8
            guard chunkDataOffset + chunkSize <= UInt64(fileSize) else { break }

            if chunkId == "fmt ", chunkSize >= 16 {
                let fmt = try Self.readData(handle: handle, offset: chunkDataOffset, count: 16)
                let audioFormat = fmt.uint16LE(at: 0)
                channelCount = Int(fmt.uint16LE(at: 2))
                sampleRate = Int(fmt.uint32LE(at: 4))
                bitsPerSample = Int(fmt.uint16LE(at: 14))
                guard audioFormat == 1 else { throw LeakageWAVReaderError.unsupportedFormat }
            } else if chunkId == "data" {
                dataOffset = Int(chunkDataOffset)
                dataByteCount = Int(chunkSize)
            }

            offset = chunkDataOffset + chunkSize + (chunkSize % 2)
        }

        guard let sampleRate, let channelCount, let bitsPerSample, let dataOffset, let dataByteCount,
              sampleRate == Self.expectedSampleRate,
              channelCount == Self.expectedChannelCount,
              bitsPerSample == Self.expectedBitsPerSample,
              dataByteCount >= 0
        else {
            throw LeakageWAVReaderError.unsupportedFormat
        }

        let frameCount = dataByteCount / (channelCount * MemoryLayout<Int16>.size)
        let duration = (Double(frameCount) / Double(sampleRate)) * 1000
        guard duration.isFinite, duration >= 0, duration <= Double(Int.max) else {
            throw LeakageWAVReaderError.unsupportedFormat
        }
        return LeakageWAVInfo(
            sampleRate: sampleRate,
            channelCount: channelCount,
            bitsPerSample: bitsPerSample,
            frameCount: frameCount,
            durationMs: Int(duration),
            dataOffset: dataOffset,
            dataByteCount: dataByteCount
        )
    }

    public func readMonoSamples(url: URL) throws -> [Float] {
        let info = try readInfo(url: url)
        guard maxSamples > 0 else { throw LeakageWAVReaderError.unsupportedFormat }
        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }
        let stride = info.channelCount * MemoryLayout<Int16>.size
        let windows = sampleWindows(frameCount: info.frameCount)
        var samples: [Float] = []
        samples.reserveCapacity(windows.reduce(0) { $0 + $1.count })

        for window in windows {
            let byteOffset = UInt64(info.dataOffset + window.start * stride)
            let data = try Self.readData(handle: handle, offset: byteOffset, count: window.count * stride)
            var frame = 0
            while frame < window.count {
                let frameOffset = frame * stride
                var sum: Float = 0
                for channel in 0..<info.channelCount {
                    let sample = Int16(bitPattern: data.uint16LE(at: frameOffset + channel * 2))
                    sum += Float(sample) / Float(Int16.max)
                }
                samples.append(sum / Float(info.channelCount))
                frame += 1
            }
        }
        return samples
    }

    private func sampleWindows(frameCount: Int) -> [(start: Int, count: Int)] {
        guard frameCount > maxSamples else {
            return [(0, frameCount)]
        }
        let windowCount = 3
        let windowLength = max(1, maxSamples / windowCount)
        let starts = [
            0,
            max(0, (frameCount - windowLength) / 2),
            max(0, frameCount - windowLength)
        ]
        var lastEnd = -1
        return starts.compactMap { start in
            guard start >= lastEnd else { return nil }
            let count = min(windowLength, frameCount - start)
            guard count > 0 else { return nil }
            lastEnd = start + count
            return (start, count)
        }
    }

    private static func fileSize(url: URL) throws -> Int {
        let value = try FileManager.default.attributesOfItem(atPath: url.path)[.size] as? NSNumber
        guard let size = value?.intValue, size >= 0 else {
            throw LeakageWAVReaderError.unreadable
        }
        return size
    }

    private static func readData(handle: FileHandle, offset: UInt64, count: Int) throws -> Data {
        try handle.seek(toOffset: offset)
        guard let data = try handle.read(upToCount: count), data.count == count else {
            throw LeakageWAVReaderError.unreadable
        }
        return data
    }
}

private extension Data {
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
