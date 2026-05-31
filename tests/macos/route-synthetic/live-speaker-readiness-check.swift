#!/usr/bin/env swift

import Foundation

struct LiveSpeakerScenario {
    let name: String
    let stimulusObserved: Bool
    let validFrameCount: UInt64
    let selfRoutingRejected: Bool
    let aggregateRouteMeasurable: Bool
    let expectedStatus: String
}

let scenarios = [
    LiveSpeakerScenario(
        name: "physical speaker observes stimulus",
        stimulusObserved: true,
        validFrameCount: 48000,
        selfRoutingRejected: false,
        aggregateRouteMeasurable: true,
        expectedStatus: "passed"
    ),
    LiveSpeakerScenario(
        name: "speaker route missing stimulus",
        stimulusObserved: false,
        validFrameCount: 0,
        selfRoutingRejected: false,
        aggregateRouteMeasurable: true,
        expectedStatus: "failed"
    ),
    LiveSpeakerScenario(
        name: "virtual speaker selected as physical output",
        stimulusObserved: true,
        validFrameCount: 48000,
        selfRoutingRejected: true,
        aggregateRouteMeasurable: true,
        expectedStatus: "failed"
    ),
    LiveSpeakerScenario(
        name: "aggregate speaker route not measurable",
        stimulusObserved: true,
        validFrameCount: 48000,
        selfRoutingRejected: false,
        aggregateRouteMeasurable: false,
        expectedStatus: "blocked"
    )
]

for scenario in scenarios {
    let actualStatus: String
    if scenario.selfRoutingRejected {
        actualStatus = "failed"
    } else if !scenario.aggregateRouteMeasurable {
        actualStatus = "blocked"
    } else if scenario.stimulusObserved && scenario.validFrameCount > 0 {
        actualStatus = "passed"
    } else {
        actualStatus = "failed"
    }

    guard actualStatus == scenario.expectedStatus else {
        fail("Live speaker readiness failed for \(scenario.name): expected \(scenario.expectedStatus), got \(actualStatus)")
    }
}

print("live-speaker-readiness-check: ACCEPTED")

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(2)
}
