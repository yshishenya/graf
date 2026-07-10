import Foundation

public enum MacOSAudioOwnershipState: String, Equatable, Sendable {
    case active
    case inactive
}

public struct MacOSAudioOwnershipEvent: Equatable, Sendable {
    public let bundleID: String
    public let displayName: String?
    public let processID: Int?
    public let state: MacOSAudioOwnershipState
    public let observedAt: Date

    public init(
        bundleID: String,
        displayName: String? = nil,
        processID: Int? = nil,
        state: MacOSAudioOwnershipState,
        observedAt: Date
    ) {
        self.bundleID = bundleID
        self.displayName = displayName
        self.processID = processID
        self.state = state
        self.observedAt = observedAt
    }
}

public struct MacOSAudioOwnershipParser: Sendable {
    public init() {}

    public func parse(line: String, observedAt: Date = Date()) -> MacOSAudioOwnershipEvent? {
        let lowercased = line.lowercased()
        return parseAudioHALAssertion(line: line, lowercased: lowercased, observedAt: observedAt)
    }

    private func parseAudioHALAssertion(
        line: String,
        lowercased: String,
        observedAt: Date
    ) -> MacOSAudioOwnershipEvent? {
        guard lowercased.contains("audiohal"),
              lowercased.contains("explanation:\"audiohal\"")
        else {
            return nil
        }
        let state: MacOSAudioOwnershipState
        if lowercased.contains("invalidating") ||
            lowercased.contains(" did invalidate") ||
            lowercased.contains(" invalidated ") ||
            lowercased.contains(" inactive ")
        {
            state = .inactive
        } else if lowercased.contains(" active ") {
            state = .active
        } else {
            return nil
        }
        guard let bundleID = capture(
            in: line,
            patterns: [
                #"target:\[app<application\.([A-Za-z][A-Za-z0-9_.-]*?)\.[0-9]+\.[0-9]+\([0-9]+\)>:[0-9]+\]\s+explanation:"AudioHAL""#,
                #"originator:\[app<application\.([A-Za-z][A-Za-z0-9_.-]*?)\.[0-9]+\.[0-9]+\([0-9]+\)>:[0-9]+\]\s+transientState:"#
            ]
        )
        else {
            return nil
        }
        return MacOSAudioOwnershipEvent(
            bundleID: bundleID,
            displayName: displayName(fromBundleID: bundleID),
            processID: capture(
                in: line,
                patterns: [
                    #"target:\[app<application\.[A-Za-z][A-Za-z0-9_.-]*?\.[0-9]+\.[0-9]+\([0-9]+\)>:([0-9]+)\]\s+explanation:"AudioHAL""#
                ]
            ).flatMap(Int.init),
            state: state,
            observedAt: observedAt
        )
    }

    private func displayName(fromBundleID bundleID: String) -> String {
        bundleID
            .split(separator: ".")
            .last
            .map { String($0).replacingOccurrences(of: "-", with: " ") } ?? bundleID
    }

    private func capture(in line: String, patterns: [String]) -> String? {
        for pattern in patterns {
            guard let regex = try? NSRegularExpression(pattern: pattern) else {
                continue
            }
            let range = NSRange(line.startIndex..<line.endIndex, in: line)
            guard let match = regex.firstMatch(in: line, range: range),
                  match.numberOfRanges > 1,
                  let valueRange = Range(match.range(at: 1), in: line)
            else {
                continue
            }
            return String(line[valueRange])
        }
        return nil
    }
}
