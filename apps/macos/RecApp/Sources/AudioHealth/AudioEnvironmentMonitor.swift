import Foundation
import TwoBrainRecShared

public enum AudioEnvironmentChange: String, Codable, Sendable, Hashable {
    case driverStateChanged
    case virtualInputStateChanged
    case virtualOutputStateChanged
    case permissionChanged
    case routeVerificationChanged
    case passthroughChanged
    case bufferRiskChanged
    case deviceChanged
    case bluetoothProfileChanged
    case activeMeetingContextChanged
    case browserTargetEvidenceChanged
    case unsupportedTargetAdded
    case coreaudiodRestarted
    case sleepWake
}

public struct AudioEnvironmentSnapshot: Codable, Equatable, Sendable {
    public var driverState: DriverInstallationState
    public var virtualMicState: VirtualDeviceAvailabilityState
    public var virtualSpeakerState: VirtualDeviceAvailabilityState
    public var microphonePermission: PermissionStatus
    public var outputPermission: PermissionStatus
    public var physicalInput: HealthPhysicalDeviceSummary?
    public var physicalOutput: HealthPhysicalDeviceSummary?
    public var routeSnapshot: RouteVerificationSnapshot?
    public var passthroughStatus: PassthroughStatus
    public var continuityStatus: String?
    public var bufferRisk: LocalBufferRiskState
    public var activeBrowserName: String?
    public var activeMeetingTitle: String?
    public var browserTargetEvidence: [BrowserTargetEvidence]
    public var livePassthroughStatus: LivePassthroughStatus?
    public var passthroughBrowserEvidence: [PassthroughBrowserCallEvidence]
    public var unsupportedTargets: [String]
    public var bluetoothRouteEvidence: BluetoothRouteEvidence?

    public init(
        driverState: DriverInstallationState,
        virtualMicState: VirtualDeviceAvailabilityState,
        virtualSpeakerState: VirtualDeviceAvailabilityState,
        microphonePermission: PermissionStatus,
        outputPermission: PermissionStatus,
        physicalInput: HealthPhysicalDeviceSummary? = nil,
        physicalOutput: HealthPhysicalDeviceSummary? = nil,
        routeSnapshot: RouteVerificationSnapshot? = nil,
        passthroughStatus: PassthroughStatus,
        continuityStatus: String? = nil,
        bufferRisk: LocalBufferRiskState,
        activeBrowserName: String? = nil,
        activeMeetingTitle: String? = nil,
        browserTargetEvidence: [BrowserTargetEvidence] = [],
        livePassthroughStatus: LivePassthroughStatus? = nil,
        passthroughBrowserEvidence: [PassthroughBrowserCallEvidence] = [],
        unsupportedTargets: [String] = [],
        bluetoothRouteEvidence: BluetoothRouteEvidence? = nil
    ) {
        self.driverState = driverState
        self.virtualMicState = virtualMicState
        self.virtualSpeakerState = virtualSpeakerState
        self.microphonePermission = microphonePermission
        self.outputPermission = outputPermission
        self.physicalInput = physicalInput
        self.physicalOutput = physicalOutput
        self.routeSnapshot = routeSnapshot
        self.passthroughStatus = passthroughStatus
        self.continuityStatus = continuityStatus
        self.bufferRisk = bufferRisk
        self.activeBrowserName = activeBrowserName
        self.activeMeetingTitle = activeMeetingTitle
        self.browserTargetEvidence = browserTargetEvidence
        self.livePassthroughStatus = livePassthroughStatus
        self.passthroughBrowserEvidence = passthroughBrowserEvidence
        self.unsupportedTargets = unsupportedTargets
        self.bluetoothRouteEvidence = bluetoothRouteEvidence
    }
}

public final class AudioEnvironmentMonitor {
    private let now: () -> Date
    private var previous: AudioEnvironmentSnapshot?

    public init(
        initialSnapshot: AudioEnvironmentSnapshot? = nil,
        now: @escaping () -> Date = Date.init
    ) {
        self.previous = initialSnapshot
        self.now = now
    }

    @discardableResult
    public func refresh(with snapshot: AudioEnvironmentSnapshot) -> ([AudioEnvironmentChange], AudioHealthState) {
        let previousSnapshot = previous
        previous = snapshot

        let changes = computeChanges(previous: previousSnapshot, current: snapshot)
        let state = state(from: snapshot)
        return (changes, state)
    }

    public func state(from snapshot: AudioEnvironmentSnapshot) -> AudioHealthState {
        var recoveryActions = gatherRecoveryActions(from: snapshot)

        if snapshot.bufferRisk != .healthy {
            recoveryActions.append("Reduce local cache usage or increase retention limit")
        }

        return AudioHealthState(
            driverState: snapshot.driverState,
            virtualMicState: snapshot.virtualMicState,
            virtualSpeakerState: snapshot.virtualSpeakerState,
            microphonePermission: snapshot.microphonePermission,
            outputPermission: snapshot.outputPermission,
            physicalInput: snapshot.physicalInput,
            physicalOutput: snapshot.physicalOutput,
            routeVerification: snapshot.routeSnapshot,
            passthroughStatus: snapshot.passthroughStatus,
            continuityStatus: snapshot.continuityStatus,
            bufferRisk: snapshot.bufferRisk,
            activeBrowserName: snapshot.activeBrowserName,
            activeMeetingTitle: snapshot.activeMeetingTitle,
            browserTargetEvidence: snapshot.browserTargetEvidence,
            livePassthroughStatus: snapshot.livePassthroughStatus,
            passthroughBrowserEvidence: snapshot.passthroughBrowserEvidence,
            unsupportedTargets: snapshot.unsupportedTargets,
            recoveryActions: recoveryActions,
            lastUpdatedAt: now()
        )
    }

    public func routeInvalidationEvents(
        for changes: [AudioEnvironmentChange],
        previousStatus: LiveRouteReadinessStatus
    ) -> [RouteInvalidationEvent] {
        let sources = Set(changes.compactMap(Self.invalidationSource(for:)))
        return sources.map { source in
            RouteInvalidationEvent(
                source: source,
                previousReadinessStatus: previousStatus,
                newReadinessStatus: source == .bluetoothProfile ? .degraded : .stale,
                detectedAt: now(),
                recoveryAction: "rerun_readiness_check"
            )
        }
        .sorted { $0.source.rawValue < $1.source.rawValue }
    }

    public func livePassthroughRecoveryEvents(
        for changes: [AudioEnvironmentChange],
        previousStatus: LivePassthroughStatus
    ) -> [PassthroughRouteRecoveryEvent] {
        Set(changes.compactMap(Self.recoveryEventType(for:))).map { eventType in
            PassthroughRouteRecoveryEvent(
                eventType: eventType,
                detectedAt: now(),
                previousStatus: previousStatus,
                newStatus: eventType == .appHeartbeatLost ? .degraded : .stale,
                recoveryAction: "rerun_live_passthrough_check"
            )
        }
        .sorted { $0.eventType.rawValue < $1.eventType.rawValue }
    }

    public func lowResourceRecoveryEvents(
        for changes: [AudioEnvironmentChange],
        previousState: AudioResourceState
    ) -> [LowResourceRecoveryEvent] {
        let policy = LowResourceRecoveryPolicy()
        return Set(changes.compactMap(Self.lowResourceRecoveryTrigger(for:))).map { trigger in
            policy.event(
                for: trigger,
                previousState: previousState,
                detectedAt: now()
            )
        }
        .sorted { $0.trigger.rawValue < $1.trigger.rawValue }
    }

    public func autorepairTriggers(for changes: [AudioEnvironmentChange]) -> [AutorepairTrigger] {
        Array(Set(changes.compactMap(Self.autorepairTrigger(for:)))).sorted { $0.rawValue < $1.rawValue }
    }

    public func monitorPermission(
        microphonePermission: PermissionStatus,
        outputPermission: PermissionStatus
    ) -> [AudioEnvironmentChange] {
        guard let previous else {
            return []
        }

        guard previous.microphonePermission != microphonePermission ||
                previous.outputPermission != outputPermission else {
            return []
        }
        return [.permissionChanged]
    }

    private func computeChanges(
        previous: AudioEnvironmentSnapshot?,
        current: AudioEnvironmentSnapshot
    ) -> [AudioEnvironmentChange] {
        guard let previous else {
            return [.driverStateChanged, .permissionChanged, .routeVerificationChanged]
        }

        var result: [AudioEnvironmentChange] = []

        if previous.driverState != current.driverState {
            result.append(.driverStateChanged)
        }
        if previous.virtualMicState != current.virtualMicState {
            result.append(.virtualInputStateChanged)
        }
        if previous.virtualSpeakerState != current.virtualSpeakerState {
            result.append(.virtualOutputStateChanged)
        }
        if previous.microphonePermission != current.microphonePermission ||
            previous.outputPermission != current.outputPermission {
            result.append(.permissionChanged)
        }
        if previous.routeSnapshot != current.routeSnapshot {
            result.append(.routeVerificationChanged)
        }
        if previous.passthroughStatus != current.passthroughStatus {
            result.append(.passthroughChanged)
        }
        if previous.bufferRisk != current.bufferRisk {
            result.append(.bufferRiskChanged)
        }

        if previous.physicalInput?.id != current.physicalInput?.id ||
            previous.physicalOutput?.id != current.physicalOutput?.id {
            result.append(.deviceChanged)
        }

        if previous.bluetoothRouteEvidence != current.bluetoothRouteEvidence {
            result.append(.bluetoothProfileChanged)
        }

        if previous.activeBrowserName != current.activeBrowserName ||
            previous.activeMeetingTitle != current.activeMeetingTitle {
            result.append(.activeMeetingContextChanged)
        }

        if previous.browserTargetEvidence != current.browserTargetEvidence {
            result.append(.browserTargetEvidenceChanged)
        }

        if previous.livePassthroughStatus != current.livePassthroughStatus ||
            previous.passthroughBrowserEvidence != current.passthroughBrowserEvidence {
            result.append(.browserTargetEvidenceChanged)
        }

        if Set(current.unsupportedTargets).subtracting(previous.unsupportedTargets).count > 0 {
            result.append(.unsupportedTargetAdded)
        }

        return Array(Set(result))
    }

    private func gatherRecoveryActions(from snapshot: AudioEnvironmentSnapshot) -> [String] {
        var actions: [String] = []

        if snapshot.driverState == .notInstalled {
            actions.append("Install virtual audio driver")
        }
        if snapshot.driverState == .needsRepair || snapshot.driverState == .needsUpdate {
            actions.append("Repair or update driver")
        }
        if snapshot.microphonePermission != .granted || snapshot.outputPermission != .granted {
            actions.append("Grant required macOS permissions")
        }
        if snapshot.virtualMicState != .available || snapshot.virtualSpeakerState != .available {
            actions.append("Re-verify driver visibility and virtual devices")
        }
        if let routeSnapshot = snapshot.routeSnapshot, !routeSnapshot.canShowReady {
            actions.append("Retry route verification")
        }
        if snapshot.passthroughStatus == .degraded {
            actions.append("Check physical device mute, silent status, and routing")
        }
        if snapshot.passthroughStatus == .failed {
            actions.append("Repair driver path before restarting capture")
        }
        if let livePassthroughStatus = snapshot.livePassthroughStatus,
           [.stale, .degraded, .failed, .blocked].contains(livePassthroughStatus) {
            actions.append("Rerun live passthrough check")
        }
        if snapshot.passthroughStatus == .mutedByPhysicalDevice {
            actions.append("Select a working output speaker profile")
        }
        if let bluetoothEvidence = snapshot.bluetoothRouteEvidence {
            actions.append(contentsOf: BluetoothRoutePolicy().recoveryActions(for: bluetoothEvidence))
        }
        if snapshot.bufferRisk == .mustDegradeOrStop || snapshot.bufferRisk == .critical {
            actions.append("Pause or stop capture and reduce local cache pressure")
        }

        return Array(Set(actions))
    }

    private static func invalidationSource(for change: AudioEnvironmentChange) -> RouteInvalidationSource? {
        switch change {
        case .deviceChanged:
            return .physicalDevice
        case .activeMeetingContextChanged, .browserTargetEvidenceChanged:
            return .browserTarget
        case .bluetoothProfileChanged:
            return .bluetoothProfile
        case .virtualInputStateChanged, .virtualOutputStateChanged, .driverStateChanged:
            return .appIO
        case .coreaudiodRestarted:
            return .coreaudiod
        case .sleepWake:
            return .appIO
        case .routeVerificationChanged, .permissionChanged, .passthroughChanged, .bufferRiskChanged, .unsupportedTargetAdded:
            return nil
        }
    }

    private static func recoveryEventType(for change: AudioEnvironmentChange) -> RouteRecoveryEventType? {
        switch change {
        case .deviceChanged:
            return .physicalInputChanged
        case .activeMeetingContextChanged, .browserTargetEvidenceChanged:
            return .browserTargetChanged
        case .bluetoothProfileChanged:
            return .bluetoothProfileChanged
        case .driverStateChanged, .virtualInputStateChanged, .virtualOutputStateChanged:
            return .driverReloaded
        case .coreaudiodRestarted:
            return .coreaudiodRestarted
        case .sleepWake:
            return .driverReloaded
        case .passthroughChanged:
            return .appHeartbeatLost
        case .routeVerificationChanged, .permissionChanged, .bufferRiskChanged, .unsupportedTargetAdded:
            return nil
        }
    }

    private static func lowResourceRecoveryTrigger(for change: AudioEnvironmentChange) -> LowResourceRecoveryTrigger? {
        switch change {
        case .passthroughChanged:
            return .staleHeartbeat
        case .coreaudiodRestarted:
            return .coreaudiodRestart
        case .sleepWake:
            return .sleepWake
        case .deviceChanged:
            return .physicalDeviceChanged
        case .activeMeetingContextChanged, .browserTargetEvidenceChanged:
            return .browserDeviceChanged
        case .driverStateChanged, .virtualInputStateChanged, .virtualOutputStateChanged, .permissionChanged,
             .routeVerificationChanged, .bufferRiskChanged, .bluetoothProfileChanged, .unsupportedTargetAdded:
            return nil
        }
    }

    private static func autorepairTrigger(for change: AudioEnvironmentChange) -> AutorepairTrigger? {
        switch change {
        case .coreaudiodRestarted:
            return .coreaudiodRestart
        case .sleepWake:
            return .sleepWake
        case .deviceChanged:
            return .physicalDeviceDisappeared
        case .driverStateChanged, .virtualInputStateChanged, .virtualOutputStateChanged:
            return .halReload
        case .activeMeetingContextChanged, .browserTargetEvidenceChanged:
            return .browserStreamRecreated
        case .routeVerificationChanged:
            return .macOSDefaultRouteChanged
        case .permissionChanged, .passthroughChanged, .bufferRiskChanged, .bluetoothProfileChanged, .unsupportedTargetAdded:
            return nil
        }
    }
}
