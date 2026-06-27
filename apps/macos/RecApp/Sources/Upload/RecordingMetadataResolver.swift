import Foundation
import TwoBrainRecShared

public struct RecordingMetadataResolver: Sendable {
    public typealias Clock = @Sendable () -> Date

    private let clock: Clock
    private let displayTimeZone: TimeZone

    public init(
        clock: @escaping Clock = Date.init,
        displayTimeZone: TimeZone = .current
    ) {
        self.clock = clock
        self.displayTimeZone = displayTimeZone
    }

    public func resolve(
        startedAt: Date,
        stoppedAt: Date?,
        directoryId: String,
        sessionId: String,
        approvedAppName: String?,
        userConfirmedTitle: String? = nil
    ) -> RecordingDisplayMetadata {
        let generatedAt = clock()
        let dateLabel = formattedMinute(startedAt, separator: " ")
        var suppressedSources: [RecordingTitleSuppression] = []

        let titleChoice: (String, RecordingTitleStatus, RecordingTitleSource, RecordingTitleConfidence)
        if let userTitle = sanitizedVisibleTitle(userConfirmedTitle) {
            titleChoice = (userTitle, .userConfirmed, .userConfirmed, .high)
        } else {
            if hasNonEmptyInput(userConfirmedTitle) {
                suppressedSources.append(RecordingTitleSuppression(source: .userConfirmed, reason: "unsafe_pattern"))
            }

            if let appTitle = sanitizedVisibleTitle(approvedAppName, maxLength: 500 - dateLabel.count - 3) {
                titleChoice = ("\(appTitle) - \(dateLabel)", .generated, .appContext, .high)
            } else {
                if hasNonEmptyInput(approvedAppName) {
                    suppressedSources.append(RecordingTitleSuppression(source: .appContext, reason: "unsafe_pattern"))
                }
                titleChoice = ("Meeting - \(dateLabel)", .generated, .generic, .medium)
            }
        }

        let stableSuffix = Self.stableSuffix(directoryId: directoryId, sessionId: sessionId)
        let basename = safeBasename(
            datePrefix: formattedMinute(startedAt, separator: "_").replacingOccurrences(of: ":", with: "-"),
            title: titleChoice.0,
            stableSuffix: stableSuffix
        )
        let validStoppedAt = stoppedAt.flatMap { $0 >= startedAt ? $0 : nil }

        return RecordingDisplayMetadata(
            recordingStartedAt: startedAt,
            recordingStoppedAt: validStoppedAt,
            title: titleChoice.0,
            titleStatus: titleChoice.1,
            titleSource: titleChoice.2,
            titleConfidence: titleChoice.3,
            titleGeneratedAt: generatedAt,
            safeFileBasename: basename,
            stableSuffix: stableSuffix,
            suppressedSources: suppressedSources
        )
    }

    private func formattedMinute(_ date: Date, separator: String) -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = displayTimeZone
        formatter.dateFormat = "yyyy-MM-dd\(separator)HH:mm"
        return formatter.string(from: date)
    }

    private func sanitizedVisibleTitle(_ raw: String?, maxLength: Int = 500) -> String? {
        guard let raw else { return nil }
        let filteredScalars = raw.unicodeScalars.filter { !CharacterSet.controlCharacters.contains($0) }
        let withoutControls = String(String.UnicodeScalarView(filteredScalars))
        let trimmed = withoutControls.trimmingCharacters(in: CharacterSet.whitespacesAndNewlines)
        guard !trimmed.isEmpty, !containsUnsafePattern(trimmed) else {
            return nil
        }

        let normalized = trimmed
            .replacingOccurrences(of: "/", with: " ")
            .replacingOccurrences(of: "\\", with: " ")
            .replacingOccurrences(of: ":", with: " ")
            .components(separatedBy: CharacterSet.whitespacesAndNewlines)
            .filter { !$0.isEmpty }
            .joined(separator: " ")
        guard !normalized.isEmpty else { return nil }
        return String(normalized.prefix(max(1, maxLength)))
    }

    private func containsUnsafePattern(_ value: String) -> Bool {
        let lowered = value.lowercased()
        if lowered.contains("http://") ||
            lowered.contains("https://") ||
            lowered.contains("www.") ||
            lowered.contains("token=") ||
            lowered.contains("password") ||
            lowered.contains("bearer ") {
            return true
        }
        if value.range(
            of: #"(^|[^A-Z0-9])sk-[A-Z0-9_-]{8,}"#,
            options: [.regularExpression, .caseInsensitive]
        ) != nil {
            return true
        }
        if value.range(
            of: #"\b(?:meet\.google\.com/[A-Z0-9_-]+|zoom\.us/(?:j|my)/[A-Z0-9._-]+|teams\.microsoft\.com/l/meetup-join|whereby\.com/[A-Z0-9_-]+|webex\.com/meet/[A-Z0-9._-]+)"#,
            options: [.regularExpression, .caseInsensitive]
        ) != nil {
            return true
        }
        return value.range(
            of: #"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}"#,
            options: [.regularExpression, .caseInsensitive]
        ) != nil
    }

    private func hasNonEmptyInput(_ raw: String?) -> Bool {
        raw?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false
    }

    private func safeBasename(datePrefix: String, title: String, stableSuffix: String) -> String {
        let slug = slugify(title)
        return "\(datePrefix)_\(slug)_\(stableSuffix)"
    }

    private func slugify(_ title: String) -> String {
        let folded = title
            .folding(options: [.diacriticInsensitive, .widthInsensitive], locale: Locale(identifier: "en_US_POSIX"))
            .lowercased()
        var result = ""
        var previousWasSeparator = false
        for scalar in folded.unicodeScalars {
            let value = scalar.value
            let isAllowed = (48...57).contains(value) || (97...122).contains(value)
            if isAllowed {
                result.unicodeScalars.append(scalar)
                previousWasSeparator = false
            } else if !previousWasSeparator {
                result.append("-")
                previousWasSeparator = true
            }
        }

        let trimmed = result.trimmingCharacters(in: CharacterSet(charactersIn: "-"))
        let slug = trimmed.isEmpty ? "recording" : trimmed
        return String(slug.prefix(80)).trimmingCharacters(in: CharacterSet(charactersIn: "-"))
    }

    private static func stableSuffix(directoryId: String, sessionId: String) -> String {
        let value = "\(directoryId)|\(sessionId)"
        var hash: UInt64 = 0xcbf29ce484222325
        for byte in value.utf8 {
            hash ^= UInt64(byte)
            hash &*= 0x100000001b3
        }
        return String(String(format: "%016llx", hash).prefix(6))
    }
}
