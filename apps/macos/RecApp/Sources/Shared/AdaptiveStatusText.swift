import Foundation
import TwoBrainRecShared

public enum AdaptiveStatusText {}

public extension AdaptiveStatusText {
    static let maxDisplayLength = 48
    static let bestEffortBrowsers: Set<String> = [
        "chrome",
        "opera",
        "yandex browser",
        "yandex telemost"
    ]

    static func safeLabel(
        _ value: String?,
        fallback: String = "Unknown",
        maxLength: Int = maxDisplayLength
    ) -> String {
        let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines) ?? fallback
        let normalized = trimmed.isEmpty ? fallback : trimmed
        let clipped = normalized.clipped(prefixLength: maxLength)
        return clipped == normalized ? clipped : "\(clipped)…"
    }

    static func deviceLabel(
        _ value: String?,
        fallback: String = "Physical audio device"
    ) -> String {
        let label = safeLabel(value, fallback: fallback)
        return "\(label)"
    }

    static func routeStatusLabel(_ status: RouteVerificationStatus) -> String {
        switch status {
        case .notStarted:
            return "Not checked"
        case .running:
            return "Checking…"
        case .passed:
            return "Passed"
        case .failed:
            return "Failed"
        case .stale:
            return "Needs audio check"
        }
    }

    static func liveReadinessStatusLabel(_ status: LiveRouteReadinessStatus) -> String {
        switch status {
        case .notStarted:
            return "Not checked"
        case .checking:
            return "Checking"
        case .ready:
            return "Ready"
        case .stale:
            return "Needs audio check"
        case .degraded:
            return "Degraded"
        case .failed:
            return "Failed"
        }
    }

    static func routeStatusIcon(_ status: RouteVerificationStatus) -> String {
        switch status {
        case .notStarted:
            return "circle.dotted"
        case .running:
            return "arrow.triangle.2.circlepath"
        case .passed:
            return "checkmark.circle.fill"
        case .failed:
            return "xmark.octagon.fill"
        case .stale:
            return "exclamationmark.triangle.fill"
        }
    }

    static func permissionLabel(
        microphone: PermissionStatus,
        output: PermissionStatus
    ) -> String {
        switch (microphone, output) {
        case (.granted, .granted):
            return "Permissions granted"
        case (.denied, _), (_, .denied):
            return "Capture permission denied"
        case (.restricted, _), (_, .restricted):
            return "Permission restricted"
        default:
            return "Not requested in this build"
        }
    }

    static func driverLabel(
        _ state: DriverInstallationState,
        virtualInputState: VirtualDeviceAvailabilityState? = nil,
        virtualOutputState: VirtualDeviceAvailabilityState? = nil
    ) -> String {
        switch state {
        case .installed:
            if virtualInputState == .available && virtualOutputState == .available {
                return "Driver loaded; routes not ready yet"
            }
            return "Driver installed"
        case .requiresRestart:
            return "Driver installed, restart required"
        case .needsRepair:
            return "Driver repair required"
        case .needsUpdate:
            return "Driver update available"
        case .uninstalling:
            return "Uninstalling"
        case .uninstalled:
            return "Driver removed"
        case .notInstalled:
            return "Driver not installed"
        case .incompatible:
            return "Driver unsupported on this host"
        }
    }

    static func passthroughLabel(_ status: PassthroughStatus) -> String {
        switch status {
        case .healthy:
            return "Verified"
        case .degraded:
            return "Degraded"
        case .failed:
            return "Failed"
        case .appIOMissing:
            return "App audio route unavailable"
        case .latencyExceeded:
            return "Latency limit exceeded"
        case .mutedByPhysicalDevice:
            return "Physical device muted"
        case .physicalDeviceMissing:
            return "Physical device missing"
        case .unknown:
            return "Not verified"
        }
    }

    static func lowResourceRouteLabel(_ state: AudioResourceState) -> String {
        switch state {
        case .idleSafe:
            return "Idle, routing is safe"
        case .starting:
            return "Starting audio route"
        case .ready:
            return "Routing ready, not recording"
        case .active:
            return "Routing active, not recording"
        case .stale:
            return "Audio route needs fresh evidence"
        case .blocked:
            return "Audio route blocked"
        case .failed:
            return "Audio route failed"
        case .retrying:
            return "Retrying audio route"
        case .fallback:
            return "Using previous audio route"
        }
    }

    static func browserLabel(_ name: String?) -> String {
        let normalized = (name ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()

        guard !normalized.isEmpty else {
            return "No target"
        }

        if bestEffortBrowsers.contains(normalized) {
            return normalized == "yandex telemost"
                ? "Yandex Telemost (best effort)"
                : "\(normalized.capitalized) (officially supported)"
        }

        return "\(safeLabel(name)) (best effort)"
    }

    static func meetingLabel(_ title: String?) -> String {
        "Meeting: \(safeLabel(title, fallback: "—"))"
    }

    static func recoveryActionLabel(_ action: String?) -> String {
        guard let action else {
            return "Review diagnostics"
        }

        switch action {
        case "select_physical_microphone":
            return "Select a physical microphone"
        case "select_physical_speaker":
            return "Select a physical speaker"
        case "run_route_verification":
            return "Refresh local audio status"
        case "refresh_local_audio_status":
            return "Refresh local audio status"
        case "install_or_repair_driver":
            return "Driver diagnostics are parked for MVP recording"
        case "implement_passthrough":
            return "Passthrough implementation is still required"
        case "rerun_readiness_check":
            return "Refresh local audio status again"
        case "retry_route_verification":
            return "Retry route verification"
        case "update_driver":
            return "Update driver package"
        case "repair_driver":
            return "Run installer repair"
        default:
            return safeLabel(action.replacingOccurrences(of: "_", with: " "))
        }
    }

    static func recoveryHint(from issues: [String]) -> String {
        guard !issues.isEmpty else {
            return "No recovery action required"
        }
        let joined = issues.joined(separator: ", ")
        return safeLabel("Recovery: \(joined)", maxLength: maxDisplayLength * 2)
    }
}

private extension String {
    func clipped(prefixLength: Int) -> String {
        guard count > max(prefixLength, 8) else {
            return self
        }
        let end = index(startIndex, offsetBy: max(prefixLength, 8))
        return String(self[..<end])
    }
}
