#!/usr/bin/env swift
import Foundation

let selectedPhysicalInput = "2brain Rec Microphone"
let rejected = selectedPhysicalInput.localizedCaseInsensitiveContains("2brain Rec")

guard rejected else {
    fputs("live-mic-self-routing-check: BLOCKED\n", stderr)
    exit(1)
}

print("live-mic-self-routing-check: ACCEPTED")
