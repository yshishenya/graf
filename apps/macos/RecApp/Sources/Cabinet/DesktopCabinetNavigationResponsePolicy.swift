import Foundation

public enum DesktopCabinetNavigationResponseDecision: Equatable {
    case allow
    case cancel(DesktopCabinetState)
}

public struct DesktopCabinetNavigationResponsePolicy: Equatable {
    public init() {}

    public func decision(forNavigationResponse response: URLResponse, isForMainFrame: Bool) -> DesktopCabinetNavigationResponseDecision {
        guard isForMainFrame else { return .allow }
        guard let httpResponse = response as? HTTPURLResponse else {
            return .cancel(.malformedResponse)
        }
        guard let state = DesktopCabinetState.state(forHTTPStatus: httpResponse.statusCode) else {
            return .allow
        }
        return .cancel(state)
    }
}
