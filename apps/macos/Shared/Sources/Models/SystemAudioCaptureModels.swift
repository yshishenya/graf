import Foundation

public enum SystemAudioCaptureModels {
    public static let featureIdentifier = "025-system-audio-capture-pivot"
}

public enum CapturePermissionState: String, Codable, Sendable {
    case unknown
    case granted
    case denied
    case restricted
    case stale
}

public enum SystemAudioCaptureScopeKind: String, Codable, Sendable {
    case application
    case window
    case display
}

public enum CaptureScopeApprovalMode: String, Codable, Sendable {
    case manualSelection
    case userConfirmedSuggestedScope
}

public enum CaptureScopeEligibleReason: String, Codable, Sendable {
    case approvedMeetingApp
    case approvedBrowserMeeting
    case manualMeetingScope
}

public enum AudioCaptureSourceKind: String, Codable, Sendable {
    case microphone
    case systemAudio
}

public enum CaptureHealthPhase: String, Codable, Sendable {
    case idle
    case activeRecording
    case stop
    case quit
}

public enum CaptureHealthGateStatus: String, Codable, Sendable {
    case passed
    case degraded
    case failed
    case blocked
}

public struct CaptureScopeApproval: Codable, Equatable, Sendable {
    public var scopeApprovalId: String
    public var scopeKind: SystemAudioCaptureScopeKind
    public var sourceDisplayName: String
    public var approvedBy: String
    public var approvedAt: Date
    public var approvalMode: CaptureScopeApprovalMode
    public var eligibleReason: CaptureScopeEligibleReason
    public var notTriggerForBackgroundAudio: Bool

    public init(
        scopeApprovalId: String,
        scopeKind: SystemAudioCaptureScopeKind,
        sourceDisplayName: String,
        approvedBy: String = "user",
        approvedAt: Date,
        approvalMode: CaptureScopeApprovalMode,
        eligibleReason: CaptureScopeEligibleReason,
        notTriggerForBackgroundAudio: Bool = true
    ) {
        self.scopeApprovalId = scopeApprovalId
        self.scopeKind = scopeKind
        self.sourceDisplayName = sourceDisplayName
        self.approvedBy = approvedBy
        self.approvedAt = approvedAt
        self.approvalMode = approvalMode
        self.eligibleReason = eligibleReason
        self.notTriggerForBackgroundAudio = notTriggerForBackgroundAudio
    }

    public var isAcceptedForMeetingRecording: Bool {
        approvedBy == "user" && notTriggerForBackgroundAudio
    }
}

public struct SystemAudioCaptureSession: Codable, Equatable, Sendable {
    public var sessionId: String
    public var permissionState: CapturePermissionState
    public var scopeApprovalId: String?
    public var scopeKind: SystemAudioCaptureScopeKind
    public var sourceDisplayName: String
    public var startedAt: Date?
    public var stoppedAt: Date?
    public var monotonicStartMs: Int?
    public var monotonicStopMs: Int?
    public var sampleRate: Double
    public var channelCount: Int
    public var frameCount: Int64
    public var droppedFrameCount: Int64
    public var silentFrameCount: Int64
    public var protectedFrameCount: Int64
    public var lastFrameAt: Date?
    public var failureReason: LocalRecordingFailureReason

    public init(
        sessionId: String,
        permissionState: CapturePermissionState,
        scopeApprovalId: String? = nil,
        scopeKind: SystemAudioCaptureScopeKind,
        sourceDisplayName: String,
        startedAt: Date? = nil,
        stoppedAt: Date? = nil,
        monotonicStartMs: Int? = nil,
        monotonicStopMs: Int? = nil,
        sampleRate: Double = 0,
        channelCount: Int = 0,
        frameCount: Int64 = 0,
        droppedFrameCount: Int64 = 0,
        silentFrameCount: Int64 = 0,
        protectedFrameCount: Int64 = 0,
        lastFrameAt: Date? = nil,
        failureReason: LocalRecordingFailureReason = .none
    ) {
        self.sessionId = sessionId
        self.permissionState = permissionState
        self.scopeApprovalId = scopeApprovalId
        self.scopeKind = scopeKind
        self.sourceDisplayName = sourceDisplayName
        self.startedAt = startedAt
        self.stoppedAt = stoppedAt
        self.monotonicStartMs = monotonicStartMs
        self.monotonicStopMs = monotonicStopMs
        self.sampleRate = sampleRate
        self.channelCount = channelCount
        self.frameCount = frameCount
        self.droppedFrameCount = droppedFrameCount
        self.silentFrameCount = silentFrameCount
        self.protectedFrameCount = protectedFrameCount
        self.lastFrameAt = lastFrameAt
        self.failureReason = failureReason
    }

    public var canBeAccepted: Bool {
        permissionState == .granted &&
            scopeApprovalId != nil &&
            frameCount > 0 &&
            failureReason == .none
    }
}

public struct MicrophoneCaptureSession: Codable, Equatable, Sendable {
    public var sessionId: String
    public var permissionState: CapturePermissionState
    public var inputDeviceId: String?
    public var inputDisplayName: String
    public var startedAt: Date?
    public var stoppedAt: Date?
    public var monotonicStartMs: Int?
    public var monotonicStopMs: Int?
    public var sampleRate: Double
    public var channelCount: Int
    public var frameCount: Int64
    public var droppedFrameCount: Int64
    public var silentFrameCount: Int64
    public var lastFrameAt: Date?
    public var failureReason: LocalRecordingFailureReason

    public init(
        sessionId: String,
        permissionState: CapturePermissionState,
        inputDeviceId: String? = nil,
        inputDisplayName: String,
        startedAt: Date? = nil,
        stoppedAt: Date? = nil,
        monotonicStartMs: Int? = nil,
        monotonicStopMs: Int? = nil,
        sampleRate: Double = 0,
        channelCount: Int = 0,
        frameCount: Int64 = 0,
        droppedFrameCount: Int64 = 0,
        silentFrameCount: Int64 = 0,
        lastFrameAt: Date? = nil,
        failureReason: LocalRecordingFailureReason = .none
    ) {
        self.sessionId = sessionId
        self.permissionState = permissionState
        self.inputDeviceId = inputDeviceId
        self.inputDisplayName = inputDisplayName
        self.startedAt = startedAt
        self.stoppedAt = stoppedAt
        self.monotonicStartMs = monotonicStartMs
        self.monotonicStopMs = monotonicStopMs
        self.sampleRate = sampleRate
        self.channelCount = channelCount
        self.frameCount = frameCount
        self.droppedFrameCount = droppedFrameCount
        self.silentFrameCount = silentFrameCount
        self.lastFrameAt = lastFrameAt
        self.failureReason = failureReason
    }

    public var canBeAccepted: Bool {
        permissionState == .granted && frameCount > 0 && failureReason == .none
    }
}

public struct SystemAudioPermissionSnapshot: Codable, Equatable, Sendable {
    public var microphone: CapturePermissionState
    public var systemAudio: CapturePermissionState
    public var evaluatedAt: Date

    public init(
        microphone: CapturePermissionState,
        systemAudio: CapturePermissionState,
        evaluatedAt: Date
    ) {
        self.microphone = microphone
        self.systemAudio = systemAudio
        self.evaluatedAt = evaluatedAt
    }

    public var allowsAcceptedRecording: Bool {
        microphone == .granted && systemAudio == .granted
    }
}

public struct CaptureHealthSnapshot: Codable, Equatable, Sendable {
    public var recordingSessionId: String
    public var phase: CaptureHealthPhase
    public var sampledAt: Date
    public var coreaudiodCpuPercent: Double
    public var appCpuPercent: Double
    public var helperCpuPercent: Double
    public var memoryMb: Double
    public var durationDifferenceSeconds: Double
    public var micFrameCount: Int64
    public var incomingFrameCount: Int64
    public var droppedFrameCount: Int64
    public var silentFrameCount: Int64
    public var protectedFrameCount: Int64
    public var halProbeObserved: Bool
    public var gateStatus: CaptureHealthGateStatus
    public var failureReason: LocalRecordingFailureReason

    public init(
        recordingSessionId: String,
        phase: CaptureHealthPhase,
        sampledAt: Date,
        coreaudiodCpuPercent: Double,
        appCpuPercent: Double,
        helperCpuPercent: Double = 0,
        memoryMb: Double = 0,
        durationDifferenceSeconds: Double = 0,
        micFrameCount: Int64 = 0,
        incomingFrameCount: Int64 = 0,
        droppedFrameCount: Int64 = 0,
        silentFrameCount: Int64 = 0,
        protectedFrameCount: Int64 = 0,
        halProbeObserved: Bool = false,
        gateStatus: CaptureHealthGateStatus = .passed,
        failureReason: LocalRecordingFailureReason = .none
    ) {
        self.recordingSessionId = recordingSessionId
        self.phase = phase
        self.sampledAt = sampledAt
        self.coreaudiodCpuPercent = coreaudiodCpuPercent
        self.appCpuPercent = appCpuPercent
        self.helperCpuPercent = helperCpuPercent
        self.memoryMb = memoryMb
        self.durationDifferenceSeconds = durationDifferenceSeconds
        self.micFrameCount = micFrameCount
        self.incomingFrameCount = incomingFrameCount
        self.droppedFrameCount = droppedFrameCount
        self.silentFrameCount = silentFrameCount
        self.protectedFrameCount = protectedFrameCount
        self.halProbeObserved = halProbeObserved
        self.gateStatus = gateStatus
        self.failureReason = failureReason
    }

    public var appHelperCpuPercent: Double {
        appCpuPercent + helperCpuPercent
    }

    public var passesNoHALGate: Bool {
        !halProbeObserved && gateStatus == .passed
    }
}
