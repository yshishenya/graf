import Foundation

public struct AppIOHealthPolicy: Sendable {
    public var heartbeatTimeoutMs: Int
    public var failClosedRecoveryAction: String
    public var keepsPublicDevicesVisibleOnFailure: Bool

    public init(
        heartbeatTimeoutMs: Int = 3000,
        failClosedRecoveryAction: String = "restart_desktop_audio_engine",
        keepsPublicDevicesVisibleOnFailure: Bool = true
    ) {
        self.heartbeatTimeoutMs = heartbeatTimeoutMs
        self.failClosedRecoveryAction = failClosedRecoveryAction
        self.keepsPublicDevicesVisibleOnFailure = keepsPublicDevicesVisibleOnFailure
    }

    public func evaluate(lastHeartbeatAt: Date?, now: Date) -> PrivateAppIOHealth {
        let failureAvailability: VirtualDeviceAvailabilityState = keepsPublicDevicesVisibleOnFailure ? .available : .hidden

        guard let lastHeartbeatAt else {
            return PrivateAppIOHealth(
                state: .waitingForApp,
                publicDeviceAvailability: failureAvailability,
                recoveryAction: failClosedRecoveryAction
            )
        }

        let elapsedMs = now.timeIntervalSince(lastHeartbeatAt) * 1000
        if elapsedMs > Double(heartbeatTimeoutMs) {
            return PrivateAppIOHealth(
                state: .heartbeatLost,
                lastHeartbeatAt: lastHeartbeatAt,
                missedHeartbeatCount: 1,
                publicDeviceAvailability: failureAvailability,
                recoveryAction: failClosedRecoveryAction
            )
        }

        return PrivateAppIOHealth(
            state: .connected,
            lastHeartbeatAt: lastHeartbeatAt,
            missedHeartbeatCount: 0,
            publicDeviceAvailability: .available,
            recoveryAction: nil
        )
    }
}

public enum LowResourceRecoveryTrigger: String, Codable, CaseIterable, Sendable {
    case staleHeartbeat = "stale_heartbeat"
    case coreaudiodRestart = "coreaudiod_restart"
    case sleepWake = "sleep_wake"
    case physicalDeviceChanged = "physical_device_changed"
    case browserDeviceChanged = "browser_device_changed"
}

public struct LowResourceRecoveryEvent: Codable, Equatable, Sendable {
    public var trigger: LowResourceRecoveryTrigger
    public var previousState: AudioResourceState
    public var newState: AudioResourceState
    public var detectedAt: Date
    public var recoveryAction: String
    public var publicDeviceAvailability: VirtualDeviceAvailabilityState

    public init(
        trigger: LowResourceRecoveryTrigger,
        previousState: AudioResourceState,
        newState: AudioResourceState = .stale,
        detectedAt: Date,
        recoveryAction: String,
        publicDeviceAvailability: VirtualDeviceAvailabilityState = .available
    ) {
        self.trigger = trigger
        self.previousState = previousState
        self.newState = newState
        self.detectedAt = detectedAt
        self.recoveryAction = recoveryAction
        self.publicDeviceAvailability = publicDeviceAvailability
    }
}

public struct LowResourceRecoveryPolicy: Sendable {
    public init() {}

    public func event(
        for trigger: LowResourceRecoveryTrigger,
        previousState: AudioResourceState,
        detectedAt: Date
    ) -> LowResourceRecoveryEvent {
        LowResourceRecoveryEvent(
            trigger: trigger,
            previousState: previousState,
            detectedAt: detectedAt,
            recoveryAction: recoveryAction(for: trigger)
        )
    }

    public func recoveryAction(for trigger: LowResourceRecoveryTrigger) -> String {
        switch trigger {
        case .staleHeartbeat:
            return "restart_desktop_audio_engine"
        case .coreaudiodRestart:
            return "rebuild_audio_route_after_coreaudiod_restart"
        case .sleepWake:
            return "revalidate_route_after_sleep_wake"
        case .physicalDeviceChanged:
            return "reselect_physical_working_devices"
        case .browserDeviceChanged:
            return "ask_user_to_reselect_2brain_virtual_devices"
        }
    }
}
