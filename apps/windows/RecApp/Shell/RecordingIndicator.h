#pragma once

#include "../Contracts/WindowsDesktopContracts.h"

#include <functional>
#include <string>

namespace graf::windows {

struct RecordingIndicatorSnapshot {
    bool visible = false;
    bool stopAvailable = false;
    SessionState state = SessionState::idle;
    ReasonCode reason = ReasonCode::none;
    std::string accessibleName;
    std::string statusText;
};

class RecordingIndicator final {
public:
    using StopHandler = std::function<void()>;

    explicit RecordingIndicator(StopHandler stopHandler = {});

    void publish(SessionState state, ReasonCode reason = ReasonCode::none);
    void hide() noexcept;
    void clickStop();

    [[nodiscard]] const RecordingIndicatorSnapshot& snapshot() const noexcept { return snapshot_; }

private:
    StopHandler stopHandler_;
    RecordingIndicatorSnapshot snapshot_;
};

} // namespace graf::windows
