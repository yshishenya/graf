#!/usr/bin/env swift

import Foundation

let virtualMicrophoneNames = ["2brain Rec Microphone", "pro.2brain.rec.microphone"]
let virtualSpeakerNames = ["2brain Rec Speaker", "pro.2brain.rec.speaker"]

guard rejectsPhysicalSelection("2brain Rec Microphone", knownVirtuals: virtualMicrophoneNames) else {
    fail("Virtual microphone must be rejected as a physical microphone selection.")
}

guard rejectsPhysicalSelection("2brain Rec Speaker", knownVirtuals: virtualSpeakerNames) else {
    fail("Virtual speaker must be rejected as a physical speaker selection.")
}

guard !rejectsPhysicalSelection("MacBook Pro Microphone", knownVirtuals: virtualMicrophoneNames) else {
    fail("Real physical microphone must not be rejected as self-routing.")
}

guard !rejectsPhysicalSelection("MacBook Pro Speakers", knownVirtuals: virtualSpeakerNames) else {
    fail("Real physical speaker must not be rejected as self-routing.")
}

print("live-self-routing-check: ACCEPTED")

func rejectsPhysicalSelection(_ selected: String, knownVirtuals: [String]) -> Bool {
    let normalized = selected.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    return knownVirtuals.contains {
        $0.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() == normalized
    }
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(2)
}
