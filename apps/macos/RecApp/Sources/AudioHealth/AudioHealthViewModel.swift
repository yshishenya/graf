import Foundation
import TwoBrainRecShared

public enum PermissionStatus: String, Codable, Sendable {
    case unknown
    case granted
    case denied
    case restricted
    case unavailable
}

public enum HealthActionStatus: String, Codable, Sendable {
    case notStarted = "not_started"
    case running
    case passed
    case failed
    case degraded
}

public struct HealthActionState: Codable, Equatable, Sendable {
    public var status: HealthActionStatus
    public var startedAt: Date?
    public var finishedAt: Date?
    public var note: String?

    public init(
        status: HealthActionStatus = .notStarted,
        startedAt: Date? = nil,
        finishedAt: Date? = nil,
        note: String? = nil
    ) {
        self.status = status
        self.startedAt = startedAt
        self.finishedAt = finishedAt
        self.note = note
    }
}

public struct HealthPhysicalDeviceSummary: Codable, Equatable, Sendable {
    public var id: String
    public var displayName: String
    public var direction: AudioDirection
    public var className: PhysicalDeviceClass?
    public var availabilityState: PhysicalDeviceAvailabilityState
    public var lastChangedAt: Date?

    public init(
        id: String,
        displayName: String,
        direction: AudioDirection,
        className: PhysicalDeviceClass? = nil,
        availabilityState: PhysicalDeviceAvailabilityState = .available,
        lastChangedAt: Date? = nil
    ) {
        self.id = id
        self.displayName = displayName
        self.direction = direction
        self.className = className
        self.availabilityState = availabilityState
        self.lastChangedAt = lastChangedAt
    }
}

public struct AudioHealthState: Codable, Equatable, Sendable {
    public var driverState: DriverInstallationState
    public var virtualMicState: VirtualDeviceAvailabilityState
    public var virtualSpeakerState: VirtualDeviceAvailabilityState
    public var microphonePermission: PermissionStatus
    public var outputPermission: PermissionStatus
    public var physicalInput: HealthPhysicalDeviceSummary?
    public var physicalOutput: HealthPhysicalDeviceSummary?
    public var routeVerification: RouteVerificationSnapshot?
    public var passthroughStatus: PassthroughStatus
    public var continuityStatus: String?
    public var bufferRisk: LocalBufferRiskState
    public var testRecording: HealthActionState
    public var testPlayback: HealthActionState
    public var activeBrowserName: String?
    public var activeMeetingTitle: String?
    public var browserTargetEvidence: [BrowserTargetEvidence]
    public var livePassthroughStatus: LivePassthroughStatus?
    public var passthroughBrowserEvidence: [PassthroughBrowserCallEvidence]
    public var unsupportedTargets: [String]
    public var recoveryActions: [String]
    public var lastUpdatedAt: Date

    public init(
        driverState: DriverInstallationState = .notInstalled,
        virtualMicState: VirtualDeviceAvailabilityState = .missing,
        virtualSpeakerState: VirtualDeviceAvailabilityState = .missing,
        microphonePermission: PermissionStatus = .unknown,
        outputPermission: PermissionStatus = .unknown,
        physicalInput: HealthPhysicalDeviceSummary? = nil,
        physicalOutput: HealthPhysicalDeviceSummary? = nil,
        routeVerification: RouteVerificationSnapshot? = nil,
        passthroughStatus: PassthroughStatus = .unknown,
        continuityStatus: String? = nil,
        bufferRisk: LocalBufferRiskState = .healthy,
        testRecording: HealthActionState = .init(),
        testPlayback: HealthActionState = .init(),
        activeBrowserName: String? = nil,
        activeMeetingTitle: String? = nil,
        browserTargetEvidence: [BrowserTargetEvidence] = [],
        livePassthroughStatus: LivePassthroughStatus? = nil,
        passthroughBrowserEvidence: [PassthroughBrowserCallEvidence] = [],
        unsupportedTargets: [String] = [],
        recoveryActions: [String] = [],
        lastUpdatedAt: Date = Date()
    ) {
        self.driverState = driverState
        self.virtualMicState = virtualMicState
        self.virtualSpeakerState = virtualSpeakerState
        self.microphonePermission = microphonePermission
        self.outputPermission = outputPermission
        self.physicalInput = physicalInput
        self.physicalOutput = physicalOutput
        self.routeVerification = routeVerification
        self.passthroughStatus = passthroughStatus
        self.continuityStatus = continuityStatus
        self.bufferRisk = bufferRisk
        self.testRecording = testRecording
        self.testPlayback = testPlayback
        self.activeBrowserName = activeBrowserName
        self.activeMeetingTitle = activeMeetingTitle
        self.browserTargetEvidence = browserTargetEvidence
        self.livePassthroughStatus = livePassthroughStatus
        self.passthroughBrowserEvidence = passthroughBrowserEvidence
        self.unsupportedTargets = unsupportedTargets
        self.recoveryActions = recoveryActions
        self.lastUpdatedAt = lastUpdatedAt
    }

    public var isRouteReady: Bool {
        routeVerification?.canShowReady ?? false
    }

    public var routeReadinessSummary: String {
        guard let routeVerification else {
            return "not_started"
        }
        if routeVerification.canShowReady {
            return "ready"
        }
        if routeVerification.mic.status == .stale || routeVerification.speaker.status == .stale {
            return "stale"
        }
        if routeVerification.mic.status == .failed || routeVerification.speaker.status == .failed {
            return "failed"
        }
        return "not_started"
    }

    public mutating func applyLatencyAndLeakage(
        latency: LatencyMeasurement?,
        leakage: LeakageMeasurement?
    ) {
        if latency?.status == .degraded || leakage?.status == .degraded {
            passthroughStatus = .degraded
            if latency?.status == .degraded {
                recoveryActions.append("Reduce route latency before release readiness")
            }
            if leakage?.status == .degraded {
                recoveryActions.append("Reduce remote-to-mic leakage before release readiness")
            }
        }
    }

    public var canRecord: Bool {
        if isPermissionBlocked { return false }
        if !isRouteReady { return false }
        if passthroughStatus == .failed { return false }
        if bufferRisk == .mustDegradeOrStop { return false }
        return true
    }

    public var isPermissionBlocked: Bool {
        microphonePermission != .granted || outputPermission != .granted
    }

    public var requiresAttention: Bool {
        !recoveryActions.isEmpty || !isRouteReady || isPermissionBlocked || bufferRisk != .healthy
    }
}

public final class AudioHealthViewModel {
    public private(set) var state: AudioHealthState

    public init(state: AudioHealthState = AudioHealthState()) {
        self.state = state
    }

    public func update(
        driverState: DriverInstallationState? = nil,
        virtualInputState: VirtualDeviceAvailabilityState? = nil,
        virtualOutputState: VirtualDeviceAvailabilityState? = nil,
        microphonePermission: PermissionStatus? = nil,
        outputPermission: PermissionStatus? = nil,
        physicalInput: HealthPhysicalDeviceSummary? = nil,
        physicalOutput: HealthPhysicalDeviceSummary? = nil,
        routeVerification: RouteVerificationSnapshot? = nil,
        passthroughStatus: PassthroughStatus? = nil,
        continuityStatus: String? = nil,
        bufferRisk: LocalBufferRiskState? = nil,
        activeBrowserName: String? = nil,
        activeMeetingTitle: String? = nil,
        browserTargetEvidence: [BrowserTargetEvidence]? = nil,
        livePassthroughStatus: LivePassthroughStatus? = nil,
        passthroughBrowserEvidence: [PassthroughBrowserCallEvidence]? = nil,
        unsupportedTargets: [String]? = nil,
        recoveryActions: [String]? = nil
    ) {
        if let driverState {
            state.driverState = driverState
        }
        if let virtualInputState {
            state.virtualMicState = virtualInputState
        }
        if let virtualOutputState {
            state.virtualSpeakerState = virtualOutputState
        }
        if let microphonePermission {
            state.microphonePermission = microphonePermission
        }
        if let outputPermission {
            state.outputPermission = outputPermission
        }
        if let physicalInput {
            state.physicalInput = physicalInput
        }
        if let physicalOutput {
            state.physicalOutput = physicalOutput
        }
        if let routeVerification {
            state.routeVerification = routeVerification
        }
        if let passthroughStatus {
            state.passthroughStatus = passthroughStatus
        }
        if let continuityStatus {
            state.continuityStatus = continuityStatus
        }
        if let bufferRisk {
            state.bufferRisk = bufferRisk
        }
        if let activeBrowserName {
            state.activeBrowserName = activeBrowserName
        }
        if let activeMeetingTitle {
            state.activeMeetingTitle = activeMeetingTitle
        }
        if let browserTargetEvidence {
            state.browserTargetEvidence = browserTargetEvidence
        }
        if let livePassthroughStatus {
            state.livePassthroughStatus = livePassthroughStatus
        }
        if let passthroughBrowserEvidence {
            state.passthroughBrowserEvidence = passthroughBrowserEvidence
        }
        if let unsupportedTargets {
            state.unsupportedTargets = unsupportedTargets
        }
        if let recoveryActions {
            state.recoveryActions = recoveryActions
        }
        state.lastUpdatedAt = Date()
    }

    public func beginTestRecording() {
        state.testRecording = HealthActionState(
            status: .running,
            startedAt: Date()
        )
    }

    public func finishTestRecording(passed: Bool, note: String? = nil) {
        state.testRecording = HealthActionState(
            status: passed ? .passed : .failed,
            startedAt: state.testRecording.startedAt,
            finishedAt: Date(),
            note: note
        )
    }

    public func beginTestPlayback() {
        state.testPlayback = HealthActionState(
            status: .running,
            startedAt: Date()
        )
    }

    public func finishTestPlayback(passed: Bool, note: String? = nil) {
        state.testPlayback = HealthActionState(
            status: passed ? .passed : .failed,
            startedAt: state.testPlayback.startedAt,
            finishedAt: Date(),
            note: note
        )
    }

    public func markRecoveryNeeded(_ suggestions: [String]) {
        state.recoveryActions = suggestions
        state.lastUpdatedAt = Date()
    }

    public func clearRecoverySuggestions() {
        state.recoveryActions = []
        state.lastUpdatedAt = Date()
    }

    public func applyLowResourceStartupState(_ resourceState: AudioResourceState, reason: String? = nil) {
        switch resourceState {
        case .blocked:
            state.passthroughStatus = .failed
            state.livePassthroughStatus = .blocked
            state.recoveryActions.append(reason ?? "Retry audio route startup")
        case .failed:
            state.passthroughStatus = .failed
            state.livePassthroughStatus = .failed
            state.recoveryActions.append(reason ?? "Review audio route diagnostics")
        case .retrying:
            state.livePassthroughStatus = .checking
        case .ready:
            state.livePassthroughStatus = .ready
        case .active:
            state.livePassthroughStatus = .active
        default:
            break
        }
        state.lastUpdatedAt = Date()
    }

    public func currentState() -> AudioHealthState {
        state
    }
}
