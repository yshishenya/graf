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
}

public struct RouteVerification: Codable, Equatable, Sendable {
    public var id: String
    public var path: RoutePath
    public var validationType: RouteValidationType
    public var target: String?
    public var status: RouteVerificationStatus
    public var failureReason: String?
    public var recoveryAction: String?
    public var startedAt: Date
    public var finishedAt: Date?
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
