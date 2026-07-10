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

    public static let allPackageTruthLabels: [AppleProcessingLineageStatus] = [
        .originalOnly,
        .candidateMetadata,
        .derivedCandidate,
        .liveAndPersisted,
        .guidanceOnly,
        .unproven,
        .blocked
    ]
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

public enum AppleProcessingFailureReason: String, Codable, Sendable {
    case processingUnavailable = "apple_processing_unavailable"
    case failedToEnable = "apple_processing_failed_to_enable"
    case userSystemControlled = "user_system_controlled_mic_mode"
    case missingFarEndReference = "missing_far_end_reference"
    case routeTopologyBlocked = "route_topology_blocked"
    case routeChanged = "route_changed"
    case diagnosticsNotSafe = "diagnostics_not_safe"
    case stopReleasedResources = "stop_released_candidate_resources"
    case failedStartReleasedResources = "failed_start_released_candidate_resources"
    case appQuitReleasedResources = "app_quit_released_candidate_resources"
}

public enum AppleProcessingLifecycleReleaseReason: String, Codable, Sendable {
    case stop
    case failedStart = "failed_start"
    case appQuit = "app_quit"
}

public struct AppleProcessingLifecycleSnapshot: Codable, Equatable, Sendable {
    public var feature: String
    public var activeCandidateId: String?
    public var releasedCandidateId: String?
    public var startedAt: Date?
    public var releasedAt: Date?
    public var releaseReason: AppleProcessingLifecycleReleaseReason?
    public var resourceActive: Bool
    public var diagnosticSafe: Bool

    public init(
        feature: String = "038-apple-voice-processing-spike",
        activeCandidateId: String? = nil,
        releasedCandidateId: String? = nil,
        startedAt: Date? = nil,
        releasedAt: Date? = nil,
        releaseReason: AppleProcessingLifecycleReleaseReason? = nil,
        resourceActive: Bool,
        diagnosticSafe: Bool = true
    ) {
        self.feature = feature
        self.activeCandidateId = activeCandidateId
        self.releasedCandidateId = releasedCandidateId
        self.startedAt = startedAt
        self.releasedAt = releasedAt
        self.releaseReason = releaseReason
        self.resourceActive = resourceActive
        self.diagnosticSafe = diagnosticSafe
    }
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
        if !diagnosticSafe {
            return .blockedStability
        }
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
        guard primaryOutcome == .acceptedForBuiltinSpeakerphone,
              diagnosticSafe,
              validationRows.allSatisfy(\.diagnosticSafe) else { return false }
        let acceptedScenarios = Set(
            validationRows
                .filter(\.isAcceptedForBuiltinSpeakerphone)
                .map(\.scenario)
        )
        return Set(AppleProcessingScenario.builtinSpeakerphoneAcceptanceScenarios)
            .isSubset(of: acceptedScenarios)
    }
}

public enum WebRTCAEC3Feature {
    public static let identifier = "039-webrtc-aec3-speakerphone-spike"
}

public enum WebRTCAEC3CandidateKind: String, Codable, Sendable {
    case nativeWebRTCAEC3
    case adapterUnavailable
    case dependencyBlocked
    case offlineCorpusOnly
}

public enum WebRTCAEC3RouteClass: String, Codable, Sendable {
    case builtInSpeakerphone
    case wiredHeadphones
    case usbHeadset
    case bluetoothAirPodsClass
    case browserTargetSupporting
    case unknown
}

public enum WebRTCAEC3PromotionScope: String, Codable, Sendable {
    case builtInMacMicAndSpeakers
    case notPromotable
}

public enum WebRTCAEC3DependencyReadiness: String, Codable, Sendable {
    case ready
    case unavailable
    case licenseBlocked
    case packagingBlocked
    case signingBlocked
    case unknown
}

public enum WebRTCAEC3ReferenceStatus: String, Codable, Sendable {
    case present
    case missing
    case late
    case protected
    case silent
    case clipped
    case notRepresentative
    case unknown
}

public enum WebRTCAEC3CaptureTimingStatus: String, Codable, Sendable {
    case safe
    case jittery
    case delayed
    case callOrderUnsafe
    case drifted
    case unknown
}

public enum WebRTCAEC3MetricsStatus: String, Codable, Sendable {
    case available
    case partial
    case notAvailable
    case unknown
}

public enum WebRTCAEC3ScenarioFamily: String, Codable, CaseIterable, Sendable {
    case farEndOnlyLeakage
    case nearEndOnlySpeech
    case doubleTalk
    case loudSpeakerClipping
    case routeChangeTimingStress
    case unsafeReferenceNegativeControl
    case stopQuit
    case diagnostics
    case appStatus
    case rollback

    public static let immediatePromotionRequired: [WebRTCAEC3ScenarioFamily] = [
        .farEndOnlyLeakage,
        .nearEndOnlySpeech,
        .doubleTalk,
        .loudSpeakerClipping,
        .routeChangeTimingStress,
        .unsafeReferenceNegativeControl
    ]

    public static let operationalPromotionRequired: [WebRTCAEC3ScenarioFamily] = [
        .stopQuit,
        .diagnostics,
        .appStatus,
        .rollback
    ]

    public static let allImmediatePromotionRequired: [WebRTCAEC3ScenarioFamily] =
        immediatePromotionRequired + operationalPromotionRequired
}

public enum WebRTCAEC3ValidationKind: String, Codable, Sendable {
    case slice
    case fullFile
    case longFormFullFile
    case controlledRealHardware
    case negativeControl
    case stopQuit
    case diagnostics
    case appStatus
    case rollback
}

public enum WebRTCAEC3BaselineStatus: String, Codable, Sendable {
    case clean
    case leakageDetected
    case unproven
    case notMeasured
}

public enum WebRTCAEC3CandidateStatus: String, Codable, Sendable {
    case accepted
    case degraded
    case blocked
    case unproven
    case notMeasured
}

public enum WebRTCAEC3LineageStatus: String, Codable, Sendable {
    case originalOnly
    case candidateMetadata
    case derivedCandidate
    case promotedBuiltinRoute
    case rolledBackToOriginal
    case guidanceOnly
    case blocked
    case unproven

    public static let allPackageTruthLabels: [WebRTCAEC3LineageStatus] = [
        .originalOnly,
        .candidateMetadata,
        .derivedCandidate,
        .promotedBuiltinRoute,
        .rolledBackToOriginal,
        .guidanceOnly,
        .unproven,
        .blocked
    ]
}

public enum WebRTCAEC3SpeechPreservationStatus: String, Codable, Sendable {
    case preserved
    case degraded
    case suppressed
    case notMeasured
    case unknown
}

public enum WebRTCAEC3ResidualLeakageStatus: String, Codable, Sendable {
    case clean
    case leakageDetected
    case unproven
    case notMeasured
    case notApplicable
}

public enum WebRTCAEC3TimingConfidence: String, Codable, Sendable {
    case safe
    case degraded
    case failed
    case notMeasured
    case unknown
}

public enum WebRTCAEC3StabilityStatus: String, Codable, Sendable {
    case accepted
    case blockedRouteTopology
    case blockedQuality
    case blockedStability
    case rollbackRequired
    case unproven
    case notMeasured
}

public enum WebRTCAEC3AppStatusState: String, Codable, Sendable {
    case notEvaluated
    case evaluatingAEC3
    case usingOriginalMicTruth
    case candidateBlocked
    case promotedBuiltinRoute
    case rolledBackToOriginal
    case fallbackRelevant
    case requiresUserAttention
    case notApplicable
}

public enum WebRTCAEC3StatusRouteScope: String, Codable, Sendable {
    case builtInMacMicAndSpeakers
    case supportingRouteOnly
    case notApplicable
}

public enum WebRTCAEC3StatusCopySafety: String, Codable, Sendable {
    case safe
    case tooTechnical
    case tooNoisy
    case stale
    case inconsistentWithPackageTruth
}

public enum WebRTCAEC3StatusActionHint: String, Codable, Sendable {
    case none
    case continueRecording
    case reviewStatus
    case useHeadphones
    case retryCheck
    case stopAvailable
}

public enum WebRTCAEC3FailureReason: String, Codable, Sendable {
    case dependencyUnavailable = "dependency_unavailable"
    case licenseBlocked = "license_blocked"
    case packagingBlocked = "packaging_blocked"
    case signingBlocked = "signing_blocked"
    case referenceMissing = "reference_missing"
    case referenceLate = "reference_late"
    case referenceProtected = "reference_protected"
    case referenceSilent = "reference_silent"
    case referenceClipped = "reference_clipped"
    case referenceNotRepresentative = "reference_not_representative"
    case callOrderUnsafe = "call_order_unsafe"
    case timingDrift = "timing_drift"
    case jitterUnsafe = "jitter_unsafe"
    case sampleFormatUnsupported = "sample_format_unsupported"
    case speechSuppressed = "speech_suppressed"
    case residualLeakageHigh = "residual_leakage_high"
    case cpuPressure = "cpu_pressure"
    case memoryPressure = "memory_pressure"
    case noHangRegression = "no_hang_regression"
    case diagnosticsUnsafe = "diagnostics_unsafe"
    case thresholdProfileMissing = "threshold_profile_missing"
    case thresholdProfileMismatch = "threshold_profile_mismatch"
    case routeNotPromotable = "route_not_promotable"
    case lineageIncomplete = "lineage_incomplete"
    case stopQuitFailed = "stop_quit_failed"
    case appStatusStale = "app_status_stale"
    case appStatusNoisy = "app_status_noisy"
    case appStatusContradictsPackage = "app_status_contradicts_package"
    case controlledHardwareMissing = "controlled_hardware_missing"
    case corpusIncomplete = "corpus_incomplete"
}

public struct WebRTCAEC3AcceptanceThresholdProfile: Codable, Equatable, Sendable {
    public var thresholdProfileId: String
    public var appliesToFeature: String
    public var residualLeakageGate: String
    public var speechPreservationGate: String
    public var doubleTalkGate: String
    public var timingDriftGate: String
    public var clippingDropoutGate: String
    public var cpuNoHangGate: String
    public var stopQuitGate: String
    public var diagnosticSafetyGate: String
    public var appStatusConsistencyGate: String
    public var rollbackTriggerGate: String
    public var declaredBeforeValidation: Bool
    public var diagnosticSafe: Bool

    public init(
        thresholdProfileId: String,
        appliesToFeature: String = WebRTCAEC3Feature.identifier,
        residualLeakageGate: String,
        speechPreservationGate: String,
        doubleTalkGate: String,
        timingDriftGate: String,
        clippingDropoutGate: String,
        cpuNoHangGate: String,
        stopQuitGate: String,
        diagnosticSafetyGate: String,
        appStatusConsistencyGate: String,
        rollbackTriggerGate: String,
        declaredBeforeValidation: Bool,
        diagnosticSafe: Bool = true
    ) {
        self.thresholdProfileId = thresholdProfileId
        self.appliesToFeature = appliesToFeature
        self.residualLeakageGate = residualLeakageGate
        self.speechPreservationGate = speechPreservationGate
        self.doubleTalkGate = doubleTalkGate
        self.timingDriftGate = timingDriftGate
        self.clippingDropoutGate = clippingDropoutGate
        self.cpuNoHangGate = cpuNoHangGate
        self.stopQuitGate = stopQuitGate
        self.diagnosticSafetyGate = diagnosticSafetyGate
        self.appStatusConsistencyGate = appStatusConsistencyGate
        self.rollbackTriggerGate = rollbackTriggerGate
        self.declaredBeforeValidation = declaredBeforeValidation
        self.diagnosticSafe = diagnosticSafe
    }

    public static let standardV1 = WebRTCAEC3AcceptanceThresholdProfile(
        thresholdProfileId: "aec3-threshold-profile-v1",
        residualLeakageGate: "residual_leakage_below_declared_bound",
        speechPreservationGate: "near_end_speech_preserved",
        doubleTalkGate: "double_talk_preserves_speech_and_blocks_leakage",
        timingDriftGate: "render_capture_timing_within_declared_bound",
        clippingDropoutGate: "clipping_or_dropout_blocks_promotion",
        cpuNoHangGate: "cpu_memory_and_no_hang_gates_pass",
        stopQuitGate: "stop_and_quit_remain_bounded",
        diagnosticSafetyGate: "metadata_only_diagnostics",
        appStatusConsistencyGate: "app_status_matches_package_truth",
        rollbackTriggerGate: "unsafe_runtime_evidence_restores_original_truth",
        declaredBeforeValidation: true
    )

    public var canSupportPromotion: Bool {
        !thresholdProfileId.isEmpty &&
            appliesToFeature == WebRTCAEC3Feature.identifier &&
            declaredBeforeValidation &&
            diagnosticSafe &&
            Self.summariesAreSafe([
                residualLeakageGate,
                speechPreservationGate,
                doubleTalkGate,
                timingDriftGate,
                clippingDropoutGate,
                cpuNoHangGate,
                stopQuitGate,
                diagnosticSafetyGate,
                appStatusConsistencyGate,
                rollbackTriggerGate
            ])
    }

    private static func summariesAreSafe(_ summaries: [String]) -> Bool {
        let forbiddenFragments = [
            "rawaudio",
            "transcript",
            "signedurl",
            "private",
            "/users/",
            "credential",
            "token"
        ]
        return summaries.allSatisfy { summary in
            let normalized = summary.lowercased()
            return !forbiddenFragments.contains { normalized.contains($0) }
        }
    }
}

public struct WebRTCAEC3Candidate: Codable, Equatable, Sendable {
    public var feature: String
    public var candidateId: String
    public var candidateKind: WebRTCAEC3CandidateKind
    public var routeClass: WebRTCAEC3RouteClass
    public var promotionScope: WebRTCAEC3PromotionScope
    public var dependencyReadiness: WebRTCAEC3DependencyReadiness
    public var renderReferenceStatus: WebRTCAEC3ReferenceStatus
    public var captureTimingStatus: WebRTCAEC3CaptureTimingStatus
    public var metricsStatus: WebRTCAEC3MetricsStatus
    public var thresholdProfileId: String
    public var diagnosticSafe: Bool
    public var failureReason: String?

    public init(
        feature: String = WebRTCAEC3Feature.identifier,
        candidateId: String,
        candidateKind: WebRTCAEC3CandidateKind,
        routeClass: WebRTCAEC3RouteClass,
        promotionScope: WebRTCAEC3PromotionScope,
        dependencyReadiness: WebRTCAEC3DependencyReadiness,
        renderReferenceStatus: WebRTCAEC3ReferenceStatus,
        captureTimingStatus: WebRTCAEC3CaptureTimingStatus,
        metricsStatus: WebRTCAEC3MetricsStatus,
        thresholdProfileId: String,
        diagnosticSafe: Bool,
        failureReason: String? = nil
    ) {
        self.feature = feature
        self.candidateId = candidateId
        self.candidateKind = candidateKind
        self.routeClass = routeClass
        self.promotionScope = promotionScope
        self.dependencyReadiness = dependencyReadiness
        self.renderReferenceStatus = renderReferenceStatus
        self.captureTimingStatus = captureTimingStatus
        self.metricsStatus = metricsStatus
        self.thresholdProfileId = thresholdProfileId
        self.diagnosticSafe = diagnosticSafe
        self.failureReason = failureReason
    }

    public var isEligibleForImmediatePromotion: Bool {
        feature == WebRTCAEC3Feature.identifier &&
            candidateKind == .nativeWebRTCAEC3 &&
            routeClass == .builtInSpeakerphone &&
            promotionScope == .builtInMacMicAndSpeakers &&
            dependencyReadiness == .ready &&
            renderReferenceStatus == .present &&
            captureTimingStatus == .safe &&
            metricsStatus == .available &&
            !thresholdProfileId.isEmpty &&
            diagnosticSafe
    }
}

public struct WebRTCAEC3ValidationRow: Codable, Equatable, Sendable {
    public var feature: String
    public var rowId: String
    public var candidateId: String
    public var corpusId: String?
    public var scenarioFamily: WebRTCAEC3ScenarioFamily
    public var validationKind: WebRTCAEC3ValidationKind
    public var routeClass: WebRTCAEC3RouteClass
    public var baselineStatus: WebRTCAEC3BaselineStatus
    public var candidateStatus: WebRTCAEC3CandidateStatus
    public var lineageStatus: WebRTCAEC3LineageStatus
    public var speechPreservationStatus: WebRTCAEC3SpeechPreservationStatus
    public var residualLeakageStatus: WebRTCAEC3ResidualLeakageStatus
    public var timingConfidence: WebRTCAEC3TimingConfidence
    public var referenceStatus: WebRTCAEC3ReferenceStatus
    public var stabilityStatus: WebRTCAEC3StabilityStatus
    public var thresholdProfileId: String
    public var thresholdSummary: String
    public var appStatusState: WebRTCAEC3AppStatusState
    public var diagnosticSafe: Bool
    public var failureReason: String?

    public init(
        feature: String = WebRTCAEC3Feature.identifier,
        rowId: String,
        candidateId: String,
        corpusId: String? = nil,
        scenarioFamily: WebRTCAEC3ScenarioFamily,
        validationKind: WebRTCAEC3ValidationKind,
        routeClass: WebRTCAEC3RouteClass,
        baselineStatus: WebRTCAEC3BaselineStatus,
        candidateStatus: WebRTCAEC3CandidateStatus,
        lineageStatus: WebRTCAEC3LineageStatus,
        speechPreservationStatus: WebRTCAEC3SpeechPreservationStatus,
        residualLeakageStatus: WebRTCAEC3ResidualLeakageStatus,
        timingConfidence: WebRTCAEC3TimingConfidence,
        referenceStatus: WebRTCAEC3ReferenceStatus,
        stabilityStatus: WebRTCAEC3StabilityStatus,
        thresholdProfileId: String,
        thresholdSummary: String,
        appStatusState: WebRTCAEC3AppStatusState,
        diagnosticSafe: Bool,
        failureReason: String? = nil
    ) {
        self.feature = feature
        self.rowId = rowId
        self.candidateId = candidateId
        self.corpusId = corpusId
        self.scenarioFamily = scenarioFamily
        self.validationKind = validationKind
        self.routeClass = routeClass
        self.baselineStatus = baselineStatus
        self.candidateStatus = candidateStatus
        self.lineageStatus = lineageStatus
        self.speechPreservationStatus = speechPreservationStatus
        self.residualLeakageStatus = residualLeakageStatus
        self.timingConfidence = timingConfidence
        self.referenceStatus = referenceStatus
        self.stabilityStatus = stabilityStatus
        self.thresholdProfileId = thresholdProfileId
        self.thresholdSummary = thresholdSummary
        self.appStatusState = appStatusState
        self.diagnosticSafe = diagnosticSafe
        self.failureReason = failureReason
    }

    public static func acceptedFixture(
        scenarioFamily: WebRTCAEC3ScenarioFamily,
        validationKind: WebRTCAEC3ValidationKind,
        thresholdProfileId: String
    ) -> WebRTCAEC3ValidationRow {
        WebRTCAEC3ValidationRow(
            rowId: "aec3-\(scenarioFamily.rawValue)-\(validationKind.rawValue)-accepted",
            candidateId: "aec3-candidate-accepted",
            corpusId: "metadata-lab-corpus-v1",
            scenarioFamily: scenarioFamily,
            validationKind: validationKind,
            routeClass: .builtInSpeakerphone,
            baselineStatus: .leakageDetected,
            candidateStatus: .accepted,
            lineageStatus: .promotedBuiltinRoute,
            speechPreservationStatus: .preserved,
            residualLeakageStatus: .clean,
            timingConfidence: .safe,
            referenceStatus: .present,
            stabilityStatus: .accepted,
            thresholdProfileId: thresholdProfileId,
            thresholdSummary: "standard_v1_all_required_gates_passed",
            appStatusState: .promotedBuiltinRoute,
            diagnosticSafe: true
        )
    }

    public func usesThresholdProfile(_ profile: WebRTCAEC3AcceptanceThresholdProfile) -> Bool {
        thresholdProfileId == profile.thresholdProfileId &&
            profile.canSupportPromotion
    }

    public func promotionBlockingReason(
        expectedProfile: WebRTCAEC3AcceptanceThresholdProfile
    ) -> String? {
        if thresholdProfileId.isEmpty {
            return WebRTCAEC3FailureReason.thresholdProfileMissing.rawValue
        }
        if thresholdProfileId != expectedProfile.thresholdProfileId {
            return WebRTCAEC3FailureReason.thresholdProfileMismatch.rawValue
        }
        if !diagnosticSafe {
            return WebRTCAEC3FailureReason.diagnosticsUnsafe.rawValue
        }
        if routeClass != .builtInSpeakerphone {
            return WebRTCAEC3FailureReason.routeNotPromotable.rawValue
        }
        if lineageStatus != .promotedBuiltinRoute {
            return WebRTCAEC3FailureReason.lineageIncomplete.rawValue
        }
        if appStatusState != .promotedBuiltinRoute {
            return WebRTCAEC3FailureReason.appStatusContradictsPackage.rawValue
        }
        return nil
    }

    public var isAcceptedForImmediatePromotion: Bool {
        promotionBlockingReason(expectedProfile: .standardV1) == nil &&
            feature == WebRTCAEC3Feature.identifier &&
            candidateStatus == .accepted &&
            speechPreservationStatus == .preserved &&
            residualLeakageStatus == .clean &&
            timingConfidence == .safe &&
            referenceStatus == .present &&
            stabilityStatus == .accepted
    }
}

public struct WebRTCAEC3CorpusScenario: Codable, Equatable, Sendable {
    public var scenarioFamily: WebRTCAEC3ScenarioFamily
    public var fileCount: Int
    public var sliceCountPerFile: Int
    public var fullFileValidationCount: Int
    public var longFormFullFileRunCount: Int
    public var criticalGateFailures: Int

    public init(
        scenarioFamily: WebRTCAEC3ScenarioFamily,
        fileCount: Int,
        sliceCountPerFile: Int,
        fullFileValidationCount: Int,
        longFormFullFileRunCount: Int,
        criticalGateFailures: Int
    ) {
        self.scenarioFamily = scenarioFamily
        self.fileCount = fileCount
        self.sliceCountPerFile = sliceCountPerFile
        self.fullFileValidationCount = fullFileValidationCount
        self.longFormFullFileRunCount = longFormFullFileRunCount
        self.criticalGateFailures = criticalGateFailures
    }

    public var slicedWindowValidationCount: Int {
        fileCount * sliceCountPerFile
    }

    public var satisfiesImmediatePromotionCounts: Bool {
        fileCount >= 10 &&
            sliceCountPerFile >= 5 &&
            fullFileValidationCount >= fileCount &&
            longFormFullFileRunCount >= 2 &&
            criticalGateFailures == 0
    }
}

public struct WebRTCAEC3ValidationCorpus: Codable, Equatable, Sendable {
    public var feature: String
    public var corpusId: String
    public var thresholdProfileId: String
    public var diagnosticSafe: Bool
    public var roomConditionCount: Int
    public var deviceProfileCount: Int
    public var speakerVolumeLevelCount: Int
    public var scenarioFamilies: [WebRTCAEC3CorpusScenario]

    public init(
        feature: String = WebRTCAEC3Feature.identifier,
        corpusId: String,
        thresholdProfileId: String,
        diagnosticSafe: Bool,
        roomConditionCount: Int,
        deviceProfileCount: Int,
        speakerVolumeLevelCount: Int,
        scenarioFamilies: [WebRTCAEC3CorpusScenario]
    ) {
        self.feature = feature
        self.corpusId = corpusId
        self.thresholdProfileId = thresholdProfileId
        self.diagnosticSafe = diagnosticSafe
        self.roomConditionCount = roomConditionCount
        self.deviceProfileCount = deviceProfileCount
        self.speakerVolumeLevelCount = speakerVolumeLevelCount
        self.scenarioFamilies = scenarioFamilies
    }

    public var requiredScenarioFamiliesMissing: [WebRTCAEC3ScenarioFamily] {
        let present = Set(scenarioFamilies.map(\.scenarioFamily))
        return WebRTCAEC3ScenarioFamily.immediatePromotionRequired
            .filter { !present.contains($0) }
    }

    public var totalFullFileValidations: Int {
        scenarioFamilies.reduce(0) { $0 + $1.fullFileValidationCount }
    }

    public var totalSlicedWindowValidations: Int {
        scenarioFamilies.reduce(0) { $0 + $1.slicedWindowValidationCount }
    }

    public var longFormRunCountByScenario: [WebRTCAEC3ScenarioFamily: Int] {
        Dictionary(uniqueKeysWithValues: scenarioFamilies.map {
            ($0.scenarioFamily, $0.longFormFullFileRunCount)
        })
    }

    public var isEligibleForImmediatePromotion: Bool {
        feature == WebRTCAEC3Feature.identifier &&
            thresholdProfileId == WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId &&
            diagnosticSafe &&
            promotionCoverageFailures.isEmpty
    }

    public var promotionCoverageFailures: [String] {
        var failures: [String] = []
        if feature != WebRTCAEC3Feature.identifier {
            failures.append("feature_mismatch")
        }
        if thresholdProfileId != WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId {
            failures.append(WebRTCAEC3FailureReason.thresholdProfileMismatch.rawValue)
        }
        if !diagnosticSafe {
            failures.append(WebRTCAEC3FailureReason.diagnosticsUnsafe.rawValue)
        }
        if roomConditionCount < 2 {
            failures.append("room_condition_count_below_minimum")
        }
        if deviceProfileCount < 2 {
            failures.append("device_profile_count_below_minimum")
        }
        if speakerVolumeLevelCount < 3 {
            failures.append("speaker_volume_level_count_below_minimum")
        }

        let scenarioByFamily = Dictionary(uniqueKeysWithValues: scenarioFamilies.map {
            ($0.scenarioFamily, $0)
        })
        for family in WebRTCAEC3ScenarioFamily.immediatePromotionRequired {
            guard let scenario = scenarioByFamily[family] else {
                failures.append("scenario_missing_\(family.rawValue)")
                continue
            }
            if scenario.fileCount < 10 {
                failures.append("file_count_below_minimum")
            }
            if scenario.sliceCountPerFile < 5 {
                failures.append("slice_count_below_minimum")
            }
            if scenario.fullFileValidationCount < scenario.fileCount {
                failures.append("full_file_validation_count_below_minimum")
            }
            if scenario.longFormFullFileRunCount < 2 {
                failures.append("long_form_full_file_run_count_below_minimum")
            }
            if scenario.criticalGateFailures > 0 {
                failures.append("critical_gate_failures_present")
            }
        }

        return Array(Set(failures)).sorted()
    }
}

public struct WebRTCAEC3InvalidCorpusCases: Codable, Equatable, Sendable {
    public var feature: String
    public var cases: [WebRTCAEC3InvalidCorpusCase]

    public init(feature: String = WebRTCAEC3Feature.identifier, cases: [WebRTCAEC3InvalidCorpusCase]) {
        self.feature = feature
        self.cases = cases
    }

    public var caseIds: [String] {
        cases.map(\.caseId)
    }

    public var promotionBlockers: [String] {
        cases.map(\.reason.blockerCode)
    }
}

public struct WebRTCAEC3InvalidCorpusCase: Codable, Equatable, Sendable {
    public var caseId: String
    public var reason: WebRTCAEC3InvalidCorpusReason
    public var scenarioFamily: WebRTCAEC3ScenarioFamily?
    public var fileCount: Int?
    public var sliceCountPerFile: Int?
    public var fullFileValidationCount: Int?
    public var longFormFullFileRunCount: Int?
    public var roomConditionCount: Int?
    public var deviceProfileCount: Int?
    public var speakerVolumeLevelCount: Int?
    public var thresholdProfileId: String?

    public init(
        caseId: String,
        reason: WebRTCAEC3InvalidCorpusReason,
        scenarioFamily: WebRTCAEC3ScenarioFamily? = nil,
        fileCount: Int? = nil,
        sliceCountPerFile: Int? = nil,
        fullFileValidationCount: Int? = nil,
        longFormFullFileRunCount: Int? = nil,
        roomConditionCount: Int? = nil,
        deviceProfileCount: Int? = nil,
        speakerVolumeLevelCount: Int? = nil,
        thresholdProfileId: String? = nil
    ) {
        self.caseId = caseId
        self.reason = reason
        self.scenarioFamily = scenarioFamily
        self.fileCount = fileCount
        self.sliceCountPerFile = sliceCountPerFile
        self.fullFileValidationCount = fullFileValidationCount
        self.longFormFullFileRunCount = longFormFullFileRunCount
        self.roomConditionCount = roomConditionCount
        self.deviceProfileCount = deviceProfileCount
        self.speakerVolumeLevelCount = speakerVolumeLevelCount
        self.thresholdProfileId = thresholdProfileId
    }
}

public enum WebRTCAEC3InvalidCorpusReason: String, Codable, Sendable {
    case fileCountBelowMinimum
    case sliceCountBelowMinimum
    case fullFileValidationCountBelowMinimum
    case longFormFullFileRunCountBelowMinimum
    case roomConditionCountBelowMinimum
    case deviceProfileCountBelowMinimum
    case speakerVolumeLevelCountBelowMinimum
    case thresholdProfileMismatch

    public var blockerCode: String {
        switch self {
        case .fileCountBelowMinimum:
            return "file_count_below_minimum"
        case .sliceCountBelowMinimum:
            return "slice_count_below_minimum"
        case .fullFileValidationCountBelowMinimum:
            return "full_file_validation_count_below_minimum"
        case .longFormFullFileRunCountBelowMinimum:
            return "long_form_full_file_run_count_below_minimum"
        case .roomConditionCountBelowMinimum:
            return "room_condition_count_below_minimum"
        case .deviceProfileCountBelowMinimum:
            return "device_profile_count_below_minimum"
        case .speakerVolumeLevelCountBelowMinimum:
            return "speaker_volume_level_count_below_minimum"
        case .thresholdProfileMismatch:
            return WebRTCAEC3FailureReason.thresholdProfileMismatch.rawValue
        }
    }
}

public struct WebRTCAEC3ControlledHardwareMatrix: Codable, Equatable, Sendable {
    public var feature: String
    public var thresholdProfileId: String
    public var diagnosticSafe: Bool
    public var criticalRows: [String]
    public var supportingRouteRows: [String]
    public var forbiddenContent: WebRTCAEC3ForbiddenContentSummary

    public init(
        feature: String = WebRTCAEC3Feature.identifier,
        thresholdProfileId: String,
        diagnosticSafe: Bool,
        criticalRows: [String],
        supportingRouteRows: [String],
        forbiddenContent: WebRTCAEC3ForbiddenContentSummary
    ) {
        self.feature = feature
        self.thresholdProfileId = thresholdProfileId
        self.diagnosticSafe = diagnosticSafe
        self.criticalRows = criticalRows
        self.supportingRouteRows = supportingRouteRows
        self.forbiddenContent = forbiddenContent
    }

    public var hasAllImmediatePromotionCriticalRows: Bool {
        let present = Set(criticalRows)
        let required = WebRTCAEC3ScenarioFamily.allImmediatePromotionRequired.map {
            "builtInSpeakerphone.\($0.rawValue)"
        }
        return feature == WebRTCAEC3Feature.identifier &&
            thresholdProfileId == WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId &&
            diagnosticSafe &&
            Set(required).isSubset(of: present)
    }

    public var supportingRoutesCanBroadenPromotionScope: Bool {
        false
    }

    public var isMetadataOnly: Bool {
        !forbiddenContent.rawAudio &&
            !forbiddenContent.transcriptText &&
            !forbiddenContent.meetingContent &&
            !forbiddenContent.credentials &&
            !forbiddenContent.signedUrls &&
            !forbiddenContent.privateLocalPaths
    }
}

public struct WebRTCAEC3ForbiddenContentSummary: Codable, Equatable, Sendable {
    public var rawAudio: Bool
    public var transcriptText: Bool
    public var meetingContent: Bool
    public var credentials: Bool
    public var signedUrls: Bool
    public var privateLocalPaths: Bool

    public init(
        rawAudio: Bool,
        transcriptText: Bool,
        meetingContent: Bool,
        credentials: Bool,
        signedUrls: Bool,
        privateLocalPaths: Bool
    ) {
        self.rawAudio = rawAudio
        self.transcriptText = transcriptText
        self.meetingContent = meetingContent
        self.credentials = credentials
        self.signedUrls = signedUrls
        self.privateLocalPaths = privateLocalPaths
    }
}

extension ControlledRealHardwareRecordingEvidence {
    public var satisfiesImmediatePromotion: Bool {
        routeClass == .builtInSpeakerphone &&
            stopBehaviorStatus == .accepted &&
            appStatusShown &&
            thresholdProfileId == WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId &&
            diagnosticSafe
    }
}

public struct ControlledRealHardwareRecordingEvidence: Codable, Equatable, Sendable {
    public var recordingEvidenceId: String
    public var candidateId: String
    public var routeClass: WebRTCAEC3RouteClass
    public var scenarioFamily: WebRTCAEC3ScenarioFamily
    public var packageLineageStatus: WebRTCAEC3LineageStatus
    public var stopBehaviorStatus: WebRTCAEC3CandidateStatus
    public var appStatusShown: Bool
    public var thresholdProfileId: String
    public var diagnosticSafe: Bool
    public var failureReason: String?

    public init(
        recordingEvidenceId: String,
        candidateId: String,
        routeClass: WebRTCAEC3RouteClass,
        scenarioFamily: WebRTCAEC3ScenarioFamily,
        packageLineageStatus: WebRTCAEC3LineageStatus,
        stopBehaviorStatus: WebRTCAEC3CandidateStatus,
        appStatusShown: Bool,
        thresholdProfileId: String,
        diagnosticSafe: Bool,
        failureReason: String? = nil
    ) {
        self.recordingEvidenceId = recordingEvidenceId
        self.candidateId = candidateId
        self.routeClass = routeClass
        self.scenarioFamily = scenarioFamily
        self.packageLineageStatus = packageLineageStatus
        self.stopBehaviorStatus = stopBehaviorStatus
        self.appStatusShown = appStatusShown
        self.thresholdProfileId = thresholdProfileId
        self.diagnosticSafe = diagnosticSafe
        self.failureReason = failureReason
    }
}

public enum AEC3RollbackTrigger: String, Codable, Sendable {
    case routeChanged
    case referenceMissing
    case referenceUnsafe
    case qualityDropped
    case timingUnsafe
    case lineageIncomplete
    case diagnosticsUnsafe
    case stopQuit
}

public struct AEC3RollbackEvent: Codable, Equatable, Sendable {
    public var rollbackId: String
    public var candidateId: String
    public var trigger: AEC3RollbackTrigger
    public var previousLineageStatus: WebRTCAEC3LineageStatus
    public var restoredLineageStatus: WebRTCAEC3LineageStatus
    public var cleanRecordingClaimRemoved: Bool
    public var appStatusShown: Bool
    public var thresholdProfileId: String
    public var occurredAt: Date
    public var diagnosticSafe: Bool

    public init(
        rollbackId: String,
        candidateId: String,
        trigger: AEC3RollbackTrigger,
        previousLineageStatus: WebRTCAEC3LineageStatus,
        restoredLineageStatus: WebRTCAEC3LineageStatus,
        cleanRecordingClaimRemoved: Bool,
        appStatusShown: Bool,
        thresholdProfileId: String,
        occurredAt: Date,
        diagnosticSafe: Bool = true
    ) {
        self.rollbackId = rollbackId
        self.candidateId = candidateId
        self.trigger = trigger
        self.previousLineageStatus = previousLineageStatus
        self.restoredLineageStatus = restoredLineageStatus
        self.cleanRecordingClaimRemoved = cleanRecordingClaimRemoved
        self.appStatusShown = appStatusShown
        self.thresholdProfileId = thresholdProfileId
        self.occurredAt = occurredAt
        self.diagnosticSafe = diagnosticSafe
    }

    public var restoresOriginalTruth: Bool {
        previousLineageStatus == .promotedBuiltinRoute &&
            restoredLineageStatus == .originalOnly &&
            cleanRecordingClaimRemoved &&
            appStatusShown &&
            diagnosticSafe
    }
}

public struct AppRecordingStatus: Codable, Equatable, Sendable {
    public var statusId: String
    public var candidateId: String?
    public var state: WebRTCAEC3AppStatusState
    public var routeScope: WebRTCAEC3StatusRouteScope
    public var copySafety: WebRTCAEC3StatusCopySafety
    public var actionHint: WebRTCAEC3StatusActionHint
    public var matchesPackageTruth: Bool
    public var diagnosticSafe: Bool

    public init(
        statusId: String,
        candidateId: String? = nil,
        state: WebRTCAEC3AppStatusState,
        routeScope: WebRTCAEC3StatusRouteScope,
        copySafety: WebRTCAEC3StatusCopySafety,
        actionHint: WebRTCAEC3StatusActionHint,
        matchesPackageTruth: Bool,
        diagnosticSafe: Bool = true
    ) {
        self.statusId = statusId
        self.candidateId = candidateId
        self.state = state
        self.routeScope = routeScope
        self.copySafety = copySafety
        self.actionHint = actionHint
        self.matchesPackageTruth = matchesPackageTruth
        self.diagnosticSafe = diagnosticSafe
    }

    public var canSupportPromotion: Bool {
        state == .promotedBuiltinRoute &&
            routeScope == .builtInMacMicAndSpeakers &&
            copySafety == .safe &&
            matchesPackageTruth &&
            diagnosticSafe
    }
}

public enum WebRTCAEC3OutcomeState: String, Codable, Sendable {
    case acceptedForImmediatePromotion = "accepted_for_immediate_promotion"
    case acceptedForDerivedCandidateOnly = "accepted_for_derived_candidate_only"
    case acceptedForGuidanceOnly = "accepted_for_guidance_only"
    case blockedRouteTopology = "blocked_route_topology"
    case blockedQuality = "blocked_quality"
    case blockedStability = "blocked_stability"
    case deferToFallbackDecision = "defer_to_fallback_decision"
}

public enum WebRTCAEC3NextStepRecommendation: String, Codable, Sendable {
    case promoteBuiltInRoute = "promote_builtin_route"
    case derivedCandidateOnly = "derived_candidate_only"
    case guidanceOnly = "guidance_only"
    case fallbackDecision = "fallback_decision"
    case routeSpecificValidation = "route_specific_validation"
    case dependencyPackaging = "dependency_packaging"
}

public struct WebRTCAEC3DecisionRecord: Codable, Equatable, Sendable {
    public var feature: String
    public var candidateId: String
    public var primaryOutcome: WebRTCAEC3OutcomeState
    public var validationRows: [WebRTCAEC3ValidationRow]
    public var nextStepRecommendation: WebRTCAEC3NextStepRecommendation
    public var diagnosticSafe: Bool
    public var rollbackEvents: [AEC3RollbackEvent]?
    public var supportingRouteRows: [WebRTCAEC3ValidationRow]?
    public var limitations: [String]?
    public var fallbackFeatureId: String?
    public var failureReason: String?

    public init(
        feature: String = WebRTCAEC3Feature.identifier,
        candidateId: String,
        primaryOutcome: WebRTCAEC3OutcomeState,
        validationRows: [WebRTCAEC3ValidationRow],
        nextStepRecommendation: WebRTCAEC3NextStepRecommendation,
        diagnosticSafe: Bool = true,
        rollbackEvents: [AEC3RollbackEvent]? = nil,
        supportingRouteRows: [WebRTCAEC3ValidationRow]? = nil,
        limitations: [String]? = nil,
        fallbackFeatureId: String? = nil,
        failureReason: String? = nil
    ) {
        self.feature = feature
        self.candidateId = candidateId
        self.primaryOutcome = primaryOutcome
        self.validationRows = validationRows
        self.nextStepRecommendation = nextStepRecommendation
        self.diagnosticSafe = diagnosticSafe
        self.rollbackEvents = rollbackEvents
        self.supportingRouteRows = supportingRouteRows
        self.limitations = limitations
        self.fallbackFeatureId = fallbackFeatureId
        self.failureReason = failureReason
    }

    public var primaryOutcomeCount: Int {
        1
    }

    public var requiresFallbackPlanning: Bool {
        fallbackFeatureId == "040-speakerphone-recording-fallback-decision"
    }

    public var supportingRoutesCanBroadenPromotionScope: Bool {
        false
    }

    public var decisionLimitations: [String] {
        limitations ?? []
    }

    public var canClaimCleanBuiltInSpeakerphone: Bool {
        primaryOutcome == .acceptedForImmediatePromotion &&
            diagnosticSafe &&
            (rollbackEvents?.isEmpty ?? true) &&
            WebRTCAEC3ScenarioFamily.allImmediatePromotionRequired.allSatisfy { family in
                validationRows.contains {
                    $0.scenarioFamily == family && $0.isAcceptedForImmediatePromotion
                }
            }
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
        "GRAF не может проверить mute в этой встрече. Чтобы локальная речь не попала в запись, используйте Паузу или Остановить в GRAF."
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
    public static let calendarGenericMeetingTitle = "Встреча из календаря"
    public static let calendarJoinPromptMessage =
        "Скоро начало. Можно открыть встречу; запись начнется только вручную."
    public static let calendarJoinOverlapPromptMessage =
        "Сейчас несколько встреч из календаря. Выберите, какую открыть."
    public static let calendarRecordPromptMessage =
        "Встреча началась. Нажмите «Начать запись», когда будете готовы."
    public static let calendarOverlapPromptMessage =
        "Сейчас несколько событий календаря. Выберите событие или начните запись без календарного контекста."
    public static let calendarPromptJoinActionTitle = "Войти во встречу"
    public static let calendarPromptRecordActionTitle = "Начать запись"
    public static let calendarPromptRecordWithoutContextActionTitle = "Начать запись без календаря"
    public static let calendarPromptDismissActionTitle = "Скрыть"
    public static let meetingDetectionSettingsTitle = "Автоопределение встреч"
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

    public static func calendarPromptAccessibilityLabel(title: String, action: String) -> String {
        "\(title). \(action). Запись не начинается автоматически."
    }

    public static func meetingDetectionAccessibilityLabel(status: String, health: String?) -> String {
        [
            meetingDetectionSettingsTitle,
            status,
            health
        ]
        .compactMap { $0 }
        .joined(separator: ". ")
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
    public static let appleProcessingStatus = "systemAudio.appleProcessing.status"
    public static let webRTCAEC3Status = "systemAudio.webRTCAEC3.status"
    public static let webRTCAEC3FallbackStatus = "systemAudio.webRTCAEC3.fallback.status"
    public static let webRTCAEC3RollbackStatus = "systemAudio.webRTCAEC3.rollback.status"
    public static let localRecordingLocation = "systemAudio.localRecording.location"
    public static let calendarPrompt = "systemAudio.calendar.prompt"
    public static let calendarPromptPrimaryButton = "systemAudio.calendar.prompt.primary"
    public static let calendarPromptDismissButton = "systemAudio.calendar.prompt.dismiss"
    public static let meetingDetectionStatus = "systemAudio.meetingDetection.status"
    public static let meetingDetectionSettingsButton = "systemAudio.meetingDetection.settingsButton"
    public static let meetingDetectionRecordingToggle = "systemAudio.meetingDetection.recordingToggle"
    public static let meters = "systemAudio.meters"
    public static let microphoneMeter = "systemAudio.meter.microphone"
    public static let incomingMeter = "systemAudio.meter.incoming"
}
