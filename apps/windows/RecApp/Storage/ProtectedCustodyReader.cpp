#include "ProtectedCustodyReader.h"
#ifdef _WIN32
#include <algorithm>
#include <cstring>
#include <limits>
#include <mutex>
#include <utility>

namespace graf::windows {
namespace {
using Pin = CustodyPin;
struct ReaderState;
struct ReadCache {
    std::mutex mutex;
    const ReaderState* owner = nullptr;
    std::uint64_t position = 0;
    CustodyBytes bytes;
    void clear() noexcept {
        if (!bytes.empty()) SecureZeroMemory(bytes.data(), bytes.size());
        bytes.clear();
        try { bytes.shrink_to_fit(); } catch (const std::bad_alloc&) {}
        owner = nullptr;
    }
    ~ReadCache() { clear(); }
};
ReadCache& cache() { static ReadCache value; return value; }
struct ReaderState {
    CustodyContext context;
    CustodySnapshot snapshot;
    std::unique_ptr<ProtectedCustodyFiles> files;
    std::shared_ptr<const std::atomic<bool>> cancellation;
    std::atomic<HRESULT> failure{S_OK};
    ReaderState(const CustodyContext& contextValue, CustodySnapshot&& snapshotValue,
        std::unique_ptr<ProtectedCustodyFiles>&& filesValue, std::shared_ptr<const std::atomic<bool>> cancelled)
        : context(contextValue), snapshot(std::move(snapshotValue)), files(std::move(filesValue)), cancellation(std::move(cancelled)) {}
    ~ReaderState() {
        auto& shared = cache(); std::lock_guard<std::mutex> lock(shared.mutex);
        if (shared.owner == this) shared.clear(); // Cannot reuse this address with old plaintext.
    }
    HRESULT fail(HRESULT hr) noexcept {
        HRESULT expected = S_OK; failure.compare_exchange_strong(expected, hr);
        return failure.load();
    }
    HRESULT status() noexcept {
        if (cancellation->load()) return fail(HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED));
        return failure.load();
    }
};
HRESULT readError(CustodyFileError error, std::uint32_t native) noexcept {
    if (error == CustodyFileError::allocationFailed) return E_OUTOFMEMORY;
    return native ? HRESULT_FROM_WIN32(native) : STG_E_READFAULT;
}
class Reader final : public IStream {
public:
    Reader(Pin&& pin, std::shared_ptr<ReaderState> state, std::uint64_t cursor = 0)
        : pin_(std::move(pin)), state_(std::move(state)), cursor_(cursor) {}
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid, void** output) noexcept override {
        if (!output) return E_POINTER;
        *output = nullptr;
        if (iid != __uuidof(IUnknown) && iid != __uuidof(ISequentialStream) && iid != __uuidof(IStream)) return E_NOINTERFACE;
        *output = static_cast<IStream*>(this); AddRef(); return S_OK;
    }
    ULONG STDMETHODCALLTYPE AddRef() noexcept override { return ++references_; }
    ULONG STDMETHODCALLTYPE Release() noexcept override {
        const auto remaining = --references_; if (!remaining) delete this; return remaining;
    }
    HRESULT STDMETHODCALLTYPE Read(void* output, ULONG requested, ULONG* got) noexcept override {
        if (got) *got = 0;
        if (!output && requested) return STG_E_INVALIDPOINTER;
        ULONG copied = 0;
        const auto reject = [&](HRESULT hr) {
            if (copied) SecureZeroMemory(output, copied);
            return state_->fail(hr); // No cursor advance or partial-byte acknowledgement.
        };
        try {
            auto& shared = cache();
            // ponytail: one process-wide block/IO lock (256KiB cache). Split
            // locks/cache only if measured parallel reader throughput requires it.
            std::lock_guard<std::mutex> lock(shared.mutex);
            if (FAILED(state_->status())) return state_->status();
            const auto length = state_->snapshot.index.logicalLength;
            const auto count = static_cast<ULONG>(std::min<std::uint64_t>(requested, cursor_ < length ? length - cursor_ : 0));
            while (copied < count) {
                const auto active = state_->status(); if (FAILED(active)) return reject(active);
                const auto at = cursor_ + copied;
                const auto block = at / ProtectedCustodyCodec::blockBytes;
                const auto within = static_cast<std::size_t>(at % ProtectedCustodyCodec::blockBytes);
                const auto payload = static_cast<std::uint32_t>(std::min<std::uint64_t>(ProtectedCustodyCodec::blockBytes,
                    length - block * ProtectedCustodyCodec::blockBytes));
                const auto& entry = state_->snapshot.index.entries[static_cast<std::size_t>(block)];
                const auto chunk = static_cast<ULONG>(std::min<std::size_t>(count - copied, payload - within));
                auto* destination = static_cast<std::uint8_t*>(output) + copied;
                if (entry.flags == 1) std::memset(destination, 0, chunk); // Authenticated explicit ZERO only.
                else {
                    if (shared.owner != state_.get() || shared.position != block) {
                        shared.clear();
                        auto cipher = state_->files->readBlock(block, entry.version, payload, entry.envelopeBytes);
                        if (!cipher.ok()) return reject(readError(cipher.error, cipher.nativeError));
                        auto plain = ProtectedCustodyCodec::openBlock(state_->context, block, entry.version, payload, *cipher.value);
                        if (!plain.ok()) return reject(plain.error == CustodyCodecError::allocationFailed ? E_OUTOFMEMORY : STG_E_READFAULT);
                        shared.bytes = std::move(*plain.value);
                        shared.owner = state_.get(); shared.position = block;
                    }
                    std::memcpy(destination, shared.bytes.data() + within, chunk);
                }
                copied += chunk;
            }
            const auto active = state_->status(); if (FAILED(active)) return reject(active);
            cursor_ += copied; if (got) *got = copied;
            return copied == requested ? S_OK : S_FALSE;
        } catch (const std::bad_alloc&) { return reject(E_OUTOFMEMORY); }
        catch (...) { return reject(E_UNEXPECTED); }
    }
    HRESULT STDMETHODCALLTYPE Write(const void*, ULONG, ULONG* written) noexcept override {
        if (written) *written = 0;
        return STG_E_ACCESSDENIED;
    }
    HRESULT STDMETHODCALLTYPE Seek(LARGE_INTEGER offset, DWORD origin, ULARGE_INTEGER* position) noexcept override {
        if (position) position->QuadPart = 0;
        try {
            std::lock_guard<std::mutex> lock(cache().mutex);
            const auto active = state_->status(); if (FAILED(active)) return active;
            if (origin != STREAM_SEEK_SET && origin != STREAM_SEEK_CUR && origin != STREAM_SEEK_END) return STG_E_INVALIDFUNCTION;
            const auto base = origin == STREAM_SEEK_SET ? 0ULL : origin == STREAM_SEEK_CUR ? cursor_ : state_->snapshot.index.logicalLength;
            const auto maximum = static_cast<std::uint64_t>((std::numeric_limits<LONGLONG>::max)());
            std::uint64_t next = 0;
            if (offset.QuadPart < 0) {
                const auto magnitude = static_cast<std::uint64_t>(-(offset.QuadPart + 1)) + 1;
                if (magnitude > base) return STG_E_INVALIDFUNCTION;
                next = base - magnitude;
            } else {
                const auto forward = static_cast<std::uint64_t>(offset.QuadPart);
                if (forward > maximum - base) return STG_E_INVALIDFUNCTION;
                next = base + forward;
            }
            cursor_ = next; if (position) position->QuadPart = next; return S_OK;
        } catch (...) { return state_->fail(E_UNEXPECTED); }
    }
    HRESULT STDMETHODCALLTYPE SetSize(ULARGE_INTEGER) noexcept override { return STG_E_ACCESSDENIED; }
    HRESULT STDMETHODCALLTYPE CopyTo(IStream* destination, ULARGE_INTEGER requested, ULARGE_INTEGER* read, ULARGE_INTEGER* written) noexcept override {
        if (read) read->QuadPart = 0;
        if (written) written->QuadPart = 0;
        if (!destination || destination == this) return STG_E_INVALIDPOINTER;
        Microsoft::WRL::ComPtr<IStream> held(this), target(destination); // Real lifetime through target callbacks.
        try {
            CustodyBytes buffer;
            struct Wipe { CustodyBytes& bytes; ~Wipe() { if (!bytes.empty()) SecureZeroMemory(bytes.data(), bytes.size()); } } wipe{buffer};
            const auto active = state_->status(); if (FAILED(active)) return active;
            if (!requested.QuadPart) return S_OK;
            buffer.resize(static_cast<std::size_t>(std::min<std::uint64_t>(requested.QuadPart, ProtectedCustodyCodec::blockBytes)));
            std::uint64_t total = 0;
            while (total < requested.QuadPart) {
                ULONG got = 0, sent = 0;
                const auto count = static_cast<ULONG>(std::min<std::uint64_t>(buffer.size(), requested.QuadPart - total));
                const auto source = Read(buffer.data(), count, &got);
                if (FAILED(source)) return source;
                total += got; if (read) read->QuadPart = total;
                const auto ready = state_->status(); if (FAILED(ready)) return ready;
                if (got) {
                    const auto result = target->Write(buffer.data(), got, &sent); // No shared IO lock held here.
                    if (sent > got) return STG_E_WRITEFAULT;
                    if (written) written->QuadPart += sent;
                    if (FAILED(result)) return result;
                    const auto completed = state_->status(); if (FAILED(completed)) return completed;
                    if (sent != got) return STG_E_MEDIUMFULL;
                    if (result != S_OK) return result;
                }
                if (source == S_FALSE) return S_FALSE;
            }
            return S_OK;
        } catch (const std::bad_alloc&) { return state_->fail(E_OUTOFMEMORY); }
        catch (...) { return state_->fail(E_UNEXPECTED); }
    }
    HRESULT STDMETHODCALLTYPE Commit(DWORD flags) noexcept override {
        return flags == STGC_DEFAULT ? state_->status() : STG_E_INVALIDFLAG; // Read-only: no commit/ACK authority.
    }
    HRESULT STDMETHODCALLTYPE Revert() noexcept override { return STG_E_INVALIDFUNCTION; }
    HRESULT STDMETHODCALLTYPE LockRegion(ULARGE_INTEGER, ULARGE_INTEGER, DWORD) noexcept override { return STG_E_INVALIDFUNCTION; }
    HRESULT STDMETHODCALLTYPE UnlockRegion(ULARGE_INTEGER, ULARGE_INTEGER, DWORD) noexcept override { return STG_E_INVALIDFUNCTION; }
    HRESULT STDMETHODCALLTYPE Stat(STATSTG* output, DWORD flags) noexcept override {
        if (!output) return STG_E_INVALIDPOINTER;
        *output = {};
        if (flags != STATFLAG_DEFAULT && flags != STATFLAG_NONAME) return STG_E_INVALIDFLAG;
        const auto active = state_->status(); if (FAILED(active)) return active;
        // An unnamed logical stream: never disclose the private filesystem path.
        output->type = STGTY_STREAM; output->cbSize.QuadPart = state_->snapshot.index.logicalLength;
        output->grfMode = STGM_READ; return S_OK;
    }
    HRESULT STDMETHODCALLTYPE Clone(IStream** output) noexcept override {
        if (!output) return STG_E_INVALIDPOINTER;
        *output = nullptr;
        try {
            std::lock_guard<std::mutex> lock(cache().mutex);
            const auto active = state_->status(); if (FAILED(active)) return active;
            Pin pin; if (!pin) return STG_E_INSUFFICIENTMEMORY;
            *output = new Reader(std::move(pin), state_, cursor_); return S_OK;
        } catch (const std::bad_alloc&) { return STG_E_INSUFFICIENTMEMORY; }
        catch (...) { return state_->fail(E_UNEXPECTED); }
    }
private:
    std::atomic<ULONG> references_{1};
    Pin pin_;
    std::shared_ptr<ReaderState> state_;
    std::uint64_t cursor_ = 0;
};
} // namespace

CustodyFileResult<CustodyReader> openProtectedCustodyReader(const std::filesystem::path& root,
    std::string_view package, const CustodyContext& context, std::shared_ptr<const std::atomic<bool>> cancelled) try {
    if (!cancelled) return {std::nullopt, CustodyFileError::invalidInput, 0};
    if (cancelled->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    Pin pin; if (!pin) return {std::nullopt, CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA};
    // First-use cache allocation belongs to this exception boundary, never
    // ReaderState's noexcept destructor after a successful open.
    (void)cache();
    auto files = ProtectedCustodyFiles::open(root, package, context, CustodyFileAccess::readExisting);
    if (!files.ok()) return {std::nullopt, files.error, files.nativeError};
    if (cancelled->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    auto snapshot = (*files.value)->readValidatedSnapshot();
    if (!snapshot.ok()) return {std::nullopt, snapshot.error, snapshot.nativeError};
    if (cancelled->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    CustodyReader result;
    result.state = snapshot.value->state; result.recoveryError = snapshot.value->recoveryError; result.nativeError = snapshot.value->nativeError;
    auto state = std::allocate_shared<ReaderState>(CustodyAllocator<ReaderState>{}, context,
        std::move(*snapshot.value), std::move(*files.value), std::move(cancelled));
    result.stream.Attach(new Reader(std::move(pin), std::move(state)));
    return {std::move(result), CustodyFileError::none, 0};
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }

} // namespace graf::windows
#endif
