#pragma once

#ifdef _WIN32
#include <windows.h>
#include <cstddef>
#include <memory>

extern "C" {
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/channel_layout.h>
#include <libavutil/frame.h>
#include <libavutil/log.h>
#include <libavutil/mem.h>
}

namespace graf::windows {

// Worker-local owner: declare before every object using these functions, so
// library resources and callbacks finish before the modules are released.
class FfmpegApi final {
public:
    static void* operator new(std::size_t);
    static void operator delete(void*) noexcept;
    FfmpegApi(); // Throws HRESULT on dependency failure; bad_alloc propagates.
    ~FfmpegApi() noexcept;
    FfmpegApi(const FfmpegApi&) = delete;
    FfmpegApi& operator=(const FfmpegApi&) = delete;
    FfmpegApi(FfmpegApi&&) = delete;
    FfmpegApi& operator=(FfmpegApi&&) = delete;

    decltype(&::av_version_info) av_version_info = nullptr;
    decltype(&::avutil_version) avutil_version = nullptr;
    decltype(&::avutil_configuration) avutil_configuration = nullptr;
    decltype(&::avutil_license) avutil_license = nullptr;
    decltype(&::av_malloc) av_malloc = nullptr;
    decltype(&::av_free) av_free = nullptr;
    decltype(&::av_freep) av_freep = nullptr;
    decltype(&::av_frame_alloc) av_frame_alloc = nullptr;
    decltype(&::av_frame_free) av_frame_free = nullptr;
    decltype(&::av_channel_layout_default) av_channel_layout_default = nullptr;
    decltype(&::av_channel_layout_copy) av_channel_layout_copy = nullptr;

    decltype(&::avcodec_version) avcodec_version = nullptr;
    decltype(&::avcodec_configuration) avcodec_configuration = nullptr;
    decltype(&::avcodec_license) avcodec_license = nullptr;
    decltype(&::avcodec_find_encoder_by_name) avcodec_find_encoder_by_name = nullptr;
    decltype(&::avcodec_alloc_context3) avcodec_alloc_context3 = nullptr;
    decltype(&::avcodec_open2) avcodec_open2 = nullptr;
    decltype(&::avcodec_free_context) avcodec_free_context = nullptr;
    decltype(&::avcodec_parameters_from_context) avcodec_parameters_from_context = nullptr;
    decltype(&::avcodec_send_frame) avcodec_send_frame = nullptr;
    decltype(&::avcodec_receive_packet) avcodec_receive_packet = nullptr;
    decltype(&::av_packet_alloc) av_packet_alloc = nullptr;
    decltype(&::av_packet_free) av_packet_free = nullptr;
    decltype(&::av_packet_unref) av_packet_unref = nullptr;
    decltype(&::av_packet_rescale_ts) av_packet_rescale_ts = nullptr;

    decltype(&::avformat_version) avformat_version = nullptr;
    decltype(&::avformat_configuration) avformat_configuration = nullptr;
    decltype(&::avformat_license) avformat_license = nullptr;
    decltype(&::avformat_alloc_output_context2) avformat_alloc_output_context2 = nullptr;
    decltype(&::avformat_new_stream) avformat_new_stream = nullptr;
    decltype(&::avformat_write_header) avformat_write_header = nullptr;
    decltype(&::avformat_free_context) avformat_free_context = nullptr;
    decltype(&::av_interleaved_write_frame) av_interleaved_write_frame = nullptr;
    decltype(&::av_write_trailer) av_write_trailer = nullptr;
    decltype(&::avio_alloc_context) avio_alloc_context = nullptr;
    decltype(&::avio_context_free) avio_context_free = nullptr;
    decltype(&::avio_flush) avio_flush = nullptr;

private:
    struct State;
    std::unique_ptr<State> state_;
};

} // namespace graf::windows
#endif
