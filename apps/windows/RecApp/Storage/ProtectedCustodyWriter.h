#pragma once

#include "ProtectedCustodyFiles.h"
#include <atomic>

namespace graf::windows {

struct CustodyWriterCommit {
    CustodyCommitState state = CustodyCommitState::notCommitted;
    CustodyFileError error = CustodyFileError::none;
    std::uint32_t nativeError = 0;
    std::uint64_t baseGeneration = 0, targetGeneration = 0;
};

// Seekable canonical/media/playback bytes, owned and operated by ONE worker.
// The caller reserves borrowed buffers and owns account/epoch/package leases.
// Writes accept bytes, not durability; checkpoint independently verifies the
// exact index/refs. Neither result nor a valid empty media grants sealed package,
// UI projection adoption, network/delete/GC authority. Never destructor IO.
// Caller retains this writer (including failed state) through result adoption
// or revalidation; last release is worker-only, not callback timeout cleanup.
class ProtectedCustodyWriter final {
public:
    [[nodiscard]] static CustodyFileResult<std::unique_ptr<ProtectedCustodyWriter>> open(
        const std::filesystem::path& root, std::string_view package, const CustodyContext&,
        std::uint64_t baseGeneration, std::shared_ptr<const std::atomic<bool>> cancellation);
    ~ProtectedCustodyWriter();
    ProtectedCustodyWriter(const ProtectedCustodyWriter&) = delete;
    ProtectedCustodyWriter& operator=(const ProtectedCustodyWriter&) = delete;
    [[nodiscard]] CustodyFileResult<std::uint64_t> writeAt(std::uint64_t offset, const void*, std::size_t bytes);
    [[nodiscard]] CustodyFileResult<std::uint64_t> readAt(std::uint64_t offset, void*, std::size_t bytes);
    [[nodiscard]] CustodyFileResult<std::uint64_t> setSize(std::uint64_t bytes);
    [[nodiscard]] CustodyWriterCommit checkpoint();
    [[nodiscard]] std::uint64_t size() const noexcept;
    [[nodiscard]] std::uint64_t generation() const noexcept;
private:
    struct State;
    explicit ProtectedCustodyWriter(std::unique_ptr<State>);
    std::unique_ptr<State> state_;
};

} // namespace graf::windows
