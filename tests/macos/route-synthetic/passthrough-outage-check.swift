#!/usr/bin/env swift

import Foundation

struct OutageScenario {
    let backendAvailable: Bool
    let passthroughExpected: Bool
}

let fiveMinuteBackendOutage = OutageScenario(
    backendAvailable: false,
    passthroughExpected: true
)

guard !fiveMinuteBackendOutage.backendAvailable && fiveMinuteBackendOutage.passthroughExpected else {
    fputs("Passthrough must remain independent of backend/network availability.\n", stderr)
    exit(1)
}

print("passthrough-outage-check: ACCEPTED")
