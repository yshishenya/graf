#pragma once

#include "RecordingIndicator.h"
#include "InteractionPermit.h"

#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace graf::windows {

class WindowsTray final {
public:
    using Handler = std::function<void()>;

    WindowsTray(std::uintptr_t ownerWindow, Handler openHandler, Handler stopHandler,
                Handler quitHandler, Handler pauseResumeHandler = {},
                Handler startHandler = {}, Handler settingsHandler = {}, Handler focusNotificationHandler = {},
                Handler interactionInvalidated = {});
    ~WindowsTray();

    WindowsTray(const WindowsTray&) = delete;
    WindowsTray& operator=(const WindowsTray&) = delete;

    // Use the native recording truth, on the same UI thread as construction.
    // The shell must keep a visible indicator: Windows may hide tray icons.
    struct MenuAvailability {
        bool start;
        bool pauseResume;
        bool stop;
        bool settings;
    };
    // Projection only: readiness comes from the same native gate as Record.
    [[nodiscard]] static MenuAvailability menuAvailability(
        const RecordingIndicatorSnapshot& snapshot, bool recordingReady, bool exiting) noexcept {
        return {recordingReady && !isCaptureState(snapshot.state) && !exiting,
                !exiting && (snapshot.state == SessionState::recording || snapshot.state == SessionState::paused),
                snapshot.stopAvailable, !exiting};
    }
    void setState(const RecordingIndicatorSnapshot& snapshot, bool recordingReady = false, bool exiting = false);

    // Revalidate registration with Explorer on the UI thread before hiding the
    // shell. An allocated object (or a previous NIM_ADD) is not availability.
    [[nodiscard]] bool available() noexcept;
    // Fresh, fail-closed native query on the constructing UI thread. Never calls
    // the invalidation handler or pumps messages; tokens survive no lifecycle break.
    [[nodiscard]] InteractionPermit interactionPermit() noexcept;

    // Меню рисуется кистями оболочки: тема приходит тем же решением, что и у
    // окон, иначе меню остаётся системным на фоне окна GRAF.
    void setTheme(bool isDark);
    void setUpdateHandler(Handler handler);
    // Only neutral history labels/time from the current in-memory context.
    // These menu rows never replay actions or navigate to old events.
    void setNotificationState(bool visible, std::vector<std::wstring> history);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace graf::windows
