import AppKit

@MainActor
public enum AppShell {
    public static func run() {
        let app = NSApplication.shared
        let appDelegate = AppLifecycleDelegate()
        AppMenuBuilder.install(on: app, zoomTarget: appDelegate)
        app.delegate = appDelegate
        withExtendedLifetime(appDelegate) {
            app.run()
        }
    }
}
