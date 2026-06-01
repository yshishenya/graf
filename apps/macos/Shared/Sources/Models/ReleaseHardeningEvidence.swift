import Foundation

public enum ReleaseHardeningEvidenceFamily: String, Codable, Sendable {
    case installedRuntime = "installed_runtime"
    case noHang = "no_hang"
    case shortSmoke = "short_smoke"
    case routeRecovery = "route_recovery"
    case installerLifecycle = "installer_lifecycle"
    case diagnostics
    case uxReadiness = "ux_readiness"
    case deferredRecordingAcceptance = "deferred_recording_acceptance"
}

public enum ReleaseHardeningRouteState: String, Codable, Sendable {
    case ready
    case active
    case stale
    case degraded
    case failed
    case blocked
    case repair
    case recheck
}

public struct ReleaseHardeningRun: Codable, Equatable, Sendable {
    public var runId: String
    public var createdAt: Date
    public var macOSVersion: String
    public var appBuild: String
    public var driverBuild: String
    public var result: ReleaseHardeningResult
    public var notes: String
    public var evidenceFamilies: [ReleaseHardeningEvidenceFamily]

    public init(
        runId: String,
        createdAt: Date,
        macOSVersion: String,
        appBuild: String,
        driverBuild: String,
        result: ReleaseHardeningResult,
        notes: String,
        evidenceFamilies: [ReleaseHardeningEvidenceFamily] = []
    ) {
        self.runId = runId
        self.createdAt = createdAt
        self.macOSVersion = macOSVersion
        self.appBuild = appBuild
        self.driverBuild = driverBuild
        self.result = result
        self.notes = notes
        self.evidenceFamilies = evidenceFamilies
    }
}

public struct CoreAudioNoHangEvidence: Codable, Equatable, Sendable {
    public var targetSurface: String
    public var openedWithinSeconds: Double
    public var coreaudiodCPUPeakPercent: Double
    public var coreaudiodCPUSustainedPercent: Double
    public var routeStateBefore: ReleaseHardeningRouteState
    public var routeStateAfter: ReleaseHardeningRouteState
    public var result: ReleaseHardeningResult
    public var failureReason: String?

    public init(
        targetSurface: String,
        openedWithinSeconds: Double,
        coreaudiodCPUPeakPercent: Double,
        coreaudiodCPUSustainedPercent: Double,
        routeStateBefore: ReleaseHardeningRouteState,
        routeStateAfter: ReleaseHardeningRouteState,
        result: ReleaseHardeningResult,
        failureReason: String? = nil
    ) {
        self.targetSurface = targetSurface
        self.openedWithinSeconds = openedWithinSeconds
        self.coreaudiodCPUPeakPercent = coreaudiodCPUPeakPercent
        self.coreaudiodCPUSustainedPercent = coreaudiodCPUSustainedPercent
        self.routeStateBefore = routeStateBefore
        self.routeStateAfter = routeStateAfter
        self.result = result
        self.failureReason = failureReason
    }
}

public struct ShortSmokeEvidence: Codable, Equatable, Sendable {
    public var targetApp: String
    public var selectedInput: String
    public var selectedOutput: String
    public var localSpeechObserved: Bool?
    public var remoteAudioObserved: Bool?
    public var loopbackObserved: Bool?
    public var recordingStarted: Bool
    public var result: ReleaseHardeningResult

    public init(
        targetApp: String,
        selectedInput: String,
        selectedOutput: String,
        localSpeechObserved: Bool?,
        remoteAudioObserved: Bool?,
        loopbackObserved: Bool?,
        recordingStarted: Bool,
        result: ReleaseHardeningResult
    ) {
        self.targetApp = targetApp
        self.selectedInput = selectedInput
        self.selectedOutput = selectedOutput
        self.localSpeechObserved = localSpeechObserved
        self.remoteAudioObserved = remoteAudioObserved
        self.loopbackObserved = loopbackObserved
        self.recordingStarted = recordingStarted
        self.result = result
    }
}

public struct RouteRecoveryEvidence: Codable, Equatable, Sendable {
    public var trigger: String
    public var detectedWithinSeconds: Double
    public var expectedState: ReleaseHardeningRouteState
    public var actualState: ReleaseHardeningRouteState
    public var recoveryAction: String
    public var result: ReleaseHardeningResult

    public init(
        trigger: String,
        detectedWithinSeconds: Double,
        expectedState: ReleaseHardeningRouteState,
        actualState: ReleaseHardeningRouteState,
        recoveryAction: String,
        result: ReleaseHardeningResult
    ) {
        self.trigger = trigger
        self.detectedWithinSeconds = detectedWithinSeconds
        self.expectedState = expectedState
        self.actualState = actualState
        self.recoveryAction = recoveryAction
        self.result = result
    }
}

public struct InstallerLifecycleEvidence: Codable, Equatable, Sendable {
    public var operation: String
    public var preState: String
    public var postState: String
    public var coreAudioRefreshRequired: Bool
    public var runtimeProbeResult: String
    public var result: ReleaseHardeningResult

    public init(
        operation: String,
        preState: String,
        postState: String,
        coreAudioRefreshRequired: Bool,
        runtimeProbeResult: String,
        result: ReleaseHardeningResult
    ) {
        self.operation = operation
        self.preState = preState
        self.postState = postState
        self.coreAudioRefreshRequired = coreAudioRefreshRequired
        self.runtimeProbeResult = runtimeProbeResult
        self.result = result
    }
}

public struct UXReadinessEvidence: Codable, Equatable, Sendable {
    public var state: ReleaseHardeningRouteState
    public var copyClaim: String
    public var nonRecordingExplicit: Bool
    public var recordingImplied: Bool
    public var accessibilityNotes: String
    public var result: ReleaseHardeningResult

    public init(
        state: ReleaseHardeningRouteState,
        copyClaim: String,
        nonRecordingExplicit: Bool,
        recordingImplied: Bool,
        accessibilityNotes: String,
        result: ReleaseHardeningResult
    ) {
        self.state = state
        self.copyClaim = copyClaim
        self.nonRecordingExplicit = nonRecordingExplicit
        self.recordingImplied = recordingImplied
        self.accessibilityNotes = accessibilityNotes
        self.result = result
    }
}

public struct DeferredRecordingAcceptanceState: Codable, Equatable, Sendable {
    public var blockedUntil: String
    public var retentionPolicyRequired: Bool
    public var deletionPolicyRequired: Bool
    public var result: ReleaseHardeningResult

    public init(
        blockedUntil: String = "local_recording_support",
        retentionPolicyRequired: Bool = true,
        deletionPolicyRequired: Bool = true,
        result: ReleaseHardeningResult = .blocked
    ) {
        self.blockedUntil = blockedUntil
        self.retentionPolicyRequired = retentionPolicyRequired
        self.deletionPolicyRequired = deletionPolicyRequired
        self.result = result
    }
}
