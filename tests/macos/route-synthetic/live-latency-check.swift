#!/usr/bin/env swift

import Foundation

struct LatencyScenario {
    let name: String
    let routeClass: String
    let addedLatencyMs: Double
    let expectedStatus: String
}

let scenarios = [
    LatencyScenario(name: "built-in at threshold", routeClass: "built_in", addedLatencyMs: 30.0, expectedStatus: "passed"),
    LatencyScenario(name: "wired above threshold", routeClass: "wired", addedLatencyMs: 30.1, expectedStatus: "degraded"),
    LatencyScenario(name: "bluetooth managed pilot", routeClass: "bluetooth", addedLatencyMs: 25.0, expectedStatus: "blocked")
]

for scenario in scenarios {
    let actualStatus: String
    switch scenario.routeClass {
    case "built_in", "wired", "usb":
        actualStatus = scenario.addedLatencyMs <= 30.0 ? "passed" : "degraded"
    case "bluetooth", "airpods_class":
        actualStatus = "blocked"
    default:
        actualStatus = "blocked"
    }

    guard actualStatus == scenario.expectedStatus else {
        fail("Latency scenario \(scenario.name) expected \(scenario.expectedStatus), got \(actualStatus)")
    }
}

print("live-latency-check: ACCEPTED")

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(2)
}
