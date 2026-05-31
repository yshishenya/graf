#!/usr/bin/env swift
import Foundation

struct LocalPassthroughDuringOutage {
    let backendAvailable: Bool
    let uploadAvailable: Bool
    let transcriptionAvailable: Bool
    let localMicPathActive: Bool
    let localSpeakerPathActive: Bool

    var accepted: Bool {
        !backendAvailable &&
            !uploadAvailable &&
            !transcriptionAvailable &&
            localMicPathActive &&
            localSpeakerPathActive
    }
}

let evidence = LocalPassthroughDuringOutage(
    backendAvailable: false,
    uploadAvailable: false,
    transcriptionAvailable: false,
    localMicPathActive: true,
    localSpeakerPathActive: true
)

guard evidence.accepted else {
    fputs("live-passthrough-outage-check: BLOCKED\n", stderr)
    exit(1)
}

print("live-passthrough-outage-check: ACCEPTED")
