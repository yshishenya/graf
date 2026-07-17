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
        recordingFailureReason: LocalRecordingFailureReason = .none
    ) -> CaptureHealthSnapshot {
        let durationDifferenceSeconds = Double(abs(micDurationMs - incomingDurationMs)) / 1000
        let failureReason: LocalRecordingFailureReason
        let gateStatus: CaptureHealthGateStatus
        if recordingFailureReason != .none {
            failureReason = recordingFailureReason
            gateStatus = Self.gateStatus(for: recordingFailureReason)
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
            gateStatus: gateStatus,
            failureReason: failureReason
        )
    }

    private static func gateStatus(for failureReason: LocalRecordingFailureReason) -> CaptureHealthGateStatus {
        switch failureReason {
        case .none:
            .passed
        case .permissionDenied, .scopeUnavailable, .protectedAudioBlocked:
            .blocked
        case .directoryUnavailable, .captureFailed, .writeFailed, .finalizationFailed,
             .timelineMisaligned, .cpuGateFailed, .deviceUnavailable,
             .appClosed:
            .failed
        case .emptyRequiredTrack, .formatNotReady, .silentInput, .noFrames,
             .stoppedBeforeFrames, .historicalPackage, .unknown:
            .degraded
        }
    }
}
