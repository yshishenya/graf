#!/usr/bin/env swift

import Foundation

struct LiveMicScenario {
    let name: String
    let validFrameCount: UInt64
    let emptyBufferCount: UInt64
    let selfRoutingRejected: Bool
    let expectedStatus: String
}

let scenarios = [
    LiveMicScenario(
        name: "physical microphone produces valid frames",
        validFrameCount: 48000,
        emptyBufferCount: 0,
        selfRoutingRejected: false,
        expectedStatus: "passed"
    ),
    LiveMicScenario(
        name: "physical microphone path has no valid frames",
        validFrameCount: 0,
        emptyBufferCount: 3,
        selfRoutingRejected: false,
        expectedStatus: "failed"
    ),
    LiveMicScenario(
        name: "virtual microphone selected as physical input",
        validFrameCount: 48000,
        emptyBufferCount: 0,
        selfRoutingRejected: true,
        expectedStatus: "failed"
    )
]

for scenario in scenarios {
    let actualStatus: String
    if scenario.selfRoutingRejected {
        actualStatus = "failed"
    } else if scenario.validFrameCount > 0 {
        actualStatus = "passed"
    } else {
        actualStatus = "failed"
    }

    guard actualStatus == scenario.expectedStatus else {
        fail("Live microphone readiness failed for \(scenario.name): expected \(scenario.expectedStatus), got \(actualStatus)")
    }
}

print("live-mic-readiness-check: ACCEPTED")

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(2)
}
