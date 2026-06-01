import Foundation

public final class ExperimentalPassthroughCoordinator: ObservableObject, @unchecked Sendable {
    public typealias Logger = @Sendable (_ event: String, _ detail: String) -> Void

    @Published public private(set) var state: PassthroughRouteEngineState

    private let routeEngine: PassthroughRouteEngine
    private let logger: Logger

    public init(
        routeEngine: PassthroughRouteEngine = .shared,
        logger: @escaping Logger
    ) {
        self.routeEngine = routeEngine
        self.logger = logger
        self.state = routeEngine.state
    }

    public func recordLaunchState() {
        state = routeEngine.recordLaunchState(logger: logger)
    }

    public func startAutomaticBridge(
        selectedPhysicalInputId: String? = nil,
        selectedPhysicalOutputId: String? = nil
    ) {
        state = routeEngine.startAutomaticRoute(
            selectedPhysicalInputId: selectedPhysicalInputId,
            selectedPhysicalOutputId: selectedPhysicalOutputId,
            logger: logger
        )
    }

    public func startExperimentalBridge(
        selectedPhysicalInputId: String? = nil,
        selectedPhysicalOutputId: String? = nil
    ) {
        state = routeEngine.startExperimentalRoute(
            selectedPhysicalInputId: selectedPhysicalInputId,
            selectedPhysicalOutputId: selectedPhysicalOutputId,
            logger: logger
        )
    }

    public func stop() {
        state = routeEngine.stop(logger: logger)
    }
}
