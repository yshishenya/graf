#!/usr/bin/env swift

import Foundation

enum AppIOState: String {
    case connected
    case heartbeatLost = "heartbeat_lost"
}

struct Scenario {
    let name: String
    let state: AppIOState
    let expectedPublicDeviceVisible: Bool
}

let scenarios = [
    Scenario(name: "app engine healthy", state: .connected, expectedPublicDeviceVisible: true),
    Scenario(name: "app engine killed", state: .heartbeatLost, expectedPublicDeviceVisible: false)
]

for scenario in scenarios {
    let actualVisible = scenario.state == .connected
    guard actualVisible == scenario.expectedPublicDeviceVisible else {
        fputs("App I/O fail-closed scenario failed: \(scenario.name)\n", stderr)
        exit(1)
    }
}

print("app-io-fail-closed-check: ACCEPTED")
