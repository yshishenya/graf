import Foundation

public enum AudioResourceState: String, Codable, CaseIterable, Sendable {
    case idleSafe = "idle_safe"
    case starting
    case ready
    case active
    case stale
    case blocked
    case failed
    case retrying
    case fallback
}

public enum LowResourceEvidenceResult: String, Codable, Sendable {
    case passed
    case blocked
    case failed
    case notAccepted = "not_accepted"
}

public enum ClientActivitySource: String, Codable, Sendable {
    case driverStartStop = "driver_start_stop"
    case deviceIsRunning = "device_is_running"
    case testFixture = "test_fixture"
    case browserDeviceSelection = "browser_device_selection"
    case coreAudioClient = "core_audio_client"
    case appBridge = "app_bridge"
    case validationFixture = "validation_fixture"
}

public enum AppBridgeHeartbeatState: String, Codable, Sendable {
    case waitingForApp = "waiting_for_app"
    case connected
    case heartbeatLost = "heartbeat_lost"
}

public enum PhysicalWorkingDeviceKind: String, Codable, Sendable {
    case physical
    case twoBrainVirtual = "2brain_virtual"
    case otherVirtual = "other_virtual"
    case aggregate
    case multiOutput = "multi_output"
    case bluetooth
    case unknown
}

public enum PhysicalWorkingDeviceSelectionResult: String, Codable, Sendable {
    case accepted
    case rejected
    case blocked
    case notAccepted = "not_accepted"
}

public enum RecordingTriggerState: String, Codable, Sendable {
    case off
    case armedFuture = "armed_future"
    case activeFuture = "active_future"
}

public enum StartupAttemptTrigger: String, Codable, Sendable {
    case clientIOOpened = "client_io_opened"
    case retry
    case recovery
    case manualCheck = "manual_check"
    case testFixture = "test_fixture"
}

public enum StartupAttemptOutcome: String, Codable, Sendable {
    case ready
    case blocked
    case failed
    case fallback
}

public struct VirtualDevicePublicationEvidence: Codable, Equatable, Sendable {
    public var microphoneVisible: Bool
    public var speakerVisible: Bool
    public var microphoneAlive: Bool?
    public var speakerAlive: Bool?
    public var microphoneRunning: Bool?
    public var speakerRunning: Bool?
    public var hidden: Bool
    public var runtimeProbeResult: LowResourceEvidenceResult

    public init(
        microphoneVisible: Bool,
        speakerVisible: Bool,
        microphoneAlive: Bool?,
        speakerAlive: Bool?,
        microphoneRunning: Bool?,
        speakerRunning: Bool?,
        hidden: Bool,
        runtimeProbeResult: LowResourceEvidenceResult
    ) {
        self.microphoneVisible = microphoneVisible
        self.speakerVisible = speakerVisible
        self.microphoneAlive = microphoneAlive
        self.speakerAlive = speakerAlive
        self.microphoneRunning = microphoneRunning
        self.speakerRunning = speakerRunning
        self.hidden = hidden
        self.runtimeProbeResult = runtimeProbeResult
    }
}

public struct ClientActivityEvidence: Codable, Equatable, Sendable {
    public var microphoneClientCount: Int
    public var speakerClientCount: Int
    public var microphoneRunning: Bool
    public var speakerRunning: Bool
    public var source: ClientActivitySource
    public var naturalSilenceAllowed: Bool

    public init(
        microphoneClientCount: Int,
        speakerClientCount: Int,
        microphoneRunning: Bool,
        speakerRunning: Bool,
        source: ClientActivitySource,
        naturalSilenceAllowed: Bool = true
    ) {
        self.microphoneClientCount = microphoneClientCount
        self.speakerClientCount = speakerClientCount
        self.microphoneRunning = microphoneRunning
        self.speakerRunning = speakerRunning
        self.source = source
        self.naturalSilenceAllowed = naturalSilenceAllowed
    }

    public var hasOpenStream: Bool {
        microphoneClientCount > 0 || speakerClientCount > 0 || microphoneRunning || speakerRunning
    }
}

public struct AppBridgeHealthEvidence: Codable, Equatable, Sendable {
    public var heartbeatState: AppBridgeHeartbeatState
    public var lastHeartbeatAt: Date?
    public var timeoutMs: Int
    public var driverFailClosed: Bool
    public var publicDeviceAvailability: String
    public var recoveryAction: String

    public init(
        heartbeatState: AppBridgeHeartbeatState,
        lastHeartbeatAt: Date? = nil,
        timeoutMs: Int = 3000,
        driverFailClosed: Bool,
        publicDeviceAvailability: String = "available",
        recoveryAction: String = "none"
    ) {
        self.heartbeatState = heartbeatState
        self.lastHeartbeatAt = lastHeartbeatAt
        self.timeoutMs = timeoutMs
        self.driverFailClosed = driverFailClosed
        self.publicDeviceAvailability = publicDeviceAvailability
        self.recoveryAction = recoveryAction
    }

    public var isFresh: Bool {
        heartbeatState == .connected
    }
}

public struct PhysicalWorkingDeviceSelection: Codable, Equatable, Sendable {
    public var inputDeviceId: String
    public var inputDeviceName: String
    public var outputDeviceId: String
    public var outputDeviceName: String
    public var inputKind: PhysicalWorkingDeviceKind
    public var outputKind: PhysicalWorkingDeviceKind
    public var selectionResult: PhysicalWorkingDeviceSelectionResult
    public var rejectionReason: String?

    public init(
        inputDeviceId: String,
        inputDeviceName: String,
        outputDeviceId: String,
        outputDeviceName: String,
        inputKind: PhysicalWorkingDeviceKind,
        outputKind: PhysicalWorkingDeviceKind,
        selectionResult: PhysicalWorkingDeviceSelectionResult,
        rejectionReason: String? = nil
    ) {
        self.inputDeviceId = inputDeviceId
        self.inputDeviceName = inputDeviceName
        self.outputDeviceId = outputDeviceId
        self.outputDeviceName = outputDeviceName
        self.inputKind = inputKind
        self.outputKind = outputKind
        self.selectionResult = selectionResult
        self.rejectionReason = rejectionReason
    }

    public var isReleaseReady: Bool {
        selectionResult == .accepted && inputKind == .physical && outputKind == .physical
    }
}

public struct RecordingTriggerBoundary: Codable, Equatable, Sendable {
    public var recordingTriggerState: RecordingTriggerState
    public var driverRecordingOwner: Bool
    public var appRecordingOwner: Bool
    public var recordingArtifactsCreated: Bool
    public var externalEgressStarted: Bool

    public init(
        recordingTriggerState: RecordingTriggerState = .off,
        driverRecordingOwner: Bool = false,
        appRecordingOwner: Bool = true,
        recordingArtifactsCreated: Bool = false,
        externalEgressStarted: Bool = false
    ) {
        self.recordingTriggerState = recordingTriggerState
        self.driverRecordingOwner = driverRecordingOwner
        self.appRecordingOwner = appRecordingOwner
        self.recordingArtifactsCreated = recordingArtifactsCreated
        self.externalEgressStarted = externalEgressStarted
    }

    public var isSafeFor006: Bool {
        recordingTriggerState == .off &&
            !driverRecordingOwner &&
            appRecordingOwner &&
            !recordingArtifactsCreated &&
            !externalEgressStarted
    }
}

public struct RouteTruthSnapshot: Codable, Equatable, Sendable {
    public var snapshotId: String
    public var recordedAt: Date
    public var publication: VirtualDevicePublicationEvidence
    public var clientActivity: ClientActivityEvidence
    public var appBridgeHealth: AppBridgeHealthEvidence
    public var physicalDevices: PhysicalWorkingDeviceSelection
    public var recordingTrigger: RecordingTriggerBoundary
    public var resourceState: AudioResourceState
    public var result: LowResourceEvidenceResult

    public init(
        snapshotId: String,
        recordedAt: Date,
        publication: VirtualDevicePublicationEvidence,
        clientActivity: ClientActivityEvidence,
        appBridgeHealth: AppBridgeHealthEvidence,
        physicalDevices: PhysicalWorkingDeviceSelection,
        recordingTrigger: RecordingTriggerBoundary,
        resourceState: AudioResourceState,
        result: LowResourceEvidenceResult
    ) {
        self.snapshotId = snapshotId
        self.recordedAt = recordedAt
        self.publication = publication
        self.clientActivity = clientActivity
        self.appBridgeHealth = appBridgeHealth
        self.physicalDevices = physicalDevices
        self.recordingTrigger = recordingTrigger
        self.resourceState = resourceState
        self.result = result
    }
}

public struct StartupAttemptEvidence: Codable, Equatable, Sendable {
    public static let maximumDurationMs = 3000

    public var attemptId: String
    public var trigger: StartupAttemptTrigger
    public var startedAt: Date
    public var completedAt: Date
    public var durationMs: Int
    public var outcome: StartupAttemptOutcome
    public var blockedReason: String?
    public var fallbackUsed: Bool

    public init(
        attemptId: String,
        trigger: StartupAttemptTrigger,
        startedAt: Date,
        completedAt: Date,
        durationMs: Int,
        outcome: StartupAttemptOutcome,
        blockedReason: String? = nil,
        fallbackUsed: Bool = false
    ) {
        self.attemptId = attemptId
        self.trigger = trigger
        self.startedAt = startedAt
        self.completedAt = completedAt
        self.durationMs = durationMs
        self.outcome = outcome
        self.blockedReason = blockedReason
        self.fallbackUsed = fallbackUsed
    }

    public var isWithinAcceptedWindow: Bool {
        durationMs <= Self.maximumDurationMs
    }
}

public struct RealtimeSafetyEvidence: Codable, Equatable, Sendable {
    public var scanId: String
    public var checkedPaths: [String]
    public var forbiddenOperationFindings: [String]
    public var result: LowResourceEvidenceResult

    public init(
        scanId: String,
        checkedPaths: [String],
        forbiddenOperationFindings: [String] = [],
        result: LowResourceEvidenceResult
    ) {
        self.scanId = scanId
        self.checkedPaths = checkedPaths
        self.forbiddenOperationFindings = forbiddenOperationFindings
        self.result = result
    }
}

public struct LowResourceValidationRun: Codable, Equatable, Sendable {
    public var runId: String
    public var createdAt: Date
    public var appBuild: String
    public var driverBuild: String
    public var baseline: String
    public var routeTruthSnapshots: [RouteTruthSnapshot]
    public var startupAttempts: [StartupAttemptEvidence]
    public var realtimeSafety: RealtimeSafetyEvidence
    public var noHangResults: [String]
    public var cpuResults: [String]
    public var recoveryResults: [String]
    public var result: LowResourceEvidenceResult

    public init(
        runId: String,
        createdAt: Date,
        appBuild: String,
        driverBuild: String,
        baseline: String = "005-macos-passthrough-release-hardening",
        routeTruthSnapshots: [RouteTruthSnapshot],
        startupAttempts: [StartupAttemptEvidence],
        realtimeSafety: RealtimeSafetyEvidence,
        noHangResults: [String] = [],
        cpuResults: [String] = [],
        recoveryResults: [String] = [],
        result: LowResourceEvidenceResult
    ) {
        self.runId = runId
        self.createdAt = createdAt
        self.appBuild = appBuild
        self.driverBuild = driverBuild
        self.baseline = baseline
        self.routeTruthSnapshots = routeTruthSnapshots
        self.startupAttempts = startupAttempts
        self.realtimeSafety = realtimeSafety
        self.noHangResults = noHangResults
        self.cpuResults = cpuResults
        self.recoveryResults = recoveryResults
        self.result = result
    }
}
