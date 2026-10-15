#pragma once

#include "ProtectedCustodyFiles.h"
#ifdef _WIN32
#include <atomic>
#include <objidl.h>
#include <wrl/client.h>

namespace graf::windows {
class ProtectedPackedCustodyTree;
class ProtectedCustodyPackagePair;
class ProtectedCustodyWriter;
class ProtectedCustodyRecordingPackage;

// The finalizer retains this wrapper independently of MF's COM references.
// Only its State/cursor (no owning native reference) may outlive close(). All
// operations serialize the actual Writer; direct Writer access is denied while
// attached. close() drains the whole active operation, never flushes, and makes
// late COM calls return STG_E_REVERTED without touching native ownership.
// Finalize -> close -> release MF/COM -> Writer checkpoint/readback, on worker.
class ProtectedCustodyWriteStream final {
public:
    static void* operator new(std::size_t) { return CustodyAllocator<ProtectedCustodyWriteStream>{}.allocate(1); }
    static void operator delete(void* memory) noexcept {
        CustodyAllocator<ProtectedCustodyWriteStream>{}.deallocate(static_cast<ProtectedCustodyWriteStream*>(memory), 1);
    }
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<ProtectedCustodyWriteStream>> open(
        std::shared_ptr<ProtectedCustodyWriter>, std::shared_ptr<const std::atomic<bool>> cancellation);
    [[nodiscard]] IStream* stream() const noexcept { return stream_.Get(); } // Borrowed; MF may AddRef.
    [[nodiscard]] HRESULT observedFailure() const noexcept; // Atomic sticky error only; no IO or close fence.
    [[nodiscard]] HRESULT close() noexcept; // First sticky error, or S_OK; not a durable ACK.
    ~ProtectedCustodyWriteStream(); // No IO; worker-only last release.
    ProtectedCustodyWriteStream(const ProtectedCustodyWriteStream&) = delete;
    ProtectedCustodyWriteStream& operator=(const ProtectedCustodyWriteStream&) = delete;
private:
    struct State;
    class Stream;
    ProtectedCustodyWriteStream(std::shared_ptr<ProtectedCustodyWriter>, std::shared_ptr<State>);
    std::shared_ptr<ProtectedCustodyWriter> writer_; // Never owned by the COM object/State.
    std::shared_ptr<State> state_;
    Microsoft::WRL::ComPtr<IStream> stream_;
};

struct CustodyReader {
    Microsoft::WRL::ComPtr<IStream> stream;
    // Value-only lifetime observation, never read/effect authority. Keep the
    // original stream while MF owns a fresh Clone; after shutdown/release,
    // acquire-load 1 proves only that original Reader remains. Missing means
    // unproven, not drained. AddRef does not create another Reader instance.
    std::weak_ptr<const std::atomic<unsigned>> readerInstances;
    CustodySnapshotState state = CustodySnapshotState::trustedPrefix;
    CustodyFileError recoveryError = CustodyFileError::none;
    std::uint32_t nativeError = 0;
};

// Worker-only open/read/last-release. Each stream/Clone owns its immutable
// snapshot and confined Files until actual release; cancellation is shared,
// not a raw controller reference. No plaintext file, refresh, logical ACK or GC.
// Caller jobs must additionally own/revalidate account/epoch/package authority;
// neither verified bytes nor trustedPrefix grants normal/upload/delete access.
[[nodiscard]] CustodyFileResult<CustodyReader> openProtectedCustodyReader(
    const std::filesystem::path& trustedRoot, std::string_view packageDirectoryId,
    const CustodyContext&, std::shared_ptr<const std::atomic<bool>> cancellation);

// Same read-only COM adapter; the immutable proof retains its existing owner.
// No reopen, representation guessing, package authority or logical ACK.
[[nodiscard]] CustodyFileResult<CustodyReader> openProtectedCustodyReader(
    std::shared_ptr<const ProtectedPackedCustodyTree>,
    std::shared_ptr<const std::atomic<bool>> cancellation);

// Exact SEALED ref from either physical slot of own protected metadata. Checks
// actual member closure/length/whole SHA before return at cursor zero. Any bad
// sibling rejects this call; a healthy LIVE sibling uses its actual checkpoint.
// Every Reader/Clone retains ALL member leases, not just its own. LIVE target
// is rejected. NOT full package/effect authority or partial live recovery.
[[nodiscard]] CustodyFileResult<CustodyReader> openProtectedCustodyReader(
    const std::filesystem::path& trustedRoot, std::shared_ptr<const ProtectedCustodyPackagePair>,
    std::uint32_t slot, std::size_t refIndex, std::shared_ptr<const std::atomic<bool>> cancellation);

using CustodyPackageReaders = std::array<std::array<CustodyReader, 5>, 2>;
// Worker-only refs from BOTH physical slots. Cells beyond refCount are empty.
// One owner per role: SEALED exact historical snapshots/whole SHA, LIVE actual
// highest checkpoint, always BOTH closures (no singleton/trustedPrefix success).
// Every stream starts at cursor zero; any sibling fault rejects the whole result.
// Streams/Clones retain the whole immutable group. No complete-frame prefix,
// manifest/normal/account/effect authority is granted by a readable checkpoint.
[[nodiscard]] CustodyFileResult<CustodyPackageReaders> openProtectedCustodyReaders(
    const std::filesystem::path& trustedRoot, std::shared_ptr<const ProtectedCustodyPackagePair>,
    std::shared_ptr<const std::atomic<bool>> cancellation);

// Same whole-group validator on genuine retained birth/metadata/member leases.
// No path reopen or writable ownership release between sealing and inspection.
[[nodiscard]] CustodyFileResult<CustodyPackageReaders> openProtectedCustodyReaders(
    std::shared_ptr<ProtectedCustodyRecordingPackage>, std::shared_ptr<const ProtectedCustodyPackagePair>,
    std::shared_ptr<const std::atomic<bool>> cancellation);

} // namespace graf::windows
#endif
