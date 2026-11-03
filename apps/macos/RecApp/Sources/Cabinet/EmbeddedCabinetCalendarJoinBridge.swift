import Foundation
#if canImport(WebKit)
import WebKit
#endif

@MainActor
final class EmbeddedCabinetCalendarJoinBridge {
    struct Request: Equatable {
        let eventID: UUID
        let requestID: UUID
        static func parse(_ body: Any) -> Request? {
            guard let body = body as? [String: String], Set(body.keys) == ["action", "eventId", "requestId"],
                  body["action"] == "joinCalendarEvent", let event = body["eventId"].flatMap(UUID.init(uuidString:)),
                  let request = body["requestId"].flatMap(UUID.init(uuidString:)) else { return nil }
            return Request(eventID: event, requestID: request)
        }
    }
    static let handlerName = "grafCalendarJoin"
    #if canImport(WebKit)
    static let contentWorld = WKContentWorld.world(name: "GRAFCalendarJoin")
    #endif
    private var task: Task<Void, Never>?
    private var activeID: UUID?

    /// A trusted request is already pending in the isolated page script and needs a terminal reply.
    static func checkReadiness(isReady: Bool, reject: () -> Void) -> Bool {
        guard isReady else { reject(); return false }
        return true
    }

    func invalidate() { activeID = nil; task?.cancel(); task = nil }

    func join(_ request: Request,
              resolve: @escaping @Sendable (UUID) async throws -> URL,
              isCurrent: @escaping @MainActor () -> Bool,
              open: @escaping @MainActor (URL) async -> Bool,
              reply: @escaping @MainActor (String) -> Void) {
        guard activeID == nil, isCurrent() else { reply("cancelled"); return }
        activeID = request.requestID
        reply("resolving")
        task = Task { [weak self] in
            guard let self else { return }
            defer { if self.activeID == request.requestID { self.activeID = nil; self.task = nil } }
            let opened = await CalendarMeetingOpener.resolveAndOpen(eventID: request.eventID,
                resolve: resolve,
                isCurrent: { self.activeID == request.requestID && isCurrent() },
                open: { url in reply("opening"); return await open(url) })
            guard !Task.isCancelled, self.activeID == request.requestID else { return }
            reply(isCurrent() ? (opened ? "handed_off" : "failed") : "cancelled")
        }
    }

    static let documentScript = #"""
    (() => {
      if (window.GRAFCalendarJoin) return;
      const pending = new Map();
      const render = item => {
        document.querySelectorAll(`[data-calendar-join="${item.eventId}"]`).forEach(button => {
        let status=button.parentElement.querySelector('[data-calendar-join-status]');
        if (!status) {status=document.createElement('span');status.dataset.calendarJoinStatus='';status.setAttribute('role','status');button.after(status);}
        const messages={resolving:'Открываем…',opening:'Открываем…',handed_off:'Ссылка передана приложению',failed:'Не удалось открыть. Повторите попытку.',cancelled:'Действие отменено. Повторите попытку.'};
        const message=messages[item.state] || messages.failed;
        if(status.textContent!==message) status.textContent=message;
        if(['resolving','opening'].includes(item.state)) button.setAttribute('aria-disabled','true');
        else button.removeAttribute('aria-disabled');
        });
      };
      window.GRAFCalendarJoin = { reply(id, state) {
        const item = pending.get(id); if (!item) return;
        item.state=state;render(item);
        if (!['resolving','opening'].includes(state)) pending.delete(id);
      }};
      new MutationObserver(()=>pending.forEach(render)).observe(document.documentElement,{childList:true,subtree:true});
      document.addEventListener('click', event => {
        const button = event.target.closest?.('[data-calendar-join]');
        if (!button || !event.isTrusted || !window.webkit?.messageHandlers?.grafCalendarJoin) return;
        event.preventDefault();
        if (button.getAttribute('aria-disabled') === 'true' || pending.size) return;
        const eventId = button.dataset.calendarJoin;
        if (!/^[0-9a-f-]{36}$/i.test(eventId)) return;
        let status = button.parentElement.querySelector('[data-calendar-join-status]');
        if (!status) { status=document.createElement('span'); status.setAttribute('role','status'); status.dataset.calendarJoinStatus=''; button.after(status); }
        const requestId = crypto.randomUUID();
        pending.set(requestId, {eventId,state:'resolving'}); render(pending.get(requestId));
        window.webkit.messageHandlers.grafCalendarJoin.postMessage({action:'joinCalendarEvent',eventId,requestId});
      }, true);
    })();
    """#
}
