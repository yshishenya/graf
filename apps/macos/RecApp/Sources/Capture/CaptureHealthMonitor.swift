import Foundation
import TwoBrainRecShared

public struct CaptureHealthMonitor: Sendable {
    public typealias Clock = @Sendable () -> Date

    private let clock: Clock

    public init(clock: @escaping Clock = Date.init) {
        self.clock = clock
    }

    public func snapshot(
        sessionId: String,
        phase: CaptureHealthPhase,
        micDurationMs: Int,
        incomingDurationMs: Int,
        micFrameCount: Int64,
        incomingFrameCount: Int64,
        droppedFrameCount: Int64 = 0,
        silentFrameCount: Int64 = 0,
        protectedFrameCount: Int64 = 0,
        coreaudiodCpuPercent: Double = 0,
        appCpuPercent: Double = 0,
        helperCpuPercent: Double = 0,
        memoryMb: Double = 0,
        halProbeObserved: Bool = false
    ) -> CaptureHealthSnapshot {
        let durationDifferenceSeconds = Double(abs(micDurationMs - incomingDurationMs)) / 1000
        let failureReason: LocalRecordingFailureReason
        let gateStatus: CaptureHealthGateStatus
        if halProbeObserved {
            failureReason = .halProbeObserved
            gateStatus = .failed
        } else if protectedFrameCount > 0 {
            failureReason = .protectedAudioBlocked
            gateStatus = .blocked
        } else if durationDifferenceSeconds > 3 {
            failureReason = .timelineMisaligned
            gateStatus = .failed
        } else if incomingFrameCount == 0 {
            failureReason = .noFrames
            gateStatus = .degraded
        } else if silentFrameCount > 0 && silentFrameCount >= incomingFrameCount {
            failureReason = .silentInput
            gateStatus = .degraded
        } else if droppedFrameCount > 0 {
            failureReason = .captureFailed
            gateStatus = .degraded
        } else {
            failureReason = .none
            gateStatus = .passed
        }

        return CaptureHealthSnapshot(
            recordingSessionId: sessionId,
            phase: phase,
            sampledAt: clock(),
            coreaudiodCpuPercent: coreaudiodCpuPercent,
            appCpuPercent: appCpuPercent,
            helperCpuPercent: helperCpuPercent,
            memoryMb: memoryMb,
            durationDifferenceSeconds: durationDifferenceSeconds,
            micFrameCount: micFrameCount,
            incomingFrameCount: incomingFrameCount,
            droppedFrameCount: droppedFrameCount,
            silentFrameCount: silentFrameCount,
            protectedFrameCount: protectedFrameCount,
            halProbeObserved: halProbeObserved,
            gateStatus: gateStatus,
            failureReason: failureReason
        )
    }
}
