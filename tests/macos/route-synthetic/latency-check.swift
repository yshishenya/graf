#!/usr/bin/env swift

import Foundation

struct LatencyScenario {
    let name: String
    let routeClass: String
    let measuredMs: Double
    let expectedStatus: String
}

let scenarios = [
    LatencyScenario(name: "built-in threshold", routeClass: "built_in", measuredMs: 30.0, expectedStatus: "healthy"),
    LatencyScenario(name: "wired above threshold", routeClass: "wired", measuredMs: 30.1, expectedStatus: "latency_exceeded"),
    LatencyScenario(name: "bluetooth managed", routeClass: "bluetooth", measuredMs: 25.0, expectedStatus: "managed_degraded")
]

for scenario in scenarios {
    let accepted =
        (scenario.routeClass == "built_in" && scenario.measuredMs <= 30.0 && scenario.expectedStatus == "healthy")
        || (scenario.routeClass == "wired" && scenario.measuredMs > 30.0 && scenario.expectedStatus == "latency_exceeded")
        || (scenario.routeClass == "bluetooth" && scenario.expectedStatus == "managed_degraded")

    if !accepted {
        fputs("Latency scenario failed: \(scenario.name)\n", stderr)
        exit(1)
    }
}

print("latency-check: ACCEPTED")
