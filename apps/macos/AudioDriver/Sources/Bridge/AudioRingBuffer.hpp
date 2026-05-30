#pragma once

#include <atomic>
#include <cstddef>
#include <cstring>
#include <vector>

namespace TwoBrainRec {

class AudioRingBuffer {
public:
    explicit AudioRingBuffer(size_t capacity)
        : mask_(capacity - 1),
          buffer_(capacity) {}

    size_t Write(const float* src, size_t count) {
        const size_t avail = AvailableWrite();
        const size_t n = count < avail ? count : avail;
        const size_t w = write_idx_.load(std::memory_order_relaxed);
        for (size_t i = 0; i < n; ++i) {
            buffer_[(w + i) & mask_] = src[i];
        }
        write_idx_.store(w + n, std::memory_order_release);
        return n;
    }

    size_t Read(float* dst, size_t count) {
        const size_t avail = AvailableRead();
        const size_t n = count < avail ? count : avail;
        const size_t r = read_idx_.load(std::memory_order_relaxed);
        for (size_t i = 0; i < n; ++i) {
            dst[i] = buffer_[(r + i) & mask_];
        }
        read_idx_.store(r + n, std::memory_order_release);
        return n;
    }

    size_t AvailableRead() const {
        return write_idx_.load(std::memory_order_acquire) - read_idx_.load(std::memory_order_relaxed);
    }

    size_t AvailableWrite() const {
        return mask_ + 1 - (write_idx_.load(std::memory_order_relaxed) - read_idx_.load(std::memory_order_acquire));
    }

    void Reset() {
        read_idx_.store(0, std::memory_order_relaxed);
        write_idx_.store(0, std::memory_order_relaxed);
    }

private:
    const size_t mask_;
    std::vector<float> buffer_;
    std::atomic<size_t> read_idx_{0};
    std::atomic<size_t> write_idx_{0};
};

} // namespace TwoBrainRec