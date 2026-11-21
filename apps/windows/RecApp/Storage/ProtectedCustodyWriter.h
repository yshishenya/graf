#pragma once

#include "ProtectedCustodyFiles.h"
#include <atomic>

namespace graf::windows {
class ProtectedPackedCustodyTree;
class ProtectedCustodyWriteStream;

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
    static void* operator new(std::size_t) { return CustodyAllocator<ProtectedCustodyWriter>{}.allocate(1); }
    static void operator delete(void* memory) noexcept {
        CustodyAllocator<ProtectedCustodyWriter>{}.deallocate(static_cast<ProtectedCustodyWriter*>(memory), 1);
    }
    [[nodiscard]] static CustodyFileResult<std::unique_ptr<ProtectedCustodyWriter>> open(
        const std::filesystem::path& root, std::string_view package, const CustodyContext&,
        std::uint64_t baseGeneration, std::shared_ptr<const std::atomic<bool>> cancellation);
    [[nodiscard]] static CustodyFileResult<std::unique_ptr<ProtectedCustodyWriter>> open(
        std::shared_ptr<const ProtectedPackedCustodyTree>, std::shared_ptr<const std::atomic<bool>> cancellation);
    ~ProtectedCustodyWriter();
    ProtectedCustodyWriter(const ProtectedCustodyWriter&) = delete;
    ProtectedCustodyWriter& operator=(const ProtectedCustodyWriter&) = delete;
    [[nodiscard]] CustodyFileResult<std::uint64_t> writeAt(std::uint64_t offset, const void*, std::size_t bytes);
    [[nodiscard]] CustodyFileResult<std::uint64_t> readAt(std::uint64_t offset, void*, std::size_t bytes);
    [[nodiscard]] CustodyFileResult<std::uint64_t> setSize(std::uint64_t bytes);
    [[nodiscard]] CustodyWriterCommit checkpoint();
    // Actual retained packed proof only, after a successful checkpoint and no
    // pending bytes. No path reopen, fabricated descriptor or package authority.
    [[nodiscard]] CustodyFileResult<std::shared_ptr<const ProtectedPackedCustodyTree>> committedPackedSnapshot();
    // Direct calls/observations are unavailable while the COM mutator is open.
    // Worker closes/drains it before checkpoint/readback; size/generation return
    // zero while attached, never a concurrent view of the mutable Writer state.
    [[nodiscard]] std::uint64_t size() const noexcept;
    [[nodiscard]] std::uint64_t generation() const noexcept;
private:
    friend class ProtectedCustodyWriteStream;
    [[nodiscard]] CustodyFileResult<bool> attachStream();
    void detachStream() noexcept;
    [[nodiscard]] CustodyFileResult<bool> streamReady();
    void failStream(CustodyFileError, std::uint32_t) noexcept;
    [[nodiscard]] std::uint64_t logicalLimit() const noexcept;
    [[nodiscard]] std::uint64_t sizeImpl() const noexcept;
    [[nodiscard]] std::uint64_t generationImpl() const noexcept;
    [[nodiscard]] CustodyFileResult<std::uint64_t> writeAtImpl(std::uint64_t, const void*, std::size_t);
    [[nodiscard]] CustodyFileResult<std::uint64_t> readAtImpl(std::uint64_t, void*, std::size_t);
    [[nodiscard]] CustodyFileResult<std::uint64_t> setSizeImpl(std::uint64_t);
    [[nodiscard]] CustodyWriterCommit checkpointImpl();
    struct State;
    explicit ProtectedCustodyWriter(std::unique_ptr<State>);
    std::unique_ptr<State> state_;
    std::atomic<bool> streamAttached_{false};
};

} // namespace graf::windows
