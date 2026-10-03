#pragma once

#include "ProtectedCustodyMemory.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <initializer_list>
#include <optional>
#include <type_traits>
#include <vector>

namespace graf::windows {

// MSVC Debug vector's default/move constructors allocate a charged iterator
// proxy even though they are noexcept. Use a potentially throwing empty-count
// construction before transferring storage, so admitted callers can classify
// exhaustion normally. No allocator charge or iterator check is exempted.
template<class T> class CustodyVector : public std::vector<T, CustodyAllocator<T>> {
    using Base = std::vector<T, CustodyAllocator<T>>;
public:
    using Base::operator=;
    CustodyVector() : Base(std::size_t{0}) {}
    explicit CustodyVector(std::size_t count) : Base(count) {}
    CustodyVector(std::size_t count, const T& value) : Base(count, value) {}
    template<class Iterator, std::enable_if_t<!std::is_integral_v<Iterator>, int> = 0>
    CustodyVector(Iterator begin, Iterator end) : Base(begin, end) {}
    CustodyVector(std::initializer_list<T> values) : Base(values) {}
    CustodyVector(CustodyVector&& other) : Base(std::size_t{0}) { this->swap(other); }
    CustodyVector(const CustodyVector&) = default;
    CustodyVector& operator=(const CustodyVector&) = default;
    CustodyVector& operator=(CustodyVector&& other) noexcept {
        if (this != &other) Base::operator=(std::move(other));
        return *this;
    }
};
class CustodyBytes final : public CustodyVector<std::uint8_t> {
    using Base = CustodyVector<std::uint8_t>;
public:
    using Base::Base;
    CustodyBytes() = default;
    CustodyBytes(CustodyBytes&&) = default;
    CustodyBytes(const CustodyBytes&) = default;
    CustodyBytes& operator=(const CustodyBytes&) = default;
    CustodyBytes& operator=(CustodyBytes&& other) noexcept {
        if (this == &other) return *this;
        wipe();
        Base::operator=(std::move(other)); // Equal stateless allocator: no new proxy.
        return *this;
    }
    ~CustodyBytes() { wipe(); } // Includes temporaries when optional/result transfer throws.
private:
    void wipe() noexcept {
        volatile std::uint8_t* bytes = data();
        for (std::size_t i = 0; i < size(); ++i) bytes[i] = 0;
    }
};
using CustodyId = std::array<std::uint8_t, 16>;
enum class CustodyRole : std::uint16_t {
    canonical = 1, media, playback, manifest, recovery, queue,
    packageState, bootstrap, migrationIntent,
};
struct CustodyContext {
    CustodyId storeId;
    CustodyId objectId;
    CustodyRole role;
};
struct CustodyIndexEntry {
    std::uint64_t version = 0;
    std::uint32_t envelopeBytes = 0;
    std::uint32_t flags = 0; // DATA=0, explicit ZERO=1; not a missing-block fallback.
};
struct CustodyIndex {
    std::uint64_t generation = 0;
    std::uint64_t logicalLength = 0;
    CustodyVector<CustodyIndexEntry> entries;
};
enum class CustodyCodecError {
    none, invalidInput, invalidEnvelope, invalidPlaintext,
    hashFailed, nativeFailed, unsupportedPlatform, allocationFailed,
};
template<class T> struct CustodyCodecResult {
    std::optional<T> value;
    CustodyCodecError error = CustodyCodecError::none;
    std::uint32_t nativeError = 0;
    [[nodiscard]] bool ok() const noexcept { return value.has_value(); }
};

// In-memory v1 codec only. No file IO, commit acknowledgment or recovery authority.
class ProtectedCustodyCodec final {
public:
    static constexpr std::uint32_t blockBytes = 256 * 1024;
    [[nodiscard]] static std::uint64_t logicalLimit(CustodyRole role) noexcept;
    // Validate before reading/allocating an untrusted envelope. Zero means invalid input.
    [[nodiscard]] static std::size_t blockEnvelopeLimit(std::uint32_t payloadBytes) noexcept;
    [[nodiscard]] static std::size_t indexEnvelopeLimit(CustodyRole role) noexcept;
    [[nodiscard]] static CustodyCodecResult<CustodyBytes> sealBlock(
        const CustodyContext&, std::uint64_t position, std::uint64_t version,
        const CustodyBytes& payload);
    [[nodiscard]] static CustodyCodecResult<CustodyBytes> openBlock(
        const CustodyContext&, std::uint64_t position, std::uint64_t version,
        std::uint32_t expectedPayloadBytes, const CustodyBytes& envelope);
    [[nodiscard]] static CustodyCodecResult<CustodyBytes> sealIndex(
        const CustodyContext&, std::uint32_t slot, const CustodyIndex&);
    [[nodiscard]] static CustodyCodecResult<CustodyIndex> openIndex(
        const CustodyContext&, std::uint32_t slot, const CustodyBytes& envelope);
};

} // namespace graf::windows
