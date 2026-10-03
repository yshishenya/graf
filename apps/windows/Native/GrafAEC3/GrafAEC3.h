#pragma once

#include <cstddef>
#include <cstdint>

extern "C" {

struct graf_aec3_processor;

enum graf_aec3_status : std::uint32_t {
    graf_aec3_ok = 0,
    graf_aec3_invalid_argument = 1,
    graf_aec3_unavailable = 2,
    graf_aec3_process_failed = 3,
};

using graf_aec3_process_callback = bool (*)(
    void* context,
    const float* render_reference,
    const float* microphone,
    float* cleaned_microphone,
    std::size_t frame_count);

struct graf_aec3_backend {
    void* context = nullptr;
    graf_aec3_process_callback process = nullptr;
};

graf_aec3_status graf_aec3_create(
    const graf_aec3_backend* backend,
    graf_aec3_processor** processor);
void graf_aec3_destroy(graf_aec3_processor* processor);
graf_aec3_status graf_aec3_process(
    graf_aec3_processor* processor,
    const float* render_reference,
    const float* microphone,
    float* cleaned_microphone,
    std::size_t frame_count);

} // extern "C"
