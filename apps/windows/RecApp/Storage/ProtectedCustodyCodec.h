#pragma once

#include "ProtectedCustodyMemory.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <initializer_list>
#include <optional>
#include <string>
#include <string_view>
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
    CustodyBytes& operator=(const CustodyBytes& other) {
        if (this != &other) assign(other.begin(), other.end());
        return *this;
    }
    CustodyBytes& operator=(CustodyBytes&& other) noexcept {
        if (this == &other) return *this;
        Base::operator=(std::move(other)); // Equal stateless allocator: no new proxy.
        return *this;
    }
    CustodyBytes& operator=(std::initializer_list<std::uint8_t> values) { assign(values); return *this; }
    void clear() noexcept { wipeCustodyMemory(data(), size()); Base::clear(); }
    void resize(std::size_t count) { resize(count, 0); }
    void resize(std::size_t count, std::uint8_t value) {
        if (count < size()) wipeCustodyMemory(data() + count, size() - count);
        Base::resize(count, value);
    }
    void pop_back() noexcept { wipeCustodyMemory(&back(), 1); Base::pop_back(); }
    void assign(std::size_t count, std::uint8_t value) {
        const auto old = size();
        Base::assign(count, value);
        wipeTail(old);
    }
    template<class Iterator, std::enable_if_t<!std::is_integral_v<Iterator>, int> = 0>
    void assign(Iterator first, Iterator last) {
        const auto old = size();
        Base::assign(first, last);
        wipeTail(old);
    }
    void assign(std::initializer_list<std::uint8_t> values) { assign(values.begin(), values.end()); }
    Base::iterator erase(Base::const_iterator first, Base::const_iterator last) {
        const auto offset = first - cbegin();
        const auto old = size();
        Base::erase(first, last);
        wipeTail(old);
        return begin() + offset; // resize invalidates the original erase iterator.
    }
    Base::iterator erase(Base::const_iterator at) { return erase(at, at + 1); }
private:
    void wipeTail(std::size_t old) noexcept {
        const auto retained = size();
        if (retained >= old || old > capacity()) return;
        Base::resize(old); // Within retained vector capacity; no allocation.
        wipeCustodyMemory(data() + retained, old - retained);
        Base::resize(retained);
    }
};
// Like CustodyVector: MSVC Debug default/move string constructors may allocate
// inside noexcept. Construct throwing empty storage first, then transfer it.
template<class Char> class BasicCustodyString final : public std::basic_string<Char, std::char_traits<Char>, CustodyAllocator<Char>> {
    using Base = std::basic_string<Char, std::char_traits<Char>, CustodyAllocator<Char>>;
public:
    BasicCustodyString() : Base(std::size_t{0}, Char{}) {}
    BasicCustodyString(const Char* value) : Base(value) {}
    BasicCustodyString(const Char* value, std::size_t count) : Base(value, count) {}
    BasicCustodyString(std::size_t count, Char value) : Base(count, value) {}
    explicit BasicCustodyString(std::basic_string_view<Char> value) : BasicCustodyString() {
        if (!value.empty()) this->assign(value.data(), value.size());
    }
    BasicCustodyString(BasicCustodyString&& other) : BasicCustodyString() {
        this->swap(other);
        other.wipe(); // Some STL implementations retain the moved-from SSO tail.
    }
    BasicCustodyString(const BasicCustodyString&) = default;
    BasicCustodyString& operator=(const BasicCustodyString& other) {
        if (this != &other) assign(other.data(), other.size());
        return *this;
    }
    BasicCustodyString& operator=(BasicCustodyString&& other) noexcept {
        if (this != &other) {
            wipe();
            Base::operator=(std::move(static_cast<Base&>(other)));
            other.wipe();
        }
        return *this;
    }
    template<class Value, std::enable_if_t<!std::is_same_v<std::decay_t<Value>, BasicCustodyString>, int> = 0>
    BasicCustodyString& operator=(Value&& value) {
        const auto old = this->size();
        Base::operator=(std::forward<Value>(value));
        wipeTail(old);
        return *this;
    }
    BasicCustodyString& operator=(std::initializer_list<Char> values) { return assign(values); }
    void clear() noexcept { wipeCustodyMemory(this->data(), this->size() * sizeof(Char)); Base::clear(); }
    void resize(std::size_t count, Char value = Char{}) {
        if (count < this->size()) wipeCustodyMemory(this->data() + count, (this->size() - count) * sizeof(Char));
        Base::resize(count, value);
    }
    void pop_back() noexcept { wipeCustodyMemory(&this->back(), sizeof(Char)); Base::pop_back(); }
    template<class... Args> BasicCustodyString& assign(Args&&... args) {
        const auto old = this->size();
        Base::assign(std::forward<Args>(args)...); // Read possible own suffix before wiping.
        wipeTail(old);
        return *this;
    }
    BasicCustodyString& assign(std::initializer_list<Char> values) { return assign(values.begin(), values.end()); }
    BasicCustodyString& assign(BasicCustodyString&& other) { return *this = std::move(other); }
    BasicCustodyString& erase(std::size_t at = 0, std::size_t count = Base::npos) {
        const auto old = this->size();
        Base::erase(at, count); // Invalid positions throw before any wipe.
        wipeTail(old);
        return *this;
    }
    typename Base::iterator erase(typename Base::const_iterator first, typename Base::const_iterator last) {
        const auto offset = first - this->cbegin();
        const auto old = this->size();
        Base::erase(first, last);
        wipeTail(old);
        return this->begin() + offset;
    }
    typename Base::iterator erase(typename Base::const_iterator at) { return erase(at, at + 1); }
    template<class... Args> BasicCustodyString& replace(Args&&... args) {
        const auto old = this->size();
        Base::replace(std::forward<Args>(args)...);
        wipeTail(old);
        return *this;
    }
    template<class... Args> BasicCustodyString& append(Args&&... args) {
        Base::append(std::forward<Args>(args)...); return *this;
    }
    template<class Value> BasicCustodyString& operator+=(Value&& value) {
        Base::operator+=(std::forward<Value>(value)); return *this;
    }
    ~BasicCustodyString() { wipe(); }
private:
    void wipeTail(std::size_t old) noexcept {
        const auto retained = this->size();
        if (retained >= old || old > this->capacity()) return;
        Base::resize(old);
        wipeCustodyMemory(this->data() + retained, (old - retained) * sizeof(Char));
        Base::resize(retained);
    }
    void wipe() noexcept {
        const auto retained = this->size();
        // Supported STL capacity fast path is checked under full quota in
        // Debug/Release; this is not a general C++17 no-allocation promise.
        Base::resize(this->capacity());
        wipeCustodyMemory(this->data(), (this->size() + 1) * sizeof(Char));
        Base::resize(retained);
    }
};
using CustodyString = BasicCustodyString<char>;
using CustodyWideString = BasicCustodyString<wchar_t>;
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
    // Historical migration block only: position0, payload<=64KiB inferred
    // after native/header validation. No current index or authority proof.
    [[nodiscard]] static CustodyCodecResult<CustodyBytes> openMigrationBirthBlock(
        const CustodyContext&, std::uint64_t version, const CustodyBytes& envelope);
    [[nodiscard]] static CustodyCodecResult<CustodyBytes> sealIndex(
        const CustodyContext&, std::uint32_t slot, const CustodyIndex&);
    [[nodiscard]] static CustodyCodecResult<CustodyIndex> openIndex(
        const CustodyContext&, std::uint32_t slot, const CustodyBytes& envelope);
};

} // namespace graf::windows
