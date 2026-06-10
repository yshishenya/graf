import Foundation
import TwoBrainRecShared

enum LiveRouteStabilityFixtures {
    static let now = Date(timeIntervalSince1970: 1_780_000_000)

    static func clientActivity(freshnessMs: Int = 500, naturalSilenceAllowed: Bool = true) -> ClientActivitySnapshot {
        ClientActivitySnapshot(
            source: .validationFixture,
            microphoneOpen: true,
            microphoneRunning: true,
            speakerOpen: true,
            speakerRunning: true,
            stillUsesVirtualMicrophone: true,
            stillUsesVirtualSpeaker: true,
            freshnessMs: freshnessMs,
            naturalSilenceAllowed: naturalSilenceAllowed
        )
    }

    static func defaultRoute(input: PhysicalDeviceClass = .builtIn, output: PhysicalDeviceClass = .usb) -> MacOSDefaultRouteSnapshot {
        MacOSDefaultRouteSnapshot(
            inputDeviceId: "input-\(input.rawValue)",
            inputDeviceClass: input,
            outputDeviceId: "output-\(output.rawValue)",
            outputDeviceClass: output,
            observedAt: now
        )
    }

    static func validationRun(result: ValidationResult = .accepted) -> ValidationRunEvidence {
        ValidationRunEvidence(
            runId: "019-dev-run",
            durationGate: .development30Minute,
            result: result,
            targetsCovered: MeetingTarget.allCases,
            deviceClassesCovered: [.builtIn, .wired, .usb],
            userActionCount: 0,
            startedAt: now,
            completedAt: now.addingTimeInterval(1_800)
        )
    }

    static func routeEvent(family: RouteEvidenceFamily = .clientActivity, name: String = "client_activity.fresh") -> RouteEvidenceEvent {
        RouteEvidenceEvent(
            eventId: "evt-019",
            sessionId: "route-session-019",
            family: family,
            name: name,
            observedAt: now,
            source: .validationScript,
            routeState: .active,
            target: .chrome,
            clientActivity: clientActivity()
        )
    }
}
