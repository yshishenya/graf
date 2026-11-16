#pragma once

#include "ProtectedCustodyCodec.h"

namespace graf::windows::custody_detail {

// Borrowed bounded input. No file access, ownership proof or serialized authority.
[[nodiscard]] std::optional<std::array<std::uint8_t, 32>> digest(
    const std::uint8_t*, std::size_t);
struct WipeBytes {
    CustodyBytes& bytes;
    ~WipeBytes();
};
// exactOutput=0 keeps the v1 variable-length index contract. Packed records
// require their exact plaintext size BEFORE copying native output to owned RAM.
[[nodiscard]] CustodyCodecResult<CustodyBytes> nativeTransform(
    const std::uint8_t* entropy, std::size_t entropyBytes,
    const std::uint8_t* input, std::size_t inputBytes,
    std::size_t outputLimit, bool protect, std::size_t exactOutput = 0);

} // namespace graf::windows::custody_detail
