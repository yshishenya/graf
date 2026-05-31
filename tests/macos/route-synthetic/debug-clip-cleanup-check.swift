#!/usr/bin/env swift

import Foundation

struct DebugClip {
    let id: String
    let developmentOnly: Bool
}

let records = [
    DebugClip(id: "dev-clip", developmentOnly: true),
    DebugClip(id: "metadata", developmentOnly: false)
]

let removed = records.filter(\.developmentOnly).map(\.id)
let remaining = records.filter { !$0.developmentOnly }.map(\.id)

guard removed == ["dev-clip"], remaining == ["metadata"] else {
    fputs("Debug clip cleanup did not remove only development clips.\n", stderr)
    exit(1)
}

print("debug-clip-cleanup-check: ACCEPTED")
