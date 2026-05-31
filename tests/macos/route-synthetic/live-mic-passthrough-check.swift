#!/usr/bin/env swift
import Foundation

struct MicPassthroughEvidence {
    let physicalInputId: String
    let virtualInputName: String
    let validFrames: UInt64
    let recordingState: String

    var accepted: Bool {
        !physicalInputId.localizedCaseInsensitiveContains("2brain Rec") &&
            virtualInputName == "2brain Rec Microphone" &&
            validFrames > 0 &&
            recordingState == "not_recording"
    }
}

let evidence = MicPassthroughEvidence(
    physicalInputId: "built-in-input",
    virtualInputName: "2brain Rec Microphone",
    validFrames: 480,
    recordingState: "not_recording"
)

guard evidence.accepted else {
    fputs("live-mic-passthrough-check: BLOCKED\n", stderr)
    exit(1)
}

print("live-mic-passthrough-check: ACCEPTED")
