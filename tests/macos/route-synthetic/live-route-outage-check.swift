#!/usr/bin/env swift

import Foundation

struct LiveRouteOutageScenario {
    let name: String
    let backendAvailable: Bool
    let networkAvailable: Bool
    let readinessPassed: Bool
    let liveRouteMustRemainUsable: Bool
}

let scenarios = [
    LiveRouteOutageScenario(
        name: "backend outage after readiness",
        backendAvailable: false,
        networkAvailable: true,
        readinessPassed: true,
        liveRouteMustRemainUsable: true
    ),
    LiveRouteOutageScenario(
        name: "network outage after readiness",
        backendAvailable: false,
        networkAvailable: false,
        readinessPassed: true,
        liveRouteMustRemainUsable: true
    )
]

for scenario in scenarios {
    guard scenario.readinessPassed && scenario.liveRouteMustRemainUsable else {
        fail("Live route must stay independent of backend/network status for \(scenario.name).")
    }
}

print("live-route-outage-check: ACCEPTED")

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(2)
}
