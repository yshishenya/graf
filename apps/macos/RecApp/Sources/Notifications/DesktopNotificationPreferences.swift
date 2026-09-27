import CryptoKit
import Foundation

public struct DesktopNotificationPreferences: Codable, Equatable {
    public var reminders = true
    public var offsetMinutes = 1
    public var showTitles = false
    public var sound = false
    public var quiet = false
    public init() {}

    private enum CodingKeys: String, CodingKey { case reminders, offsetMinutes, showTitles, sound, quiet }
    public init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        reminders = try values.decodeIfPresent(Bool.self, forKey: .reminders) ?? true
        offsetMinutes = try values.decodeIfPresent(Int.self, forKey: .offsetMinutes) ?? 1
        guard [0, 1, 5].contains(offsetMinutes) else {
            throw DecodingError.dataCorruptedError(forKey: .offsetMinutes, in: values, debugDescription: "Unsupported reminder offset")
        }
        showTitles = try values.decodeIfPresent(Bool.self, forKey: .showTitles) ?? false
        sound = try values.decodeIfPresent(Bool.self, forKey: .sound) ?? false
        quiet = try values.decodeIfPresent(Bool.self, forKey: .quiet) ?? false
    }
}

public final class DesktopNotificationPreferencesStore {
    private let defaults: UserDefaults
    public init(defaults: UserDefaults = .standard) { self.defaults = defaults }

    static func digest(_ value: String) -> String {
        SHA256.hash(data: Data(value.utf8)).map { String(format: "%02x", $0) }.joined()
    }
    private func key(_ owner: String) -> String { "graf.notifications." + Self.digest(owner) }

    public func load(owner: String) -> DesktopNotificationPreferences {
        guard !owner.isEmpty, let data = defaults.data(forKey: key(owner)),
              let value = try? JSONDecoder().decode(DesktopNotificationPreferences.self, from: data) else { return .init() }
        return value
    }

    public func save(_ value: DesktopNotificationPreferences, owner: String) throws {
        guard !owner.isEmpty, [0, 1, 5].contains(value.offsetMinutes) else {
            throw CocoaError(.validationMissingMandatoryProperty)
        }
        let data = try JSONEncoder().encode(value)
        defaults.set(data, forKey: key(owner))
        guard defaults.data(forKey: key(owner)) == data else { throw CocoaError(.fileWriteUnknown) }
    }

    // First owner remains authoritative, including an explicitly unknown owner.
    public func bindSession(_ id: String, context: String) {
        let name = key("session:" + id)
        if defaults.string(forKey: name) == nil { defaults.set(key(context), forKey: name) }
    }

    public func ownsSession(_ id: String, context: String) -> Bool {
        !context.isEmpty && defaults.string(forKey: key("session:" + id)) == key(context)
    }

    // A legacy account/workspace binding is adopted once by the confirmed origin.
    // Unknown and other-owner bindings are never rebound.
    func adoptLegacySession(_ id: String, context: String, legacyContext: String) {
        guard !context.isEmpty, !legacyContext.isEmpty, context != legacyContext else { return }
        let name = key("session:" + id)
        if defaults.string(forKey: name) == key(legacyContext) { defaults.set(key(context), forKey: name) }
    }

    // Captured at presenter initialization, immediately before OS retirement,
    // without waiting for an owner or calendar. Keep the first cutover across
    // restarts: a cancelled future request must not later become "delivered".
    func beginCalendarRetirement(at date: Date) {
        let name = "graf.notifications.calendarRetiredAt"
        if defaults.object(forKey: name) == nil {
            defaults.set(date.timeIntervalSince1970, forKey: name)
        }
    }

    // Called only for an eligible occurrence, immediately before presentation.
    // Keys contain no title/URL; context includes origin, owner and workspace.
    // Receipt lifetime covers the occurrence's possible 0/1/5-minute windows,
    // not its display duration. Repeated reads never extend either deadline.
    func claimMeeting(eventID: String, startsAt: Date, endsAt: Date,
                      owner: String, context: String, legacyContext: String, now: Date) -> Bool {
        let expires = startsAt.addingTimeInterval(120).timeIntervalSince1970
        guard !owner.isEmpty, !context.isEmpty, endsAt > now, expires > now.timeIntervalSince1970,
              let retiredAt = defaults.object(forKey: "graf.notifications.calendarRetiredAt") as? NSNumber else {
            return false
        }
        let receiptsKey = key(owner) + ".meetingReceipts"
        let identity = Self.digest("graf.local.reminder." + Self.digest(
            context + ":" + eventID + ":" + String(startsAt.timeIntervalSince1970)))
        var receipts = defaults.dictionary(forKey: receiptsKey) as? [String: Double] ?? [:]
        receipts = receipts.filter { $0.value > now.timeIntervalSince1970 }

        let attemptsKey = key(owner) + ".attempts"
        let reservationsKey = attemptsKey + ".reservations"
        var attempts = defaults.dictionary(forKey: attemptsKey) ?? [:]
        var reservations = defaults.dictionary(forKey: reservationsKey) ?? [:]
        let oldBase = legacyContext + ":" + eventID
        let oldDigests = [oldBase, oldBase + ":" + String(startsAt.timeIntervalSince1970)].map {
            Self.digest("graf.local.reminder." + Self.digest($0))
        }
        let inherited = oldDigests.contains { digest in
            guard let expiry = attempts[digest] as? NSNumber,
                  expiry.doubleValue > now.timeIntervalSince1970 else { return false }
            let reservation = reservations[digest] as? [String: Any]
            // Absence of a reservation means the old attempt was consumed.
            // Only a strictly future reservation proves cancellation before due.
            guard let due = reservation?["scheduledFor"] as? NSNumber else { return true }
            return due.doubleValue <= retiredAt.doubleValue
        }
        let alreadyClaimed = receipts[identity] != nil || inherited
        if receipts[identity] == nil { receipts[identity] = expires }
        defaults.set(receipts, forKey: receiptsKey)
        guard (defaults.dictionary(forKey: receiptsKey) as? [String: Double]) == receipts else {
            return false // Keep old evidence and do not present on write failure.
        }
        // One-way migration only. Unknown attempts/reservations and incident
        // indices stay untouched; no old scheduler consumes these dictionaries.
        for digest in oldDigests {
            attempts.removeValue(forKey: digest)
            reservations.removeValue(forKey: digest)
        }
        if defaults.object(forKey: attemptsKey) != nil { defaults.set(attempts, forKey: attemptsKey) }
        if defaults.object(forKey: reservationsKey) != nil {
            if reservations.isEmpty { defaults.removeObject(forKey: reservationsKey) }
            else { defaults.set(reservations, forKey: reservationsKey) }
        }
        return !alreadyClaimed
    }

    // Only known incident identifiers are migrated. Unknown entries in the old
    // numeric ledger are not calendar reservations and must not be wiped.
    @discardableResult
    func claimLocalIncident(_ incident: DesktopLocalNotificationIncident, owner: String, now: Date) -> Bool {
        guard !owner.isEmpty, incident.expires > now else { return false }
        let claimsKey = key(owner) + ".incidentClaims"
        let digest = Self.digest(incident.id)
        var claims = defaults.dictionary(forKey: claimsKey) as? [String: Bool] ?? [:]
        let oldKey = key(owner) + ".attempts"
        var old = defaults.dictionary(forKey: oldKey) ?? [:]
        let previous = defaults.dictionary(forKey: key(owner) + ".activeIncidents") as? [String: [String]] ?? [:]
        let items = Set(incident.itemIDs + (previous[incident.sessionID] ?? []))
        let oldDigests = (["graf.local.capture." + incident.sessionID]
            + items.map { "graf.local.incident." + $0 }).map(Self.digest)
        let inherited = oldDigests.contains { ((old[$0] as? NSNumber)?.doubleValue ?? 0) > now.timeIntervalSince1970 }
        let alreadyClaimed = claims[digest] == true || inherited
        // Persist the new deny marker before removing any old marker.
        claims[digest] = true
        defaults.set(claims, forKey: claimsKey)
        for value in oldDigests { old.removeValue(forKey: value) }
        if defaults.object(forKey: oldKey) != nil { defaults.set(old, forKey: oldKey) }
        return !alreadyClaimed
    }

    func reconcileIncidents(_ incidents: [DesktopLocalNotificationIncident], knownSessions: Set<String>, owner: String) {
        guard !owner.isEmpty else { return }
        let stateKey = key(owner) + ".activeIncidents"
        var previous = defaults.dictionary(forKey: stateKey) as? [String: [String]] ?? [:]
        let current = Set(incidents.map(\.sessionID))
        let claimsKey = key(owner) + ".incidentClaims"
        var claims = defaults.dictionary(forKey: claimsKey) as? [String: Bool] ?? [:]
        let oldKey = key(owner) + ".attempts"
        var old = defaults.dictionary(forKey: oldKey) ?? [:]
        for session in knownSessions.subtracting(current) {
            guard let items = previous.removeValue(forKey: session) else { continue }
            claims.removeValue(forKey: Self.digest("graf.local.capture." + session))
            for id in ["graf.local.capture." + session] + items.map({ "graf.local.incident." + $0 }) {
                old.removeValue(forKey: Self.digest(id))
            }
        }
        // Keep previous identifiers until claimLocalIncident has migrated them;
        // a partial snapshot cannot erase the only link to an old deny marker.
        for incident in incidents {
            previous[incident.sessionID] = Array(Set((previous[incident.sessionID] ?? []) + incident.itemIDs)).sorted()
        }
        defaults.set(claims, forKey: claimsKey)
        defaults.set(previous, forKey: stateKey)
        if defaults.object(forKey: oldKey) != nil { defaults.set(old, forKey: oldKey) }
    }
}
