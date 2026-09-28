import Foundation
#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif
#if canImport(AppKit)
import AppKit
#endif

/// Conference URLs have different semantics from help links: query and fragment are retained.
public enum CalendarMeetingOpener {
    public static func validatedHTTPS(_ raw: String) -> URL? {
        guard raw.utf8.count <= 8192, !raw.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }),
              let url = URL(string: raw), let parts = URLComponents(url: url, resolvingAgainstBaseURL: false),
              parts.scheme?.lowercased() == "https", let host = parts.host, !host.isEmpty,
              parts.user == nil, parts.password == nil, parts.port.map({ (0...65535).contains($0) }) ?? true else { return nil }
        let normalizedHost = host.lowercased().trimmingCharacters(in: CharacterSet(charactersIn: "."))
        guard isAllowedMeetingHost(normalizedHost) else { return nil }
        return url
    }

    // Mirrors the server's Python 3.13 ipaddress.is_global policy. Shared URL fixtures
    // guard parity, including globally reachable exceptions and IPv4-mapped IPv6.
    private static func isAllowedMeetingHost(_ host: String) -> Bool {
        guard host != "localhost", !host.hasSuffix(".localhost") else { return false }
        let literal = host.trimmingCharacters(in: CharacterSet(charactersIn: "[]"))
            .split(separator: "%", maxSplits: 1).first.map(String.init) ?? host
        let family = literal.contains(":") ? AF_INET6 : AF_INET
        guard let bytes = addressBytes(literal, family: family) else { return true } // DNS name
        if family == AF_INET6 && bytes.prefix(10).allSatisfy({ $0 == 0 }) && bytes[10] == 255 && bytes[11] == 255 {
            return isAllowedMeetingHost(bytes.suffix(4).map(String.init).joined(separator: "."))
        }
        let denied: [String]
        let exceptions: [String]
        if family == AF_INET {
            denied = ["0.0.0.0/8", "10.0.0.0/8", "127.0.0.0/8", "169.254.0.0/16", "172.16.0.0/12", "192.0.0.0/24", "192.0.0.170/31", "192.0.2.0/24", "192.168.0.0/16", "198.18.0.0/15", "198.51.100.0/24", "203.0.113.0/24", "240.0.0.0/4", "255.255.255.255/32", "100.64.0.0/10"]
            exceptions = ["192.0.0.9/32", "192.0.0.10/32"]
        } else {
            denied = ["::1/128", "::/128", "::ffff:0.0.0.0/96", "64:ff9b:1::/48", "100::/64", "2001::/23", "2001:db8::/32", "2002::/16", "3fff::/20", "fc00::/7", "fe80::/10"]
            exceptions = ["2001:1::1/128", "2001:1::2/128", "2001:3::/32", "2001:4:112::/48", "2001:20::/28", "2001:30::/28"]
        }
        func matches(_ cidr: String) -> Bool {
            let parts = cidr.split(separator: "/")
            guard let prefix = Int(parts[1]), let network = addressBytes(String(parts[0]), family: family) else { return false }
            return (0..<prefix).allSatisfy { bit in
                let mask = UInt8(1 << (7 - bit % 8))
                return (bytes[bit / 8] & mask) == (network[bit / 8] & mask)
            }
        }
        return exceptions.contains(where: matches) || !denied.contains(where: matches)
    }

    private static func addressBytes(_ literal: String, family: Int32) -> [UInt8]? {
        if family == AF_INET {
            // Darwin inet_pton accepts leading-zero decimal components; browsers
            // use inet_aton's octal/hex/abbreviated interpretation instead.
            var address = in_addr()
            guard inet_aton(literal, &address) == 1 else { return nil }
            return withUnsafeBytes(of: address) { Array($0) }
        }
        var bytes = [UInt8](repeating: 0, count: 16)
        let result = bytes.withUnsafeMutableBytes { inet_pton(family, literal, $0.baseAddress) }
        return result == 1 ? bytes : nil
    }

    public static func nativeCandidate(for url: URL) -> URL? {
        guard validatedHTTPS(url.absoluteString) != nil,
              var parts = URLComponents(url: url, resolvingAgainstBaseURL: false), let host = parts.host?.lowercased(),
              parts.port == nil || parts.port == 443 else { return nil }
        if host == "teams.microsoft.com", parts.path.hasPrefix("/l/meetup-join/") {
            parts.scheme = "msteams"
            return parts.url
        }
        if host == "zoom.us" || host.hasSuffix(".zoom.us") || host == "zoom.com" || host.hasSuffix(".zoom.com") {
            let segments = parts.path.split(separator: "/")
            guard segments.count == 2, segments[0] == "j", (9...11).contains(segments[1].count),
                  segments[1].allSatisfy({ $0.isASCII && $0.isNumber }) else { return nil }
            let parameters = (parts.queryItems ?? []).filter { !["action", "confno"].contains($0.name) }
            parts.scheme = "zoommtg"
            parts.path = "/join"
            parts.queryItems = [URLQueryItem(name: "action", value: "join"), URLQueryItem(name: "confno", value: String(segments[1]))] + parameters
            return parts.url
        }
        return nil
    }

    static func nativeApplicationIdentifiers(for url: URL) -> [String] {
        switch nativeCandidate(for: url)?.scheme {
        case "msteams": return ["com.microsoft.teams2", "com.microsoft.teams"]
        case "zoommtg": return ["us.zoom.xos"]
        default: return []
        }
    }

    @MainActor private static var eventOpening = false
    @MainActor private static var menuOpening = false

    @MainActor
    static func resolveAndOpen(eventID: UUID,
                               resolve: (UUID) async throws -> URL,
                               isCurrent: () -> Bool,
                               open: (URL) async -> Bool) async -> Bool {
        guard !eventOpening, isCurrent() else { return false }
        eventOpening = true
        defer { eventOpening = false }
        do {
            let url = try await resolve(eventID)
            guard !Task.isCancelled, isCurrent(), validatedHTTPS(url.absoluteString) != nil else { return false }
            return await open(url)
        } catch { return false }
    }

    #if canImport(AppKit)
    @MainActor
    public static func openEvent(_ id: String, isCurrent callerIsCurrent: @escaping () -> Bool = { true }) async -> Bool {
        guard let eventID = UUID(uuidString: id), let client = DesktopUploadClient.configuredFromEnvironment() else { return false }
        let generation = DesktopCabinetSessionBridge.generation
        let origin = client.baseOrigin
        let token = DesktopUploadClient.defaultAuthSessionToken(for: origin)
        let isCurrent = {
                callerIsCurrent() && DesktopCabinetSessionBridge.isCurrentSession(generation)
                    && DesktopUploadClient.defaultAuthSessionToken(for: origin) == token
                    && DesktopUploadClient.configuredFromEnvironment()?.baseOrigin == origin
        }
        return await resolveAndOpen(eventID: eventID,
            resolve: { try await client.calendarJoinTarget(eventID: $0) },
            isCurrent: isCurrent, open: { await Self.open($0,
                resolveFallback: { try await client.calendarJoinTarget(eventID: eventID) },
                isCurrent: isCurrent) })
    }

    @MainActor
    static func retryFailedJoin(attempt: () async -> Bool, isCurrent: () -> Bool,
                                confirmRetry: () async -> Bool) async -> Bool {
        while !Task.isCancelled && isCurrent() {
            if await attempt() { return true }
            guard !Task.isCancelled, isCurrent(), await confirmRetry() else { return false }
        }
        return false
    }

    @MainActor
    public static func openEventFromMenu(_ id: String) async {
        guard !menuOpening else { return }
        menuOpening = true
        defer { menuOpening = false }
        let generation = DesktopCabinetSessionBridge.generation
        _ = await retryFailedJoin(attempt: { await openEvent(id) },
            isCurrent: { DesktopCabinetSessionBridge.isCurrentSession(generation) }, confirmRetry: {
                let alert = NSAlert()
                alert.messageText = "Не удалось открыть встречу"
                alert.informativeText = "Проверьте подключение и повторите попытку. Если событие изменилось, обновите календарь."
                alert.addButton(withTitle: "Повторить подключение")
                alert.addButton(withTitle: "Отмена")
                return alert.runModal() == .alertFirstButtonReturn
            })
    }

    /// Browser recovery is a separate explicit user action, with fresh authorization.
    @MainActor
    static func recoverInBrowser(
        confirm: () async -> Bool,
        resolve: () async throws -> URL,
        isCurrent: () -> Bool,
        open: (URL) async -> Bool
    ) async -> Bool {
        guard !Task.isCancelled, isCurrent(), await confirm(), !Task.isCancelled, isCurrent() else { return false }
        do {
            let target = try await resolve()
            guard !Task.isCancelled, isCurrent(), let safe = validatedHTTPS(target.absoluteString) else { return false }
            return await open(safe)
        } catch { return false }
    }

    @MainActor
    public static func open(_ url: URL, resolveFallback: () async throws -> URL,
                            isCurrent: () -> Bool) async -> Bool {
        guard isCurrent(), let safe = validatedHTTPS(url.absoluteString) else { return false }
        let workspace = NSWorkspace.shared
        var application: URL?
        var target = safe
        // Nonstandard HTTPS ports belong to the browser, not custom native schemes.
        if safe.port == nil || safe.port == 443 {
            if safe.host?.lowercased() == "telemost.yandex.ru", safe.path.hasPrefix("/j/") {
                application = workspace.urlForApplication(withBundleIdentifier: "ru.yandex.desktop.telemost")
            } else if let native = nativeCandidate(for: safe) {
                application = nativeApplicationIdentifiers(for: safe)
                    .compactMap { workspace.urlForApplication(withBundleIdentifier: $0) }.first
                if application != nil { target = native }
            }
        }
        guard let application else { return workspace.open(safe) }
        let opened: Bool = await withCheckedContinuation { continuation in
            workspace.open([target], withApplicationAt: application, configuration: NSWorkspace.OpenConfiguration()) { _, error in
                continuation.resume(returning: error == nil)
            }
        }
        if opened { return true }
        return await recoverInBrowser(confirm: {
            let alert = NSAlert()
            alert.messageText = "Не удалось открыть приложение встречи"
            alert.informativeText = "Можно открыть встречу в браузере. Перед переходом GRAF ещё раз проверит доступность ссылки."
            alert.addButton(withTitle: "Открыть в браузере")
            alert.addButton(withTitle: "Отмена")
            return alert.runModal() == .alertFirstButtonReturn
        }, resolve: resolveFallback, isCurrent: isCurrent, open: { fresh in
            // Explicitly address the default HTTPS browser to avoid retrying a universal-link app.
            guard let browser = workspace.urlForApplication(toOpen: URL(string: "https://example.com")!) else { return false }
            return await withCheckedContinuation { continuation in
                workspace.open([fresh], withApplicationAt: browser, configuration: NSWorkspace.OpenConfiguration()) { _, error in
                    continuation.resume(returning: error == nil)
                }
            }
        })
    }
    #endif
}
