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
    case unsupportedTargetAdded
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
            unsupportedTargets: snapshot.unsupportedTargets,
            recoveryActions: recoveryActions,
            lastUpdatedAt: now()
        )
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
}
