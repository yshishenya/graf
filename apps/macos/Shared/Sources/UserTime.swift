import Foundation

/// Presentation only: stored instants and elapsed durations remain unchanged.
public enum UserTime {
    public static func format(
        _ date: Date,
        dateOnly: Bool = false,
        timeOnly: Bool = false,
        showZone: Bool = false,
        timeZone: TimeZone = .autoupdatingCurrent
    ) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "ru_RU")
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.timeZone = timeZone
        formatter.dateFormat = dateOnly ? "dd.MM.yyyy" : timeOnly ? "HH:mm" : "dd.MM.yyyy, HH:mm"
        let text = formatter.string(from: date)
        guard showZone || ["UTC", "GMT", "Etc/UTC", "Etc/GMT"].contains(timeZone.identifier) else { return text }
        let offsetMinutes = timeZone.secondsFromGMT(for: date) / 60
        let offset = abs(offsetMinutes)
        let zone = offset == 0 ? "UTC" : String(format: "UTC%@%02d:%02d", offsetMinutes < 0 ? "-" : "+", offset / 60, offset % 60)
        return "\(text) (\(zone))"
    }

    public static func interval(start: Date, end: Date, timeZone: TimeZone = .autoupdatingCurrent) -> String {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = timeZone
        return "\(format(start, timeZone: timeZone)) — \(format(end, timeOnly: calendar.isDate(start, inSameDayAs: end), timeZone: timeZone))"
    }

    public static func formatDuration(_ seconds: Int) -> String {
        let total = max(0, seconds)
        let hours = total / 3600
        let minutes = total / 60 % 60
        if hours > 0 {
            return minutes > 0 ? "\(hours) ч \(minutes) мин" : "\(hours) ч"
        }
        return minutes > 0 ? "\(minutes) мин" : "\(total) с"
    }
}

public extension DesktopUploadQueueItem {
    var displayStartedAt: Date { recordingMetadata?.recordingStartedAt ?? createdAt }
}

public extension RecordingDisplayMetadata {
    var generatedDisplayTitlePrefix: String? {
        guard titleStatus == .generated, titleSource != .userConfirmed,
              let suffix = title.range(of: #" - \d{4}-\d{2}-\d{2} \d{2}:\d{2}$"#, options: .regularExpression) else {
            return nil
        }
        return titleSource == .generic ? "Запись " : "\(title[..<suffix.lowerBound]) — "
    }

    func displayTitle(timeZone: TimeZone = .autoupdatingCurrent) -> String {
        guard let prefix = generatedDisplayTitlePrefix else { return title }
        return "\(prefix)\(UserTime.format(recordingStartedAt, timeZone: timeZone))"
    }
}
