import Foundation

public enum MacOSMicAttributionState: String, Equatable, Sendable {
    case active
    case inactive
}

public struct MacOSMicAttributionEvent: Equatable, Sendable {
    public let bundleID: String
    public let displayName: String?
    public let processID: Int?
    public let state: MacOSMicAttributionState
    public let observedAt: Date

    public init(
        bundleID: String,
        displayName: String? = nil,
        processID: Int? = nil,
        state: MacOSMicAttributionState,
        observedAt: Date
    ) {
        self.bundleID = bundleID
        self.displayName = displayName
        self.processID = processID
        self.state = state
        self.observedAt = observedAt
    }
}

public struct MacOSMicAttributionParser: Sendable {
    public init() {}

    public func parse(line: String, observedAt: Date = Date()) -> MacOSMicAttributionEvent? {
        let lowercased = line.lowercased()
        guard lowercased.contains("sensor-indicators") ||
            lowercased.contains("sensor indicators") ||
            lowercased.contains("sensorindicators")
        else {
            return nil
        }
        guard lowercased.contains("microphone") ||
            lowercased.contains(" mic") ||
            lowercased.contains("mic:")
        else {
            return nil
        }
        guard let state = state(in: lowercased),
              let bundleID = capture(
                in: line,
                patterns: [
                    #"(?:^|[^A-Za-z0-9_.-])mic:([A-Za-z0-9_.-]+)"#,
                    #"bundleID[=: ]+([A-Za-z0-9_.-]+)"#,
                    #"bundle_id[=: ]+([A-Za-z0-9_.-]+)"#,
                    #"bundle[=: ]+([A-Za-z0-9_.-]+)"#,
                    #"attribution[=: ]+([A-Za-z0-9_.-]+)"#
                ]
              )
        else {
            return nil
        }
        return MacOSMicAttributionEvent(
            bundleID: bundleID,
            displayName: capture(in: line, patterns: [#"displayName="([^"]+)""#, #"name="([^"]+)""#]),
            processID: capture(in: line, patterns: [#"pid[=: ]+([0-9]+)"#]).flatMap(Int.init),
            state: state,
            observedAt: observedAt
        )
    }

    private func state(in line: String) -> MacOSMicAttributionState? {
        if line.contains("inactive") ||
            line.contains("stopped") ||
            line.contains("state=off") ||
            line.contains("ended") ||
            line.contains("removed") ||
            line.contains("removing") ||
            line.contains("cleared")
        {
            return .inactive
        }
        if line.contains("active") ||
            line.contains("started") ||
            line.contains("state=on") ||
            line.contains("began") ||
            line.contains("added") ||
            line.contains("adding")
        {
            return .active
        }
        return nil
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
