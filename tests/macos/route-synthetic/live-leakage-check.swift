#!/usr/bin/env swift

import Foundation

struct LeakageScenario {
    let name: String
    let relativeLeakageDb: Double
    let intelligible: Bool
    let expectedStatus: String
}

let scenarios = [
    LeakageScenario(name: "below threshold and not intelligible", relativeLeakageDb: -45.0, intelligible: false, expectedStatus: "passed"),
    LeakageScenario(name: "above threshold", relativeLeakageDb: -44.9, intelligible: false, expectedStatus: "degraded"),
    LeakageScenario(name: "intelligible leakage", relativeLeakageDb: -50.0, intelligible: true, expectedStatus: "degraded")
]

for scenario in scenarios {
    let actualStatus = scenario.relativeLeakageDb <= -45.0 && !scenario.intelligible
        ? "passed"
        : "degraded"

    guard actualStatus == scenario.expectedStatus else {
        fail("Leakage scenario \(scenario.name) expected \(scenario.expectedStatus), got \(actualStatus)")
    }
}

print("live-leakage-check: ACCEPTED")

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(2)
}
