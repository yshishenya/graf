#include "../Bridge/SharedAudioBuffer.hpp"

#include <array>

namespace two_brain_rec::audio_proof {

bool SharedAudioBufferRejectsOverflowWithoutMovingReadIndex() {
    TwoBrainRec::SharedAudioBuffer ring{};
    std::array<float, TwoBrainRec::kSharedRingCapacity> source{};
    std::array<float, TwoBrainRec::kSharedRingCapacity> destination{};
    for (std::size_t index = 0; index < source.size(); ++index) {
        source[index] = static_cast<float>(index + 1);
    }

    const bool first_write = ring.Write(
        ring.mic_buffer,
        ring.mic_write_idx,
        ring.mic_read_idx,
        source.data(),
        source.size()
    );
    if (!first_write ||
        ring.mic_write_idx.load() != TwoBrainRec::kSharedRingCapacity ||
        ring.mic_read_idx.load() != 0) {
        return false;
    }

    const bool overflow_write = ring.Write(
        ring.mic_buffer,
        ring.mic_write_idx,
        ring.mic_read_idx,
        source.data(),
        1
    );
    if (overflow_write ||
        ring.mic_write_idx.load() != TwoBrainRec::kSharedRingCapacity ||
        ring.mic_read_idx.load() != 0) {
        return false;
    }

    const std::size_t read = ring.Read(
        ring.mic_buffer,
        ring.mic_write_idx,
        ring.mic_read_idx,
        destination.data(),
        destination.size()
    );
    return read == destination.size() &&
           destination == source &&
           ring.mic_read_idx.load() == TwoBrainRec::kSharedRingCapacity;
}

bool SharedAudioBufferRejectsOversizedWrites() {
    TwoBrainRec::SharedAudioBuffer ring{};
    std::array<float, TwoBrainRec::kSharedRingCapacity + 1> source{};
    return !ring.Write(
        ring.mic_buffer,
        ring.mic_write_idx,
        ring.mic_read_idx,
        source.data(),
        source.size()
    );
}

bool SharedAudioBufferAcceptsZeroLengthWrite() {
    TwoBrainRec::SharedAudioBuffer ring{};
    std::array<float, 1> source{1.0f};
    return ring.Write(
        ring.mic_buffer,
        ring.mic_write_idx,
        ring.mic_read_idx,
        source.data(),
        0
    ) && ring.mic_write_idx.load() == 0 && ring.mic_read_idx.load() == 0;
}

}  // namespace two_brain_rec::audio_proof
