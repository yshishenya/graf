#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>

namespace TwoBrainRec {

constexpr size_t kSharedRingCapacity = 16384;
constexpr const char* kShmName = "/graf-audio-bridge";

struct SharedAudioBuffer {
    std::atomic<size_t> mic_read_idx{0};
    std::atomic<size_t> mic_write_idx{0};
    std::atomic<size_t> speaker_read_idx{0};
    std::atomic<size_t> speaker_write_idx{0};
    std::atomic<size_t> capture_read_idx{0};
    std::atomic<size_t> capture_write_idx{0};
    std::atomic<uint64_t> app_heartbeat_nanos{0};
    std::atomic<uint64_t> app_io_state{0};
    std::atomic<uint64_t> app_writer_pid{0};

    float mic_buffer[kSharedRingCapacity];
    float speaker_buffer[kSharedRingCapacity];
    float capture_buffer[kSharedRingCapacity];

    struct CounterSnapshot {
        size_t captured_frame_count;
        size_t stored_frame_count;
        size_t retrieved_or_processed_frame_count;
        size_t dropped_frame_count;
        size_t empty_buffer_count;
        uint64_t last_valid_frame_nanos;
        uint64_t latency_timestamp_nanos;
    };

    bool Write(float* buf, std::atomic<size_t>& w_idx, std::atomic<size_t>& r_idx, const float* src, size_t count) {
        if (src == nullptr) return false;
        if (count == 0) return true;
        if (count > kSharedRingCapacity) return false;
        size_t w = w_idx.load(std::memory_order_relaxed);
        size_t r = r_idx.load(std::memory_order_acquire);
        size_t avail = kSharedRingCapacity - (w - r);
        if (count > avail) return false;
        for (size_t i = 0; i < count; ++i)
            buf[(w + i) & (kSharedRingCapacity - 1)] = src[i];
        w_idx.store(w + count, std::memory_order_release);
        return true;
    }

    size_t Read(float* buf, std::atomic<size_t>& w_idx, std::atomic<size_t>& r_idx, float* dst, size_t count) {
        size_t w = w_idx.load(std::memory_order_acquire);
        size_t r = r_idx.load(std::memory_order_relaxed);
        size_t avail = w - r;
        size_t n = count < avail ? count : avail;
        for (size_t i = 0; i < n; ++i)
            dst[i] = buf[(r + i) & (kSharedRingCapacity - 1)];
        r_idx.store(r + n, std::memory_order_release);
        return n;
    }

    size_t MicAvailable() {
        return mic_write_idx.load(std::memory_order_acquire) - mic_read_idx.load(std::memory_order_relaxed);
    }

    size_t SpeakerAvailable() {
        return speaker_write_idx.load(std::memory_order_acquire) - speaker_read_idx.load(std::memory_order_relaxed);
    }

    size_t CaptureAvailable() {
        return capture_write_idx.load(std::memory_order_acquire) - capture_read_idx.load(std::memory_order_relaxed);
    }

    CounterSnapshot MicCounterSnapshot() {
        const size_t written = mic_write_idx.load(std::memory_order_acquire);
        const size_t read = mic_read_idx.load(std::memory_order_relaxed);
        return CounterSnapshot{written, written, read, 0, written == read ? 1u : 0u, 0, 0};
    }

    CounterSnapshot SpeakerCounterSnapshot() {
        const size_t written = speaker_write_idx.load(std::memory_order_acquire);
        const size_t read = speaker_read_idx.load(std::memory_order_relaxed);
        return CounterSnapshot{written, written, read, 0, written == read ? 1u : 0u, 0, 0};
    }

    CounterSnapshot CaptureCounterSnapshot() {
        const size_t written = capture_write_idx.load(std::memory_order_acquire);
        const size_t read = capture_read_idx.load(std::memory_order_relaxed);
        return CounterSnapshot{written, written, read, 0, written == read ? 1u : 0u, 0, 0};
    }
};

static_assert(sizeof(SharedAudioBuffer) == 3 * kSharedRingCapacity * sizeof(float) + 6 * sizeof(std::atomic<size_t>) + 3 * sizeof(std::atomic<uint64_t>),
              "Unexpected SharedAudioBuffer layout");

} // namespace TwoBrainRec
