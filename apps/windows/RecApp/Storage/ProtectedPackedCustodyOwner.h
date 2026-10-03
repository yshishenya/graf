#pragma once

#include "ProtectedCustodyFiles.h"
#include "ProtectedPackedCustodyCodec.h"
#include <mutex>

namespace graf::windows {
class ProtectedPackedCustodyOwner;
class ProtectedPackedCustodyTree;
struct PackedCipherRead {
    // A failed byte move must leave the source's owner and pin intact.
    // Ciphertext storage remains charged until its actual deallocation.
    CustodyBytes bytes;
    CustodyPin pin;
    std::shared_ptr<ProtectedPackedCustodyOwner> owner;
};

// Worker-only physical prerequisite, not a logical reader/writer or authority.
// Existing-open checks confinement/prefix, NOT cold closure. A physical HEAD
// publication is NOT commit ACK. The tree layer must establish full/live proof,
// paired descriptors, operation authority, retained roots and logical budgets.
// Jobs/results share this owner, never reopen or expose its native handle.
class ProtectedPackedCustodyOwner final : public std::enable_shared_from_this<ProtectedPackedCustodyOwner> {
public:
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<ProtectedPackedCustodyOwner>> open(
        const std::filesystem::path&, std::string_view packageDirectoryId,
        const PackedCustodyContext&, CustodyFileAccess);
    ~ProtectedPackedCustodyOwner();
    ProtectedPackedCustodyOwner(const ProtectedPackedCustodyOwner&) = delete;
    ProtectedPackedCustodyOwner& operator=(const ProtectedPackedCustodyOwner&) = delete;
    [[nodiscard]] std::uint64_t epoch() const noexcept;
    [[nodiscard]] CustodyFileResult<PackedCipherRead> readCiphertext(std::uint64_t offset, std::uint32_t bytes);
    [[nodiscard]] CustodyFileResult<std::uint64_t> appendPosition();
    [[nodiscard]] CustodyFileResult<std::uint32_t> append(const PackedRecordAddress&, const CustodyBytes&);
    [[nodiscard]] CustodyFileResult<bool> flush();
    [[nodiscard]] CustodyPublishResult publishHead(std::uint32_t slot, const CustodyBytes&);
    void revokeWrites() noexcept;
    void blockWrites() noexcept;
private:
    friend class ProtectedPackedCustodyTree;
    struct State;
    // Stack-only private operation: one job + owner + the SAME physical mutex
    // across the entire tree/DPAPI/failure classification. No nested public IO.
    class Guard final {
        friend class ProtectedPackedCustodyTree;
        explicit Guard(std::shared_ptr<ProtectedPackedCustodyOwner>);
        [[nodiscard]] CustodyFileResult<bool> check();
        [[nodiscard]] CustodyFileResult<std::uint64_t> size();
        [[nodiscard]] CustodyFileResult<CustodyBytes> read(std::uint64_t, std::uint32_t);
        [[nodiscard]] CustodyFileResult<bool> reject(CustodyFileError, std::uint32_t = 0) noexcept;
        [[nodiscard]] const PackedCustodyContext& context() const noexcept;
        std::shared_ptr<ProtectedPackedCustodyOwner> owner_;
        CustodyNativeJob job_;
        std::unique_lock<std::mutex> lock_;
    };
    explicit ProtectedPackedCustodyOwner(std::shared_ptr<State>);
    std::shared_ptr<State> state_;
};
} // namespace graf::windows
