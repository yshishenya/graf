import SwiftUI

@MainActor
struct AppContentRoot: View {
    @ObservedObject private var workspaceZoomStore: WorkspaceZoomStore
    @ObservedObject private var appUpdateController: AppUpdateController

    init(
        workspaceZoomStore: WorkspaceZoomStore,
        appUpdateController: AppUpdateController
    ) {
        self.workspaceZoomStore = workspaceZoomStore
        self.appUpdateController = appUpdateController
    }

    var body: some View {
        ContentView(
            appUpdateController: appUpdateController,
            workspaceZoom: workspaceZoomStore.preference
        )
    }
}
