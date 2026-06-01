#!/usr/bin/env swift
import Foundation

enum SpeakerFailureReason: String {
    case unavailable
    case muted
    case disconnected
    case aggregateUnmanaged
    case selfRouted
}

let failure: SpeakerFailureReason = .disconnected
let hasRecoveryAction = true

guard failure == .disconnected && hasRecoveryAction else {
    fputs("live-speaker-failure-check: BLOCKED\n", stderr)
    exit(1)
}

print("live-speaker-failure-check: ACCEPTED")
