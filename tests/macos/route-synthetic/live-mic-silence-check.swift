#!/usr/bin/env swift
import Foundation

struct MicSilenceEvidence {
    let validFrames: UInt64
    let emptyBuffers: UInt64
    let userStimulusRequired: Bool

    var shouldBlockReady: Bool {
        userStimulusRequired && validFrames == 0 && emptyBuffers > 0
    }
}

let evidence = MicSilenceEvidence(validFrames: 0, emptyBuffers: 4, userStimulusRequired: true)

guard evidence.shouldBlockReady else {
    fputs("live-mic-silence-check: BLOCKED\n", stderr)
    exit(1)
}

print("live-mic-silence-check: ACCEPTED")
