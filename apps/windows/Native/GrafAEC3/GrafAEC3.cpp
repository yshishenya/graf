#include "GrafAEC3.h"

#include <array>
#include <cstring>
#include <new>

struct graf_aec3_processor {
    graf_aec3_backend backend;
};

extern "C" graf_aec3_status graf_aec3_create(const graf_aec3_backend* backend,
                                                graf_aec3_processor** processor) {
    if (backend == nullptr || processor == nullptr || backend->process == nullptr) {
        return graf_aec3_invalid_argument;
    }
    auto* created = new (std::nothrow) graf_aec3_processor{*backend};
    if (created == nullptr) return graf_aec3_unavailable;
    *processor = created;
    return graf_aec3_ok;
}

extern "C" void graf_aec3_destroy(graf_aec3_processor* processor) { delete processor; }

extern "C" graf_aec3_status graf_aec3_process(graf_aec3_processor* processor,
                                                 const float* render_reference,
                                                 const float* microphone,
                                                 float* cleaned_microphone,
                                                 std::size_t frame_count) {
    if (processor == nullptr || render_reference == nullptr || microphone == nullptr ||
        cleaned_microphone == nullptr || frame_count == 0) {
        return graf_aec3_invalid_argument;
    }
    // The pinned upstream implementation is supplied through this C ABI backend.
    // There is deliberately no untreated-microphone fallback when it is absent.
    return processor->backend.process(processor->backend.context, render_reference, microphone,
                                      cleaned_microphone, frame_count)
        ? graf_aec3_ok : graf_aec3_process_failed;
}
