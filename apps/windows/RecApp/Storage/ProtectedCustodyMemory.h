#pragma once

#include <atomic>
#include <cstddef>
#include <memory>
#include <new>
#include <type_traits>
#include <utility>

namespace graf::windows {

template<class T> class CustodyAllocator;

inline void wipeCustodyMemory(void* memory, std::size_t bytes) noexcept {
    auto* target = static_cast<volatile unsigned char*>(memory);
    for (std::size_t i = 0; i < bytes; ++i) target[i] = 0;
}

// Shared admission for packed native worker operations, including mutex wait.
// The operation keeps its owner/buffers until actual synchronous completion.
class CustodyNativeJob final {
public:
    CustodyNativeJob() noexcept {
        auto count = live_.load(std::memory_order_relaxed);
        while (count < 4) {
            if (live_.compare_exchange_weak(count, count + 1, std::memory_order_relaxed)) { held_ = true; break; }
        }
    }
    CustodyNativeJob(const CustodyNativeJob&) = delete;
    CustodyNativeJob& operator=(const CustodyNativeJob&) = delete;
    ~CustodyNativeJob() { if (held_) live_.fetch_sub(1, std::memory_order_relaxed); }
    explicit operator bool() const noexcept { return held_; }
private:
    inline static std::atomic<unsigned> live_{0};
    bool held_ = false;
};

// One shared admission count for actual reader/Clone and retained commit owners.
// Declare this before the owned handles so those close before admission releases.
class CustodyPin final {
public:
    CustodyPin() noexcept {
        auto count = live_.load(std::memory_order_relaxed);
        while (count < 32) {
            if (live_.compare_exchange_weak(count, count + 1, std::memory_order_relaxed)) { held_ = true; break; }
        }
    }
    CustodyPin(CustodyPin&& other) noexcept : held_(std::exchange(other.held_, false)) {}
    ~CustodyPin() { if (held_) live_.fetch_sub(1, std::memory_order_relaxed); }
    explicit operator bool() const noexcept { return held_; }
private:
    inline static std::atomic<unsigned> live_{0};
    bool held_ = false;
};

// Shared by media writers and full-value metadata staging: at most four
// live 256KiB dirty blocks/process. Release only after wiping/deallocating bytes.
class CustodyDirtySlot final {
public:
    CustodyDirtySlot() noexcept {
        auto count = live_.load(std::memory_order_relaxed);
        while (count < 4) {
            if (live_.compare_exchange_weak(count, count + 1, std::memory_order_relaxed)) { held_ = true; break; }
        }
    }
    CustodyDirtySlot(const CustodyDirtySlot&) = delete;
    CustodyDirtySlot& operator=(const CustodyDirtySlot&) = delete;
    ~CustodyDirtySlot() { if (held_) live_.fetch_sub(1, std::memory_order_relaxed); }
    explicit operator bool() const noexcept { return held_; }
private:
    inline static std::atomic<unsigned> live_{0};
    bool held_ = false;
};

// One process-wide charge for actual owned allocations, including capacity and
// retained results. Not a pin/GC registry or proof of the still-unconnected
// metadata/hash/upload/cache pipeline; native DPAPI/MF allocations are separate.
// Complete the specialization before the inline counter: MSVC/LTCG otherwise
// emits C4744 when another TU first instantiates this atomic as a class member.
static_assert(alignof(std::atomic<std::size_t>) >= alignof(std::size_t));
class CustodyOwnedMemory final {
public:
    static constexpr std::size_t limit = 64 * 1024 * 1024;
    // Observation only: admission MUST use the allocator's atomic reservation.
    [[nodiscard]] static std::size_t usedBytes() noexcept { return bytes_.load(std::memory_order_relaxed); }
private:
    template<class T> friend class CustodyAllocator;
    inline static std::atomic<std::size_t> bytes_{0};
};

// Standard vector ownership performs release only when storage is deallocated.
// Stateless/equal across types: moves/swaps transfer the same charged allocation.
template<class T> class CustodyAllocator {
public:
    using value_type = T;
    using is_always_equal = std::true_type;
    CustodyAllocator() noexcept = default;
    template<class U> CustodyAllocator(const CustodyAllocator<U>&) noexcept {}

    [[nodiscard]] T* allocate(std::size_t count) {
        if (count > CustodyOwnedMemory::limit / sizeof(T)) throw std::bad_alloc();
        const auto bytes = count * sizeof(T); // Bound checked before multiplication.
        auto used = CustodyOwnedMemory::bytes_.load(std::memory_order_relaxed);
        do {
            if (used > CustodyOwnedMemory::limit - bytes) throw std::bad_alloc();
        } while (!CustodyOwnedMemory::bytes_.compare_exchange_weak(used, used + bytes, std::memory_order_relaxed));
        try { return std::allocator<T>{}.allocate(count); }
        catch (...) { CustodyOwnedMemory::bytes_.fetch_sub(bytes, std::memory_order_relaxed); throw; }
    }
    void deallocate(T* memory, std::size_t count) noexcept {
        // Object lifetimes have ended; erase the entire retiring allocation,
        // including former tails, before releasing storage or its charge.
        wipeCustodyMemory(memory, count * sizeof(T));
        std::allocator<T>{}.deallocate(memory, count);
        CustodyOwnedMemory::bytes_.fetch_sub(count * sizeof(T), std::memory_order_relaxed);
    }
    template<class U> bool operator==(const CustodyAllocator<U>&) const noexcept { return true; }
    template<class U> bool operator!=(const CustodyAllocator<U>&) const noexcept { return false; }
};

} // namespace graf::windows
