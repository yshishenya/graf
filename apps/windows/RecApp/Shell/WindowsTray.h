#pragma once

#include <cstdint>
#include <functional>
#include <memory>

namespace graf::windows {

class WindowsTray final {
public:
    using Handler = std::function<void()>;

    WindowsTray(std::uintptr_t ownerWindow, Handler openHandler, Handler stopHandler, Handler quitHandler);
    ~WindowsTray();

    WindowsTray(const WindowsTray&) = delete;
    WindowsTray& operator=(const WindowsTray&) = delete;

    void setRecording(bool active) noexcept;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace graf::windows
