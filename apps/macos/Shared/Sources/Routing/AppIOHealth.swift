import Foundation

public struct AppIOHealthPolicy: Sendable {
    public var heartbeatTimeoutMs: Int
    public var failClosedRecoveryAction: String

    public init(
        heartbeatTimeoutMs: Int = 3000,
        failClosedRecoveryAction: String = "restart_desktop_audio_engine"
    ) {
        self.heartbeatTimeoutMs = heartbeatTimeoutMs
        self.failClosedRecoveryAction = failClosedRecoveryAction
    }

    public func evaluate(lastHeartbeatAt: Date?, now: Date) -> PrivateAppIOHealth {
        guard let lastHeartbeatAt else {
            return PrivateAppIOHealth(
                state: .waitingForApp,
                publicDeviceAvailability: .hidden,
                recoveryAction: failClosedRecoveryAction
            )
        }

        let elapsedMs = now.timeIntervalSince(lastHeartbeatAt) * 1000
        if elapsedMs > Double(heartbeatTimeoutMs) {
            return PrivateAppIOHealth(
                state: .heartbeatLost,
                lastHeartbeatAt: lastHeartbeatAt,
                missedHeartbeatCount: 1,
                publicDeviceAvailability: .hidden,
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
