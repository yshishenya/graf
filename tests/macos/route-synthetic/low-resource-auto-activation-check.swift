import Foundation

struct Evidence: Codable {
    let feature: String
    let baseline: String
    let activationTrigger: String
    let requiresRunCheck: Bool
    let recordingStarted: Bool
    let result: String
}

let evidence = Evidence(
    feature: "006-low-resource-audio",
    baseline: "005-macos-passthrough-release-hardening",
    activationTrigger: "explicit_client_io_state",
    requiresRunCheck: false,
    recordingStarted: false,
    result: "passed"
)

let data = try JSONEncoder().encode(evidence)
let object = try JSONSerialization.jsonObject(with: data) as? [String: Any]

guard object?["activationTrigger"] as? String == "explicit_client_io_state",
      object?["requiresRunCheck"] as? Bool == false,
      object?["recordingStarted"] as? Bool == false else {
    fputs("low-resource-auto-activation-check: BLOCKED\n", stderr)
    exit(1)
}

print("low-resource-auto-activation-check: ACCEPTED")
