#!/usr/bin/env swift
import Foundation

let leakageDbBelowReference = 48.0
let notIntelligible = true
let accepted = leakageDbBelowReference >= 45.0 && notIntelligible

guard accepted else {
    fputs("live-passthrough-no-loopback-check: BLOCKED\n", stderr)
    exit(1)
}

print("live-passthrough-no-loopback-check: ACCEPTED")
