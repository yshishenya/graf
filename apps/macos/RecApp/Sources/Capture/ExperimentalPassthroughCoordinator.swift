import Foundation
import TwoBrainRecShared

public enum ExperimentalPassthroughCoordinatorState: Equatable, Sendable {
    case disabled
    case inactive
    case starting
    case active
    case failed(String)
}

public final class ExperimentalPassthroughCoordinator: ObservableObject, @unchecked Sendable {
    public typealias Logger = @Sendable (_ event: String, _ detail: String) -> Void

    @Published public private(set) var state: ExperimentalPassthroughCoordinatorState = .inactive

    private let logger: Logger
    private let sharedMemory: SharedAudioMemory?
    private var bridge: PassthroughBridge?
    private var heartbeatTimer: Timer?

    public init(logger: @escaping Logger) {
        self.logger = logger
        self.sharedMemory = SharedAudioMemory()
        if !Self.isExperimentEnabled {
            state = .disabled
        }
    }

    deinit {
        stop()
    }

    public static var isExperimentEnabled: Bool {
        ProcessInfo.processInfo.environment["TWO_BRAIN_REC_ENABLE_EXPERIMENTAL_PASSTHROUGH"] == "1"
    }

    public func recordLaunchState() {
        guard Self.isExperimentEnabled else {
            logger(
                "passthrough_bridge_disabled",
                "set TWO_BRAIN_REC_ENABLE_EXPERIMENTAL_PASSTHROUGH=1 for local bridge experiments"
            )
            return
        }
        logger(
            "passthrough_bridge_experiment_available",
            "experimental bridge requires an explicit start action before app IO heartbeat is written"
        )
    }

    public func startExperimentalBridge(
        selectedPhysicalInputId: String? = nil,
        selectedPhysicalOutputId: String? = nil
    ) {
        guard Self.isExperimentEnabled else {
            state = .disabled
            sharedMemory?.clearAppHeartbeat()
            recordLaunchState()
            return
        }
        guard bridge == nil else { return }

        state = .starting
        logger("passthrough_bridge_starting", "explicit experimental start")
        do {
            let bridge = try PassthroughBridge(
                selectedPhysicalInputId: selectedPhysicalInputId,
                selectedPhysicalOutputId: selectedPhysicalOutputId
            )
            try bridge.start()
            self.bridge = bridge
            bridge.refreshAppIOHeartbeat()
            heartbeatTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
                self?.bridge?.refreshAppIOHeartbeat()
            }
            state = .active
            logger("passthrough_bridge_started", "explicit experimental bridge active")
        } catch {
            sharedMemory?.clearAppHeartbeat()
            state = .failed(String(describing: error))
            logger("passthrough_bridge_failed", String(describing: error))
        }
    }

    public func stop() {
        heartbeatTimer?.invalidate()
        heartbeatTimer = nil
        bridge?.stop()
        bridge = nil
        sharedMemory?.clearAppHeartbeat()
        if Self.isExperimentEnabled {
            state = .inactive
        } else {
            state = .disabled
        }
    }
}
