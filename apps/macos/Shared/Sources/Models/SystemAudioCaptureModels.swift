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

public enum SystemAudioPermissionOutcome: String, Codable, Sendable {
    case accepted
    case degradedAttempt
    case blocked
}

public enum SystemAudioPermissionRecoveryAction: String, Codable, Sendable {
    case grantMicrophone = "grant_microphone"
    case grantSystemAudio = "grant_system_audio"
    case grantBoth = "grant_both"
    case retryPermissionCheck = "retry_permission_check"
}

public struct SystemAudioPermissionPresentation: Codable, Equatable, Sendable {
    public var title: String
    public var message: String
    public var recoveryAction: SystemAudioPermissionRecoveryAction

    public init(
        title: String,
        message: String,
        recoveryAction: SystemAudioPermissionRecoveryAction
    ) {
        self.title = title
        self.message = message
        self.recoveryAction = recoveryAction
    }
}

public struct SystemAudioPermissionGateResult: Codable, Equatable, Sendable {
    public var snapshot: SystemAudioPermissionSnapshot
    public var outcome: SystemAudioPermissionOutcome
    public var presentation: SystemAudioPermissionPresentation?
    public var manifestFailureReason: LocalRecordingFailureReason

    public init(
        snapshot: SystemAudioPermissionSnapshot,
        outcome: SystemAudioPermissionOutcome,
        presentation: SystemAudioPermissionPresentation?,
        manifestFailureReason: LocalRecordingFailureReason
    ) {
        self.snapshot = snapshot
        self.outcome = outcome
        self.presentation = presentation
        self.manifestFailureReason = manifestFailureReason
    }

    public var allowsAcceptedRecording: Bool {
        outcome == .accepted && snapshot.allowsAcceptedRecording
    }

    public var allowsExplicitDegradedAttempt: Bool {
        outcome == .degradedAttempt
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

public struct SystemAudioCPUGatePolicy: Codable, Equatable, Sendable {
    public var idleCoreaudiodMaxPercent: Double
    public var idleAppHelperMaxPercent: Double
    public var activeCoreaudiodMaxPercent: Double
    public var activeAppHelperMaxPercent: Double
    public var sustainedSampleCount: Int

    public init(
        idleCoreaudiodMaxPercent: Double = 5,
        idleAppHelperMaxPercent: Double = 5,
        activeCoreaudiodMaxPercent: Double = 10,
        activeAppHelperMaxPercent: Double = 25,
        sustainedSampleCount: Int = 3
    ) {
        self.idleCoreaudiodMaxPercent = idleCoreaudiodMaxPercent
        self.idleAppHelperMaxPercent = idleAppHelperMaxPercent
        self.activeCoreaudiodMaxPercent = activeCoreaudiodMaxPercent
        self.activeAppHelperMaxPercent = activeAppHelperMaxPercent
        self.sustainedSampleCount = max(1, sustainedSampleCount)
    }
}

public struct SystemAudioCPUSample: Codable, Equatable, Sendable {
    public var recordingSessionId: String
    public var phase: CaptureHealthPhase
    public var sampledAt: Date
    public var coreaudiodCpuPercent: Double
    public var appCpuPercent: Double
    public var helperCpuPercent: Double
    public var memoryMb: Double
    public var halProbeObserved: Bool

    public init(
        recordingSessionId: String,
        phase: CaptureHealthPhase,
        sampledAt: Date,
        coreaudiodCpuPercent: Double,
        appCpuPercent: Double,
        helperCpuPercent: Double = 0,
        memoryMb: Double = 0,
        halProbeObserved: Bool = false
    ) {
        self.recordingSessionId = recordingSessionId
        self.phase = phase
        self.sampledAt = sampledAt
        self.coreaudiodCpuPercent = coreaudiodCpuPercent
        self.appCpuPercent = appCpuPercent
        self.helperCpuPercent = helperCpuPercent
        self.memoryMb = memoryMb
        self.halProbeObserved = halProbeObserved
    }

    public var appHelperCpuPercent: Double {
        appCpuPercent + helperCpuPercent
    }
}

public struct SystemAudioCPUGateEvaluation: Codable, Equatable, Sendable {
    public var phase: CaptureHealthPhase
    public var sampleCount: Int
    public var gateStatus: CaptureHealthGateStatus
    public var failureReason: LocalRecordingFailureReason
    public var maxCoreaudiodCpuPercent: Double
    public var maxAppHelperCpuPercent: Double
    public var sustainedCoreaudiodExceeded: Bool
    public var sustainedAppHelperExceeded: Bool
    public var halProbeObserved: Bool

    public init(
        phase: CaptureHealthPhase,
        sampleCount: Int,
        gateStatus: CaptureHealthGateStatus,
        failureReason: LocalRecordingFailureReason,
        maxCoreaudiodCpuPercent: Double,
        maxAppHelperCpuPercent: Double,
        sustainedCoreaudiodExceeded: Bool,
        sustainedAppHelperExceeded: Bool,
        halProbeObserved: Bool
    ) {
        self.phase = phase
        self.sampleCount = sampleCount
        self.gateStatus = gateStatus
        self.failureReason = failureReason
        self.maxCoreaudiodCpuPercent = maxCoreaudiodCpuPercent
        self.maxAppHelperCpuPercent = maxAppHelperCpuPercent
        self.sustainedCoreaudiodExceeded = sustainedCoreaudiodExceeded
        self.sustainedAppHelperExceeded = sustainedAppHelperExceeded
        self.halProbeObserved = halProbeObserved
    }

    public var passed: Bool {
        gateStatus == .passed && failureReason == .none
    }
}

public enum SystemAudioCPUGateEvaluator {
    public static func evaluate(
        samples: [SystemAudioCPUSample],
        phase: CaptureHealthPhase,
        policy: SystemAudioCPUGatePolicy = SystemAudioCPUGatePolicy()
    ) -> SystemAudioCPUGateEvaluation {
        let phaseSamples = samples.filter { $0.phase == phase }
        let maxCoreaudiod = phaseSamples.map(\.coreaudiodCpuPercent).max() ?? 0
        let maxAppHelper = phaseSamples.map(\.appHelperCpuPercent).max() ?? 0
        let halProbeObserved = phaseSamples.contains { $0.halProbeObserved }

        guard !phaseSamples.isEmpty else {
            return SystemAudioCPUGateEvaluation(
                phase: phase,
                sampleCount: 0,
                gateStatus: .failed,
                failureReason: .cpuGateFailed,
                maxCoreaudiodCpuPercent: 0,
                maxAppHelperCpuPercent: 0,
                sustainedCoreaudiodExceeded: false,
                sustainedAppHelperExceeded: false,
                halProbeObserved: false
            )
        }

        if halProbeObserved {
            return SystemAudioCPUGateEvaluation(
                phase: phase,
                sampleCount: phaseSamples.count,
                gateStatus: .failed,
                failureReason: .halProbeObserved,
                maxCoreaudiodCpuPercent: maxCoreaudiod,
                maxAppHelperCpuPercent: maxAppHelper,
                sustainedCoreaudiodExceeded: false,
                sustainedAppHelperExceeded: false,
                halProbeObserved: true
            )
        }

        let coreaudiodLimit: Double
        let appHelperLimit: Double
        let sustained: Bool
        switch phase {
        case .activeRecording:
            coreaudiodLimit = policy.activeCoreaudiodMaxPercent
            appHelperLimit = policy.activeAppHelperMaxPercent
            sustained = true
        case .idle, .stop, .quit:
            coreaudiodLimit = policy.idleCoreaudiodMaxPercent
            appHelperLimit = policy.idleAppHelperMaxPercent
            sustained = false
        }

        let coreaudiodExceeded = sustained
            ? hasSustainedExceedance(
                phaseSamples.map(\.coreaudiodCpuPercent),
                limit: coreaudiodLimit,
                sampleCount: policy.sustainedSampleCount
            )
            : phaseSamples.contains { $0.coreaudiodCpuPercent >= coreaudiodLimit }
        let appHelperExceeded = sustained
            ? hasSustainedExceedance(
                phaseSamples.map(\.appHelperCpuPercent),
                limit: appHelperLimit,
                sampleCount: policy.sustainedSampleCount
            )
            : phaseSamples.contains { $0.appHelperCpuPercent >= appHelperLimit }

        let passed = !coreaudiodExceeded && !appHelperExceeded
        return SystemAudioCPUGateEvaluation(
            phase: phase,
            sampleCount: phaseSamples.count,
            gateStatus: passed ? .passed : .failed,
            failureReason: passed ? .none : .cpuGateFailed,
            maxCoreaudiodCpuPercent: maxCoreaudiod,
            maxAppHelperCpuPercent: maxAppHelper,
            sustainedCoreaudiodExceeded: sustained && coreaudiodExceeded,
            sustainedAppHelperExceeded: sustained && appHelperExceeded,
            halProbeObserved: false
        )
    }

    private static func hasSustainedExceedance(
        _ values: [Double],
        limit: Double,
        sampleCount: Int
    ) -> Bool {
        var consecutive = 0
        for value in values {
            if value > limit {
                consecutive += 1
                if consecutive >= sampleCount {
                    return true
                }
            } else {
                consecutive = 0
            }
        }
        return false
    }
}

public struct SystemAudioNoHALEvidence: Codable, Equatable, Sendable {
    public var halRuntimeProbeExecuted: Bool
    public var virtualDeviceSelectionRequired: Bool
    public var driverRepairRequired: Bool
    public var coreAudioRestartRequired: Bool
    public var recordingUsedVirtualDevice: Bool
    public var gateStatus: CaptureHealthGateStatus
    public var failureReason: LocalRecordingFailureReason

    public init(
        halRuntimeProbeExecuted: Bool,
        virtualDeviceSelectionRequired: Bool,
        driverRepairRequired: Bool,
        coreAudioRestartRequired: Bool,
        recordingUsedVirtualDevice: Bool,
        gateStatus: CaptureHealthGateStatus = .passed,
        failureReason: LocalRecordingFailureReason = .none
    ) {
        self.halRuntimeProbeExecuted = halRuntimeProbeExecuted
        self.virtualDeviceSelectionRequired = virtualDeviceSelectionRequired
        self.driverRepairRequired = driverRepairRequired
        self.coreAudioRestartRequired = coreAudioRestartRequired
        self.recordingUsedVirtualDevice = recordingUsedVirtualDevice
        self.gateStatus = gateStatus
        self.failureReason = failureReason
    }

    public var passesMVPBoundary: Bool {
        !halRuntimeProbeExecuted &&
            !virtualDeviceSelectionRequired &&
            !driverRepairRequired &&
            !coreAudioRestartRequired &&
            !recordingUsedVirtualDevice &&
            gateStatus == .passed &&
            failureReason == .none
    }
}

public struct SystemAudioDriverParkedReadiness: Codable, Equatable, Sendable {
    public var driverState: DriverInstallationState
    public var microphoneState: VirtualDeviceAvailabilityState
    public var speakerState: VirtualDeviceAvailabilityState
    public var routeVerificationReady: Bool

    public init(
        driverState: DriverInstallationState,
        microphoneState: VirtualDeviceAvailabilityState,
        speakerState: VirtualDeviceAvailabilityState,
        routeVerificationReady: Bool
    ) {
        self.driverState = driverState
        self.microphoneState = microphoneState
        self.speakerState = speakerState
        self.routeVerificationReady = routeVerificationReady
    }

    public var mvpRecordingIgnoresDriverDiagnostics: Bool {
        true
    }

    public var summary: String {
        if routeVerificationReady {
            return "System audio recording uses macOS permissions; driver diagnostics are parked for MVP"
        }
        return "System audio recording is checked from Record; driver diagnostics are parked for MVP"
    }

    public var driverDiagnosticSummary: String {
        switch driverState {
        case .installed:
            return "Driver installed; not required for system-audio MVP recording"
        case .requiresRestart:
            return "Driver restart pending; not required for system-audio MVP recording"
        case .needsRepair, .needsUpdate, .incompatible:
            return "Driver maintenance is parked for future routing work"
        case .notInstalled, .uninstalled:
            return "Driver absent; system-audio MVP recording can still use macOS capture permissions"
        case .uninstalling:
            return "Driver removal in progress; system-audio MVP recording remains permission-gated"
        }
    }

    public var virtualDeviceDiagnosticSummary: String {
        if microphoneState == .available && speakerState == .available {
            return "Virtual devices visible for legacy passthrough diagnostics only"
        }
        return "Virtual devices are not an MVP recording prerequisite"
    }
}

public enum SystemAudioStatusLabels {
    public static let captureRegion = "System audio recording controls"
    public static let recordingIdle = "Recording idle"
    public static let recordButtonTitle = "Record System Audio"
    public static let recordButtonAccessibilityLabel = "Start system audio recording"
    public static let stopButtonTitle = "Stop"
    public static let stopButtonAccessibilityLabel = "Stop recording"
    public static let captureAudioTitle = "Recorder Input Meters"
    public static let microphoneTitle = "Microphone"
    public static let incomingTitle = "Incoming"
    public static let microphonePendingStatus = "Permission checked when recording starts"
    public static let speakerPendingStatus = "Checked when recording starts"
    public static let activeState = "Active"
    public static let silentState = "Silent"
    public static let metersWaiting = "Meters show audio only while recording"
    public static let waitingForRecordingAudio = "Waiting for recording audio"
    public static let localAudioRouteActiveNotRecording =
        "Local audio route is active; recording still starts only from Record"
    public static let recordingMeterFreshnessWindowSeconds: TimeInterval = 1.5

    public static func liveSummary(
        routeIsActive: Bool,
        microphoneIsLive: Bool,
        incomingIsLive: Bool
    ) -> String {
        guard routeIsActive else {
            return metersWaiting
        }
        if microphoneIsLive && incomingIsLive {
            return "Microphone and system audio are active"
        }
        if microphoneIsLive {
            return "Microphone active, system audio silent"
        }
        if incomingIsLive {
            return "System audio active, microphone silent"
        }
        return "No capture audio observed"
    }

    public static func microphoneDetail(routeIsActive: Bool, microphoneIsLive: Bool) -> String {
        guard routeIsActive else { return waitingForRecordingAudio }
        return microphoneIsLive
            ? "Microphone audio is reaching the recorder."
            : "No microphone audio is reaching the recorder."
    }

    public static func incomingDetail(routeIsActive: Bool, incomingIsLive: Bool) -> String {
        guard routeIsActive else { return waitingForRecordingAudio }
        return incomingIsLive
            ? "System audio is reaching the recorder."
            : "No system audio is reaching the recorder."
    }

    public static func meterState(isLive: Bool) -> String {
        isLive ? activeState : silentState
    }

    public static func meterAccessibilityLabel(title: String, detail: String) -> String {
        "\(title): \(detail)"
    }

    public static func localRecordingLocationAccessibilityLabel(_ path: String) -> String {
        "Local recording location: \(path)"
    }
}

public enum SystemAudioAccessibilityIdentifier {
    public static let captureControls = "systemAudio.capture.controls"
    public static let recordButton = "systemAudio.record.button"
    public static let stopButton = "systemAudio.stop.button"
    public static let statusSurface = "systemAudio.status.surface"
    public static let blockerBanner = "systemAudio.blocker.banner"
    public static let localRecordingStatus = "systemAudio.localRecording.status"
    public static let localRecordingLocation = "systemAudio.localRecording.location"
    public static let meters = "systemAudio.meters"
    public static let microphoneMeter = "systemAudio.meter.microphone"
    public static let incomingMeter = "systemAudio.meter.incoming"
}
