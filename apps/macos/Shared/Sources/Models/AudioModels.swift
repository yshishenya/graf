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

    public init(
        speakerReferenceDb: Double,
        virtualMicLeakageDb: Double,
        relativeLeakageDb: Double,
        intelligibilityStatus: IntelligibilityStatus,
        status: MeasurementStatus,
        measuredAt: Date
    ) {
        self.speakerReferenceDb = speakerReferenceDb
        self.virtualMicLeakageDb = virtualMicLeakageDb
        self.relativeLeakageDb = relativeLeakageDb
        self.intelligibilityStatus = intelligibilityStatus
        self.status = status
        self.measuredAt = measuredAt
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
        stoppedAt: Date?
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
