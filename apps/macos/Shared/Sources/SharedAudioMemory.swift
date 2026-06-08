import Foundation
import CShmHelpers

public let kShmName = "/2brain-rec-audio-bridge"
public let kSharedRingCapacity = 16384

public enum SharedRingPolicy {
    public static func writableSampleCount(writeIndex: UInt64, readIndex: UInt64, capacity: Int = kSharedRingCapacity) -> UInt64 {
        UInt64(capacity) - (writeIndex &- readIndex)
    }

    public static func canWrite(writeIndex: UInt64, readIndex: UInt64, sampleCount: Int, capacity: Int = kSharedRingCapacity) -> Bool {
        guard sampleCount >= 0, sampleCount <= capacity else { return false }
        return UInt64(sampleCount) <= writableSampleCount(writeIndex: writeIndex, readIndex: readIndex, capacity: capacity)
    }
}

public final class SharedAudioMemory {
    public static let expectedSharedMemorySize = 3 * kSharedRingCapacity * MemoryLayout<Float>.stride + 6 * MemoryLayout<UInt64>.stride + 24

    public struct AvailabilitySnapshot: Codable, Equatable, Sendable {
        public var micAvailableFrames: UInt64
        public var speakerAvailableFrames: UInt64
        public var captureAvailableFrames: UInt64
        public var checkedAt: Date
    }

    public struct WriteIndexSnapshot: Codable, Equatable, Sendable {
        public var micReadIndex: UInt64
        public var micWriteIndex: UInt64
        public var speakerReadIndex: UInt64
        public var speakerWriteIndex: UInt64
        public var captureReadIndex: UInt64
        public var captureWriteIndex: UInt64
        public var checkedAt: Date

        public init(
            micReadIndex: UInt64,
            micWriteIndex: UInt64,
            speakerReadIndex: UInt64,
            speakerWriteIndex: UInt64,
            captureReadIndex: UInt64,
            captureWriteIndex: UInt64,
            checkedAt: Date
        ) {
            self.micReadIndex = micReadIndex
            self.micWriteIndex = micWriteIndex
            self.speakerReadIndex = speakerReadIndex
            self.speakerWriteIndex = speakerWriteIndex
            self.captureReadIndex = captureReadIndex
            self.captureWriteIndex = captureWriteIndex
            self.checkedAt = checkedAt
        }
    }

    public struct StreamCounterSnapshot: Codable, Equatable, Sendable {
        public var capturedFrameCount: UInt64
        public var storedFrameCount: UInt64
        public var retrievedOrProcessedFrameCount: UInt64
        public var droppedFrameCount: UInt64
        public var emptyBufferCount: UInt64
        public var lastValidFrameAt: Date?
        public var latencyTimestampNanos: UInt64?

        public init(
            capturedFrameCount: UInt64,
            storedFrameCount: UInt64,
            retrievedOrProcessedFrameCount: UInt64,
            droppedFrameCount: UInt64,
            emptyBufferCount: UInt64,
            lastValidFrameAt: Date?,
            latencyTimestampNanos: UInt64?
        ) {
            self.capturedFrameCount = capturedFrameCount
            self.storedFrameCount = storedFrameCount
            self.retrievedOrProcessedFrameCount = retrievedOrProcessedFrameCount
            self.droppedFrameCount = droppedFrameCount
            self.emptyBufferCount = emptyBufferCount
            self.lastValidFrameAt = lastValidFrameAt
            self.latencyTimestampNanos = latencyTimestampNanos
        }
    }

    public struct Layout {
        public let micReadIdx: UnsafeMutablePointer<UInt64>
        public let micWriteIdx: UnsafeMutablePointer<UInt64>
        public let speakerReadIdx: UnsafeMutablePointer<UInt64>
        public let speakerWriteIdx: UnsafeMutablePointer<UInt64>
        public let captureReadIdx: UnsafeMutablePointer<UInt64>
        public let captureWriteIdx: UnsafeMutablePointer<UInt64>
        public let appHeartbeatNanos: UnsafeMutablePointer<UInt64>
        public let appIOState: UnsafeMutablePointer<UInt64>
        public let appWriterPID: UnsafeMutablePointer<UInt64>
        public let micBuffer: UnsafeMutablePointer<Float>
        public let speakerBuffer: UnsafeMutablePointer<Float>
        public let captureBuffer: UnsafeMutablePointer<Float>

        public init(base: UnsafeMutableRawPointer) {
            var offset = 0
            micReadIdx = base.advanced(by: offset).assumingMemoryBound(to: UInt64.self); offset += MemoryLayout<UInt64>.size
            micWriteIdx = base.advanced(by: offset).assumingMemoryBound(to: UInt64.self); offset += MemoryLayout<UInt64>.size
            speakerReadIdx = base.advanced(by: offset).assumingMemoryBound(to: UInt64.self); offset += MemoryLayout<UInt64>.size
            speakerWriteIdx = base.advanced(by: offset).assumingMemoryBound(to: UInt64.self); offset += MemoryLayout<UInt64>.size
            captureReadIdx = base.advanced(by: offset).assumingMemoryBound(to: UInt64.self); offset += MemoryLayout<UInt64>.size
            captureWriteIdx = base.advanced(by: offset).assumingMemoryBound(to: UInt64.self); offset += MemoryLayout<UInt64>.size
            appHeartbeatNanos = base.advanced(by: offset).assumingMemoryBound(to: UInt64.self); offset += MemoryLayout<UInt64>.size
            appIOState = base.advanced(by: offset).assumingMemoryBound(to: UInt64.self); offset += MemoryLayout<UInt64>.size
            appWriterPID = base.advanced(by: offset).assumingMemoryBound(to: UInt64.self); offset += MemoryLayout<UInt64>.size
            micBuffer = base.advanced(by: offset).assumingMemoryBound(to: Float.self); offset += kSharedRingCapacity * MemoryLayout<Float>.size
            speakerBuffer = base.advanced(by: offset).assumingMemoryBound(to: Float.self); offset += kSharedRingCapacity * MemoryLayout<Float>.size
            captureBuffer = base.advanced(by: offset).assumingMemoryBound(to: Float.self)
        }
    }

    private let fd: Int32
    private let mapped: UnsafeMutableRawPointer
    public let layout: Layout
    public let isOwner: Bool

    public var isValid: Bool { true }

    private let shmSize: Int

    public init?() {
        let fd = shm_open_fixed(kShmName, O_RDWR, 0)
        guard fd >= 0 else { return nil }
        self.fd = fd

        shmSize = Self.expectedSharedMemorySize

        var isOwner = false
        var st = stat()
        if fstat_fixed(fd, &st) == 0, st.st_size != off_t(shmSize) {
            ftruncate(fd, off_t(shmSize))
            isOwner = true
        }

        guard let ptr = mmap(nil, shmSize, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0),
              ptr != MAP_FAILED else {
            close(fd)
            return nil
        }
        self.mapped = ptr
        self.isOwner = isOwner
        self.layout = Layout(base: ptr)

        if isOwner {
            mapped.initializeMemory(as: UInt8.self, repeating: 0, count: shmSize)
        }
    }

    deinit {
        munmap(mapped, shmSize)
        close(fd)
    }

    @discardableResult
    public func writeMic(src: UnsafePointer<Float>, count: Int) -> Bool {
        guard count > 0 else { return true }
        guard count <= kSharedRingCapacity else { return false }
        let l = layout
        let w = l.micWriteIdx.pointee
        let r = l.micReadIdx.pointee
        guard SharedRingPolicy.canWrite(writeIndex: w, readIndex: r, sampleCount: count) else {
            return false
        }
        for i in 0..<count {
            l.micBuffer[Int(w &+ UInt64(i)) & (kSharedRingCapacity - 1)] = src[i]
        }
        OSMemoryBarrier()
        l.micWriteIdx.pointee = w &+ UInt64(count)
        return true
    }

    @discardableResult
    public func readSpeaker(dst: UnsafeMutablePointer<Float>, count: Int) -> Int {
        let l = layout
        OSMemoryBarrier()
        let w = l.speakerWriteIdx.pointee
        let r = l.speakerReadIdx.pointee
        let avail = w &- r
        let n = min(count, Int(avail))
        for i in 0..<n {
            dst[i] = l.speakerBuffer[Int(r &+ UInt64(i)) & (kSharedRingCapacity - 1)]
        }
        OSMemoryBarrier()
        l.speakerReadIdx.pointee = r &+ UInt64(n)
        return n
    }

    @discardableResult
    public func readCapture(dst: UnsafeMutablePointer<Float>, count: Int) -> Int {
        let l = layout
        OSMemoryBarrier()
        let w = l.captureWriteIdx.pointee
        let r = l.captureReadIdx.pointee
        let avail = Self.clampedAvailable(writeIndex: w, readIndex: r)
        let n = min(count, Int(avail))
        for i in 0..<n {
            dst[i] = l.captureBuffer[Int(r &+ UInt64(i)) & (kSharedRingCapacity - 1)]
        }
        OSMemoryBarrier()
        l.captureReadIdx.pointee = r &+ UInt64(n)
        return n
    }

    public func micAvailable() -> UInt64 {
        OSMemoryBarrier()
        return Self.clampedAvailable(
            writeIndex: layout.micWriteIdx.pointee,
            readIndex: layout.micReadIdx.pointee
        )
    }

    public func speakerAvailable() -> UInt64 {
        OSMemoryBarrier()
        return Self.clampedAvailable(
            writeIndex: layout.speakerWriteIdx.pointee,
            readIndex: layout.speakerReadIdx.pointee
        )
    }

    public func captureAvailable() -> UInt64 {
        OSMemoryBarrier()
        return Self.clampedAvailable(
            writeIndex: layout.captureWriteIdx.pointee,
            readIndex: layout.captureReadIdx.pointee
        )
    }

    public func writeIndexSnapshot(checkedAt: Date = Date()) -> WriteIndexSnapshot {
        OSMemoryBarrier()
        return WriteIndexSnapshot(
            micReadIndex: layout.micReadIdx.pointee,
            micWriteIndex: layout.micWriteIdx.pointee,
            speakerReadIndex: layout.speakerReadIdx.pointee,
            speakerWriteIndex: layout.speakerWriteIdx.pointee,
            captureReadIndex: layout.captureReadIdx.pointee,
            captureWriteIndex: layout.captureWriteIdx.pointee,
            checkedAt: checkedAt
        )
    }

    public func peekLatestMic(dst: UnsafeMutablePointer<Float>, count: Int) -> Int {
        peekLatest(buffer: layout.micBuffer, writeIndex: layout.micWriteIdx.pointee, dst: dst, count: count)
    }

    public func peekLatestSpeaker(dst: UnsafeMutablePointer<Float>, count: Int) -> Int {
        peekLatest(buffer: layout.speakerBuffer, writeIndex: layout.speakerWriteIdx.pointee, dst: dst, count: count)
    }

    public func peekLatestCapture(dst: UnsafeMutablePointer<Float>, count: Int) -> Int {
        peekLatest(buffer: layout.captureBuffer, writeIndex: layout.captureWriteIdx.pointee, dst: dst, count: count)
    }

    public func availabilitySnapshot(checkedAt: Date = Date()) -> AvailabilitySnapshot {
        AvailabilitySnapshot(
            micAvailableFrames: micAvailable(),
            speakerAvailableFrames: speakerAvailable(),
            captureAvailableFrames: captureAvailable(),
            checkedAt: checkedAt
        )
    }

    private func peekLatest(
        buffer: UnsafeMutablePointer<Float>,
        writeIndex: UInt64,
        dst: UnsafeMutablePointer<Float>,
        count: Int
    ) -> Int {
        Self.copyLatestSamples(
            from: UnsafePointer(buffer),
            writeIndex: writeIndex,
            dst: dst,
            count: count
        )
    }

    public static func clampedAvailable(
        writeIndex: UInt64,
        readIndex: UInt64,
        capacity: Int = kSharedRingCapacity
    ) -> UInt64 {
        min(writeIndex &- readIndex, UInt64(max(capacity, 0)))
    }

    public static func copyLatestSamples(
        from buffer: UnsafePointer<Float>,
        writeIndex: UInt64,
        dst: UnsafeMutablePointer<Float>,
        count: Int,
        capacity: Int = kSharedRingCapacity
    ) -> Int {
        OSMemoryBarrier()
        guard count > 0, writeIndex > 0, capacity > 0 else { return 0 }
        let sampleCount = min(count, capacity, Int(min(UInt64(capacity), writeIndex)))
        let start = writeIndex &- UInt64(sampleCount)
        for index in 0..<sampleCount {
            dst[index] = buffer[Int(start &+ UInt64(index)) & (capacity - 1)]
        }
        return sampleCount
    }

    public func writeAppHeartbeat(at date: Date = Date()) {
        let nanos = UInt64(max(date.timeIntervalSince1970, 0) * 1_000_000_000)
        OSMemoryBarrier()
        layout.appWriterPID.pointee = UInt64(ProcessInfo.processInfo.processIdentifier)
        layout.appHeartbeatNanos.pointee = nanos
        layout.appIOState.pointee = 1
        OSMemoryBarrier()
    }

    public func clearAppHeartbeat() {
        OSMemoryBarrier()
        layout.appIOState.pointee = 0
        layout.appHeartbeatNanos.pointee = 0
        layout.appWriterPID.pointee = 0
        OSMemoryBarrier()
    }

    public static func streamHealthEvidence(
        track: AudioTrackRole,
        snapshot: StreamCounterSnapshot,
        checkedAt: Date,
        healthIntervalMs: Int = 3000
    ) -> StreamHealthEvidence {
        let hasValidFrames = snapshot.capturedFrameCount > 0
            || snapshot.storedFrameCount > 0
            || snapshot.retrievedOrProcessedFrameCount > 0
        return StreamHealthEvidence(
            track: track,
            checkedAt: checkedAt,
            healthIntervalMs: healthIntervalMs,
            capturabilityStatus: hasValidFrames ? .capturable : .notCapturable,
            validFrameCount: snapshot.retrievedOrProcessedFrameCount,
            emptyBufferCount: snapshot.emptyBufferCount,
            droppedFrameCount: snapshot.droppedFrameCount,
            lastValidFrameAt: snapshot.lastValidFrameAt,
            hardFailure: !hasValidFrames,
            warningWindowMs: 30000
        )
    }
}
