import Foundation
import CShmHelpers

public let kShmName = "/2brain-rec-audio-bridge"
public let kSharedRingCapacity = 16384

public final class SharedAudioMemory {

    public struct AvailabilitySnapshot: Codable, Equatable, Sendable {
        public var micAvailableFrames: UInt64
        public var speakerAvailableFrames: UInt64
        public var captureAvailableFrames: UInt64
        public var checkedAt: Date
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
        public let micValidFrameCount: UnsafeMutablePointer<UInt64>
        public let speakerStimulusFrameCount: UnsafeMutablePointer<UInt64>
        public let routeInvalidationCount: UnsafeMutablePointer<UInt64>
        public let readinessGeneration: UnsafeMutablePointer<UInt64>
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
            micValidFrameCount = base.advanced(by: offset).assumingMemoryBound(to: UInt64.self); offset += MemoryLayout<UInt64>.size
            speakerStimulusFrameCount = base.advanced(by: offset).assumingMemoryBound(to: UInt64.self); offset += MemoryLayout<UInt64>.size
            routeInvalidationCount = base.advanced(by: offset).assumingMemoryBound(to: UInt64.self); offset += MemoryLayout<UInt64>.size
            readinessGeneration = base.advanced(by: offset).assumingMemoryBound(to: UInt64.self); offset += MemoryLayout<UInt64>.size
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

        shmSize = 3 * kSharedRingCapacity * MemoryLayout<Float>.stride + 12 * MemoryLayout<UInt64>.stride

        var isOwner = false
        var st = stat()
        if fstat_fixed(fd, &st) == 0, st.st_size == 0 {
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
    }

    deinit {
        munmap(mapped, shmSize)
        close(fd)
    }

    @discardableResult
    public func writeMic(src: UnsafePointer<Float>, count: Int) -> Bool {
        let l = layout
        let w = l.micWriteIdx.pointee
        let r = l.micReadIdx.pointee
        let avail = UInt64(kSharedRingCapacity) - (w &- r)
        guard count <= avail else { return false }
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
        let avail = w &- r
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
        return layout.micWriteIdx.pointee - layout.micReadIdx.pointee
    }

    public func speakerAvailable() -> UInt64 {
        OSMemoryBarrier()
        return layout.speakerWriteIdx.pointee - layout.speakerReadIdx.pointee
    }

    public func captureAvailable() -> UInt64 {
        OSMemoryBarrier()
        return layout.captureWriteIdx.pointee - layout.captureReadIdx.pointee
    }

    public func availabilitySnapshot(checkedAt: Date = Date()) -> AvailabilitySnapshot {
        AvailabilitySnapshot(
            micAvailableFrames: micAvailable(),
            speakerAvailableFrames: speakerAvailable(),
            captureAvailableFrames: captureAvailable(),
            checkedAt: checkedAt
        )
    }

    public func writeAppHeartbeat(at date: Date = Date()) {
        let nanos = UInt64(max(date.timeIntervalSince1970, 0) * 1_000_000_000)
        OSMemoryBarrier()
        layout.appHeartbeatNanos.pointee = nanos
        layout.appIOState.pointee = 1
        OSMemoryBarrier()
    }

    public func clearAppHeartbeat() {
        OSMemoryBarrier()
        layout.appIOState.pointee = 0
        layout.appHeartbeatNanos.pointee = 0
        OSMemoryBarrier()
    }

    public func routeEvidenceCounterSnapshot() -> RouteEvidenceCounterSnapshot {
        OSMemoryBarrier()
        return RouteEvidenceCounterSnapshot(
            micValidFrameCount: layout.micValidFrameCount.pointee,
            speakerStimulusFrameCount: layout.speakerStimulusFrameCount.pointee,
            routeInvalidationCount: layout.routeInvalidationCount.pointee,
            readinessGeneration: layout.readinessGeneration.pointee
        )
    }

    public struct RouteEvidenceCounterSnapshot: Codable, Equatable, Sendable {
        public var micValidFrameCount: UInt64
        public var speakerStimulusFrameCount: UInt64
        public var routeInvalidationCount: UInt64
        public var readinessGeneration: UInt64
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
