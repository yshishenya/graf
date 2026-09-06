#pragma once

#include "RecordingIndicator.h"

#include <cstdint>
#include <functional>
#include <memory>

namespace graf::windows {

class WindowsTray final {
public:
    using Handler = std::function<void()>;

    WindowsTray(std::uintptr_t ownerWindow, Handler openHandler, Handler stopHandler,
                Handler quitHandler, Handler pauseResumeHandler = {});
    ~WindowsTray();

    WindowsTray(const WindowsTray&) = delete;
    WindowsTray& operator=(const WindowsTray&) = delete;

    // Use the native recording truth, on the same UI thread as construction.
    // The shell must keep a visible indicator: Windows may hide tray icons.
    void setState(const RecordingIndicatorSnapshot& snapshot);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace graf::windows
