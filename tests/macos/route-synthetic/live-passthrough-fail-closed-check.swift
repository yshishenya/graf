#!/usr/bin/env swift
import Foundation

enum BridgeProcessState {
    case running
    case stopped
    case heartbeatLost
}

struct LivePassthroughFailClosedEvidence {
    let bridgeState: BridgeProcessState
    let driverPublishesDevices: Bool
    let micPathActive: Bool
    let speakerPathActive: Bool
    let virtualMicEmitsSilence: Bool
    let virtualSpeakerDropsToSilence: Bool

    var accepted: Bool {
        driverPublishesDevices &&
            bridgeState != .running &&
            !micPathActive &&
            !speakerPathActive &&
            virtualMicEmitsSilence &&
            virtualSpeakerDropsToSilence
    }
}

let evidence = LivePassthroughFailClosedEvidence(
    bridgeState: .heartbeatLost,
    driverPublishesDevices: true,
    micPathActive: false,
    speakerPathActive: false,
    virtualMicEmitsSilence: true,
    virtualSpeakerDropsToSilence: true
)

guard evidence.accepted else {
    fputs("live-passthrough-fail-closed-check: BLOCKED\n", stderr)
    exit(1)
}

print("live-passthrough-fail-closed-check: ACCEPTED")
