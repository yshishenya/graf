import Foundation
import TwoBrainRecShared

public enum PassthroughRouteEngineState: Equatable, Sendable {
    case disabled
    case inactive
    case starting
    case active
    case blocked(String)
    case failed(String)
}

public final class PassthroughRouteEngine: @unchecked Sendable {
    public typealias Logger = @Sendable (_ event: String, _ detail: String) -> Void

    public static let shared = PassthroughRouteEngine()

    private let queue = DispatchQueue(label: "com.2brainrec.passthrough-route-engine")
    private var stateStorage: PassthroughRouteEngineState
    private let sharedMemory: SharedAudioMemory?
    private var bridge: PassthroughBridge?
    private var heartbeatTimer: DispatchSourceTimer?

    public init(sharedMemory: SharedAudioMemory? = SharedAudioMemory()) {
        self.sharedMemory = sharedMemory
        self.stateStorage = .inactive
        sharedMemory?.clearAppHeartbeat()
    }

    public var state: PassthroughRouteEngineState {
        queue.sync { stateStorage }
    }

    public func recordLaunchState(logger: Logger) -> PassthroughRouteEngineState {
        queue.sync {
            stateStorage = .inactive
            logger(
                "passthrough_bridge_experiment_available",
                "route engine is service-owned and starts only after explicit readiness check"
            )
            return stateStorage
        }
    }

    public func startExperimentalRoute(
        selectedPhysicalInputId: String? = nil,
        selectedPhysicalOutputId: String? = nil,
        logger: Logger
    ) -> PassthroughRouteEngineState {
        queue.sync {
            if bridge != nil {
                bridge?.refreshAppIOHeartbeat()
                stateStorage = .active
                logger("passthrough_bridge_already_active", "route engine refreshed app IO heartbeat")
                return stateStorage
            }

            stateStorage = .starting
            logger("passthrough_bridge_starting", "explicit readiness check")
            do {
                let bridge = try PassthroughBridge(
                    selectedPhysicalInputId: selectedPhysicalInputId,
                    selectedPhysicalOutputId: selectedPhysicalOutputId
                )
                try bridge.start()
                bridge.refreshAppIOHeartbeat()
                self.bridge = bridge
                startHeartbeatTimer(for: bridge)
                stateStorage = .active
                logger("passthrough_bridge_started", "explicit route engine active")
            } catch {
                stopHeartbeatTimer()
                bridge = nil
                sharedMemory?.clearAppHeartbeat()
                stateStorage = .failed(String(describing: error))
                logger("passthrough_bridge_failed", String(describing: error))
            }
            return stateStorage
        }
    }

    public func stop(logger: Logger? = nil) -> PassthroughRouteEngineState {
        queue.sync {
            stopHeartbeatTimer()
            bridge?.stop()
            bridge = nil
            sharedMemory?.clearAppHeartbeat()
            stateStorage = .inactive
            logger?("passthrough_bridge_stopped", "route engine cleared app IO heartbeat")
            return stateStorage
        }
    }

    private func startHeartbeatTimer(for bridge: PassthroughBridge) {
        stopHeartbeatTimer()
        let timer = DispatchSource.makeTimerSource(queue: queue)
        timer.schedule(deadline: .now() + 1.0, repeating: 1.0)
        timer.setEventHandler { [weak bridge] in
            bridge?.refreshAppIOHeartbeat()
        }
        heartbeatTimer = timer
        timer.resume()
    }

    private func stopHeartbeatTimer() {
        heartbeatTimer?.cancel()
        heartbeatTimer = nil
    }
}
