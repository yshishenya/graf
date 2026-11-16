#pragma once

#include "ProtectedPackedCustodyFormat.h"

namespace graf::windows {

struct PackedRecordAddress {
    PackedRecordKind kind;
    std::uint64_t offset;
    std::uint64_t selector;
    std::uint64_t version;
    std::uint32_t bodyBytes;
};
struct PackedDecodedRecord {
    CustodyBytes body;
    std::uint64_t version;
};

// In-memory typed protection only. NODE refs/HEAD descriptor semantics, paired
// authority, extent/path/ZERO/EOF checks and ownership proof belong to the tree
// layer. A decoded body is NOT permission to read, publish, upload or delete.
// Callers retain charged plaintext ownership and must wipe it before release.
class ProtectedPackedCustodyCodec final {
public:
    [[nodiscard]] static CustodyCodecResult<CustodyBytes> seal(
        const PackedCustodyContext&, const PackedRecordAddress&, const CustodyBytes& body);
    // Expected selector/ref MUST come from the authorized parent path. This
    // checks intrinsic ref shape and exact envelope SHA BEFORE native decode;
    // it does not establish the parent path's provenance or committed extent.
    [[nodiscard]] static CustodyCodecResult<PackedDecodedRecord> openReferenced(
        const PackedCustodyContext&, std::uint64_t selector,
        const PackedReference&, const CustodyBytes& envelope);
    // Only HEAD permits unknown generation=0 during cold decoding. The caller
    // still must verify descriptor/paired heads and their full reachable closure.
    [[nodiscard]] static CustodyCodecResult<PackedDecodedRecord> openHead(
        const PackedCustodyContext&, std::uint32_t slot,
        const CustodyBytes& cell, std::uint64_t expectedGeneration = 0);
};
} // namespace graf::windows
