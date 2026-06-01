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

    public init(sharedMemory: SharedAudioMemory? = SharedAudioMemory()) {
        self.sharedMemory = sharedMemory
        self.stateStorage = Self.isExperimentEnabled ? .inactive : .disabled
        if !Self.isExperimentEnabled {
            sharedMemory?.clearAppHeartbeat()
        }
    }

    public static var isExperimentEnabled: Bool {
        ProcessInfo.processInfo.environment["TWO_BRAIN_REC_ENABLE_EXPERIMENTAL_PASSTHROUGH"] == "1"
    }

    public var state: PassthroughRouteEngineState {
        queue.sync { stateStorage }
    }

    public func recordLaunchState(logger: Logger) -> PassthroughRouteEngineState {
        queue.sync {
            guard Self.isExperimentEnabled else {
                sharedMemory?.clearAppHeartbeat()
                stateStorage = .disabled
                logger(
                    "passthrough_bridge_disabled",
                    "set TWO_BRAIN_REC_ENABLE_EXPERIMENTAL_PASSTHROUGH=1 for local bridge experiments"
                )
                return stateStorage
            }

            stateStorage = .inactive
            logger(
                "passthrough_bridge_experiment_available",
                "route engine is service-owned and blocked until measured live evidence gates are implemented"
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
            guard Self.isExperimentEnabled else {
                sharedMemory?.clearAppHeartbeat()
                stateStorage = .disabled
                logger(
                    "passthrough_bridge_disabled",
                    "set TWO_BRAIN_REC_ENABLE_EXPERIMENTAL_PASSTHROUGH=1 for local bridge experiments"
                )
                return stateStorage
            }

            _ = selectedPhysicalInputId
            _ = selectedPhysicalOutputId
            sharedMemory?.clearAppHeartbeat()
            stateStorage = .blocked("measured_live_route_evidence_gate_missing")
            logger(
                "passthrough_bridge_blocked",
                "route engine refused app-side bridge start until measured live route evidence owns heartbeat"
            )
            return stateStorage
        }
    }

    public func stop(logger: Logger? = nil) -> PassthroughRouteEngineState {
        queue.sync {
            sharedMemory?.clearAppHeartbeat()
            stateStorage = Self.isExperimentEnabled ? .inactive : .disabled
            logger?("passthrough_bridge_stopped", "route engine cleared app IO heartbeat")
            return stateStorage
        }
    }
}
