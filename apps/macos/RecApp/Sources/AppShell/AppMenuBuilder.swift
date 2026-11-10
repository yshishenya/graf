import AppKit
import TwoBrainRecShared

@MainActor
enum AppMenuBuilder {
    static func install(on app: NSApplication, zoomTarget: AnyObject) {
        let menu = makeMenu(zoomTarget: zoomTarget)
        app.mainMenu = menu
        app.windowsMenu = menu.items.first { $0.submenu?.title == "Окно" }?.submenu
    }

    static func makeMenu(zoomTarget: AnyObject) -> NSMenu {
        let displayName = GrafAppChannel.current.displayName
        let mainMenu = NSMenu()

        let appMenuItem = NSMenuItem()
        mainMenu.addItem(appMenuItem)
        let appMenu = NSMenu(title: displayName)
        appMenuItem.submenu = appMenu

        appMenu.addItem(
            withTitle: "О \(displayName)",
            action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)),
            keyEquivalent: ""
        )
        addItem(
            to: appMenu,
            title: "Проверить обновления…",
            action: #selector(AppLifecycleDelegate.checkForUpdates(_:)),
            target: zoomTarget
        )
        appMenu.addItem(.separator())
        addItem(
            to: appMenu,
            title: "Настройки…",
            action: #selector(AppLifecycleDelegate.openSettings(_:)),
            target: zoomTarget,
            keyEquivalent: ","
        )
        addItem(
            to: appMenu,
            title: "Остановить запись",
            action: #selector(AppLifecycleDelegate.stopRecordingFromMenu(_:)),
            target: zoomTarget,
            keyEquivalent: "s",
            modifiers: [.command, .shift]
        )
        addItem(
            to: appMenu,
            title: "Меню GRAF",
            action: #selector(AppLifecycleDelegate.openGrafMenu(_:)),
            target: zoomTarget
        )
        addItem(
            to: appMenu,
            title: "Перейти к уведомлению",
            action: #selector(AppLifecycleDelegate.focusNotification(_:)),
            target: zoomTarget,
            keyEquivalent: "n",
            modifiers: [.command, .option]
        )
        appMenu.addItem(.separator())
        addItem(
            to: appMenu,
            title: "Скрыть \(displayName)",
            action: #selector(NSApplication.hide(_:)),
            keyEquivalent: "h"
        )
        addItem(
            to: appMenu,
            title: "Скрыть остальные",
            action: #selector(NSApplication.hideOtherApplications(_:)),
            keyEquivalent: "h",
            modifiers: [.command, .option]
        )
        addItem(
            to: appMenu,
            title: "Показать все",
            action: #selector(NSApplication.unhideAllApplications(_:))
        )
        appMenu.addItem(.separator())
        addItem(
            to: appMenu,
            title: "Завершить \(displayName)",
            action: #selector(NSApplication.terminate(_:)),
            keyEquivalent: "q"
        )

        let editMenuItem = NSMenuItem()
        mainMenu.addItem(editMenuItem)
        let editMenu = NSMenu(title: "Правка")
        editMenuItem.submenu = editMenu
        editMenu.addItem(withTitle: "Отменить", action: NSSelectorFromString("undo:"), keyEquivalent: "z")
        addItem(
            to: editMenu,
            title: "Повторить",
            action: NSSelectorFromString("redo:"),
            keyEquivalent: "z",
            modifiers: [.command, .shift]
        )
        editMenu.addItem(.separator())
        editMenu.addItem(withTitle: "Вырезать", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        editMenu.addItem(withTitle: "Копировать", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        editMenu.addItem(withTitle: "Вставить", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        addItem(
            to: editMenu,
            title: "Вставить и согласовать стиль",
            action: #selector(NSTextView.pasteAsPlainText(_:)),
            keyEquivalent: "v",
            modifiers: [.command, .option, .shift]
        )
        editMenu.addItem(withTitle: "Удалить", action: #selector(NSText.delete(_:)), keyEquivalent: "")
        editMenu.addItem(.separator())
        editMenu.addItem(withTitle: "Выбрать все", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")

        let viewMenuItem = NSMenuItem()
        mainMenu.addItem(viewMenuItem)
        let viewMenu = NSMenu(title: "Вид")
        viewMenuItem.submenu = viewMenu
        for item in WorkspaceZoomMenu.items {
            addItem(
                to: viewMenu,
                title: item.title,
                action: selector(for: item.command),
                target: zoomTarget,
                keyEquivalent: item.keyEquivalent
            )
        }

        let windowMenuItem = NSMenuItem()
        mainMenu.addItem(windowMenuItem)
        let windowMenu = NSMenu(title: "Окно")
        windowMenuItem.submenu = windowMenu
        windowMenu.addItem(
            withTitle: "Свернуть",
            action: #selector(NSWindow.miniaturize(_:)),
            keyEquivalent: "m"
        )
        windowMenu.addItem(
            withTitle: "Масштаб",
            action: #selector(NSWindow.zoom(_:)),
            keyEquivalent: ""
        )

        return mainMenu
    }

    private static func addItem(
        to menu: NSMenu,
        title: String,
        action: Selector?,
        target: AnyObject? = nil,
        keyEquivalent: String = "",
        modifiers: NSEvent.ModifierFlags = [.command]
    ) {
        let item = menu.addItem(withTitle: title, action: action, keyEquivalent: keyEquivalent)
        item.target = target
        if !keyEquivalent.isEmpty {
            item.keyEquivalentModifierMask = modifiers
        }
    }

    private static func selector(for command: WorkspaceZoomCommand) -> Selector {
        switch command {
        case .increase:
            return #selector(AppLifecycleDelegate.increaseWorkspaceZoom(_:))
        case .decrease:
            return #selector(AppLifecycleDelegate.decreaseWorkspaceZoom(_:))
        case .reset:
            return #selector(AppLifecycleDelegate.resetWorkspaceZoom(_:))
        }
    }
}
