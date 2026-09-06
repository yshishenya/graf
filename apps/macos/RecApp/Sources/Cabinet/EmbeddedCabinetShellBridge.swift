import AppKit
import Combine
import Foundation
import WebKit

struct EmbeddedCabinetShellSnapshot: Equatable {
    struct Item: Equatable, Identifiable {
        let id: String
        let label: String
        let url: URL
        let group: String
        let selected: Bool
    }
    let generation: String
    let items: [Item]
    let commands: Set<String>
    let name: String
    let theme: String

    static func allowsDocument(_ url: URL, policy: DesktopCabinetRoutePolicy) -> Bool {
        let decision = policy.decision(for: url)
        return (url.path.hasPrefix("/desktop/") || url.path == "/billing" || url.path.hasPrefix("/billing/"))
            && decision.decision == .allow
            && [.meetingList, .meetingDetail, .meetingShare, .meetingDeletionReport,
                .settings, .calendarSettings, .meetingDetectionSettings, .billing].contains(decision.route.kind)
    }

    static func sameDocumentRoute(_ lhs: URL, _ rhs: URL) -> Bool {
        // In-document anchors and filter query changes keep their generation and WebView.
        lhs.scheme == rhs.scheme && lhs.host == rhs.host && lhs.port == rhs.port && lhs.path == rhs.path
            && lhs.user == nil && lhs.password == nil && rhs.user == nil && rhs.password == nil
    }

    static func parse(_ body: Any, sourceURL: URL, documentURL: URL, isMainFrame: Bool,
                      generation: String, routePolicy: DesktopCabinetRoutePolicy) -> Self? {
        guard isMainFrame, sameDocumentRoute(sourceURL, documentURL),
              allowsDocument(documentURL, policy: routePolicy), allowsDocument(sourceURL, policy: routePolicy),
              JSONSerialization.isValidJSONObject(body),
              let bytes = try? JSONSerialization.data(withJSONObject: body), bytes.count <= 32_768,
              let body = body as? [String: Any], body["version"] as? String == "desktop-shell/v1",
              body["generation"] as? String == generation,
              let theme = body["theme"] as? String, ["light", "dark", "system"].contains(theme),
              let name = body["name"] as? String, validText(name, limit: 256),
              let commands = body["commands"] as? [String], commands.count <= 6,
              Set(commands).count == commands.count,
              Set(commands).isSubset(of: ["account", "settings", "theme", "logout", "update", "quit"]),
              let rows = body["items"] as? [[String: Any]], !rows.isEmpty, rows.count <= 32 else { return nil }
        var items: [Item] = []
        var selectedGroups = Set<String>()
        var ids = Set<String>()
        for row in rows {
            guard let id = row["id"] as? String, !id.isEmpty, id.count <= 64,
                  id.unicodeScalars.allSatisfy({ CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_").contains($0) }),
                  ids.insert(id).inserted,
                  let label = row["label"] as? String, !label.isEmpty, validText(label, limit: 160),
                  let group = row["group"] as? String, ["main", "settings"].contains(group),
                  let selectedNumber = row["selected"] as? NSNumber,
                  CFGetTypeID(selectedNumber) == CFBooleanGetTypeID(),
                  let route = row["route"] as? String, route.count <= 2048,
                  route.hasPrefix("/"), !route.hasPrefix("//"), !route.contains("\\"),
                  let url = URL(string: route, relativeTo: documentURL)?.absoluteURL,
                  url.scheme == documentURL.scheme, url.host == documentURL.host, url.port == documentURL.port,
                  url.user == nil, url.password == nil, allowsDocument(url, policy: routePolicy) else { return nil }
            let selected = selectedNumber.boolValue
            if selected && !selectedGroups.insert(group).inserted { return nil }
            items.append(Item(id: id, label: label, url: url, group: group, selected: selected))
        }
        return Self(generation: generation, items: items, commands: Set(commands), name: name, theme: theme)
    }

    private static func validText(_ text: String, limit: Int) -> Bool {
        text.count <= limit && text.rangeOfCharacter(from: .controlCharacters) == nil
    }
}

/// A document-scoped presentation of the existing server menu, never an authorization source.
@MainActor
public final class EmbeddedCabinetShellBridge: ObservableObject {
    static let messageHandlerName = "grafDesktopShell"
    @Published private(set) var snapshot: EmbeddedCabinetShellSnapshot?
    @Published private(set) var focusSidebar = false
    private weak var webView: WKWebView?
    private var documentURL: URL?
    private var generation = UUID().uuidString
    private var policy: DesktopCabinetRoutePolicy?
    private var sessionBoundaryID: UUID?

    private var currentWebView: WKWebView? {
        guard let webView, let url = webView.url, let documentURL, let policy,
              EmbeddedCabinetShellSnapshot.sameDocumentRoute(url, documentURL),
              EmbeddedCabinetShellSnapshot.allowsDocument(url, policy: policy) else { return nil }
        return webView
    }

    func committed(webView: WKWebView, policy: DesktopCabinetRoutePolicy, sessionBoundaryID: UUID) {
        invalidate()
        self.webView = webView
        self.policy = policy
        self.documentURL = webView.url
        self.sessionBoundaryID = sessionBoundaryID
    }

    func publishDocument(sessionBoundaryID: UUID) {
        guard let webView = currentWebView, let documentURL,
              self.sessionBoundaryID == sessionBoundaryID else { return }
        let token = generation
        webView.evaluateJavaScript(script("begin", arguments: [token])) { [weak self, weak webView] body, error in
            guard let self, let webView, self.generation == token, self.webView === webView else { return }
            guard error == nil, let body else { self.invalidate(); return }
            self.receive(body, sourceURL: documentURL, isMainFrame: true, sessionBoundaryID: sessionBoundaryID)
        }
    }

    func receive(_ body: Any, sourceURL: URL, isMainFrame: Bool, sessionBoundaryID: UUID) {
        guard let webView = currentWebView, let documentURL, let policy,
              self.sessionBoundaryID == sessionBoundaryID else { return }
        guard let envelope = body as? [String: Any], envelope["generation"] as? String == generation else { return }
        guard let value = EmbeddedCabinetShellSnapshot.parse(body, sourceURL: sourceURL, documentURL: documentURL,
                                                           isMainFrame: isMainFrame, generation: generation, routePolicy: policy) else {
            // Untrusted frames cannot clear the current menu; a bad current document falls back to HTML.
            if isMainFrame && EmbeddedCabinetShellSnapshot.sameDocumentRoute(sourceURL, documentURL) { invalidate() }
            return
        }
        let token = generation
        webView.evaluateJavaScript(script("adopt", arguments: [token])) { [weak self, weak webView] result, error in
            guard let self, let webView, self.currentWebView === webView, self.generation == token else { return }
            guard error == nil, let result = result as? [String: Any], result["adopted"] as? Bool == true else {
                self.invalidate(); return
            }
            self.focusSidebar = result["focusSidebar"] as? Bool == true
            self.snapshot = value
            webView.window?.appearance = value.theme == "system" ? nil : NSAppearance(named: value.theme == "dark" ? .darkAqua : .aqua)
        }
    }

    func invalidate(deferPublication: Bool = false) {
        if let webView { webView.evaluateJavaScript(script("release", arguments: [generation]), completionHandler: nil) }
        generation = UUID().uuidString
        documentURL = nil
        sessionBoundaryID = nil
        if deferPublication {
            // SwiftUI dismantling must revoke commands now, but cannot publish inside GraphHost teardown.
            let token = generation
            Task { @MainActor [weak self] in
                guard let self, self.generation == token else { return }
                self.snapshot = nil
                self.focusSidebar = false
            }
        } else {
            snapshot = nil
            focusSidebar = false
        }
    }

    func navigate(_ item: EmbeddedCabinetShellSnapshot.Item, controller: EmbeddedCabinetNavigationController) {
        guard let snapshot, snapshot.generation == generation, snapshot.items.contains(item),
              currentWebView != nil else { return }
        controller.openDocument(item.url)
    }

    func perform(_ action: String, value: String? = nil) {
        guard let snapshot, snapshot.generation == generation, snapshot.commands.contains(action),
              let webView = currentWebView,
              action != "theme" || ["light", "dark", "system"].contains(value ?? "") else { return }
        guard !webView.isLoading else { return }
        let token = generation
        webView.evaluateJavaScript(script("perform", arguments: [token, action, value ?? ""])) { [weak self] result, error in
            guard let self, self.generation == token else { return }
            if error != nil || result as? Bool != true { self.invalidate() }
        }
    }

    private func script(_ method: String, arguments: [String]) -> String {
        // Only native constants select a method; values are JSON, never interpolated executable code.
        let json = String(data: try! JSONSerialization.data(withJSONObject: arguments), encoding: .utf8)!
        return "window.grafDesktopShell?.\(method)(...\(json))"
    }
}
