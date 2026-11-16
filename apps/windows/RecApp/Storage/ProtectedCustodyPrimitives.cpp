#include "ProtectedCustodyPrimitives.h"
#include "Sha256.h"
#include <algorithm>
#include <cstring>
#include <istream>
#include <limits>
#include <streambuf>
#ifdef _WIN32
#include <windows.h>
#include <dpapi.h>
#endif

namespace graf::windows::custody_detail {
namespace {
class ByteInput final : public std::streambuf {
public:
    ByteInput(const std::uint8_t* bytes, std::size_t count) : bytes_(bytes), remaining_(count) {}
private:
    const std::uint8_t* bytes_;
    std::size_t remaining_;
    std::streamsize xsgetn(char* out, std::streamsize requested) override {
        const auto count = std::min(remaining_, static_cast<std::size_t>(requested));
        if (count != 0) { std::memcpy(out, bytes_, count); bytes_ += count; remaining_ -= count; }
        return static_cast<std::streamsize>(count);
    }
};
}
std::optional<std::array<std::uint8_t, 32>> digest(const std::uint8_t* bytes, std::size_t count) {
    if ((!bytes && count != 0) || count > CustodyOwnedMemory::limit) return std::nullopt;
    ByteInput buffer(bytes, count); std::istream input(&buffer);
    const auto hex = sha256Stream(input);
    if (hex.size() != 64) return std::nullopt;
    std::array<std::uint8_t, 32> out{};
    const auto nibble = [](char ch) { return ch <= '9' ? ch - '0' : ch - 'a' + 10; };
    for (std::size_t i = 0; i < out.size(); ++i)
        out[i] = static_cast<std::uint8_t>(nibble(hex[i * 2]) * 16 + nibble(hex[i * 2 + 1]));
    return out;
}
WipeBytes::~WipeBytes() {
#ifdef _WIN32
    if (!bytes.empty()) SecureZeroMemory(bytes.data(), bytes.size());
#else
    std::fill(bytes.begin(), bytes.end(), std::uint8_t{0});
#endif
}
CustodyCodecResult<CustodyBytes> nativeTransform(
    const std::uint8_t* entropy, std::size_t entropyBytes,
    const std::uint8_t* bytes, std::size_t count,
    std::size_t outputLimit, bool protect, std::size_t exactOutput) {
    using Error = CustodyCodecError;
    if (!bytes || count == 0 || !entropy || entropyBytes == 0 || outputLimit == 0 ||
        count > std::numeric_limits<std::uint32_t>::max() ||
        entropyBytes > std::numeric_limits<std::uint32_t>::max() || exactOutput > outputLimit)
        return {std::nullopt, Error::invalidInput, 0};
#ifdef _WIN32
    DATA_BLOB input{static_cast<DWORD>(count), const_cast<BYTE*>(bytes)};
    DATA_BLOB extra{static_cast<DWORD>(entropyBytes), const_cast<BYTE*>(entropy)};
    struct NativeOutput {
        DATA_BLOB blob{};
        ~NativeOutput() {
            if (blob.pbData) { SecureZeroMemory(blob.pbData, blob.cbData); LocalFree(blob.pbData); }
        }
    } output;
    const auto ok = protect
        ? CryptProtectData(&input, nullptr, &extra, nullptr, nullptr, CRYPTPROTECT_UI_FORBIDDEN, &output.blob)
        : CryptUnprotectData(&input, nullptr, &extra, nullptr, nullptr, CRYPTPROTECT_UI_FORBIDDEN, &output.blob);
    if (!ok) return {std::nullopt, Error::nativeFailed, GetLastError()};
    if (!output.blob.pbData || output.blob.cbData == 0 || output.blob.cbData > outputLimit ||
        (exactOutput != 0 && output.blob.cbData != exactOutput))
        return {std::nullopt, Error::invalidPlaintext, 0};
    return {CustodyBytes(output.blob.pbData, output.blob.pbData + output.blob.cbData), Error::none, 0};
#else
    (void)protect;
    return {std::nullopt, Error::unsupportedPlatform, 0};
#endif
}
} // namespace graf::windows::custody_detail
