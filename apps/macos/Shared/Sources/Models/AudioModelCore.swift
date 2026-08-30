import Foundation

public struct PhysicalAudioDevice: Codable, Equatable, Sendable {
    public var id: String
    public var displayName: String
    public var direction: AudioDirection
    public var deviceClass: PhysicalDeviceClass
    public var availabilityState: PhysicalDeviceAvailabilityState
    public var lastVerificationId: String?
    public var lastChangedAt: Date?

    public init(
        id: String,
        displayName: String,
        direction: AudioDirection,
        deviceClass: PhysicalDeviceClass,
        availabilityState: PhysicalDeviceAvailabilityState,
        lastVerificationId: String? = nil,
        lastChangedAt: Date? = nil
    ) {
        self.id = id
        self.displayName = displayName
        self.direction = direction
        self.deviceClass = deviceClass
        self.availabilityState = availabilityState
        self.lastVerificationId = lastVerificationId
        self.lastChangedAt = lastChangedAt
    }
}

public struct BrowserTargetEvidence: Codable, Equatable, Sendable {
    public var target: String
    public var browserBundleID: String?
    public var serviceFamily: String?
    public var hostCategory: String?
    public var patternClass: String?
    public var pageState: BrowserMeetingPageState?
    public var metadataAvailable: Bool?
    public var calendarOrJoinIntentPresent: Bool?
    public var failureReason: String?
    public var checkedAt: Date

    public init(
        target: String,
        browserBundleID: String? = nil,
        serviceFamily: String? = nil,
        hostCategory: String? = nil,
        patternClass: String? = nil,
        pageState: BrowserMeetingPageState? = nil,
        metadataAvailable: Bool? = nil,
        calendarOrJoinIntentPresent: Bool? = nil,
        failureReason: String? = nil,
        checkedAt: Date
    ) {
        self.target = target
        self.browserBundleID = browserBundleID
        self.serviceFamily = serviceFamily
        self.hostCategory = hostCategory
        self.patternClass = patternClass
        self.pageState = pageState
        self.metadataAvailable = metadataAvailable
        self.calendarOrJoinIntentPresent = calendarOrJoinIntentPresent
        self.failureReason = failureReason
        self.checkedAt = checkedAt
    }
}

public struct StreamHealthEvidence: Codable, Equatable, Sendable {
    public var track: AudioTrackRole
    public var checkedAt: Date
    public var healthIntervalMs: Int
    public var capturabilityStatus: CapturabilityStatus
    public var validFrameCount: UInt64
    public var emptyBufferCount: UInt64
    public var droppedFrameCount: UInt64
    public var lastValidFrameAt: Date?
    public var hardFailure: Bool
    public var warningWindowMs: Int

    public init(
        track: AudioTrackRole,
        checkedAt: Date,
        healthIntervalMs: Int = 3000,
        capturabilityStatus: CapturabilityStatus,
        validFrameCount: UInt64,
        emptyBufferCount: UInt64,
        droppedFrameCount: UInt64,
        lastValidFrameAt: Date?,
        hardFailure: Bool,
        warningWindowMs: Int = 30000
    ) {
        self.track = track
        self.checkedAt = checkedAt
        self.healthIntervalMs = healthIntervalMs
        self.capturabilityStatus = capturabilityStatus
        self.validFrameCount = validFrameCount
        self.emptyBufferCount = emptyBufferCount
        self.droppedFrameCount = droppedFrameCount
        self.lastValidFrameAt = lastValidFrameAt
        self.hardFailure = hardFailure
        self.warningWindowMs = warningWindowMs
    }
}

public struct CaptureSession: Codable, Equatable, Sendable {
    public var id: String
    public var mode: CaptureMode
    public var state: CaptureSessionState
    public var sourceAppEligibility: SourceAppEligibility
    public var policySnapshotRef: String?
    public var triggerEvidence: [String: String]
    public var visibleIndicatorState: VisibleIndicatorState
    public var stopActionAvailable: Bool
    public var bufferSummaryId: String?
    public var startedAt: Date?
    public var stoppedAt: Date?
    public var stopReason: RecordingStopReason?
    public var failureCategory: RecordingStartBlocker?

    public init(
        id: String,
        mode: CaptureMode,
        state: CaptureSessionState,
        sourceAppEligibility: SourceAppEligibility,
        policySnapshotRef: String?,
        triggerEvidence: [String: String],
        visibleIndicatorState: VisibleIndicatorState,
        stopActionAvailable: Bool,
        bufferSummaryId: String?,
        startedAt: Date?,
        stoppedAt: Date?,
        stopReason: RecordingStopReason? = nil,
        failureCategory: RecordingStartBlocker? = nil
    ) {
        self.id = id
        self.mode = mode
        self.state = state
        self.sourceAppEligibility = sourceAppEligibility
        self.policySnapshotRef = policySnapshotRef
        self.triggerEvidence = triggerEvidence
        self.visibleIndicatorState = visibleIndicatorState
        self.stopActionAvailable = stopActionAvailable
        self.bufferSummaryId = bufferSummaryId
        self.startedAt = startedAt
        self.stoppedAt = stoppedAt
        self.stopReason = stopReason
        self.failureCategory = failureCategory
    }
}

public struct RecordingPrerequisiteSnapshot: Codable, Equatable, Sendable {
    public var policyAllowsRecording: Bool
    public var microphonePermissionGranted: Bool
    public var systemAudioPermissionGranted: Bool
    public var storageRisk: LocalBufferRiskState
    public var indicatorAvailable: Bool
    public var sourceAppEligibility: SourceAppEligibility
    public var blockedReason: RecordingStartBlocker
    public var recoveryAction: String?
    public var evaluatedAt: Date

    public init(
        policyAllowsRecording: Bool,
        microphonePermissionGranted: Bool,
        systemAudioPermissionGranted: Bool,
        storageRisk: LocalBufferRiskState,
        indicatorAvailable: Bool,
        sourceAppEligibility: SourceAppEligibility,
        blockedReason: RecordingStartBlocker = .none,
        recoveryAction: String? = nil,
        evaluatedAt: Date
    ) {
        self.policyAllowsRecording = policyAllowsRecording
        self.microphonePermissionGranted = microphonePermissionGranted
        self.systemAudioPermissionGranted = systemAudioPermissionGranted
        self.storageRisk = storageRisk
        self.indicatorAvailable = indicatorAvailable
        self.sourceAppEligibility = sourceAppEligibility
        self.blockedReason = blockedReason
        self.recoveryAction = recoveryAction
        self.evaluatedAt = evaluatedAt
    }

    public var allowsRecording: Bool {
        return blockedReason == .none &&
            policyAllowsRecording &&
            microphonePermissionGranted &&
            systemAudioPermissionGranted &&
            storageRisk == .healthy &&
            indicatorAvailable &&
            sourceAppEligibility == .eligible
    }
}

public struct CaptureIndicatorSnapshot: Codable, Equatable, Sendable {
    public var surface: String
    public var state: VisibleIndicatorState
    public var visible: Bool
    public var stopActionAvailable: Bool
    public var accessibilityLabel: String
    public var lastVerifiedAt: Date

    public init(
        surface: String,
        state: VisibleIndicatorState,
        visible: Bool,
        stopActionAvailable: Bool,
        accessibilityLabel: String,
        lastVerifiedAt: Date
    ) {
        self.surface = surface
        self.state = state
        self.visible = visible
        self.stopActionAvailable = stopActionAvailable
        self.accessibilityLabel = accessibilityLabel
        self.lastVerifiedAt = lastVerifiedAt
    }

    public var satisfiesActiveRecordingRequirement: Bool {
        visible &&
            state != .hidden &&
            stopActionAvailable &&
            !accessibilityLabel.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }
}

public struct RecordingEvidenceEvent: Codable, Equatable, Sendable {
    public var eventId: String
    public var sessionId: String
    public var eventType: RecordingEvidenceEventType
    public var occurredAt: Date
    public var initiator: RecordingEvidenceInitiator
    public var captureState: CaptureSessionState
    public var indicatorState: VisibleIndicatorState
    public var stopActionAvailable: Bool
    public var blockedReason: RecordingStartBlocker
    public var recoveryAction: String?
    public var durationMs: Int?
    public var diagnosticSafe: Bool

    public init(
        eventId: String,
        sessionId: String,
        eventType: RecordingEvidenceEventType,
        occurredAt: Date,
        initiator: RecordingEvidenceInitiator,
        captureState: CaptureSessionState,
        indicatorState: VisibleIndicatorState,
        stopActionAvailable: Bool,
        blockedReason: RecordingStartBlocker = .none,
        recoveryAction: String? = nil,
        durationMs: Int? = nil,
        diagnosticSafe: Bool = true
    ) {
        self.eventId = eventId
        self.sessionId = sessionId
        self.eventType = eventType
        self.occurredAt = occurredAt
        self.initiator = initiator
        self.captureState = captureState
        self.indicatorState = indicatorState
        self.stopActionAvailable = stopActionAvailable
        self.blockedReason = blockedReason
        self.recoveryAction = recoveryAction
        self.durationMs = durationMs
        self.diagnosticSafe = diagnosticSafe
    }
}

public struct AudioTrack: Codable, Equatable, Sendable {
    public var id: String
    public var sessionId: String
    public var role: AudioTrackRole
    public var state: AudioTrackState
    public var sampleRate: Double
    public var channelLayout: String
    public var timebase: String
    public var clockDriftMs: Double?
    public var dropoutMarkerIds: [String]
    public var finalizedAt: Date?

    public init(
        id: String,
        sessionId: String,
        role: AudioTrackRole,
        state: AudioTrackState,
        sampleRate: Double,
        channelLayout: String,
        timebase: String,
        clockDriftMs: Double? = nil,
        dropoutMarkerIds: [String] = [],
        finalizedAt: Date? = nil
    ) {
        self.id = id
        self.sessionId = sessionId
        self.role = role
        self.state = state
        self.sampleRate = sampleRate
        self.channelLayout = channelLayout
        self.timebase = timebase
        self.clockDriftMs = clockDriftMs
        self.dropoutMarkerIds = dropoutMarkerIds
        self.finalizedAt = finalizedAt
    }
}

public struct LocalRecordingTrack: Codable, Equatable, Sendable {
    /// At 48 kHz, 100 ms is the maximum tolerated difference between the
    /// canonical timeline and the decoded AAC presentation timeline.
    public static let maximumAACPresentationDeltaFrames: Int64 = 4_800

    public var trackId: String
    public var role: AudioTrackRole
    public var sourceKind: AudioCaptureSourceKind?
    public var mediaScribeField: MediaScribeTrackField
    public var status: LocalRecordingTrackStatus
    public var fileName: String
    public var format: String
    public var sampleRate: Double
    public var channelCount: Int
    public var bitsPerSample: Int
    public var durationMs: Int
    public var byteCount: Int64
    public var sha256: String?
    public var frameCount: Int64
    /// Difference between the decoded AAC presentation frame count and the
    /// shared 48 kHz canonical frame count. This preserves observable encoder
    /// priming/edit-list compensation as package truth instead of hiding it.
    /// It is intentionally absent for historical or unavailable playback.
    public var aacPresentationFrameDelta: Int64?
    public var timelineStartMs: Int
    public var timelineAligned: Bool
    public var failureReason: LocalRecordingFailureReason

    public init(
        trackId: String,
        role: AudioTrackRole,
        sourceKind: AudioCaptureSourceKind? = nil,
        mediaScribeField: MediaScribeTrackField? = nil,
        status: LocalRecordingTrackStatus,
        fileName: String,
        format: String,
        sampleRate: Double,
        channelCount: Int,
        bitsPerSample: Int = 0,
        durationMs: Int,
        byteCount: Int64,
        sha256: String? = nil,
        frameCount: Int64,
        aacPresentationFrameDelta: Int64? = nil,
        timelineStartMs: Int = 0,
        timelineAligned: Bool = false,
        failureReason: LocalRecordingFailureReason = .none
    ) {
        self.trackId = trackId
        self.role = role
        self.sourceKind = sourceKind ?? Self.defaultSourceKind(for: role)
        self.mediaScribeField = mediaScribeField ?? Self.defaultMediaScribeField(for: role)
        self.status = status
        self.fileName = fileName
        self.format = format
        self.sampleRate = sampleRate
        self.channelCount = channelCount
        self.bitsPerSample = bitsPerSample
        self.durationMs = durationMs
        self.byteCount = byteCount
        self.sha256 = sha256
        self.frameCount = frameCount
        self.aacPresentationFrameDelta = aacPresentationFrameDelta
        self.timelineStartMs = timelineStartMs
        self.timelineAligned = timelineAligned
        self.failureReason = failureReason
    }

    public var isComplete: Bool {
        status == .saved && byteCount > 44 && frameCount > 0 && durationMs > 0
    }

    public var isMediaScribeReady: Bool {
        isComplete &&
            format == "wav-pcm-s16le" &&
            sampleRate == 16_000 &&
            channelCount == 1 &&
            bitsPerSample == 16 &&
            timelineStartMs == 0 &&
            timelineAligned
    }

    public var isCanonicalTranscriptionArtifact: Bool {
        role == .mixedMeetingAudio &&
            sourceKind == .canonicalMix &&
            mediaScribeField == .mediaFile &&
            fileName == "meeting-transcription.wav" &&
            hasValidSHA256 &&
            isMediaScribeReady
    }

    public var isReviewPlaybackArtifact: Bool {
        role == .reviewPlayback &&
            sourceKind == .canonicalMix &&
            mediaScribeField == .playbackFile &&
            fileName == "meeting-review.m4a" &&
            hasValidSHA256 &&
            isComplete &&
            format == "m4a-aac-lc" &&
            sampleRate == 48_000 &&
            channelCount == 1 &&
            aacPresentationFrameDelta.map { abs($0) <= Self.maximumAACPresentationDeltaFrames } == true &&
            timelineStartMs == 0 &&
            timelineAligned
    }

    public var hasValidSHA256: Bool {
        guard let sha256, sha256.count == 64 else { return false }
        return sha256.unicodeScalars.allSatisfy {
            ($0.value >= 48 && $0.value <= 57) || ($0.value >= 97 && $0.value <= 102)
        }
    }

    public static func defaultMediaScribeField(for role: AudioTrackRole) -> MediaScribeTrackField {
        switch role {
        case .localMic:
            .micFile
        case .remoteSpeaker:
            .incomingFile
        case .derivedLocalMic:
            .derivedMicFile
        case .mixedMeetingAudio:
            .mediaFile
        case .reviewPlayback:
            .playbackFile
        }
    }

    public static func defaultSourceKind(for role: AudioTrackRole) -> AudioCaptureSourceKind {
        switch role {
        case .localMic, .derivedLocalMic:
            .microphone
        case .remoteSpeaker:
            .systemAudio
        case .mixedMeetingAudio, .reviewPlayback:
            .canonicalMix
        }
    }

}

public enum RecordingTitleStatus: String, Codable, Equatable, Sendable {
    case generated
    case userConfirmed = "user_confirmed"
}

public enum RecordingTitleSource: String, Codable, Equatable, Sendable {
    case userConfirmed = "user_confirmed"
    case appContext = "app_context"
    case generic
}

public enum RecordingTitleConfidence: String, Codable, Equatable, Sendable {
    case high
    case medium
}

public struct RecordingTitleSuppression: Codable, Equatable, Sendable {
    public var source: RecordingTitleSource
    public var reason: String

    public init(source: RecordingTitleSource, reason: String) {
        self.source = source
        self.reason = reason
    }
}

public struct RecordingDisplayMetadata: Codable, Equatable, Sendable {
    public var recordingStartedAt: Date
    public var recordingStoppedAt: Date?
    public var recordingDisplayTimeZoneOffsetMinutes: Int?
    public var title: String
    public var titleStatus: RecordingTitleStatus
    public var titleSource: RecordingTitleSource
    public var titleConfidence: RecordingTitleConfidence
    public var titleGeneratedAt: Date
    public var safeFileBasename: String
    public var stableSuffix: String
    public var suppressedSources: [RecordingTitleSuppression]

    public init(
        recordingStartedAt: Date,
        recordingStoppedAt: Date?,
        recordingDisplayTimeZoneOffsetMinutes: Int? = nil,
        title: String,
        titleStatus: RecordingTitleStatus,
        titleSource: RecordingTitleSource,
        titleConfidence: RecordingTitleConfidence,
        titleGeneratedAt: Date,
        safeFileBasename: String,
        stableSuffix: String,
        suppressedSources: [RecordingTitleSuppression] = []
    ) {
        self.recordingStartedAt = recordingStartedAt
        self.recordingStoppedAt = recordingStoppedAt
        self.recordingDisplayTimeZoneOffsetMinutes = recordingDisplayTimeZoneOffsetMinutes
        self.title = title
        self.titleStatus = titleStatus
        self.titleSource = titleSource
        self.titleConfidence = titleConfidence
        self.titleGeneratedAt = titleGeneratedAt
        self.safeFileBasename = safeFileBasename
        self.stableSuffix = stableSuffix
        self.suppressedSources = suppressedSources
    }
}

public struct EchoProcessorDescriptor: Codable, Equatable, Sendable {
    public static let webrtcAEC3 = EchoProcessorDescriptor(
        algorithm: "webrtc_aec3_m131",
        libraryVersion: "2.1",
        sourceCommit: "846fe90a289f58b7c9303a635142aa2c7caa93e5",
        sampleRate: 48_000,
        channels: 1,
        frameSamples: 480,
        streamDelayMs: 0,
        optionalProcessingEnabled: false
    )

    public var algorithm: String
    public var libraryVersion: String
    public var sourceCommit: String
    public var sampleRate: Int
    public var channels: Int
    public var frameSamples: Int
    public var streamDelayMs: Int
    public var optionalProcessingEnabled: Bool

    public init(
        algorithm: String,
        libraryVersion: String,
        sourceCommit: String,
        sampleRate: Int,
        channels: Int,
        frameSamples: Int,
        streamDelayMs: Int,
        optionalProcessingEnabled: Bool
    ) {
        self.algorithm = algorithm
        self.libraryVersion = libraryVersion
        self.sourceCommit = sourceCommit
        self.sampleRate = sampleRate
        self.channels = channels
        self.frameSamples = frameSamples
        self.streamDelayMs = streamDelayMs
        self.optionalProcessingEnabled = optionalProcessingEnabled
    }
}

public enum EchoProcessingHealthState: String, Codable, Equatable, Sendable {
    case ready
    case active
    case completed
    case degraded
    case failed
}

public enum EchoProcessingFailureReason: String, Codable, Equatable, Sendable {
    case processorUnavailable = "processor_unavailable"
    case processorConfigurationFailed = "processor_configuration_failed"
    case renderReferenceMissing = "render_reference_missing"
    case processReverseFailed = "process_reverse_failed"
    case processCaptureFailed = "process_capture_failed"
    case routeChanged = "route_changed"
    case formatChanged = "format_changed"
    case timebaseChanged = "timebase_changed"
    case ptsDiscontinuity = "pts_discontinuity"
    case sourceStopped = "source_stopped"
    case sourceOverflow = "source_overflow"
    case nonFiniteSamples = "non_finite_samples"
    case finalizationFailed = "finalization_failed"
}

public struct EchoProcessingHealth: Codable, Equatable, Sendable {
    public var state: EchoProcessingHealthState
    public var reason: EchoProcessingFailureReason?
    public var processedFrameCount: Int64
    public var processErrorCount: Int
    public var resetCount: Int
    public var ptsGapCount: Int
    public var estimatedDriftPpm: Double?
    public var hostUnderrunCount: Int
    public var hostOverrunCount: Int
    public var clippedSampleCount: Int64
    public var nonFiniteSampleCount: Int64
    public var aecDelayMs: Int?
    public var echoReturnLossDb: Double?
    public var echoReturnLossEnhancementDb: Double?
    public var processingTimeP95Ms: Double?

    public init(
        state: EchoProcessingHealthState,
        reason: EchoProcessingFailureReason? = nil,
        processedFrameCount: Int64 = 0,
        processErrorCount: Int = 0,
        resetCount: Int = 0,
        ptsGapCount: Int = 0,
        estimatedDriftPpm: Double? = nil,
        hostUnderrunCount: Int = 0,
        hostOverrunCount: Int = 0,
        clippedSampleCount: Int64 = 0,
        nonFiniteSampleCount: Int64 = 0,
        aecDelayMs: Int? = nil,
        echoReturnLossDb: Double? = nil,
        echoReturnLossEnhancementDb: Double? = nil,
        processingTimeP95Ms: Double? = nil
    ) {
        self.state = state
        self.reason = reason
        self.processedFrameCount = max(0, processedFrameCount)
        self.processErrorCount = max(0, processErrorCount)
        self.resetCount = max(0, resetCount)
        self.ptsGapCount = max(0, ptsGapCount)
        self.estimatedDriftPpm = estimatedDriftPpm?.isFinite == true ? estimatedDriftPpm : nil
        self.hostUnderrunCount = max(0, hostUnderrunCount)
        self.hostOverrunCount = max(0, hostOverrunCount)
        self.clippedSampleCount = max(0, clippedSampleCount)
        self.nonFiniteSampleCount = max(0, nonFiniteSampleCount)
        self.aecDelayMs = aecDelayMs
        self.echoReturnLossDb = echoReturnLossDb?.isFinite == true ? echoReturnLossDb : nil
        self.echoReturnLossEnhancementDb = echoReturnLossEnhancementDb?.isFinite == true
            ? echoReturnLossEnhancementDb
            : nil
        if let processingTimeP95Ms, processingTimeP95Ms.isFinite, processingTimeP95Ms >= 0 {
            self.processingTimeP95Ms = processingTimeP95Ms
        } else {
            self.processingTimeP95Ms = nil
        }
    }

    public var permitsNormalPackage: Bool {
        state == .completed && reason == nil && processErrorCount == 0 && nonFiniteSampleCount == 0
    }
}

public struct LocalRecordingManifest: Codable, Equatable, Sendable {
    public static let schemaVersion = "local-recording-manifest.v5"
    public static let canonicalMixProfileVersion = "canonical-mix.v1"
    public static let legacySchemaVersion = "local-recording-manifest.v3"
    public static let historicCompatibilitySchemaVersions: Set<String> = [
        "local-recording-manifest.v3",
        "local-recording-manifest.v4"
    ]

    public var schemaVersion: String
    public var sessionId: String
    public var createdAt: Date
    public var startedAt: Date
    public var stoppedAt: Date
    public var finalizedAt: Date?
    public var status: LocalRecordingSessionStatus
    public var directoryId: String
    public var manifestFileName: String
    public var transcriptionReadiness: TranscriptionReadinessState
    public var mediaScribeSourceMode: String
    public var canonicalMixProfile: String?
    public var tracks: [LocalRecordingTrack]
    public var externalEgressStarted: Bool
    public var transcriptionStarted: Bool
    public var diagnosticSafe: Bool
    public var localDeletionRegistered: Bool
    public var failureReason: LocalRecordingFailureReason
    /// Safe machine-readable capture/finalization detail. It contains no
    /// audio, transcript content, credentials, or local paths.
    public var captureFailureCode: String?
    public var durationDifferenceSeconds: Double
    public var scopeApproval: CaptureScopeApproval?
    public var permissions: SystemAudioPermissionSnapshot?
    public var microphoneSelection: RecordingMicrophoneSelection?
    public var microphoneStream: AppOwnedMicrophoneStreamSession?
    public var microphoneStreamHealth: MicrophoneStreamHealth?
    public var captureHealth: CaptureHealthSnapshot?
    public var privacySegments: [ProductPrivacySegment]?
    public var meetingMuteTruth: MuteTruthDecision?
    public var meetingMuteTruthEvidence: [MeetingMuteTruthEvidence]?
    public var targetMuteCapability: TargetMuteCapability?
    public var limitationCopyShownAt: Date?
    public var recordingMetadata: RecordingDisplayMetadata?
    public var echoProcessor: EchoProcessorDescriptor?
    public var echoProcessingHealth: EchoProcessingHealth?

    public init(
        schemaVersion: String = Self.schemaVersion,
        sessionId: String,
        createdAt: Date,
        startedAt: Date,
        stoppedAt: Date,
        finalizedAt: Date? = nil,
        status: LocalRecordingSessionStatus,
        directoryId: String,
        manifestFileName: String = "manifest.json",
        transcriptionReadiness: TranscriptionReadinessState = .degraded,
        mediaScribeSourceMode: String = "single_wav_v1",
        canonicalMixProfile: String? = Self.canonicalMixProfileVersion,
        tracks: [LocalRecordingTrack],
        externalEgressStarted: Bool = false,
        transcriptionStarted: Bool = false,
        diagnosticSafe: Bool = true,
        localDeletionRegistered: Bool = false,
        failureReason: LocalRecordingFailureReason = .none,
        captureFailureCode: String? = nil,
        durationDifferenceSeconds: Double = 0,
        scopeApproval: CaptureScopeApproval? = nil,
        permissions: SystemAudioPermissionSnapshot? = nil,
        microphoneSelection: RecordingMicrophoneSelection? = nil,
        microphoneStream: AppOwnedMicrophoneStreamSession? = nil,
        microphoneStreamHealth: MicrophoneStreamHealth? = nil,
        captureHealth: CaptureHealthSnapshot? = nil,
        privacySegments: [ProductPrivacySegment]? = nil,
        meetingMuteTruth: MuteTruthDecision? = nil,
        meetingMuteTruthEvidence: [MeetingMuteTruthEvidence]? = nil,
        targetMuteCapability: TargetMuteCapability? = nil,
        limitationCopyShownAt: Date? = nil,
        recordingMetadata: RecordingDisplayMetadata? = nil,
        echoProcessor: EchoProcessorDescriptor? = nil,
        echoProcessingHealth: EchoProcessingHealth? = nil
    ) {
        self.schemaVersion = schemaVersion
        self.sessionId = sessionId
        self.createdAt = createdAt
        self.startedAt = startedAt
        self.stoppedAt = stoppedAt
        self.finalizedAt = finalizedAt
        self.status = status
        self.directoryId = directoryId
        self.manifestFileName = manifestFileName
        self.transcriptionReadiness = transcriptionReadiness
        self.mediaScribeSourceMode = mediaScribeSourceMode
        self.canonicalMixProfile = canonicalMixProfile
        self.tracks = tracks
        self.externalEgressStarted = externalEgressStarted
        self.transcriptionStarted = transcriptionStarted
        self.diagnosticSafe = diagnosticSafe
        self.localDeletionRegistered = localDeletionRegistered
        self.failureReason = failureReason
        self.captureFailureCode = captureFailureCode
        self.durationDifferenceSeconds = durationDifferenceSeconds
        self.scopeApproval = scopeApproval
        self.permissions = permissions
        self.microphoneSelection = microphoneSelection
        self.microphoneStream = microphoneStream
        self.microphoneStreamHealth = microphoneStreamHealth
        self.captureHealth = captureHealth
        self.privacySegments = privacySegments
        self.meetingMuteTruth = meetingMuteTruth
        self.meetingMuteTruthEvidence = meetingMuteTruthEvidence
        self.targetMuteCapability = targetMuteCapability
        self.limitationCopyShownAt = limitationCopyShownAt
        self.recordingMetadata = recordingMetadata
        self.echoProcessor = echoProcessor
        self.echoProcessingHealth = echoProcessingHealth
    }

    public var isComplete: Bool {
        guard status == .saved,
              transcriptionReadiness == .ready,
              !externalEgressStarted,
              !transcriptionStarted,
              failureReason == .none,
              scopeApproval?.isAcceptedForMeetingRecording == true,
              permissions?.allowsAcceptedRecording == true,
              durationDifferenceSeconds <= 3
        else {
            return false
        }

        if isV5Package {
            let v5Roles: Set<AudioTrackRole> = [.mixedMeetingAudio, .reviewPlayback]
            guard tracks.count == v5Roles.count,
                  Set(tracks.map(\.role)) == v5Roles,
                  let media = tracks.first(where: { $0.role == .mixedMeetingAudio }),
                  let playback = tracks.first(where: { $0.role == .reviewPlayback }),
                  durationDifferenceSeconds <= 0.1
            else {
                return false
            }
            return media.isCanonicalTranscriptionArtifact && playback.isReviewPlaybackArtifact
        }

        guard isHistoricCompatibilityPackage else {
            return false
        }

        if mediaScribeSourceMode == "dual" {
            return Set(tracks.map(\.role)) == Set([.localMic, .remoteSpeaker]) &&
                tracks.allSatisfy { $0.sourceKind != nil } &&
                tracks.allSatisfy(\.isMediaScribeReady)
        }

        if mediaScribeSourceMode == "derived_dual" {
            return tracks.contains(where: { $0.role == .derivedLocalMic && $0.isMediaScribeReady }) &&
                tracks.contains(where: { $0.role == .remoteSpeaker && $0.isMediaScribeReady })
        }

        return false
    }

    public var isV5Package: Bool {
        schemaVersion == Self.schemaVersion &&
            mediaScribeSourceMode == "single_wav_v1" &&
            canonicalMixProfile == Self.canonicalMixProfileVersion
    }

    public var isHistoricCompatibilityPackage: Bool {
        Self.historicCompatibilitySchemaVersions.contains(schemaVersion) &&
            ["dual", "derived_dual"].contains(mediaScribeSourceMode)
    }

    public static func transcriptionReadiness(
        forSchemaVersion schemaVersion: String,
        tracks: [LocalRecordingTrack] = []
    ) -> TranscriptionReadinessState {
        guard schemaVersion == Self.schemaVersion ||
              Self.historicCompatibilitySchemaVersions.contains(schemaVersion)
        else {
            return .historicalPackage
        }
        guard schemaVersion != Self.schemaVersion else {
            return .degraded
        }
        if tracks.contains(where: { $0.role == .localMic && $0.isMediaScribeReady }) &&
            tracks.contains(where: { $0.role == .remoteSpeaker && $0.isMediaScribeReady }) {
            return .ready
        }
        if tracks.contains(where: { $0.role == .derivedLocalMic && $0.isMediaScribeReady }) &&
            tracks.contains(where: { $0.role == .remoteSpeaker && $0.isMediaScribeReady }) {
            return .ready
        }
        return .degraded
    }
}

public struct LocalBufferItem: Codable, Equatable, Sendable {
    public var id: String
    public var sessionId: String
    public var trackId: String?
    public var artifactType: LocalBufferArtifactType
    public var encryptedSizeBytes: Int64
    public var createdAt: Date
    public var retentionDeadline: Date
    public var uploadState: UploadState
    public var purgeState: PurgeState
    public var deletionReportState: DeletionReportState

    public init(
        id: String,
        sessionId: String,
        trackId: String?,
        artifactType: LocalBufferArtifactType,
        encryptedSizeBytes: Int64,
        createdAt: Date,
        retentionDeadline: Date,
        uploadState: UploadState,
        purgeState: PurgeState,
        deletionReportState: DeletionReportState
    ) {
        self.id = id
        self.sessionId = sessionId
        self.trackId = trackId
        self.artifactType = artifactType
        self.encryptedSizeBytes = encryptedSizeBytes
        self.createdAt = createdAt
        self.retentionDeadline = retentionDeadline
        self.uploadState = uploadState
        self.purgeState = purgeState
        self.deletionReportState = deletionReportState
    }
}

public enum DesktopUploadTransportRole: String, Codable, CaseIterable, Sendable {
    case microphone
    case system
    case media
    case manifest
    case playback

    public static func role(forLocalTrackRole role: AudioTrackRole) -> DesktopUploadTransportRole? {
        switch role {
        case .localMic:
            return .microphone
        case .remoteSpeaker:
            return .system
        case .mixedMeetingAudio:
            return .media
        case .reviewPlayback:
            return .playback
        case .derivedLocalMic:
            return nil
        }
    }
}

public enum UploadItemState: String, Codable, CaseIterable, Sendable {
    case saving
    case queued
    case uploading
    case retrying
    case uploaded
    case degraded
    case failed
    case blocked
    case terminalDeleted = "terminal_deleted"

    public var isTerminal: Bool {
        switch self {
        case .uploaded, .failed, .terminalDeleted:
            return true
        case .saving, .queued, .uploading, .retrying, .degraded, .blocked:
            return false
        }
    }

    public var canAutomaticallyRetry: Bool {
        switch self {
        case .queued, .retrying, .degraded:
            return true
        case .saving, .uploading, .uploaded, .failed, .blocked, .terminalDeleted:
            return false
        }
    }

    public var displayName: String {
        switch self {
        case .saving:
            return "Сохраняется"
        case .queued:
            return "Ожидает загрузки"
        case .uploading:
            return "Загружается"
        case .retrying:
            return "Повторяем загрузку"
        case .uploaded:
            return "Загружено"
        case .degraded:
            return "Загрузка с ограничениями"
        case .failed:
            return "Загрузка не удалась"
        case .blocked:
            return "Нужна проверка"
        case .terminalDeleted:
            return "Закрыто"
        }
    }

    public var sortPriority: Int {
        switch self {
        case .saving:
            return 0
        case .uploading:
            return 1
        case .retrying:
            return 2
        case .blocked, .degraded:
            return 3
        case .queued:
            return 4
        case .failed:
            return 5
        case .uploaded:
            return 6
        case .terminalDeleted:
            return 7
        }
    }
}

public enum UploadFailureCategory: String, Codable, CaseIterable, Sendable {
    case none
    case network
    case authSession = "auth_session"
    case serverValidation = "server_validation"
    case schemaIncompatibility = "schema_incompatibility"
    case localResource = "local_resource"
    case storageQuota = "storage_quota"
    case cancelled
    case unknown

    public var isAutomaticallyRetryable: Bool {
        switch self {
        case .none, .network, .storageQuota, .unknown:
            return true
        case .authSession, .serverValidation, .schemaIncompatibility, .localResource, .cancelled:
            return false
        }
    }
}

public enum UploadRetryMode: String, Codable, CaseIterable, Sendable {
    case automatic
    case manualOnly = "manual_only"
    case terminal

    public var displayName: String {
        switch self {
        case .automatic:
            return "Автоповтор"
        case .manualOnly:
            return "Ручная проверка"
        case .terminal:
            return "Завершено"
        }
    }
}

public struct UploadTrackCompleteness: Codable, Equatable, Sendable {
    public var transportRole: DesktopUploadTransportRole
    public var fileName: String
    public var present: Bool
    public var byteCount: Int64
    public var sha256: String?
    public var durationSeconds: Int?

    public init(
        transportRole: DesktopUploadTransportRole,
        fileName: String,
        present: Bool,
        byteCount: Int64,
        sha256: String? = nil,
        durationSeconds: Int? = nil
    ) {
        self.transportRole = transportRole
        self.fileName = fileName
        self.present = present
        self.byteCount = byteCount
        self.sha256 = sha256
        self.durationSeconds = durationSeconds
    }

    public var uploadable: Bool {
        present && byteCount > 0 && sha256?.count == 64
    }
}

public struct ArtifactCompletenessProfile: Codable, Equatable, Sendable {
    public var schemaVersion: String
    public var manifestPresent: Bool
    public var microphonePresent: Bool
    public var systemAudioPresent: Bool
    public var manifestSha256: String?
    public var microphoneSha256: String?
    public var systemAudioSha256: String?
    public var manifestSizeBytes: Int64
    public var microphoneSizeBytes: Int64
    public var systemAudioSizeBytes: Int64
    public var durationSeconds: Int
    public var trackCompleteness: [UploadTrackCompleteness]
    public var isUploadable: Bool
    public var qualityWarningReason: String?

    public init(
        schemaVersion: String,
        manifestPresent: Bool,
        microphonePresent: Bool,
        systemAudioPresent: Bool,
        manifestSha256: String?,
        microphoneSha256: String?,
        systemAudioSha256: String?,
        manifestSizeBytes: Int64,
        microphoneSizeBytes: Int64,
        systemAudioSizeBytes: Int64,
        durationSeconds: Int,
        trackCompleteness: [UploadTrackCompleteness],
        isUploadable: Bool,
        qualityWarningReason: String? = nil
    ) {
        self.schemaVersion = schemaVersion
        self.manifestPresent = manifestPresent
        self.microphonePresent = microphonePresent
        self.systemAudioPresent = systemAudioPresent
        self.manifestSha256 = manifestSha256
        self.microphoneSha256 = microphoneSha256
        self.systemAudioSha256 = systemAudioSha256
        self.manifestSizeBytes = manifestSizeBytes
        self.microphoneSizeBytes = microphoneSizeBytes
        self.systemAudioSizeBytes = systemAudioSizeBytes
        self.durationSeconds = max(1, durationSeconds)
        self.trackCompleteness = trackCompleteness
        self.isUploadable = isUploadable
        self.qualityWarningReason = qualityWarningReason
    }

    public func totalUploadBytes(limitedToRoles roles: Set<String>? = nil) -> Int64 {
        let legacySizes: [DesktopUploadTransportRole: Int64] = [
            .manifest: manifestSizeBytes,
            .microphone: microphoneSizeBytes,
            .system: systemAudioSizeBytes
        ]
        let roleMatches: (DesktopUploadTransportRole) -> Bool = { role in
            roles?.contains(role.rawValue) ?? true
        }
        if !trackCompleteness.isEmpty {
            let total = trackCompleteness.reduce(Int64(0)) { result, track in
                guard roleMatches(track.transportRole) else { return result }
                return result + max(0, track.byteCount)
            }
            if total > 0 || roles == nil {
                return total
            }
        }
        return legacySizes.reduce(Int64(0)) { result, item in
            guard roleMatches(item.key) else { return result }
            return result + max(0, item.value)
        }
    }

    public var totalUploadBytes: Int64 {
        totalUploadBytes(limitedToRoles: nil)
    }

    public var isV5Package: Bool {
        let requiredFiles: [DesktopUploadTransportRole: String] = [
            .manifest: "manifest.json",
            .media: "meeting-transcription.wav",
            .playback: "meeting-review.m4a"
        ]
        guard schemaVersion == LocalRecordingManifest.schemaVersion,
              trackCompleteness.count == requiredFiles.count
        else {
            return false
        }
        var tracksByRole: [DesktopUploadTransportRole: UploadTrackCompleteness] = [:]
        for track in trackCompleteness {
            guard tracksByRole[track.transportRole] == nil else { return false }
            tracksByRole[track.transportRole] = track
        }
        return requiredFiles.allSatisfy { role, fileName in
            tracksByRole[role]?.fileName == fileName
        }
    }
}

public struct RetryRecord: Codable, Equatable, Sendable {
    public var attemptNumber: Int
    public var startedAt: Date
    public var finishedAt: Date?
    public var stateBefore: UploadItemState
    public var stateAfter: UploadItemState
    public var failureCategory: UploadFailureCategory
    public var failureReason: String?
    public var acceptedBytesByTrack: [String: Int64]
    public var nextRetryAt: Date?

    public init(
        attemptNumber: Int,
        startedAt: Date,
        finishedAt: Date? = nil,
        stateBefore: UploadItemState,
        stateAfter: UploadItemState,
        failureCategory: UploadFailureCategory,
        failureReason: String? = nil,
        acceptedBytesByTrack: [String: Int64] = [:],
        nextRetryAt: Date? = nil
    ) {
        self.attemptNumber = max(0, attemptNumber)
        self.startedAt = startedAt
        self.finishedAt = finishedAt
        self.stateBefore = stateBefore
        self.stateAfter = stateAfter
        self.failureCategory = failureCategory
        self.failureReason = failureReason
        self.acceptedBytesByTrack = acceptedBytesByTrack
        self.nextRetryAt = nextRetryAt
    }
}

public struct ServerTruthFingerprint: Codable, Equatable, Sendable {
    public var meetingId: String?
    public var mediaRevisionId: String?
    public var uploadSessionId: String?
    public var serverStatus: String?
    public var processingStatus: String?
    public var acceptedBytesByTrack: [String: Int64]
    public var requiredTrackSha256: [String: String]
    public var expectedTrackRoles: [String]?
    public var finalizedAt: Date?
    public var desktopTruthRule: String?
    public var deletionState: String?
    public var accessState: String?
    public var uploadStatus: String?
    public var processingReasonCode: String?
    public var reviewAvailable: Bool?
    public var reviewStatus: String?
    public var conflictReason: String?
    public var nextAction: String?

    public init(
        meetingId: String? = nil,
        mediaRevisionId: String? = nil,
        uploadSessionId: String? = nil,
        serverStatus: String? = nil,
        processingStatus: String? = nil,
        acceptedBytesByTrack: [String: Int64] = [:],
        requiredTrackSha256: [String: String] = [:],
        expectedTrackRoles: [String]? = nil,
        finalizedAt: Date? = nil,
        desktopTruthRule: String? = nil,
        deletionState: String? = nil,
        accessState: String? = nil,
        uploadStatus: String? = nil,
        processingReasonCode: String? = nil,
        reviewAvailable: Bool? = nil,
        reviewStatus: String? = nil,
        conflictReason: String? = nil,
        nextAction: String? = nil
    ) {
        self.meetingId = meetingId
        self.mediaRevisionId = mediaRevisionId
        self.uploadSessionId = uploadSessionId
        self.serverStatus = serverStatus
        self.processingStatus = processingStatus
        self.acceptedBytesByTrack = acceptedBytesByTrack
        self.requiredTrackSha256 = requiredTrackSha256
        self.expectedTrackRoles = expectedTrackRoles
        self.finalizedAt = finalizedAt
        self.desktopTruthRule = desktopTruthRule
        self.deletionState = deletionState
        self.accessState = accessState
        self.uploadStatus = uploadStatus
        self.processingReasonCode = processingReasonCode
        self.reviewAvailable = reviewAvailable
        self.reviewStatus = reviewStatus
        self.conflictReason = conflictReason
        self.nextAction = nextAction
    }

    public func hasAcceptedAll(profile: ArtifactCompletenessProfile) -> Bool {
        let roles = uploadProgressRoles
        let tracks = profile.trackCompleteness.filter { roles?.contains($0.transportRole.rawValue) ?? true }
        if !tracks.isEmpty {
            for track in tracks {
                guard acceptedBytesByTrack[track.transportRole.rawValue, default: 0] >= track.byteCount else {
                    return false
                }
            }
            return true
        }
        let legacySizes: [(String, Int64)] = [
            (DesktopUploadTransportRole.manifest.rawValue, profile.manifestSizeBytes),
            (DesktopUploadTransportRole.microphone.rawValue, profile.microphoneSizeBytes),
            (DesktopUploadTransportRole.system.rawValue, profile.systemAudioSizeBytes)
        ]
        for (role, byteCount) in legacySizes where roles?.contains(role) ?? true {
            guard acceptedBytesByTrack[role, default: 0] >= max(0, byteCount) else {
                return false
            }
        }
        return true
    }

    public var uploadProgressRoles: Set<String>? {
        if let expectedTrackRoles, !expectedTrackRoles.isEmpty {
            return Set(expectedTrackRoles)
        }
        if !requiredTrackSha256.isEmpty {
            return Set(requiredTrackSha256.keys)
        }
        return nil
    }

    /// Keeps progress truthful when a delayed response from the same server upload
    /// session arrives after a later accepted part. A different session is a real
    /// restart, so its accepted-byte counter intentionally replaces the old one.
    public func mergingConfirmedProgress(_ reported: ServerTruthFingerprint) -> ServerTruthFingerprint {
        guard uploadSessionId == nil ||
            reported.uploadSessionId == nil ||
            uploadSessionId == reported.uploadSessionId
        else {
            return reported
        }

        var merged = reported
        merged.meetingId = reported.meetingId ?? meetingId
        merged.mediaRevisionId = reported.mediaRevisionId ?? mediaRevisionId
        merged.uploadSessionId = reported.uploadSessionId ?? uploadSessionId
        merged.serverStatus = reported.serverStatus ?? serverStatus
        merged.processingStatus = reported.processingStatus ?? processingStatus
        merged.requiredTrackSha256 = reported.requiredTrackSha256.isEmpty
            ? requiredTrackSha256
            : reported.requiredTrackSha256
        if reported.expectedTrackRoles?.isEmpty ?? true {
            merged.expectedTrackRoles = expectedTrackRoles
        }
        merged.finalizedAt = reported.finalizedAt ?? finalizedAt
        merged.desktopTruthRule = reported.desktopTruthRule ?? desktopTruthRule
        merged.deletionState = reported.deletionState ?? deletionState
        merged.accessState = reported.accessState ?? accessState
        merged.uploadStatus = reported.uploadStatus ?? uploadStatus
        merged.processingReasonCode = reported.processingReasonCode ?? processingReasonCode
        merged.reviewAvailable = reported.reviewAvailable ?? reviewAvailable
        merged.reviewStatus = reported.reviewStatus ?? reviewStatus
        merged.conflictReason = reported.conflictReason ?? conflictReason
        merged.nextAction = reported.nextAction ?? nextAction
        for (role, acceptedBytes) in acceptedBytesByTrack {
            merged.acceptedBytesByTrack[role] = max(
                max(0, acceptedBytes),
                max(0, merged.acceptedBytesByTrack[role, default: 0])
            )
        }
        return merged
    }
}

public enum DesktopSyncConflictState: String, Codable, CaseIterable, Sendable {
    case none
    case localFilesMissing = "local_files_missing"
    case localChecksumChanged = "local_checksum_changed"
    case queueDocumentMalformed = "queue_document_malformed"
    case queueSchemaMigrationBlocked = "queue_schema_migration_blocked"
    case serverMeetingDeleted = "server_meeting_deleted"
    case accessRevoked = "access_revoked"
    case authRequired = "auth_required"
    case staleDeviceIdentity = "stale_device_identity"
    case serverExpectedMetadataMismatch = "server_expected_metadata_mismatch"
    case serverRangesInconsistent = "server_ranges_inconsistent"
    case uploadSessionExpired = "upload_session_expired"
    case processingFailed = "processing_failed"
    case processingBlocked = "processing_blocked"
    case retentionExpired = "retention_expired"
    case dependencyUnavailable = "dependency_unavailable"

    public var blocksReviewDestination: Bool {
        switch self {
        case .serverMeetingDeleted, .accessRevoked, .authRequired, .staleDeviceIdentity,
             .serverExpectedMetadataMismatch, .dependencyUnavailable:
            return true
        case .none, .localFilesMissing, .localChecksumChanged, .queueDocumentMalformed,
             .queueSchemaMigrationBlocked, .serverRangesInconsistent, .uploadSessionExpired,
             .processingFailed, .processingBlocked, .retentionExpired:
            return false
        }
    }

    public var safeDetail: String? {
        switch self {
        case .none:
            return nil
        case .localFilesMissing, .localChecksumChanged:
            return "локальные файлы изменились, нужна проверка"
        case .queueDocumentMalformed, .queueSchemaMigrationBlocked:
            return "очередь загрузки требует проверки"
        case .serverMeetingDeleted:
            return "запись удалена на сервере, нужна проверка"
        case .accessRevoked, .authRequired, .staleDeviceIdentity:
            return "нужно заново войти или проверить доступ"
        case .serverExpectedMetadataMismatch, .serverRangesInconsistent:
            return "данные на устройстве и сервере не совпадают"
        case .uploadSessionExpired:
            return "сеанс загрузки устарел, создадим новый"
        case .processingFailed, .processingBlocked:
            return "обработка на сервере остановлена"
        case .retentionExpired:
            return "истек срок автоматической отправки"
        case .dependencyUnavailable:
            return "сервер временно недоступен, повторим позже"
        }
    }
}

public enum RetentionDecisionValue: String, Codable, CaseIterable, Sendable {
    case retain
    case manualOnly = "manual_only"
    case terminalUploaded = "terminal_uploaded"
    case terminalFailed = "terminal_failed"
    case terminalDeleted = "terminal_deleted"
}

public struct RetentionDecision: Codable, Equatable, Sendable {
    public var decision: RetentionDecisionValue
    public var decidedAt: Date
    public var reason: String
    public var localArtifactsRetained: Bool
    public var policyReference: String

    public init(
        decision: RetentionDecisionValue,
        decidedAt: Date,
        reason: String,
        localArtifactsRetained: Bool,
        policyReference: String
    ) {
        self.decision = decision
        self.decidedAt = decidedAt
        self.reason = reason
        self.localArtifactsRetained = localArtifactsRetained
        self.policyReference = policyReference
    }
}

public enum DesktopSupportIncidentSubmissionStatus: String, Codable, CaseIterable, Sendable {
    case notSent = "not_sent"
    case sending
    case pendingSync = "pending_sync"
    case sent
    case failedWithCopyFallback = "failed_with_copy_fallback"
    case unavailable
}

public struct DesktopSupportIncidentSubmissionState: Codable, Equatable, Sendable {
    public var state: DesktopSupportIncidentSubmissionStatus
    public var localReportFingerprint: String?
    public var dedupeKey: String?
    public var incidentNumber: String?
    public var githubIssueNumber: Int?
    public var lastSubmissionAttemptAt: Date?
    public var lastFailureCategory: String?
    public var lastFailureCode: String?
    public var copyFallbackAvailable: Bool
    public var accessibilityLabel: String

    public init(
        state: DesktopSupportIncidentSubmissionStatus,
        localReportFingerprint: String? = nil,
        dedupeKey: String? = nil,
        incidentNumber: String? = nil,
        githubIssueNumber: Int? = nil,
        lastSubmissionAttemptAt: Date? = nil,
        lastFailureCategory: String? = nil,
        lastFailureCode: String? = nil,
        copyFallbackAvailable: Bool = true,
        accessibilityLabel: String? = nil
    ) {
        self.state = state
        self.localReportFingerprint = localReportFingerprint
        self.dedupeKey = dedupeKey
        self.incidentNumber = incidentNumber
        self.githubIssueNumber = githubIssueNumber
        self.lastSubmissionAttemptAt = lastSubmissionAttemptAt
        self.lastFailureCategory = lastFailureCategory
        self.lastFailureCode = lastFailureCode
        self.copyFallbackAvailable = copyFallbackAvailable
        self.accessibilityLabel = accessibilityLabel ?? Self.defaultAccessibilityLabel(
            state: state,
            incidentNumber: incidentNumber
        )
    }

    public static func sending(
        reportFingerprint: String,
        dedupeKey: String,
        attemptedAt: Date
    ) -> DesktopSupportIncidentSubmissionState {
        DesktopSupportIncidentSubmissionState(
            state: .sending,
            localReportFingerprint: reportFingerprint,
            dedupeKey: dedupeKey,
            lastSubmissionAttemptAt: attemptedAt,
            accessibilityLabel: "Отправляем запрос в поддержку…"
        )
    }

    public static func sent(
        reportFingerprint: String,
        dedupeKey: String,
        incidentNumber: String,
        githubIssueNumber: Int?,
        attemptedAt: Date,
        copyFallbackAvailable: Bool
    ) -> DesktopSupportIncidentSubmissionState {
        DesktopSupportIncidentSubmissionState(
            state: .sent,
            localReportFingerprint: reportFingerprint,
            dedupeKey: dedupeKey,
            incidentNumber: incidentNumber,
            githubIssueNumber: githubIssueNumber,
            lastSubmissionAttemptAt: attemptedAt,
            copyFallbackAvailable: copyFallbackAvailable,
            accessibilityLabel: "Запрос принят и передан в поддержку. Номер: \(incidentNumber)."
        )
    }

    public static func pendingSync(
        reportFingerprint: String,
        dedupeKey: String,
        incidentNumber: String,
        attemptedAt: Date,
        copyFallbackAvailable: Bool,
        failureCode: String? = nil
    ) -> DesktopSupportIncidentSubmissionState {
        DesktopSupportIncidentSubmissionState(
            state: .pendingSync,
            localReportFingerprint: reportFingerprint,
            dedupeKey: dedupeKey,
            incidentNumber: incidentNumber,
            lastSubmissionAttemptAt: attemptedAt,
            lastFailureCategory: failureCode == nil ? nil : UploadFailureCategory.network.rawValue,
            lastFailureCode: failureCode,
            copyFallbackAvailable: copyFallbackAvailable,
            accessibilityLabel: "Запрос принят сервером. Синхронизация с поддержкой ожидает проверки. Номер: \(incidentNumber)."
        )
    }

    public static func failedWithCopyFallback(
        reportFingerprint: String,
        dedupeKey: String,
        attemptedAt: Date,
        failureCategory: String,
        failureCode: String
    ) -> DesktopSupportIncidentSubmissionState {
        DesktopSupportIncidentSubmissionState(
            state: .failedWithCopyFallback,
            localReportFingerprint: reportFingerprint,
            dedupeKey: dedupeKey,
            lastSubmissionAttemptAt: attemptedAt,
            lastFailureCategory: failureCategory,
            lastFailureCode: failureCode,
            copyFallbackAvailable: true,
            accessibilityLabel: "Запрос не принят. Проверьте подключение или скопируйте безопасную сводку."
        )
    }

    public static func unavailable(attemptedAt: Date) -> DesktopSupportIncidentSubmissionState {
        DesktopSupportIncidentSubmissionState(
            state: .unavailable,
            lastSubmissionAttemptAt: attemptedAt,
            copyFallbackAvailable: false,
            accessibilityLabel: "Поддержка сейчас недоступна. Попробуйте позже."
        )
    }

    private static func defaultAccessibilityLabel(
        state: DesktopSupportIncidentSubmissionStatus,
        incidentNumber: String?
    ) -> String {
        switch state {
        case .notSent:
            return "Запрос в поддержку не отправлен."
        case .sending:
            return "Отправляем запрос в поддержку…"
        case .pendingSync:
            guard let incidentNumber = incidentNumber?.trimmingCharacters(in: .whitespacesAndNewlines),
                  !incidentNumber.isEmpty else {
                return "Запрос принят сервером. Синхронизация с поддержкой ожидает проверки."
            }
            return "Запрос принят сервером. Синхронизация с поддержкой ожидает проверки. Номер: \(incidentNumber)."
        case .sent:
            guard let incidentNumber = incidentNumber?.trimmingCharacters(in: .whitespacesAndNewlines),
                  !incidentNumber.isEmpty else {
                return "Запрос принят и передан в поддержку."
            }
            return "Запрос принят и передан в поддержку. Номер: \(incidentNumber)."
        case .failedWithCopyFallback:
            return "Запрос не принят. Проверьте подключение или скопируйте безопасную сводку."
        case .unavailable:
            return "Поддержка сейчас недоступна. Попробуйте позже."
        }
    }
}

public struct DesktopUploadQueueItem: Codable, Equatable, Identifiable, Sendable {
    public var id: String
    public var sessionId: String
    public var directoryId: String
    public var localMediaRevisionId: String
    public var directoryPath: String
    public var manifestPath: String
    public var microphonePath: String
    public var systemAudioPath: String
    public var state: UploadItemState
    public var failureCategory: UploadFailureCategory
    public var failureReason: String?
    public var retryMode: UploadRetryMode
    public var attemptCount: Int
    public var nextRetryAt: Date?
    public var retentionDeadline: Date
    public var createdAt: Date
    public var updatedAt: Date
    public var meetingId: String?
    public var mediaRevisionId: String?
    public var uploadSessionId: String?
    public var calendarContextEventId: String?
    public var calendarMatchAttemptId: String?
    public var syncGeneration: Int
    public var lastReconciledAt: Date?
    public var syncConflictState: DesktopSyncConflictState
    public var recordingMetadata: RecordingDisplayMetadata?
    public var artifactProfile: ArtifactCompletenessProfile
    public var serverTruth: ServerTruthFingerprint
    public var retryRecords: [RetryRecord]
    public var retentionDecision: RetentionDecision
    public var supportIncidentSubmission: DesktopSupportIncidentSubmissionState?

    public var reviewAudioPath: String {
        guard !directoryPath.isEmpty && directoryPath != "metadata-only" else { return "metadata-only" }
        return URL(fileURLWithPath: directoryPath).appendingPathComponent("meeting-review.m4a").path
    }

    public var transcriptionAudioPath: String {
        guard !directoryPath.isEmpty && directoryPath != "metadata-only" else { return "metadata-only" }
        return URL(fileURLWithPath: directoryPath).appendingPathComponent("meeting-transcription.wav").path
    }

    public var isV5Package: Bool {
        artifactProfile.isV5Package
    }

    public init(
        id: String,
        sessionId: String,
        directoryId: String,
        localMediaRevisionId: String? = nil,
        directoryPath: String,
        manifestPath: String,
        microphonePath: String,
        systemAudioPath: String,
        state: UploadItemState,
        failureCategory: UploadFailureCategory = .none,
        failureReason: String? = nil,
        retryMode: UploadRetryMode,
        attemptCount: Int = 0,
        nextRetryAt: Date? = nil,
        retentionDeadline: Date,
        createdAt: Date,
        updatedAt: Date,
        meetingId: String? = nil,
        mediaRevisionId: String? = nil,
        uploadSessionId: String? = nil,
        calendarContextEventId: String? = nil,
        calendarMatchAttemptId: String? = nil,
        syncGeneration: Int = 0,
        lastReconciledAt: Date? = nil,
        syncConflictState: DesktopSyncConflictState = .none,
        recordingMetadata: RecordingDisplayMetadata? = nil,
        artifactProfile: ArtifactCompletenessProfile,
        serverTruth: ServerTruthFingerprint = ServerTruthFingerprint(),
        retryRecords: [RetryRecord] = [],
        retentionDecision: RetentionDecision,
        supportIncidentSubmission: DesktopSupportIncidentSubmissionState? = nil
    ) {
        self.id = id
        self.sessionId = sessionId
        self.directoryId = directoryId
        self.localMediaRevisionId = localMediaRevisionId ?? Self.initialMediaRevisionId(directoryId: directoryId)
        self.directoryPath = directoryPath
        self.manifestPath = manifestPath
        self.microphonePath = microphonePath
        self.systemAudioPath = systemAudioPath
        self.state = state
        self.failureCategory = failureCategory
        self.failureReason = failureReason
        self.retryMode = retryMode
        self.attemptCount = max(0, attemptCount)
        self.nextRetryAt = nextRetryAt
        self.retentionDeadline = retentionDeadline
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.meetingId = meetingId
        self.mediaRevisionId = mediaRevisionId ?? serverTruth.mediaRevisionId
        self.uploadSessionId = uploadSessionId
        self.calendarContextEventId = calendarContextEventId
        self.calendarMatchAttemptId = calendarMatchAttemptId
        self.syncGeneration = max(0, syncGeneration)
        self.lastReconciledAt = lastReconciledAt
        self.syncConflictState = syncConflictState
        self.recordingMetadata = recordingMetadata
        self.artifactProfile = artifactProfile
        self.serverTruth = serverTruth
        self.retryRecords = retryRecords
        self.retentionDecision = retentionDecision
        self.supportIncidentSubmission = supportIncidentSubmission
    }

    public var progressFraction: Double {
        if state == .uploaded { return 1 }
        let roles = serverTruth.uploadProgressRoles
        let total = artifactProfile.totalUploadBytes(limitedToRoles: roles)
        guard total > 0 else { return state == .uploaded ? 1 : 0 }
        let matchingTracks = artifactProfile.trackCompleteness.filter {
            roles?.contains($0.transportRole.rawValue) ?? true
        }
        let accepted: Int64
        if matchingTracks.isEmpty {
            accepted = serverTruth.acceptedBytesByTrack.reduce(Int64(0)) { result, item in
                guard roles?.contains(item.key) ?? true else { return result }
                return result + item.value
            }
        } else {
            accepted = matchingTracks.reduce(Int64(0)) { result, track in
                let acceptedBytes = serverTruth.acceptedBytesByTrack[track.transportRole.rawValue, default: 0]
                return result + min(max(0, acceptedBytes), max(0, track.byteCount))
            }
        }
        return min(1, max(0, Double(accepted) / Double(total)))
    }

    public var nextActionLabel: String? {
        nil
    }

    public func withTransition(
        to nextState: UploadItemState,
        now: Date,
        failureCategory: UploadFailureCategory? = nil,
        failureReason: String? = nil,
        retryMode: UploadRetryMode? = nil,
        nextRetryAt: Date? = nil,
        syncConflictState: DesktopSyncConflictState? = nil,
        serverTruth: ServerTruthFingerprint? = nil,
        retentionDecision: RetentionDecision? = nil
    ) -> DesktopUploadQueueItem {
        if state.isTerminal && !nextState.isTerminal {
            return self
        }

        var copy = self
        copy.state = nextState
        copy.updatedAt = now
        if let failureCategory {
            copy.failureCategory = failureCategory
        }
        if let failureReason {
            copy.failureReason = failureReason
        }
        if let retryMode {
            copy.retryMode = retryMode
        }
        copy.nextRetryAt = nextRetryAt
        if let syncConflictState {
            copy.syncConflictState = syncConflictState
        }
        if let serverTruth {
            copy.serverTruth = serverTruth
            copy.meetingId = serverTruth.meetingId ?? copy.meetingId
            copy.mediaRevisionId = serverTruth.mediaRevisionId ?? copy.mediaRevisionId
            copy.uploadSessionId = serverTruth.uploadSessionId ?? copy.uploadSessionId
            copy.lastReconciledAt = now
            copy.syncGeneration += 1
        }
        if let retentionDecision {
            copy.retentionDecision = retentionDecision
        }
        return copy
    }

    public static func deterministicId(directoryId: String, sessionId: String) -> String {
        "\(directoryId)--\(sessionId)"
    }

    public static func initialMediaRevisionId(directoryId: String) -> String {
        "\(directoryId)--initial"
    }

    enum CodingKeys: String, CodingKey {
        case id
        case sessionId
        case directoryId
        case localMediaRevisionId
        case directoryPath
        case manifestPath
        case microphonePath
        case systemAudioPath
        case state
        case failureCategory
        case failureReason
        case retryMode
        case attemptCount
        case nextRetryAt
        case retentionDeadline
        case createdAt
        case updatedAt
        case meetingId
        case mediaRevisionId
        case uploadSessionId
        case calendarContextEventId
        case calendarMatchAttemptId
        case syncGeneration
        case lastReconciledAt
        case syncConflictState
        case recordingMetadata
        case artifactProfile
        case serverTruth
        case retryRecords
        case retentionDecision
        case supportIncidentSubmission
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let directoryId = try container.decode(String.self, forKey: .directoryId)
        let serverTruth = try container.decodeIfPresent(ServerTruthFingerprint.self, forKey: .serverTruth) ?? ServerTruthFingerprint()
        self.init(
            id: try container.decode(String.self, forKey: .id),
            sessionId: try container.decode(String.self, forKey: .sessionId),
            directoryId: directoryId,
            localMediaRevisionId: try container.decodeIfPresent(String.self, forKey: .localMediaRevisionId),
            directoryPath: try container.decode(String.self, forKey: .directoryPath),
            manifestPath: try container.decode(String.self, forKey: .manifestPath),
            microphonePath: try container.decode(String.self, forKey: .microphonePath),
            systemAudioPath: try container.decode(String.self, forKey: .systemAudioPath),
            state: try container.decode(UploadItemState.self, forKey: .state),
            failureCategory: try container.decodeIfPresent(UploadFailureCategory.self, forKey: .failureCategory) ?? .none,
            failureReason: try container.decodeIfPresent(String.self, forKey: .failureReason),
            retryMode: try container.decode(UploadRetryMode.self, forKey: .retryMode),
            attemptCount: try container.decodeIfPresent(Int.self, forKey: .attemptCount) ?? 0,
            nextRetryAt: try container.decodeIfPresent(Date.self, forKey: .nextRetryAt),
            retentionDeadline: try container.decode(Date.self, forKey: .retentionDeadline),
            createdAt: try container.decode(Date.self, forKey: .createdAt),
            updatedAt: try container.decode(Date.self, forKey: .updatedAt),
            meetingId: try container.decodeIfPresent(String.self, forKey: .meetingId),
            mediaRevisionId: try container.decodeIfPresent(String.self, forKey: .mediaRevisionId),
            uploadSessionId: try container.decodeIfPresent(String.self, forKey: .uploadSessionId),
            calendarContextEventId: try container.decodeIfPresent(String.self, forKey: .calendarContextEventId),
            calendarMatchAttemptId: try container.decodeIfPresent(String.self, forKey: .calendarMatchAttemptId),
            syncGeneration: try container.decodeIfPresent(Int.self, forKey: .syncGeneration) ?? 0,
            lastReconciledAt: try container.decodeIfPresent(Date.self, forKey: .lastReconciledAt),
            syncConflictState: try container.decodeIfPresent(DesktopSyncConflictState.self, forKey: .syncConflictState) ?? .none,
            recordingMetadata: try container.decodeIfPresent(RecordingDisplayMetadata.self, forKey: .recordingMetadata),
            artifactProfile: try container.decode(ArtifactCompletenessProfile.self, forKey: .artifactProfile),
            serverTruth: serverTruth,
            retryRecords: try container.decodeIfPresent([RetryRecord].self, forKey: .retryRecords) ?? [],
            retentionDecision: try container.decode(RetentionDecision.self, forKey: .retentionDecision),
            supportIncidentSubmission: try container.decodeIfPresent(
                DesktopSupportIncidentSubmissionState.self,
                forKey: .supportIncidentSubmission
            )
        )
    }
}

public struct DesktopUploadQueueDocument: Codable, Equatable, Sendable {
    public static let schemaVersion = "desktop-upload-queue.v2"

    public var schemaVersion: String
    public var updatedAt: Date
    public var items: [DesktopUploadQueueItem]

    public init(
        schemaVersion: String = Self.schemaVersion,
        updatedAt: Date,
        items: [DesktopUploadQueueItem]
    ) {
        self.schemaVersion = schemaVersion
        self.updatedAt = updatedAt
        self.items = items
    }
}
