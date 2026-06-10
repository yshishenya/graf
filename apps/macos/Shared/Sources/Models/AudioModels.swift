import Foundation

public struct VirtualAudioDevice: Codable, Equatable, Sendable {
    public var id: String
    public var displayName: String
    public var direction: AudioDirection
    public var driverVersion: String?
    public var availabilityState: VirtualDeviceAvailabilityState
    public var routeValidationState: RouteVerificationStatus
    public var lastSeenAt: Date?

    public init(
        id: String,
        displayName: String,
        direction: AudioDirection,
        driverVersion: String? = nil,
        availabilityState: VirtualDeviceAvailabilityState,
        routeValidationState: RouteVerificationStatus,
        lastSeenAt: Date? = nil
    ) {
        self.id = id
        self.displayName = displayName
        self.direction = direction
        self.driverVersion = driverVersion
        self.availabilityState = availabilityState
        self.routeValidationState = routeValidationState
        self.lastSeenAt = lastSeenAt
    }
}

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

public struct RouteVerification: Codable, Equatable, Sendable {
    public var id: String
    public var path: RoutePath
    public var validationType: RouteValidationType
    public var target: String?
    public var status: RouteVerificationStatus
    public var failureReason: String?
    public var recoveryAction: String?
    public var latencyMs: Double?
    public var referenceLeakageDb: Double?
    public var streamHealth: StreamHealthEvidence?
    public var startedAt: Date
    public var finishedAt: Date?

    public init(
        id: String,
        path: RoutePath,
        validationType: RouteValidationType,
        target: String?,
        status: RouteVerificationStatus,
        failureReason: String?,
        recoveryAction: String?,
        latencyMs: Double? = nil,
        referenceLeakageDb: Double? = nil,
        streamHealth: StreamHealthEvidence? = nil,
        startedAt: Date,
        finishedAt: Date?
    ) {
        self.id = id
        self.path = path
        self.validationType = validationType
        self.target = target
        self.status = status
        self.failureReason = failureReason
        self.recoveryAction = recoveryAction
        self.latencyMs = latencyMs
        self.referenceLeakageDb = referenceLeakageDb
        self.streamHealth = streamHealth
        self.startedAt = startedAt
        self.finishedAt = finishedAt
    }
}

public struct LiveRouteReadinessResult: Codable, Equatable, Sendable {
    public var status: LiveRouteReadinessStatus
    public var microphoneEvidence: MicrophonePathEvidence
    public var speakerEvidence: SpeakerPathEvidence
    public var latencyMeasurement: LatencyMeasurement?
    public var leakageMeasurement: LeakageMeasurement?
    public var browserTargetEvidence: [BrowserTargetEvidence]
    public var checkedAt: Date
    public var expiresAt: Date?
    public var recoveryAction: String?

    public init(
        status: LiveRouteReadinessStatus,
        microphoneEvidence: MicrophonePathEvidence,
        speakerEvidence: SpeakerPathEvidence,
        latencyMeasurement: LatencyMeasurement? = nil,
        leakageMeasurement: LeakageMeasurement? = nil,
        browserTargetEvidence: [BrowserTargetEvidence] = [],
        checkedAt: Date,
        expiresAt: Date? = nil,
        recoveryAction: String? = nil
    ) {
        self.status = status
        self.microphoneEvidence = microphoneEvidence
        self.speakerEvidence = speakerEvidence
        self.latencyMeasurement = latencyMeasurement
        self.leakageMeasurement = leakageMeasurement
        self.browserTargetEvidence = browserTargetEvidence
        self.checkedAt = checkedAt
        self.expiresAt = expiresAt
        self.recoveryAction = recoveryAction
    }

    public var canShowReady: Bool {
        status == .ready && microphoneEvidence.status == .passed && speakerEvidence.status == .passed
    }
}

public struct LivePassthroughSession: Codable, Equatable, Sendable {
    public var sessionId: String
    public var status: LivePassthroughStatus
    public var microphonePath: MicrophonePassthroughPath
    public var speakerPath: SpeakerPassthroughPath
    public var healthEvidence: PassthroughHealthEvidence
    public var browserEvidence: [PassthroughBrowserCallEvidence]
    public var startedAt: Date?
    public var endedAt: Date?
    public var recordingState: String
    public var lastRecoveryAction: String?

    public init(
        sessionId: String,
        status: LivePassthroughStatus,
        microphonePath: MicrophonePassthroughPath,
        speakerPath: SpeakerPassthroughPath,
        healthEvidence: PassthroughHealthEvidence,
        browserEvidence: [PassthroughBrowserCallEvidence] = [],
        startedAt: Date? = nil,
        endedAt: Date? = nil,
        recordingState: String = "not_recording",
        lastRecoveryAction: String? = nil
    ) {
        self.sessionId = sessionId
        self.status = status
        self.microphonePath = microphonePath
        self.speakerPath = speakerPath
        self.healthEvidence = healthEvidence
        self.browserEvidence = browserEvidence
        self.startedAt = startedAt
        self.endedAt = endedAt
        self.recordingState = recordingState
        self.lastRecoveryAction = lastRecoveryAction
    }

    public var canActivate: Bool {
        recordingState == "not_recording" &&
            status == .ready &&
            microphonePath.status == .ready &&
            speakerPath.status == .ready &&
            healthEvidence.appHeartbeatStatus == .connected
    }
}

public struct MicrophonePassthroughPath: Codable, Equatable, Sendable {
    public var physicalInputId: String
    public var physicalInputName: String
    public var virtualInputName: String
    public var status: LivePassthroughStatus
    public var validFrameObserved: Bool
    public var lastFrameAt: Date?
    public var failureReason: PassthroughFailureReason

    public init(
        physicalInputId: String,
        physicalInputName: String,
        virtualInputName: String = "2brain Rec Microphone",
        status: LivePassthroughStatus,
        validFrameObserved: Bool,
        lastFrameAt: Date? = nil,
        failureReason: PassthroughFailureReason = .none
    ) {
        self.physicalInputId = physicalInputId
        self.physicalInputName = physicalInputName
        self.virtualInputName = virtualInputName
        self.status = status
        self.validFrameObserved = validFrameObserved
        self.lastFrameAt = lastFrameAt
        self.failureReason = failureReason
    }
}

public struct SpeakerPassthroughPath: Codable, Equatable, Sendable {
    public var virtualOutputName: String
    public var physicalOutputId: String
    public var physicalOutputName: String
    public var status: LivePassthroughStatus
    public var stimulusObserved: Bool
    public var playbackConfirmedAt: Date?
    public var failureReason: PassthroughFailureReason

    public init(
        virtualOutputName: String = "2brain Rec Speaker",
        physicalOutputId: String,
        physicalOutputName: String,
        status: LivePassthroughStatus,
        stimulusObserved: Bool,
        playbackConfirmedAt: Date? = nil,
        failureReason: PassthroughFailureReason = .none
    ) {
        self.virtualOutputName = virtualOutputName
        self.physicalOutputId = physicalOutputId
        self.physicalOutputName = physicalOutputName
        self.status = status
        self.stimulusObserved = stimulusObserved
        self.playbackConfirmedAt = playbackConfirmedAt
        self.failureReason = failureReason
    }
}

public struct PassthroughHealthEvidence: Codable, Equatable, Sendable {
    public var appHeartbeatStatus: AppIOState
    public var latencyMs: Double?
    public var leakageDbBelowReference: Double?
    public var notIntelligible: Bool
    public var dropoutFraction: Double?
    public var routeInvalidatedAt: Date?
    public var diagnosticSafe: Bool

    public init(
        appHeartbeatStatus: AppIOState,
        latencyMs: Double? = nil,
        leakageDbBelowReference: Double? = nil,
        notIntelligible: Bool = true,
        dropoutFraction: Double? = nil,
        routeInvalidatedAt: Date? = nil,
        diagnosticSafe: Bool = true
    ) {
        self.appHeartbeatStatus = appHeartbeatStatus
        self.latencyMs = latencyMs
        self.leakageDbBelowReference = leakageDbBelowReference
        self.notIntelligible = notIntelligible
        self.dropoutFraction = dropoutFraction
        self.routeInvalidatedAt = routeInvalidatedAt
        self.diagnosticSafe = diagnosticSafe
    }

    public var passesBuiltInWiredGate: Bool {
        guard diagnosticSafe else { return false }
        guard let latencyMs, latencyMs <= RouteLatencyEvidence.builtInWiredThresholdMs else { return false }
        guard let leakageDbBelowReference, leakageDbBelowReference >= 45 else { return false }
        return notIntelligible
    }
}

public struct PassthroughBrowserCallEvidence: Codable, Equatable, Sendable {
    public var targetName: String
    public var targetVersion: String?
    public var selectedMicrophone: String
    public var selectedSpeaker: String
    public var localSpeechUsable: Bool
    public var remoteAudioUsable: Bool
    public var status: BrowserTargetEvidenceStatus
    public var failureReason: String?
    public var checkedAt: Date

    public init(
        targetName: String,
        targetVersion: String? = nil,
        selectedMicrophone: String,
        selectedSpeaker: String,
        localSpeechUsable: Bool,
        remoteAudioUsable: Bool,
        status: BrowserTargetEvidenceStatus,
        failureReason: String? = nil,
        checkedAt: Date
    ) {
        self.targetName = targetName
        self.targetVersion = targetVersion
        self.selectedMicrophone = selectedMicrophone
        self.selectedSpeaker = selectedSpeaker
        self.localSpeechUsable = localSpeechUsable
        self.remoteAudioUsable = remoteAudioUsable
        self.status = status
        self.failureReason = failureReason
        self.checkedAt = checkedAt
    }
}

public struct PassthroughRouteRecoveryEvent: Codable, Equatable, Sendable {
    public var eventType: RouteRecoveryEventType
    public var detectedAt: Date
    public var previousStatus: LivePassthroughStatus
    public var newStatus: LivePassthroughStatus
    public var recoveryAction: String

    public init(
        eventType: RouteRecoveryEventType,
        detectedAt: Date,
        previousStatus: LivePassthroughStatus,
        newStatus: LivePassthroughStatus,
        recoveryAction: String
    ) {
        self.eventType = eventType
        self.detectedAt = detectedAt
        self.previousStatus = previousStatus
        self.newStatus = newStatus
        self.recoveryAction = recoveryAction
    }
}

public struct MicrophonePathEvidence: Codable, Equatable, Sendable {
    public var selectedPhysicalDeviceId: String
    public var selectedPhysicalDeviceName: String
    public var virtualMicrophoneName: String
    public var status: RouteEvidenceStatus
    public var validFrameCount: UInt64
    public var emptyBufferCount: UInt64
    public var capturabilityStatus: CapturabilityStatus
    public var selfRoutingRejected: Bool
    public var failureReason: String?
    public var checkedAt: Date

    public init(
        selectedPhysicalDeviceId: String,
        selectedPhysicalDeviceName: String,
        virtualMicrophoneName: String = "2brain Rec Microphone",
        status: RouteEvidenceStatus,
        validFrameCount: UInt64,
        emptyBufferCount: UInt64,
        capturabilityStatus: CapturabilityStatus,
        selfRoutingRejected: Bool,
        failureReason: String? = nil,
        checkedAt: Date
    ) {
        self.selectedPhysicalDeviceId = selectedPhysicalDeviceId
        self.selectedPhysicalDeviceName = selectedPhysicalDeviceName
        self.virtualMicrophoneName = virtualMicrophoneName
        self.status = status
        self.validFrameCount = validFrameCount
        self.emptyBufferCount = emptyBufferCount
        self.capturabilityStatus = capturabilityStatus
        self.selfRoutingRejected = selfRoutingRejected
        self.failureReason = failureReason
        self.checkedAt = checkedAt
    }
}

public struct SpeakerPathEvidence: Codable, Equatable, Sendable {
    public var selectedPhysicalOutputId: String
    public var selectedPhysicalOutputName: String
    public var virtualSpeakerName: String
    public var status: RouteEvidenceStatus
    public var stimulusObserved: Bool
    public var validFrameCount: UInt64
    public var emptyBufferCount: UInt64
    public var selfRoutingRejected: Bool
    public var failureReason: String?
    public var checkedAt: Date

    public init(
        selectedPhysicalOutputId: String,
        selectedPhysicalOutputName: String,
        virtualSpeakerName: String = "2brain Rec Speaker",
        status: RouteEvidenceStatus,
        stimulusObserved: Bool,
        validFrameCount: UInt64,
        emptyBufferCount: UInt64,
        selfRoutingRejected: Bool,
        failureReason: String? = nil,
        checkedAt: Date
    ) {
        self.selectedPhysicalOutputId = selectedPhysicalOutputId
        self.selectedPhysicalOutputName = selectedPhysicalOutputName
        self.virtualSpeakerName = virtualSpeakerName
        self.status = status
        self.stimulusObserved = stimulusObserved
        self.validFrameCount = validFrameCount
        self.emptyBufferCount = emptyBufferCount
        self.selfRoutingRejected = selfRoutingRejected
        self.failureReason = failureReason
        self.checkedAt = checkedAt
    }
}

public struct LatencyMeasurement: Codable, Equatable, Sendable {
    public var routeClass: PhysicalDeviceClass
    public var addedLatencyMs: Double
    public var thresholdMs: Double
    public var status: MeasurementStatus
    public var measuredAt: Date

    public init(
        routeClass: PhysicalDeviceClass,
        addedLatencyMs: Double,
        thresholdMs: Double = RouteLatencyEvidence.builtInWiredThresholdMs,
        status: MeasurementStatus,
        measuredAt: Date
    ) {
        self.routeClass = routeClass
        self.addedLatencyMs = addedLatencyMs
        self.thresholdMs = thresholdMs
        self.status = status
        self.measuredAt = measuredAt
    }
}

public struct LeakageMeasurement: Codable, Equatable, Sendable {
    public var speakerReferenceDb: Double
    public var virtualMicLeakageDb: Double
    public var relativeLeakageDb: Double
    public var intelligibilityStatus: IntelligibilityStatus
    public var status: MeasurementStatus
    public var measuredAt: Date
    public var measurementId: String?
    public var windowCount: Int?
    public var farEndOnlyWindowMs: Int?
    public var doubleTalkExcludedWindowMs: Int?
    public var alignmentOffsetMs: Int?
    public var alignmentDriftMs: Int?
    public var leakageLevelDb: Double?
    public var correlationPeak: Double?
    public var correlationLagMs: Int?
    public var directLoopbackSuspicion: Bool?
    public var acousticLeakageSuspicion: Bool?
    public var clippingObserved: Bool?
    public var dropoutObserved: Bool?
    public var confidence: Double?

    public init(
        speakerReferenceDb: Double,
        virtualMicLeakageDb: Double,
        relativeLeakageDb: Double,
        intelligibilityStatus: IntelligibilityStatus,
        status: MeasurementStatus,
        measuredAt: Date,
        measurementId: String? = nil,
        windowCount: Int? = nil,
        farEndOnlyWindowMs: Int? = nil,
        doubleTalkExcludedWindowMs: Int? = nil,
        alignmentOffsetMs: Int? = nil,
        alignmentDriftMs: Int? = nil,
        leakageLevelDb: Double? = nil,
        correlationPeak: Double? = nil,
        correlationLagMs: Int? = nil,
        directLoopbackSuspicion: Bool? = nil,
        acousticLeakageSuspicion: Bool? = nil,
        clippingObserved: Bool? = nil,
        dropoutObserved: Bool? = nil,
        confidence: Double? = nil
    ) {
        self.speakerReferenceDb = speakerReferenceDb
        self.virtualMicLeakageDb = virtualMicLeakageDb
        self.relativeLeakageDb = relativeLeakageDb
        self.intelligibilityStatus = intelligibilityStatus
        self.status = status
        self.measuredAt = measuredAt
        self.measurementId = measurementId
        self.windowCount = windowCount
        self.farEndOnlyWindowMs = farEndOnlyWindowMs
        self.doubleTalkExcludedWindowMs = doubleTalkExcludedWindowMs
        self.alignmentOffsetMs = alignmentOffsetMs
        self.alignmentDriftMs = alignmentDriftMs
        self.leakageLevelDb = leakageLevelDb
        self.correlationPeak = correlationPeak
        self.correlationLagMs = correlationLagMs
        self.directLoopbackSuspicion = directLoopbackSuspicion
        self.acousticLeakageSuspicion = acousticLeakageSuspicion
        self.clippingObserved = clippingObserved
        self.dropoutObserved = dropoutObserved
        self.confidence = confidence
    }
}

public struct RecordingRouteMetadata: Codable, Equatable, Sendable {
    public var inputRouteClass: String?
    public var outputRouteClass: String?
    public var outputVolumeBucket: LeakageRouteVolumeBucket
    public var muteState: LeakageRouteMuteState
    public var browserTarget: String?
    public var routeChangeCount: Int
    public var coreaudiodState: String?
    public var sleepWakeObserved: Bool
    public var selfRoutingRejected: Bool
    public var notes: [String]

    public init(
        inputRouteClass: String? = nil,
        outputRouteClass: String? = nil,
        outputVolumeBucket: LeakageRouteVolumeBucket = .unknown,
        muteState: LeakageRouteMuteState = .unknown,
        browserTarget: String? = nil,
        routeChangeCount: Int = 0,
        coreaudiodState: String? = nil,
        sleepWakeObserved: Bool = false,
        selfRoutingRejected: Bool = false,
        notes: [String] = []
    ) {
        self.inputRouteClass = inputRouteClass
        self.outputRouteClass = outputRouteClass
        self.outputVolumeBucket = outputVolumeBucket
        self.muteState = muteState
        self.browserTarget = browserTarget
        self.routeChangeCount = routeChangeCount
        self.coreaudiodState = coreaudiodState
        self.sleepWakeObserved = sleepWakeObserved
        self.selfRoutingRejected = selfRoutingRejected
        self.notes = notes
    }
}

public struct LeakageThresholdVersion: Codable, Equatable, Sendable {
    public static let v1 = LeakageThresholdVersion()

    public var id: String
    public var timelineToleranceMs: Int
    public var minimumFarEndOnlyWindowMs: Int
    public var maximumLeakageLevelDb: Double
    public var maximumCorrelationPeak: Double
    public var minimumConfidence: Double
    public var maximumAlignmentDriftMs: Int
    public var minimumDerivedConfidence: Double
    public var maximumDerivedResidualLeakageDb: Double
    public var doubleTalkPolicy: String
    public var derivedResidualPolicy: String

    public init(
        id: String = "leakage-threshold.v1",
        timelineToleranceMs: Int = 1_000,
        minimumFarEndOnlyWindowMs: Int = 15_000,
        maximumLeakageLevelDb: Double = -45.0,
        maximumCorrelationPeak: Double = 0.12,
        minimumConfidence: Double = 0.80,
        maximumAlignmentDriftMs: Int = 250,
        minimumDerivedConfidence: Double = 0.85,
        maximumDerivedResidualLeakageDb: Double = -50.0,
        doubleTalkPolicy: String = "exclude_or_downgrade_confidence",
        derivedResidualPolicy: String = "separate_artifact_requires_residual_gate"
    ) {
        self.id = id
        self.timelineToleranceMs = timelineToleranceMs
        self.minimumFarEndOnlyWindowMs = minimumFarEndOnlyWindowMs
        self.maximumLeakageLevelDb = maximumLeakageLevelDb
        self.maximumCorrelationPeak = maximumCorrelationPeak
        self.minimumConfidence = minimumConfidence
        self.maximumAlignmentDriftMs = maximumAlignmentDriftMs
        self.minimumDerivedConfidence = minimumDerivedConfidence
        self.maximumDerivedResidualLeakageDb = maximumDerivedResidualLeakageDb
        self.doubleTalkPolicy = doubleTalkPolicy
        self.derivedResidualPolicy = derivedResidualPolicy
    }
}

public struct DerivedCleanedTrackMetadata: Codable, Equatable, Sendable {
    public var sourceTrackIds: [String]
    public var processorId: String
    public var processorVersion: String
    public var createdAt: Date
    public var lineageHash: String?
    public var confidence: Double
    public var residualLeakageStatus: LeakageStatus
    public var residualThresholdVersion: String
    public var eligibleForTranscription: Bool
    public var retentionClass: String
    public var deletionScope: String
    public var localDeletionRegistered: Bool
    public var failureReason: LocalRecordingFailureReason

    public init(
        sourceTrackIds: [String],
        processorId: String,
        processorVersion: String,
        createdAt: Date,
        lineageHash: String? = nil,
        confidence: Double,
        residualLeakageStatus: LeakageStatus,
        residualThresholdVersion: String = LeakageThresholdVersion.v1.id,
        eligibleForTranscription: Bool,
        retentionClass: String = "local_recording_derived_audio",
        deletionScope: String = "local_desktop_purge",
        localDeletionRegistered: Bool,
        failureReason: LocalRecordingFailureReason = .none
    ) {
        self.sourceTrackIds = sourceTrackIds
        self.processorId = processorId
        self.processorVersion = processorVersion
        self.createdAt = createdAt
        self.lineageHash = lineageHash
        self.confidence = confidence
        self.residualLeakageStatus = residualLeakageStatus
        self.residualThresholdVersion = residualThresholdVersion
        self.eligibleForTranscription = eligibleForTranscription
        self.retentionClass = retentionClass
        self.deletionScope = deletionScope
        self.localDeletionRegistered = localDeletionRegistered
        self.failureReason = failureReason
    }
}

public struct LeakageFinalization: Codable, Equatable, Sendable {
    public var status: LeakageStatus
    public var evaluatedAt: Date
    public var thresholdVersion: String
    public var measurementAttempted: Bool
    public var measurementApplicable: Bool
    public var alignmentStatus: LeakageAlignmentStatus
    public var confidence: Double
    public var failureReason: LocalRecordingFailureReason
    public var originalEvidenceStatus: LeakageStatus
    public var derivedArtifactStatus: LeakageStatus?
    public var transcriptionGate: LeakageTranscriptionGate
    public var routeMetadata: RecordingRouteMetadata
    public var measurement: LeakageMeasurement?

    public init(
        status: LeakageStatus,
        evaluatedAt: Date,
        thresholdVersion: String = LeakageThresholdVersion.v1.id,
        measurementAttempted: Bool,
        measurementApplicable: Bool,
        alignmentStatus: LeakageAlignmentStatus,
        confidence: Double,
        failureReason: LocalRecordingFailureReason,
        originalEvidenceStatus: LeakageStatus,
        derivedArtifactStatus: LeakageStatus? = nil,
        transcriptionGate: LeakageTranscriptionGate,
        routeMetadata: RecordingRouteMetadata = RecordingRouteMetadata(),
        measurement: LeakageMeasurement? = nil
    ) {
        self.status = status
        self.evaluatedAt = evaluatedAt
        self.thresholdVersion = thresholdVersion
        self.measurementAttempted = measurementAttempted
        self.measurementApplicable = measurementApplicable
        self.alignmentStatus = alignmentStatus
        self.confidence = confidence
        self.failureReason = failureReason
        self.originalEvidenceStatus = originalEvidenceStatus
        self.derivedArtifactStatus = derivedArtifactStatus
        self.transcriptionGate = transcriptionGate
        self.routeMetadata = routeMetadata
        self.measurement = measurement
    }
}

public struct LeakageDependencyDecisionRecord: Codable, Equatable, Sendable {
    public var option: String
    public var outcome: String
    public var reason: String
    public var sourceBasis: String
    public var testCoverageRequired: [String]

    public init(
        option: String,
        outcome: String,
        reason: String,
        sourceBasis: String,
        testCoverageRequired: [String]
    ) {
        self.option = option
        self.outcome = outcome
        self.reason = reason
        self.sourceBasis = sourceBasis
        self.testCoverageRequired = testCoverageRequired
    }
}

public struct BrowserTargetEvidence: Codable, Equatable, Sendable {
    public var target: String
    public var status: BrowserTargetEvidenceStatus
    public var microphoneSelected: String
    public var speakerSelected: String
    public var localSpeechUsable: Bool
    public var remoteAudioUsable: Bool
    public var failureReason: String?
    public var checkedAt: Date

    public init(
        target: String,
        status: BrowserTargetEvidenceStatus,
        microphoneSelected: String,
        speakerSelected: String,
        localSpeechUsable: Bool,
        remoteAudioUsable: Bool,
        failureReason: String? = nil,
        checkedAt: Date
    ) {
        self.target = target
        self.status = status
        self.microphoneSelected = microphoneSelected
        self.speakerSelected = speakerSelected
        self.localSpeechUsable = localSpeechUsable
        self.remoteAudioUsable = remoteAudioUsable
        self.failureReason = failureReason
        self.checkedAt = checkedAt
    }
}

public struct RouteInvalidationEvent: Codable, Equatable, Sendable {
    public var source: RouteInvalidationSource
    public var previousReadinessStatus: LiveRouteReadinessStatus
    public var newReadinessStatus: LiveRouteReadinessStatus
    public var detectedAt: Date
    public var recoveryAction: String

    public init(
        source: RouteInvalidationSource,
        previousReadinessStatus: LiveRouteReadinessStatus,
        newReadinessStatus: LiveRouteReadinessStatus,
        detectedAt: Date,
        recoveryAction: String
    ) {
        self.source = source
        self.previousReadinessStatus = previousReadinessStatus
        self.newReadinessStatus = newReadinessStatus
        self.detectedAt = detectedAt
        self.recoveryAction = recoveryAction
    }
}

public struct PrivateAppIOHealth: Codable, Equatable, Sendable {
    public var state: AppIOState
    public var lastHeartbeatAt: Date?
    public var lastValidFrameAt: Date?
    public var missedHeartbeatCount: Int
    public var publicDeviceAvailability: VirtualDeviceAvailabilityState
    public var recoveryAction: String?

    public init(
        state: AppIOState,
        lastHeartbeatAt: Date? = nil,
        lastValidFrameAt: Date? = nil,
        missedHeartbeatCount: Int = 0,
        publicDeviceAvailability: VirtualDeviceAvailabilityState = .unavailable,
        recoveryAction: String? = nil
    ) {
        self.state = state
        self.lastHeartbeatAt = lastHeartbeatAt
        self.lastValidFrameAt = lastValidFrameAt
        self.missedHeartbeatCount = missedHeartbeatCount
        self.publicDeviceAvailability = publicDeviceAvailability
        self.recoveryAction = recoveryAction
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

public struct RouteLatencyEvidence: Codable, Equatable, Sendable {
    public static let builtInWiredThresholdMs: Double = 30

    public var routeClass: PhysicalDeviceClass
    public var measuredLatencyMs: Double
    public var measuredAt: Date

    public init(routeClass: PhysicalDeviceClass, measuredLatencyMs: Double, measuredAt: Date) {
        self.routeClass = routeClass
        self.measuredLatencyMs = measuredLatencyMs
        self.measuredAt = measuredAt
    }

    public var isBuiltInOrWiredReleaseReady: Bool {
        switch routeClass {
        case .builtIn, .wired, .usb:
            measuredLatencyMs <= Self.builtInWiredThresholdMs
        default:
            false
        }
    }
}

public struct BluetoothRouteEvidence: Codable, Equatable, Sendable {
    public var profileName: String
    public var profileState: BluetoothProfileState
    public var inputAvailable: Bool
    public var outputAvailable: Bool
    public var validFrameIntervalsPassed: Bool
    public var oneSidedAudioEvent: Bool
    public var dropoutRate: Double
    public var measuredLatencyMs: Double?

    public init(
        profileName: String,
        profileState: BluetoothProfileState,
        inputAvailable: Bool,
        outputAvailable: Bool,
        validFrameIntervalsPassed: Bool,
        oneSidedAudioEvent: Bool,
        dropoutRate: Double,
        measuredLatencyMs: Double?
    ) {
        self.profileName = profileName
        self.profileState = profileState
        self.inputAvailable = inputAvailable
        self.outputAvailable = outputAvailable
        self.validFrameIntervalsPassed = validFrameIntervalsPassed
        self.oneSidedAudioEvent = oneSidedAudioEvent
        self.dropoutRate = dropoutRate
        self.measuredLatencyMs = measuredLatencyMs
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
    public var routeState: LivePassthroughStatus
    public var routeEvidenceKind: RecordingRouteEvidenceKind
    public var policyAllowsRecording: Bool
    public var microphonePermissionGranted: Bool
    public var storageRisk: LocalBufferRiskState
    public var indicatorAvailable: Bool
    public var sourceAppEligibility: SourceAppEligibility
    public var blockedReason: RecordingStartBlocker
    public var recoveryAction: String?
    public var evaluatedAt: Date

    public init(
        routeState: LivePassthroughStatus,
        routeEvidenceKind: RecordingRouteEvidenceKind,
        policyAllowsRecording: Bool,
        microphonePermissionGranted: Bool,
        storageRisk: LocalBufferRiskState,
        indicatorAvailable: Bool,
        sourceAppEligibility: SourceAppEligibility,
        blockedReason: RecordingStartBlocker = .none,
        recoveryAction: String? = nil,
        evaluatedAt: Date
    ) {
        self.routeState = routeState
        self.routeEvidenceKind = routeEvidenceKind
        self.policyAllowsRecording = policyAllowsRecording
        self.microphonePermissionGranted = microphonePermissionGranted
        self.storageRisk = storageRisk
        self.indicatorAvailable = indicatorAvailable
        self.sourceAppEligibility = sourceAppEligibility
        self.blockedReason = blockedReason
        self.recoveryAction = recoveryAction
        self.evaluatedAt = evaluatedAt
    }

    public var allowsRecording: Bool {
        let routeAllowsRecording = routeEvidenceKind == .systemAudioCapture ||
            [.ready, .active].contains(routeState)

        return blockedReason == .none &&
            routeAllowsRecording &&
            routeEvidenceKind != .publicationOnly &&
            routeEvidenceKind != .stale &&
            routeEvidenceKind != .unknown &&
            policyAllowsRecording &&
            microphonePermissionGranted &&
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
    public var routeState: LivePassthroughStatus
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
        routeState: LivePassthroughStatus,
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
        self.routeState = routeState
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
    public var trackId: String
    public var role: AudioTrackRole
    public var sourceKind: AudioCaptureSourceKind?
    public var mediaScribeField: MediaScribeTrackField
    public var status: LocalRecordingTrackStatus
    public var evidenceRole: LeakageEvidenceRole
    public var fileName: String
    public var format: String
    public var sampleRate: Double
    public var channelCount: Int
    public var bitsPerSample: Int
    public var durationMs: Int
    public var byteCount: Int64
    public var frameCount: Int64
    public var timelineStartMs: Int
    public var timelineAligned: Bool
    public var failureReason: LocalRecordingFailureReason
    public var sourceTrackIds: [String]?
    public var processorId: String?
    public var processorVersion: String?
    public var residualLeakageStatus: LeakageStatus?
    public var eligibleForTranscription: Bool?
    public var derivedMetadata: DerivedCleanedTrackMetadata?

    public init(
        trackId: String,
        role: AudioTrackRole,
        sourceKind: AudioCaptureSourceKind? = nil,
        mediaScribeField: MediaScribeTrackField? = nil,
        status: LocalRecordingTrackStatus,
        evidenceRole: LeakageEvidenceRole = .original,
        fileName: String,
        format: String,
        sampleRate: Double,
        channelCount: Int,
        bitsPerSample: Int = 0,
        durationMs: Int,
        byteCount: Int64,
        frameCount: Int64,
        timelineStartMs: Int = 0,
        timelineAligned: Bool = false,
        failureReason: LocalRecordingFailureReason = .none,
        sourceTrackIds: [String]? = nil,
        processorId: String? = nil,
        processorVersion: String? = nil,
        residualLeakageStatus: LeakageStatus? = nil,
        eligibleForTranscription: Bool? = nil,
        derivedMetadata: DerivedCleanedTrackMetadata? = nil
    ) {
        self.trackId = trackId
        self.role = role
        self.sourceKind = sourceKind ?? Self.defaultSourceKind(for: role)
        self.mediaScribeField = mediaScribeField ?? Self.defaultMediaScribeField(for: role)
        self.status = status
        self.evidenceRole = evidenceRole
        self.fileName = fileName
        self.format = format
        self.sampleRate = sampleRate
        self.channelCount = channelCount
        self.bitsPerSample = bitsPerSample
        self.durationMs = durationMs
        self.byteCount = byteCount
        self.frameCount = frameCount
        self.timelineStartMs = timelineStartMs
        self.timelineAligned = timelineAligned
        self.failureReason = failureReason
        self.sourceTrackIds = sourceTrackIds
        self.processorId = processorId
        self.processorVersion = processorVersion
        self.residualLeakageStatus = residualLeakageStatus
        self.eligibleForTranscription = eligibleForTranscription
        self.derivedMetadata = derivedMetadata
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

    public static func defaultMediaScribeField(for role: AudioTrackRole) -> MediaScribeTrackField {
        switch role {
        case .localMic:
            .micFile
        case .remoteSpeaker:
            .incomingFile
        case .derivedLocalMic:
            .derivedMicFile
        case .mixedMeetingAudio:
            .mixedAudioFile
        }
    }

    public static func defaultSourceKind(for role: AudioTrackRole) -> AudioCaptureSourceKind {
        switch role {
        case .localMic, .derivedLocalMic:
            .microphone
        case .remoteSpeaker, .mixedMeetingAudio:
            .systemAudio
        }
    }

    public var isDerivedTranscriptionEligible: Bool {
        evidenceRole == .derived &&
            isComplete &&
            eligibleForTranscription == true &&
            residualLeakageStatus == .clean &&
            derivedMetadata?.localDeletionRegistered == true
    }
}

public struct LocalRecordingManifest: Codable, Equatable, Sendable {
    public static let schemaVersion = "local-recording-manifest.v3"

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
    public var tracks: [LocalRecordingTrack]
    public var externalEgressStarted: Bool
    public var transcriptionStarted: Bool
    public var diagnosticSafe: Bool
    public var localDeletionRegistered: Bool
    public var leakageFinalization: LeakageFinalization?
    public var failureReason: LocalRecordingFailureReason
    public var durationDifferenceSeconds: Double
    public var recordingTimelineEvidence: RecordingTimelineIntegrityEvidence?
    public var scopeApproval: CaptureScopeApproval?
    public var permissions: SystemAudioPermissionSnapshot?
    public var captureHealth: CaptureHealthSnapshot?

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
        mediaScribeSourceMode: String = "dual",
        tracks: [LocalRecordingTrack],
        externalEgressStarted: Bool = false,
        transcriptionStarted: Bool = false,
        diagnosticSafe: Bool = true,
        localDeletionRegistered: Bool = false,
        leakageFinalization: LeakageFinalization? = nil,
        failureReason: LocalRecordingFailureReason = .none,
        durationDifferenceSeconds: Double = 0,
        recordingTimelineEvidence: RecordingTimelineIntegrityEvidence? = nil,
        scopeApproval: CaptureScopeApproval? = nil,
        permissions: SystemAudioPermissionSnapshot? = nil,
        captureHealth: CaptureHealthSnapshot? = nil
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
        self.tracks = tracks
        self.externalEgressStarted = externalEgressStarted
        self.transcriptionStarted = transcriptionStarted
        self.diagnosticSafe = diagnosticSafe
        self.localDeletionRegistered = localDeletionRegistered
        self.leakageFinalization = leakageFinalization
        self.failureReason = failureReason
        self.durationDifferenceSeconds = durationDifferenceSeconds
        self.recordingTimelineEvidence = recordingTimelineEvidence
        self.scopeApproval = scopeApproval
        self.permissions = permissions
        self.captureHealth = captureHealth
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

        if mediaScribeSourceMode == "dual" {
            let originalTracks = tracks.filter { $0.evidenceRole == .original }
            return Set(originalTracks.map(\.role)) == Set([.localMic, .remoteSpeaker]) &&
                originalTracks.allSatisfy { $0.sourceKind != nil } &&
                originalTracks.allSatisfy(\.isMediaScribeReady) &&
                (
                    leakageFinalization == nil ||
                        leakageFinalization?.status == .clean &&
                        leakageFinalization?.transcriptionGate == .eligibleOriginalDual
                )
        }

        if mediaScribeSourceMode == "derived_dual" {
            return tracks.contains(where: \.isDerivedTranscriptionEligible) &&
                leakageFinalization?.transcriptionGate == .eligibleDerivedDual
        }

        return false
    }

    public static func transcriptionReadiness(
        forSchemaVersion schemaVersion: String,
        leakageFinalization: LeakageFinalization? = nil,
        tracks: [LocalRecordingTrack] = []
    ) -> TranscriptionReadinessState {
        guard schemaVersion == Self.schemaVersion else {
            return .legacyNotReady
        }
        if leakageFinalization?.transcriptionGate == .eligibleOriginalDual {
            return .ready
        }
        if leakageFinalization?.transcriptionGate == .eligibleDerivedDual &&
            tracks.contains(where: \.isDerivedTranscriptionEligible) {
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

public struct DriverHealthReport: Codable, Equatable, Sendable {
    public var id: String
    public var driverStatus: DriverInstallationState
    public var permissionStatus: [String: String]
    public var routeGraphStatus: String
    public var passthroughStatus: PassthroughStatus
    public var continuityStatus: String
    public var diagnosticRedactionStatus: DiagnosticRedactionStatus
    public var recoveryActions: [String]
    public var createdAt: Date
}

public struct InstallerState: Codable, Equatable, Sendable {
    public var operation: InstallerOperation
    public var state: InstallerOperationState
    public var versionBefore: String?
    public var versionAfter: String?
    public var previousPhysicalInput: String?
    public var previousPhysicalOutput: String?
    public var manualCleanupRequired: Bool
    public var manualCleanupReason: String?
    public var completedAt: Date?
}
