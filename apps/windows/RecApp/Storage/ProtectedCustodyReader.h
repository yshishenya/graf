#pragma once

#include "ProtectedCustodyFiles.h"
#ifdef _WIN32
#include <atomic>
#include <objidl.h>
#include <wrl/client.h>

namespace graf::windows {

struct CustodyReader {
    Microsoft::WRL::ComPtr<IStream> stream;
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

} // namespace graf::windows
#endif
