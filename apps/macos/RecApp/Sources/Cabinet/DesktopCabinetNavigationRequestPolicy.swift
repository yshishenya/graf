import Foundation

public enum DesktopCabinetNavigationRequestDecision: Equatable {
    case allow
    case reload(URLRequest)
}

public struct DesktopCabinetNavigationRequestPolicy: Equatable {
    private let routePolicy: DesktopCabinetRoutePolicy
    private let desktopHeaders: [String: String]

    public init(routePolicy: DesktopCabinetRoutePolicy, desktopHeaders: [String: String]) {
        self.routePolicy = routePolicy
        self.desktopHeaders = desktopHeaders
    }

    public func decision(
        forNavigationRequest request: URLRequest,
        isForMainFrame: Bool
    ) -> DesktopCabinetNavigationRequestDecision {
        guard isForMainFrame,
              isSafeReloadMethod(request.httpMethod),
              let url = request.url
        else {
            return .allow
        }

        let routeDecision = routePolicy.decision(for: url)
        guard routeDecision.decision == .allow,
              routeRequiresDesktopHeaders(routeDecision.route.kind),
              requestNeedsDesktopHeaders(request)
        else {
            return .allow
        }

        var reloaded = request
        for (header, value) in desktopHeaders where !value.isEmpty {
            reloaded.setValue(value, forHTTPHeaderField: header)
        }
        return .reload(reloaded)
    }

    private func routeRequiresDesktopHeaders(_ kind: DesktopCabinetRouteKind) -> Bool {
        kind == .meetingList ||
            kind == .meetingDetail ||
            kind == .meetingShare ||
            kind == .meetingDeletionReport ||
            kind == .calendarSettings
    }

    private func requestNeedsDesktopHeaders(_ request: URLRequest) -> Bool {
        guard !desktopHeaders.isEmpty else { return false }
        return desktopHeaders.contains { header, value in
            !value.isEmpty && normalizedHeaderValue(for: header, in: request) != value
        }
    }

    private func normalizedHeaderValue(for header: String, in request: URLRequest) -> String? {
        let target = header.lowercased()
        return request.allHTTPHeaderFields?.first { existingHeader, _ in
            existingHeader.lowercased() == target
        }?.value
    }

    private func isSafeReloadMethod(_ method: String?) -> Bool {
        (method ?? "GET").uppercased() == "GET"
    }
}
