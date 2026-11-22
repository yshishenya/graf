#pragma once

#ifdef _WIN32
#include <windows.h>
#include <functional>
#include <memory>
#include <optional>
#include <string>

namespace graf::windows {

class ExportSaveWorker;
enum class ExportSaveResult;

// UI thread only. Closing programmatically never returns focus or invokes the result.
class ExportSavePanel {
public:
    using Result = std::function<void(std::optional<std::wstring>, bool fromUser)>;
    [[nodiscard]] static std::unique_ptr<ExportSavePanel> open(HWND owner, const std::wstring& suggestedName, Result result);
    ~ExportSavePanel();
    void watch(const std::shared_ptr<ExportSaveWorker>& worker) noexcept;
    [[nodiscard]] bool acceptsResult() const noexcept;
    [[nodiscard]] bool retryAfter(ExportSaveResult result) noexcept;
    void revoke() noexcept;
    void close() noexcept;

private:
    struct State;
    explicit ExportSavePanel(std::shared_ptr<State> state);
    std::shared_ptr<State> state_;
};

} // namespace graf::windows
#endif
