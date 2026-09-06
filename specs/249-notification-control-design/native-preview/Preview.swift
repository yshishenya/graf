import AppKit
import SwiftUI
import UserNotifications

// A standalone design preview. No capture, product API, files, or account data.
enum Capture: String, CaseIterable {
    case ready = "Готовность", recording = "Запись", paused = "Пауза", offline = "Без сети"
    var active: Bool { self != .ready }
    var title: String {
        switch self {
        case .ready: "Готово к записи"
        case .recording, .offline: "Идёт запись"
        case .paused: "Запись на паузе"
        }
    }
}
struct LocalIssue: Identifiable {
    let id: Int
    let title: String
    let detail: String
}
func updateLocalIssue(_ items: [LocalIssue], _ issue: LocalIssue) -> [LocalIssue] {
    items.contains(where: { $0.id == issue.id }) ? items.map { $0.id == issue.id ? issue : $0 } : items + [issue]
}
func rememberedRule(action: String, remember: Bool) -> String {
    guard remember else { return "Спрашивать" }
    return action == "record" ? "Всегда" : action == "decline" ? "Никогда" : "Спрашивать"
}

@MainActor
final class PreviewModel: ObservableObject {
    @Published var capture: Capture = .ready
    @Published var delivery = ""
    @Published var page = "Управление"
    @Published var reminders = true
    @Published var showTitles = false
    @Published var sound = false
    @Published var offset = 1
    @Published var permission = "Проверяем разрешение macOS…"
    @Published var feedback = ""
    @Published var autoRule = "Спрашивать"
    @Published var remaining = 8
    @Published var remember = false
    @Published var selectedIssue: LocalIssue?
    @Published var localIssues: [LocalIssue] = []
    func stop() { capture = .ready; delivery = "Запись остановлена · Отправка смоделирована" }
    func addUploadIssue() {
        localIssues = updateLocalIssue(localIssues, LocalIssue(id: 2, title: "Запись не отправлена", detail: "Этот Mac · Учебная запись · Локальная копия подтверждена только в сценарии макета"))
        feedback = "Один локальный вопрос. Повтор того же события не создаёт вторую карточку."
    }
    func resolve(_ issue: LocalIssue) {
        localIssues.removeAll { $0.id == issue.id }
        selectedIssue = nil
        delivery = "Отправка подтверждена в макете · Дальнейшая обработка доступна во встречах"
        feedback = "Локальная проблема решена. Итоги и ошибки серверной обработки относятся к веб-кабинету."
    }

}

struct PreviewBadge: View {
    var body: some View {
        Text("МАКЕТ · ЗАПИСИ ЗВУКА НЕТ").font(.system(size: 10, weight: .semibold)).foregroundStyle(.secondary)
    }
}
struct CaptureCard: View {
    @ObservedObject var model: PreviewModel
    let app: PreviewApp
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text("GRAF").font(.headline)
                Spacer()
                Button { app.showWindow(page: "Настройки") } label: { Image(systemName: "gearshape") }
                    .buttonStyle(.plain).accessibilityLabel("Настройки уведомлений")
            }
            PreviewBadge()
            HStack {
                Image(systemName: model.capture == .paused ? "pause.circle.fill" : model.capture.active ? "record.circle" : "waveform.circle")
                    .foregroundStyle(model.capture.active ? Color.red : Color.secondary).font(.title)
                VStack(alignment: .leading, spacing: 4) {
                    Text(model.capture.title).font(.title3.weight(.semibold))
                    if model.capture.active { Text("12:34").font(.system(.title, design: .monospaced)) }
                }
            }.accessibilityElement(children: .combine)
            LabeledContent("Микрофон", value: model.capture.active ? "Пример источника" : "Готов · пример")
            LabeledContent("Системный звук", value: model.capture == .paused ? "На паузе · пример" : "Пример источника")
                .foregroundStyle(.secondary)
            HStack {
                if model.capture.active {
                    Button(model.capture == .paused ? "Продолжить" : "Пауза") {
                        model.capture = model.capture == .paused ? .recording : .paused
                        app.updateCapture()
                    }
                    Button("Остановить", role: .destructive) { model.stop(); app.updateCapture() }
                        .keyboardShortcut(".", modifiers: [.command])
                } else {
                    Button("Начать запись · макет") { model.capture = .recording; model.delivery = ""; app.updateCapture() }
                        .buttonStyle(.borderedProminent)
                }
            }.controlSize(.large)
            if model.capture == .offline {
                Label("Нет связи. Запись продолжается на Mac — пример состояния.", systemImage: "wifi.slash")
                    .font(.callout).foregroundStyle(.orange).fixedSize(horizontal: false, vertical: true)
            }
            if !model.delivery.isEmpty { Text(model.delivery).font(.callout).foregroundStyle(.secondary) }
            Divider()
            VStack(alignment: .leading, spacing: 8) {
                Text("Ближайшая встреча").font(.caption).foregroundStyle(.secondary)
                Text("Учебное обсуждение").fontWeight(.medium)
                HStack { Text("14:30 — 15:00").foregroundStyle(.secondary); Spacer(); Button("Подключиться") { model.feedback = "В продукте откроется ссылка встречи. Запись этим действием не начинается." } }
            }
            Divider()
            HStack {
                Button("Открыть GRAF") { app.showWindow(page: "Управление") }
                Button { app.showWindow(page: "На этом Mac") } label: { Label("Этот Mac", systemImage: model.localIssues.isEmpty ? "desktopcomputer" : "exclamationmark.triangle") }
                    .accessibilityLabel(model.localIssues.isEmpty ? "Этот Mac: локальных проблем нет" : "Этот Mac: отправка требует действия")
                Spacer()
                Menu("Ещё") {
                    Button("Показать виджет") { app.showWidget() }
                    Button("Настройки…") { app.showWindow(page: "Настройки") }
                    Button("Проверить обновления") { model.feedback = "В продукте — текущий механизм обновления GRAF. Во время записи установка откладывается." }
                    Divider()
                    Button("Завершить макет") { app.requestQuit() }
                }.menuStyle(.borderlessButton).fixedSize()
            }.controlSize(.small)
        }.padding(20).frame(width: 360)
    }
}
struct FloatingControls: View {
    @ObservedObject var model: PreviewModel
    let app: PreviewApp
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: model.capture == .paused ? "pause.circle.fill" : "record.circle").foregroundStyle(.red)
            VStack(alignment: .leading, spacing: 2) {
                Text(model.capture.active ? "\(model.capture.title) · 12:34" : "Готово к записи").font(.callout.weight(.medium))
                Text("МАКЕТ · без захвата звука").font(.system(size: 9)).foregroundStyle(.secondary)
            }
            Spacer(minLength: 0)
            if model.capture.active {
                Button { model.capture = model.capture == .paused ? .recording : .paused; app.updateCapture() } label: {
                    Image(systemName: model.capture == .paused ? "play.fill" : "pause.fill")
                }.accessibilityLabel(model.capture == .paused ? "Продолжить запись" : "Пауза")
                Button("Стоп", role: .destructive) { model.stop(); app.updateCapture() }
            } else {
                Button("Открыть") { app.showWindow(page: "Управление") }
            }
        }.padding(14).frame(width: 390).background(.regularMaterial)
    }
}
struct AskView: View {
    @ObservedObject var model: PreviewModel
    let app: PreviewApp
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            PreviewBadge()
            Text("Началась встреча в Zoom").font(.headline)
            Text("Запись начнётся автоматически через \(model.remaining) секунд.")
            HStack {
                Button("Записать") { app.finishAsk("record") }.buttonStyle(.borderedProminent)
                Button("Не записывать") { app.finishAsk("decline") }
            }
            Toggle("Запомнить выбор для Zoom", isOn: $model.remember)
            Text("Это демонстрация. Микрофон и системный звук не используются.").font(.caption).foregroundStyle(.secondary)
        }.padding(20).frame(width: 360)
    }
}
struct LocalIssuesView: View {
    @ObservedObject var model: PreviewModel
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("На этом Mac").font(.title2.weight(.semibold))
            Text("Запись, устройства и отправка. Результаты встреч, доступ и оплата находятся в веб-кабинете.").foregroundStyle(.secondary)
            if model.localIssues.isEmpty {
                ContentUnavailableView("Локальных проблем нет", systemImage: "checkmark.circle", description: Text("Состояние текущей записи всегда видно в панели управления. Здесь нет истории готовых итогов."))
            } else {
                ForEach(model.localIssues) { issue in
                    VStack(alignment: .leading, spacing: 12) {
                        Label(issue.title, systemImage: "exclamationmark.triangle").font(.headline)
                        Text(issue.detail).foregroundStyle(.secondary)
                        Text("Требует действия на этом Mac").font(.caption)
                        Button("Открыть локальную запись") { model.selectedIssue = issue }
                    }.padding(16).frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color.orange.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
                }
            }
            Text("Просмотр не устраняет проблему. После подтверждённого восстановления она исчезает автоматически.").font(.caption).foregroundStyle(.secondary)
        }
        .sheet(item: $model.selectedIssue) { issue in
            VStack(alignment: .leading, spacing: 16) {
                PreviewBadge(); Text(issue.title).font(.title2); Text(issue.detail)
                Text("В продукте повторная отправка использует существующую очередь. Здесь можно проверить только переход и подтверждённое завершение сценария.")
                Button("Смоделировать успешную отправку") { model.resolve(issue) }
                Button("Назад") { model.selectedIssue = nil }.keyboardShortcut(.cancelAction)
            }.padding(24).frame(width: 420)
        }
    }
}
struct NativeSettings: View {
    @ObservedObject var model: PreviewModel
    let app: PreviewApp
    var body: some View {
        Form {
            Section("На этом Mac") {
                LabeledContent("Уведомления macOS", value: model.permission)
                Button("Показать системное уведомление…") { app.requestTestNotification() }
                Text("По нажатию macOS может запросить разрешение для отдельного приложения-макета. Настройки рабочего GRAF не меняются.").font(.caption).foregroundStyle(.secondary)
                Toggle("Напоминать о встречах", isOn: $model.reminders)
                Picker("Когда напоминать", selection: $model.offset) {
                    Text("За минуту").tag(1); Text("За 5 минут").tag(5); Text("В момент начала").tag(0)
                }.disabled(!model.reminders)
                Toggle("Названия в системных уведомлениях", isOn: $model.showTitles)
                Toggle("Звук уведомлений", isOn: $model.sound)
                Text("Напоминания и локальные проблемы относятся к этому Mac. Во время записи звук уведомлений выключен; важное состояние остаётся в виджете.").font(.caption).foregroundStyle(.secondary)
            }
            Section("Управление записью") {
                LabeledContent("Zoom · правило макета", value: model.autoRule)
                Text("Всегда / Спрашивать / Никогда. При «Спрашивать» — 8 секунд. Настройки уведомлений не отключают этот запрос, индикатор и Stop.").font(.callout)
            }
        }.formStyle(.grouped)
    }
}
struct PreviewWindow: View {
    @ObservedObject var model: PreviewModel
    let app: PreviewApp
    var body: some View {
        VStack(spacing: 0) {
            HStack {
                VStack(alignment: .leading) { Text("GRAF · Нативный дизайн").font(.headline); PreviewBadge() }
                Spacer()
                Button { model.page = "На этом Mac" } label: { Label("Этот Mac", systemImage: model.localIssues.isEmpty ? "desktopcomputer" : "exclamationmark.triangle") }
                    .accessibilityLabel("Состояние этого Mac")
                Button { model.page = "Настройки" } label: { Image(systemName: "gearshape") }.accessibilityLabel("Настройки")
            }.padding(18)
            Picker("Раздел", selection: $model.page) {
                Text("Управление").tag("Управление"); Text("На этом Mac").tag("На этом Mac"); Text("Настройки").tag("Настройки")
            }.pickerStyle(.segmented).padding(.horizontal, 18).padding(.bottom, 14)
            Divider()
            if model.page == "Управление" {
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        Text("Проверьте реальные поверхности macOS").font(.title2.weight(.semibold))
                        Text("Значок «GRAF·Макет» находится в системной строке меню. Плавающий виджет остаётся после закрытия этого окна. Все состояния записи — демонстрация.").foregroundStyle(.secondary)
                        HStack {
                            Button("Открыть панель строки меню") { app.showTray() }
                            Button("Показать виджет") { app.showWidget() }
                        }
                        Picker("Состояние макета", selection: $model.capture) {
                            ForEach(Capture.allCases, id: \.self) { Text($0.rawValue).tag($0) }
                        }.pickerStyle(.segmented).onChange(of: model.capture) { _, _ in app.updateCapture() }
                        HStack(alignment: .top, spacing: 20) {
                            CaptureCard(model: model, app: app).background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 14))
                            VStack(alignment: .leading, spacing: 14) {
                                Text("Сценарии").font(.headline)
                                Button("Запрос автозаписи · 8 с") { app.showAsk() }
                                Button("Ошибка отправки · макет") { model.addUploadIssue() }
                                Button("Обычный день") { model.localIssues = []; model.feedback = "Локальных проблем нет. Готовности встреч не появляются в панели Mac." }
                                Button("Системное уведомление…") { app.requestTestNotification() }
                                Text("Обычный баннер покажет macOS. Отдельный запрос на запись и Stop остаются нативными панелями GRAF.").font(.callout).foregroundStyle(.secondary)
                            }.frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }.padding(24)
                }
            } else if model.page == "На этом Mac" {
                LocalIssuesView(model: model).padding(24)
            } else {
                NativeSettings(model: model, app: app)
            }
            if !model.feedback.isEmpty { Divider(); Text(model.feedback).font(.callout).foregroundStyle(.secondary).frame(maxWidth: .infinity, alignment: .leading).padding(14) }
        }.frame(minWidth: 780, minHeight: 650)
    }
}

@MainActor
final class PreviewApp: NSObject, NSApplicationDelegate, UNUserNotificationCenterDelegate {
    let model = PreviewModel()
    var window: NSWindow!
    var status: NSStatusItem!
    let popover = NSPopover()
    var widget: NSPanel!
    var ask: NSPanel!
    var timer: Timer?
    var promptActive = false
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        let menu = NSMenu(); let root = NSMenuItem(); menu.addItem(root)
        let submenu = NSMenu(); root.submenu = submenu
        submenu.addItem(withTitle: "Панель управления", action: #selector(showTray), keyEquivalent: "p").target = self
        submenu.addItem(withTitle: "Настройки уведомлений…", action: #selector(openSettings), keyEquivalent: ",").target = self
        submenu.addItem(.separator())
        submenu.addItem(withTitle: "Завершить макет", action: #selector(quitFromMenu), keyEquivalent: "q").target = self
        NSApp.mainMenu = menu
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 850, height: 740), styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        window.title = "GRAF · Нативный макет уведомлений"
        window.isReleasedWhenClosed = false
        window.contentView = NSHostingView(rootView: PreviewWindow(model: model, app: self))
        window.center()
        status = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        status.button?.title = "GRAF·Макет"
        status.button?.image = NSImage(systemSymbolName: "waveform.circle", accessibilityDescription: "GRAF, макет")
        status.button?.imagePosition = .imageLeading
        status.button?.target = self; status.button?.action = #selector(toggleTray)
        popover.behavior = .transient
        popover.contentViewController = NSHostingController(rootView: CaptureCard(model: model, app: self))
        popover.contentSize = NSSize(width: 360, height: 520)
        widget = makePanel(root: FloatingControls(model: model, app: self), size: NSSize(width: 390, height: 68))
        ask = makePanel(root: AskView(model: model, app: self), size: NSSize(width: 360, height: 240))
        UNUserNotificationCenter.current().delegate = self
        refreshPermission()
        showWindow(page: "Управление")
    }
    func makePanel<V: View>(root: V, size: NSSize) -> NSPanel {
        let panel = NSPanel(contentRect: NSRect(origin: .zero, size: size), styleMask: [.titled, .nonactivatingPanel, .fullSizeContentView], backing: .buffered, defer: false)
        panel.titleVisibility = .hidden; panel.titlebarAppearsTransparent = true
        panel.isFloatingPanel = true; panel.level = .floating
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.isReleasedWhenClosed = false; panel.hidesOnDeactivate = false
        panel.isMovableByWindowBackground = true
        panel.contentView = NSHostingView(rootView: root)
        return panel
    }
    func showWindow(page: String) { model.page = page; window.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true) }
    @objc func openSettings() { showWindow(page: "Настройки") }
    @objc func quitFromMenu() { requestQuit() }
    @objc func toggleTray() { if popover.isShown { popover.performClose(nil) } else { showTray() } }
    @objc func showTray() {
        guard let button = status.button else { return }
        popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
    }
    func showWidget() {
        if !widget.isVisible, let screen = NSScreen.main {
            let frame = screen.visibleFrame
            widget.setFrameOrigin(NSPoint(x: frame.maxX - 420, y: frame.maxY - 110))
        }
        widget.orderFrontRegardless()
    }
    func updateCapture() {
        if model.capture.active && promptActive {
            promptActive = false; timer?.invalidate(); timer = nil; ask.orderOut(nil)
            model.autoRule = rememberedRule(action: "record", remember: model.remember)
        }
        status.button?.title = model.capture.active ? "GRAF·Макет 12:34" : "GRAF·Макет"
        status.button?.image = NSImage(systemSymbolName: model.capture == .paused ? "pause.circle" : model.capture.active ? "record.circle" : "waveform.circle", accessibilityDescription: model.capture.title)
        status.button?.setAccessibilityLabel("GRAF, макет. \(model.capture.title). Открыть управление")
        if model.capture.active { showWidget() } else { widget.orderOut(nil) }
    }
    func showAsk() {
        guard !model.capture.active, !promptActive else { model.feedback = "Сначала остановите текущую демонстрацию записи."; return }
        promptActive = true; model.remaining = 8; model.remember = false
        ask.center(); ask.orderFrontRegardless()
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard let self, self.promptActive else { return }
                self.model.remaining -= 1
                if self.model.remaining <= 0 { self.finishAsk("timeout") }
            }
        }
    }
    func finishAsk(_ action: String) {
        guard promptActive else { return }
        promptActive = false; timer?.invalidate(); timer = nil; ask.orderOut(nil)
        model.autoRule = rememberedRule(action: action, remember: model.remember)
        if action != "decline" { model.capture = .recording; updateCapture() }
        model.feedback = "Исход: \(action == "timeout" ? "истёк отсчёт" : action == "decline" ? "не записывать" : "записать"). Правило макета: \(model.autoRule). Звук не захватывался."
    }
    func refreshPermission() {
        Task {
            let settings = await UNUserNotificationCenter.current().notificationSettings()
            model.permission = settings.authorizationStatus == .authorized ? "Разрешены" : settings.authorizationStatus == .denied ? "Выключены в macOS" : "Разрешение ещё не запрашивалось"
        }
    }
    func requestTestNotification() {
        // Explicit UI action only. Never ask for OS permission on startup.
        guard !model.capture.active else { model.feedback = "Запись активна в макете: системный баннер подавлен. Состояние доступно в локальной панели."; return }
        Task {
            do {
                let center = UNUserNotificationCenter.current()
                let allowed = try await center.requestAuthorization(options: [.alert, .sound, .badge])
                refreshPermission()
                guard allowed else { model.feedback = "macOS не разрешила уведомления. Управление и локальные проблемы доступны."; return }
                guard !model.capture.active else { model.feedback = "За время запроса началась демонстрация записи. Баннер подавлен."; return }
                let content = UNMutableNotificationContent()
                content.title = "Проверка уведомлений GRAF"
                content.body = "Напоминания и проблемы записи на этом Mac. Это проверочное сообщение макета."
                if model.sound { content.sound = .default }
                content.userInfo = ["preview": true]
                try await center.add(UNNotificationRequest(identifier: "graf-design-preview-local-test", content: content, trigger: nil))
                model.feedback = "Проверочное уведомление передано macOS. Показ зависит от разрешений и режима фокусирования."
            } catch { model.feedback = "Не удалось передать уведомление macOS: \(error.localizedDescription)" }
        }
    }
    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification, withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        Task { @MainActor in
            if self.model.capture.active { completionHandler([]) }
            else { completionHandler(self.model.sound ? [.banner, .list, .sound] : [.banner, .list]) }
        }
    }
    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse, withCompletionHandler completionHandler: @escaping () -> Void) {
        Task { @MainActor in self.showWindow(page: "На этом Mac") }
        completionHandler()
    }
    func requestQuit() {
        if model.capture.active {
            let alert = NSAlert(); alert.messageText = "Остановить запись и выйти из макета?"
            alert.informativeText = "Запись искусственная. В GRAF выход должен дождаться остановки и сохранения очереди."
            alert.addButton(withTitle: "Продолжить запись"); alert.addButton(withTitle: "Остановить и выйти")
            guard alert.runModal() == .alertSecondButtonReturn else { return }
            model.stop()
        }
        timer?.invalidate()
        UNUserNotificationCenter.current().removePendingNotificationRequests(withIdentifiers: ["graf-design-preview-local-test"])
        UNUserNotificationCenter.current().removeDeliveredNotifications(withIdentifiers: ["graf-design-preview-local-test"])
        NSApp.terminate(nil)
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }
}

@main
struct PreviewEntry {
    @MainActor static func main() {
if CommandLine.arguments.contains("--self-check") {
    precondition(Capture.offline.active && Capture.paused.active && !Capture.ready.active)
    let issue = LocalIssue(id: 1, title: "Ошибка отправки", detail: "Макет")
    let items = updateLocalIssue([], issue)
    precondition(items.count == 1 && updateLocalIssue(items, issue).count == 1)
    precondition(items.filter { $0.id != issue.id }.isEmpty)
    precondition(rememberedRule(action: "timeout", remember: true) == "Спрашивать")
    precondition(rememberedRule(action: "record", remember: true) == "Всегда")
    precondition(rememberedRule(action: "decline", remember: true) == "Никогда")
    precondition(rememberedRule(action: "decline", remember: false) == "Спрашивать")
    print("7 native preview checks passed")
} else {
    let app = NSApplication.shared
    let delegate = PreviewApp()
    app.delegate = delegate
    app.run()
}

    }
}
