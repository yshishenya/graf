import Foundation
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
        guard normalizedHost.contains("."), !normalizedHost.contains(":"),
              !normalizedHost.hasSuffix(".localhost"), !normalizedHost.hasSuffix(".local"),
              !normalizedHost.allSatisfy({ $0.isNumber || $0 == "." }) else { return nil }
        return url
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
