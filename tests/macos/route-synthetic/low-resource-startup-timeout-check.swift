import Foundation

let maximumDurationMs = 3000
let simulatedAttempts: [(id: String, durationMs: Int, outcome: String)] = [
    ("ready-fast", 1800, "ready"),
    ("blocked-threshold", 3000, "blocked"),
    ("failed-fast", 500, "failed"),
    ("fallback-fast", 700, "fallback")
]

for attempt in simulatedAttempts {
    guard attempt.durationMs <= maximumDurationMs else {
        fputs("low-resource-startup-timeout-check: BLOCKED \(attempt.id)\n", stderr)
        exit(1)
    }
    guard ["ready", "blocked", "failed", "fallback"].contains(attempt.outcome) else {
        fputs("low-resource-startup-timeout-check: INVALID_OUTCOME \(attempt.id)\n", stderr)
        exit(1)
    }
}

print("low-resource-startup-timeout-check: ACCEPTED")
