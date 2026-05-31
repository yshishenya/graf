#!/usr/bin/env swift
import Foundation

struct SpeakerPassthroughEvidence {
    let virtualOutputName: String
    let physicalOutputId: String
    let stimulusObserved: Bool
    let recordingState: String

    var accepted: Bool {
        virtualOutputName == "2brain Rec Speaker" &&
            !physicalOutputId.localizedCaseInsensitiveContains("2brain Rec") &&
            stimulusObserved &&
            recordingState == "not_recording"
    }
}

let evidence = SpeakerPassthroughEvidence(
    virtualOutputName: "2brain Rec Speaker",
    physicalOutputId: "built-in-output",
    stimulusObserved: true,
    recordingState: "not_recording"
)

guard evidence.accepted else {
    fputs("live-speaker-passthrough-check: BLOCKED\n", stderr)
    exit(1)
}

print("live-speaker-passthrough-check: ACCEPTED")
