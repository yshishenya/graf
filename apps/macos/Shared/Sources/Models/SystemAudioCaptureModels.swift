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

public enum RecordingMicrophoneSelectionMode: String, Codable, Sendable {
    case userSelected = "user_selected"
    case macOSDefaultFallback = "macos_default_fallback"
}

public enum RecordingMicrophoneSelectionResult: String, Codable, Sendable {
    case accepted
    case rejected
    case unavailable
}

public enum RecordingMicrophoneSelectionRejectionReason: String, Codable, Sendable {
    case unsupportedSelfRoutingInput = "unsupported_self_routing_input"
    case unsupportedVirtualInput = "unsupported_virtual_input"
    case deviceUnavailable = "device_unavailable"
    case inputIdentityUnproven = "input_identity_unproven"
}

public struct RecordingMicrophoneSelection: Codable, Equatable, Sendable {
    public var selectionId: String
    public var mode: RecordingMicrophoneSelectionMode
    public var inputDeviceId: String?
    public var inputDisplayName: String?
    public var deviceClass: PhysicalDeviceClass?
    public var workingDeviceKind: PhysicalWorkingDeviceKind?
    public var selectionResult: RecordingMicrophoneSelectionResult
    public var rejectionReason: RecordingMicrophoneSelectionRejectionReason?
    public var resolvedAt: Date
    public var diagnosticSafe: Bool

    public init(
        selectionId: String,
        mode: RecordingMicrophoneSelectionMode,
        inputDeviceId: String? = nil,
        inputDisplayName: String? = nil,
        deviceClass: PhysicalDeviceClass? = nil,
        workingDeviceKind: PhysicalWorkingDeviceKind? = nil,
        selectionResult: RecordingMicrophoneSelectionResult,
        rejectionReason: RecordingMicrophoneSelectionRejectionReason? = nil,
        resolvedAt: Date,
        diagnosticSafe: Bool = true
    ) {
        self.selectionId = selectionId
        self.mode = mode
        self.inputDeviceId = inputDeviceId
        self.inputDisplayName = inputDisplayName
        self.deviceClass = deviceClass
        self.workingDeviceKind = workingDeviceKind
        self.selectionResult = selectionResult
        self.rejectionReason = rejectionReason
        self.resolvedAt = resolvedAt
        self.diagnosticSafe = diagnosticSafe
    }

    public var isAccepted: Bool {
        selectionResult == .accepted && diagnosticSafe
    }
}

public enum MicrophoneStreamKind: String, Codable, Sendable {
    case appOwnedSampleSource = "app_owned_sample_source"
    case legacyRecorderFallback = "legacy_recorder_fallback"
}

public enum MicrophoneTimingConfidence: String, Codable, Sendable {
    case usable
    case degraded
    case missing
    case unknown
}

public enum MicrophoneSilenceStatus: String, Codable, Sendable {
    case audible
    case silent
    case clipped
    case notMeasured = "not_measured"
    case unknown
}

public enum FutureProcessingReadiness: String, Codable, Sendable {
    case readyForFutureProcessing = "ready_for_future_processing"
    case unproven
    case legacyNotReady = "legacy_not_ready"
    case blocked
}

public struct AppOwnedMicrophoneStreamSession: Codable, Equatable, Sendable {
    public var sessionId: String
    public var selection: RecordingMicrophoneSelection
    public var permissionState: CapturePermissionState
    public var streamKind: MicrophoneStreamKind
    public var startedAt: Date?
    public var stoppedAt: Date?
    public var monotonicStartMs: Int?
    public var monotonicStopMs: Int?
    public var sampleRate: Double
    public var channelCount: Int
    public var writerSampleRate: Double
    public var writerChannelCount: Int
    public var frameCount: Int64
    public var droppedFrameCount: Int64
    public var silentFrameCount: Int64
    public var clippedFrameCount: Int64
    public var routeChangeCount: Int
    public var lastFrameAt: Date?
    public var failureReason: LocalRecordingFailureReason
    public var diagnosticSafe: Bool

    public init(
        sessionId: String,
        selection: RecordingMicrophoneSelection,
        permissionState: CapturePermissionState,
        streamKind: MicrophoneStreamKind,
        startedAt: Date? = nil,
        stoppedAt: Date? = nil,
        monotonicStartMs: Int? = nil,
        monotonicStopMs: Int? = nil,
        sampleRate: Double = 0,
        channelCount: Int = 0,
        writerSampleRate: Double = 0,
        writerChannelCount: Int = 0,
        frameCount: Int64 = 0,
        droppedFrameCount: Int64 = 0,
        silentFrameCount: Int64 = 0,
        clippedFrameCount: Int64 = 0,
        routeChangeCount: Int = 0,
        lastFrameAt: Date? = nil,
        failureReason: LocalRecordingFailureReason = .none,
        diagnosticSafe: Bool = true
    ) {
        self.sessionId = sessionId
        self.selection = selection
        self.permissionState = permissionState
        self.streamKind = streamKind
        self.startedAt = startedAt
        self.stoppedAt = stoppedAt
        self.monotonicStartMs = monotonicStartMs
        self.monotonicStopMs = monotonicStopMs
        self.sampleRate = sampleRate
        self.channelCount = channelCount
        self.writerSampleRate = writerSampleRate
        self.writerChannelCount = writerChannelCount
        self.frameCount = frameCount
        self.droppedFrameCount = droppedFrameCount
        self.silentFrameCount = silentFrameCount
        self.clippedFrameCount = clippedFrameCount
        self.routeChangeCount = routeChangeCount
        self.lastFrameAt = lastFrameAt
        self.failureReason = failureReason
        self.diagnosticSafe = diagnosticSafe
    }

    public var provesGraphReadiness: Bool {
        streamKind == .appOwnedSampleSource &&
            permissionState == .granted &&
            selection.isAccepted &&
            frameCount > 0 &&
            writerSampleRate == 16_000 &&
            writerChannelCount == 1 &&
            failureReason == .none &&
            diagnosticSafe
    }
}

public struct MicrophoneStreamHealth: Codable, Equatable, Sendable {
    public var gateStatus: CaptureHealthGateStatus
    public var failureReason: LocalRecordingFailureReason
    public var framesObserved: Bool
    public var timingConfidence: MicrophoneTimingConfidence
    public var silenceStatus: MicrophoneSilenceStatus
    public var lastLevel: Double?
    public var lastLevelAt: Date?
    public var cleanupReadiness: FutureProcessingReadiness
    public var evidenceCodes: [String]
    public var diagnosticSafe: Bool

    public init(
        gateStatus: CaptureHealthGateStatus,
        failureReason: LocalRecordingFailureReason,
        framesObserved: Bool,
        timingConfidence: MicrophoneTimingConfidence,
        silenceStatus: MicrophoneSilenceStatus,
        lastLevel: Double? = nil,
        lastLevelAt: Date? = nil,
        cleanupReadiness: FutureProcessingReadiness,
        evidenceCodes: [String] = [],
        diagnosticSafe: Bool = true
    ) {
        self.gateStatus = gateStatus
        self.failureReason = failureReason
        self.framesObserved = framesObserved
        self.timingConfidence = timingConfidence
        self.silenceStatus = silenceStatus
        self.lastLevel = lastLevel
        self.lastLevelAt = lastLevelAt
        self.cleanupReadiness = cleanupReadiness
        self.evidenceCodes = evidenceCodes
        self.diagnosticSafe = diagnosticSafe
    }
}

public enum AppleProcessingCandidateKind: String, Codable, Sendable {
    case appOwnedGraphVoiceProcessing = "app_owned_graph_voice_processing"
    case voiceProcessingIO = "voice_processing_io"
    case micModeGuidance = "mic_mode_guidance"
}

public enum AppleProcessingRouteClass: String, Codable, Sendable {
    case builtInSpeakerphone = "built_in_speakerphone"
    case wiredHeadphones = "wired_headphones"
    case usbHeadset = "usb_headset"
    case bluetoothAirPodsClass = "bluetooth_airpods_class"
    case unknown
}

public enum AppleProcessingScenario: String, Codable, Sendable, CaseIterable {
    case farEndOnly = "far_end_only"
    case nearEndOnly = "near_end_only"
    case doubleTalk = "double_talk"
    case loudSpeaker = "loud_speaker"
    case routeChange = "route_change"
    case browserMeeting = "browser_meeting"
    case stopQuit = "stop_quit"
    case diagnostics

    public static let builtinSpeakerphoneAcceptanceScenarios: [AppleProcessingScenario] = [
        .farEndOnly,
        .nearEndOnly,
        .doubleTalk,
        .loudSpeaker,
        .routeChange,
        .browserMeeting,
        .stopQuit,
        .diagnostics
    ]
}

public enum AppleProcessingEvidenceStatus: String, Codable, Sendable {
    case accepted
    case degraded
    case blocked
    case unproven
    case notMeasured = "not_measured"
}

public enum AppleProcessingLineageStatus: String, Codable, Sendable {
    case originalOnly = "original_only"
    case candidateMetadata = "candidate_metadata"
    case derivedCandidate = "derived_candidate"
    case liveAndPersisted = "live_and_persisted"
    case guidanceOnly = "guidance_only"
    case unproven
    case blocked
}

public enum AppleSpeechPreservationStatus: String, Codable, Sendable {
    case preserved
    case degraded
    case suppressed
    case notMeasured = "not_measured"
    case unknown
}

public enum AppleProcessingAlignmentStatus: String, Codable, Sendable {
    case accepted
    case degraded
    case failed
    case notMeasured = "not_measured"
}

public enum AppleProcessingStabilityStatus: String, Codable, Sendable {
    case accepted
    case blockedRouteTopology = "blocked_route_topology"
    case blockedQuality = "blocked_quality"
    case blockedStability = "blocked_stability"
    case unproven
    case notMeasured = "not_measured"
}

public enum AppleProcessingOutcomeState: String, Codable, Sendable {
    case acceptedForBuiltinSpeakerphone = "accepted_for_builtin_speakerphone"
    case acceptedForGuidanceOnly = "accepted_for_guidance_only"
    case acceptedForHeadsetRoutesOnly = "accepted_for_headset_routes_only"
    case blockedRouteTopology = "blocked_route_topology"
    case blockedQuality = "blocked_quality"
    case blockedStability = "blocked_stability"
    case deferToWebRTCAEC3 = "defer_to_webrtc_aec3"
}

public enum AppleProcessingNextStepRecommendation: String, Codable, Sendable {
    case promoteAppleProcessing = "promote_apple_processing"
    case guidanceOnly = "guidance_only"
    case headsetRoutesOnly = "headset_routes_only"
    case deferToWebRTCAEC3 = "defer_to_webrtc_aec3"
    case fallbackDecision = "fallback_decision"
}

public struct AppleProcessingCandidate: Codable, Equatable, Sendable {
    public var feature: String
    public var candidateId: String
    public var candidateKind: AppleProcessingCandidateKind
    public var routeClass: AppleProcessingRouteClass
    public var featureGateEnabled: Bool
    public var apiAvailable: Bool
    public var processingEnabled: Bool
    public var observedAt: Date
    public var failureReason: String?
    public var diagnosticSafe: Bool

    public init(
        feature: String = "038-apple-voice-processing-spike",
        candidateId: String,
        candidateKind: AppleProcessingCandidateKind,
        routeClass: AppleProcessingRouteClass,
        featureGateEnabled: Bool,
        apiAvailable: Bool,
        processingEnabled: Bool,
        observedAt: Date,
        failureReason: String? = nil,
        diagnosticSafe: Bool = true
    ) {
        self.feature = feature
        self.candidateId = candidateId
        self.candidateKind = candidateKind
        self.routeClass = routeClass
        self.featureGateEnabled = featureGateEnabled
        self.apiAvailable = apiAvailable
        self.processingEnabled = processingEnabled
        self.observedAt = observedAt
        self.failureReason = failureReason
        self.diagnosticSafe = diagnosticSafe
    }

    public var isUsableCandidate: Bool {
        featureGateEnabled && apiAvailable && processingEnabled && diagnosticSafe
    }
}

public struct AppleProcessingValidationRow: Codable, Equatable, Sendable {
    public var feature: String
    public var candidateId: String
    public var candidateKind: AppleProcessingCandidateKind
    public var routeClass: AppleProcessingRouteClass
    public var scenario: AppleProcessingScenario
    public var baselineStatus: AppleProcessingEvidenceStatus
    public var candidateStatus: AppleProcessingEvidenceStatus
    public var lineageStatus: AppleProcessingLineageStatus
    public var speechPreservationStatus: AppleSpeechPreservationStatus
    public var alignmentStatus: AppleProcessingAlignmentStatus
    public var stabilityStatus: AppleProcessingStabilityStatus
    public var diagnosticSafe: Bool
    public var failureReason: String?

    public init(
        feature: String = "038-apple-voice-processing-spike",
        candidateId: String,
        candidateKind: AppleProcessingCandidateKind,
        routeClass: AppleProcessingRouteClass,
        scenario: AppleProcessingScenario,
        baselineStatus: AppleProcessingEvidenceStatus,
        candidateStatus: AppleProcessingEvidenceStatus,
        lineageStatus: AppleProcessingLineageStatus,
        speechPreservationStatus: AppleSpeechPreservationStatus,
        alignmentStatus: AppleProcessingAlignmentStatus,
        stabilityStatus: AppleProcessingStabilityStatus,
        diagnosticSafe: Bool,
        failureReason: String? = nil
    ) {
        self.feature = feature
        self.candidateId = candidateId
        self.candidateKind = candidateKind
        self.routeClass = routeClass
        self.scenario = scenario
        self.baselineStatus = baselineStatus
        self.candidateStatus = candidateStatus
        self.lineageStatus = lineageStatus
        self.speechPreservationStatus = speechPreservationStatus
        self.alignmentStatus = alignmentStatus
        self.stabilityStatus = stabilityStatus
        self.diagnosticSafe = diagnosticSafe
        self.failureReason = failureReason
    }

    public var normalizedStabilityStatus: AppleProcessingStabilityStatus {
        if speechPreservationStatus == .suppressed {
            return .blockedQuality
        }
        if lineageStatus == .blocked {
            return .blockedRouteTopology
        }
        return stabilityStatus
    }

    public var isAcceptedForBuiltinSpeakerphone: Bool {
        routeClass == .builtInSpeakerphone &&
            candidateStatus == .accepted &&
            lineageStatus == .liveAndPersisted &&
            speechPreservationStatus == .preserved &&
            alignmentStatus == .accepted &&
            normalizedStabilityStatus == .accepted &&
            diagnosticSafe
    }
}

public struct ProcessedMicrophoneEvidence: Codable, Equatable, Sendable {
    public var feature: String
    public var candidateId: String
    public var lineageStatus: AppleProcessingLineageStatus
    public var originalMicrophoneTrackPreserved: Bool
    public var incomingReferencePreserved: Bool
    public var manifestLabelsCandidate: Bool
    public var leakageFinalizationAuthorityPreserved: Bool
    public var diagnosticSafe: Bool

    public init(
        feature: String = "038-apple-voice-processing-spike",
        candidateId: String,
        lineageStatus: AppleProcessingLineageStatus,
        originalMicrophoneTrackPreserved: Bool,
        incomingReferencePreserved: Bool,
        manifestLabelsCandidate: Bool,
        leakageFinalizationAuthorityPreserved: Bool,
        diagnosticSafe: Bool = true
    ) {
        self.feature = feature
        self.candidateId = candidateId
        self.lineageStatus = lineageStatus
        self.originalMicrophoneTrackPreserved = originalMicrophoneTrackPreserved
        self.incomingReferencePreserved = incomingReferencePreserved
        self.manifestLabelsCandidate = manifestLabelsCandidate
        self.leakageFinalizationAuthorityPreserved = leakageFinalizationAuthorityPreserved
        self.diagnosticSafe = diagnosticSafe
    }

    public var preservesPackageTruth: Bool {
        originalMicrophoneTrackPreserved &&
            incomingReferencePreserved &&
            manifestLabelsCandidate &&
            leakageFinalizationAuthorityPreserved &&
            diagnosticSafe
    }

    public var canRedefineOriginalMicTrack: Bool {
        false
    }
}

public struct AppleProcessingOutcome: Codable, Equatable, Sendable {
    public var feature: String
    public var candidateId: String
    public var primaryOutcome: AppleProcessingOutcomeState
    public var validationRows: [AppleProcessingValidationRow]
    public var nextStepRecommendation: AppleProcessingNextStepRecommendation
    public var diagnosticSafe: Bool
    public var failureReason: String?

    public init(
        feature: String = "038-apple-voice-processing-spike",
        candidateId: String,
        primaryOutcome: AppleProcessingOutcomeState,
        validationRows: [AppleProcessingValidationRow],
        nextStepRecommendation: AppleProcessingNextStepRecommendation,
        diagnosticSafe: Bool = true,
        failureReason: String? = nil
    ) {
        self.feature = feature
        self.candidateId = candidateId
        self.primaryOutcome = primaryOutcome
        self.validationRows = validationRows
        self.nextStepRecommendation = nextStepRecommendation
        self.diagnosticSafe = diagnosticSafe
        self.failureReason = failureReason
    }

    public var canClaimCleanBuiltinSpeakerphone: Bool {
        guard primaryOutcome == .acceptedForBuiltinSpeakerphone, diagnosticSafe else { return false }
        let acceptedScenarios = Set(
            validationRows
                .filter(\.isAcceptedForBuiltinSpeakerphone)
                .map(\.scenario)
        )
        return Set(AppleProcessingScenario.builtinSpeakerphoneAcceptanceScenarios)
            .isSubset(of: acceptedScenarios)
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
            return "Запись системного звука готова через права macOS"
        }
        return "Готовность записи проверяется при старте"
    }

    public var driverDiagnosticSummary: String {
        switch driverState {
        case .installed:
            return "Драйвер установлен; для записи системного звука он не обязателен"
        case .requiresRestart:
            return "Перезапуск драйвера ожидает; запись системного звука доступна без него"
        case .needsRepair, .needsUpdate, .incompatible:
            return "Обслуживание драйвера отложено для будущей маршрутизации"
        case .notInstalled, .uninstalled:
            return "Драйвер отсутствует; запись использует права macOS"
        case .uninstalling:
            return "Удаление драйвера выполняется; запись по-прежнему управляется правами macOS"
        }
    }

    public var virtualDeviceDiagnosticSummary: String {
        if microphoneState == .available && speakerState == .available {
            return "Виртуальные устройства видны только для диагностики"
        }
        return "Виртуальные устройства не обязательны для записи"
    }
}

public enum SystemAudioStatusLabels {
    public static let captureRegion = "Управление записью"
    public static let recordingIdle = "Запись не идет"
    public static let recordButtonTitle = "Начать запись"
    public static let recordButtonAccessibilityLabel = "Начать запись системного звука"
    public static let stopButtonTitle = "Остановить"
    public static let stopButtonAccessibilityLabel = "Остановить запись"
    public static let pauseButtonTitle = "Пауза"
    public static let pauseButtonAccessibilityLabel = "Поставить локальный микрофон на паузу"
    public static let resumeButtonTitle = "Продолжить"
    public static let resumeButtonAccessibilityLabel = "Продолжить запись локального микрофона"
    public static let recordingMicrophoneMenuAccessibilityLabel = "Выбрать микрофон записи"
    public static let localRecordingPausedStatus =
        "Запись на паузе. Остановить можно в любой момент."
    public static let meetingMuteTruthLimitationCopy =
        "2brain не может проверить mute в этой встрече. Чтобы локальная речь не попала в запись, используйте Паузу или Остановить в 2brain."
    public static let captureAudioTitle = "Уровни записи"
    public static let microphoneTitle = "Микрофон"
    public static let incomingTitle = "Встреча"
    public static let microphonePendingStatus = "Проверим доступ при старте записи"
    public static let speakerPendingStatus = "Проверим звук при старте записи"
    public static let activeState = "Есть звук"
    public static let silentState = "Тихо"
    public static let metersWaiting = "Уровни появятся во время записи"
    public static let waitingForRecordingAudio = "Ожидаем старт записи"
    public static let localAudioRouteActiveNotRecording =
        "Локальный аудиомаршрут активен; запись начинается только вручную"
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
            return "Микрофон и звук встречи записываются"
        }
        if microphoneIsLive {
            return "Микрофон есть, звук встречи тихий"
        }
        if incomingIsLive {
            return "Звук встречи есть, микрофон тихий"
        }
        return "Звук пока не обнаружен"
    }

    public static func microphoneDetail(routeIsActive: Bool, microphoneIsLive: Bool) -> String {
        guard routeIsActive else { return waitingForRecordingAudio }
        return microphoneIsLive
            ? "Микрофон поступает в запись."
            : "Микрофон пока не слышен."
    }

    public static func incomingDetail(routeIsActive: Bool, incomingIsLive: Bool) -> String {
        guard routeIsActive else { return waitingForRecordingAudio }
        return incomingIsLive
            ? "Звук встречи поступает в запись."
            : "Звук встречи пока не слышен."
    }

    public static func meterState(isLive: Bool) -> String {
        isLive ? activeState : silentState
    }

    public static func meterAccessibilityLabel(title: String, detail: String) -> String {
        "\(title): \(detail)"
    }

    public static func localRecordingLocationAccessibilityLabel(_ path: String) -> String {
        "Путь локальной записи: \(path)"
    }
}

public enum SystemAudioAccessibilityIdentifier {
    public static let captureControls = "systemAudio.capture.controls"
    public static let recordButton = "systemAudio.record.button"
    public static let pauseButton = "systemAudio.pause.button"
    public static let resumeButton = "systemAudio.resume.button"
    public static let stopButton = "systemAudio.stop.button"
    public static let statusSurface = "systemAudio.status.surface"
    public static let blockerBanner = "systemAudio.blocker.banner"
    public static let localRecordingStatus = "systemAudio.localRecording.status"
    public static let recordingMicrophoneMenu = "systemAudio.recordingMicrophone.menu"
    public static let recordingMicrophoneStatus = "systemAudio.recordingMicrophone.status"
    public static let recordingMicrophoneRecovery = "systemAudio.recordingMicrophone.recovery"
    public static let muteTruthWarning = "systemAudio.muteTruth.warning"
    public static let localRecordingLocation = "systemAudio.localRecording.location"
    public static let meters = "systemAudio.meters"
    public static let microphoneMeter = "systemAudio.meter.microphone"
    public static let incomingMeter = "systemAudio.meter.incoming"
}
