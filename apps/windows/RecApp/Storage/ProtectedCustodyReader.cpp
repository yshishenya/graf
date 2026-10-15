#include "ProtectedCustodyReader.h"
#ifdef _WIN32
#include "ProtectedPackedCustodyTree.h"
#include "ProtectedCustodyMetadata.h"
#include "ProtectedCustodyWriter.h"
#include "Sha256.h"
#include <algorithm>
#include <cstring>
#include <limits>
#include <mutex>
#include <system_error>
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
HRESULT readError(CustodyFileError error, std::uint32_t native) noexcept {
    if (error == CustodyFileError::allocationFailed) return E_OUTOFMEMORY;
    return native ? HRESULT_FROM_WIN32(native) : STG_E_READFAULT;
}
struct PackageReadLease {
    std::shared_ptr<ProtectedCustodyRecordingPackage> recording; // Borrowed members close before this parent.
    std::shared_ptr<const ProtectedCustodyPackagePair> pair; // Members close BEFORE parent lease.
    std::array<const CustodyPackageReference*, 5> identities{}; // Borrowed only from held pair.
    std::array<std::unique_ptr<ProtectedCustodyFiles>, 5> files;
    std::array<ProtectedCustodyFiles*, 5> borrowedFiles{}; // Private; recording/files retain actual owners.
    std::array<std::array<CustodyIndex, 2>, 5> indices;
    std::array<std::shared_ptr<ProtectedPackedCustodyOwner>, 5> owners;
    std::array<std::shared_ptr<const ProtectedPackedCustodyTree>, 10> proofs;
    std::atomic<HRESULT> failure{S_OK};
};
struct ReaderState {
    std::shared_ptr<PackageReadLease> package;
    CustodyContext context;
    CustodySnapshot snapshot;
    std::unique_ptr<ProtectedCustodyFiles> files;
    std::shared_ptr<const ProtectedPackedCustodyTree> packed;
    std::shared_ptr<const std::atomic<bool>> cancellation;
    // Separate value allocation: observing drain must not retain native state.
    std::shared_ptr<std::atomic<unsigned>> readerInstances =
        std::allocate_shared<std::atomic<unsigned>>(CustodyAllocator<std::atomic<unsigned>>{}, 0U);
    std::atomic<HRESULT> failure{S_OK};
    ReaderState(const CustodyContext& contextValue, CustodySnapshot&& snapshotValue,
        std::unique_ptr<ProtectedCustodyFiles>&& filesValue, std::shared_ptr<const std::atomic<bool>> cancelled)
        : context(contextValue), snapshot(std::move(snapshotValue)), files(std::move(filesValue)), cancellation(std::move(cancelled)) {}
    ReaderState(std::shared_ptr<const ProtectedPackedCustodyTree> proof, std::shared_ptr<const std::atomic<bool>> cancelled)
        : packed(std::move(proof)), cancellation(std::move(cancelled)) {}
    std::uint64_t length() const noexcept { return packed ? packed->logicalBytes() : snapshot.index.logicalLength; }
    ProtectedCustodyFiles* flatFiles() const noexcept {
        return package ? package->borrowedFiles[static_cast<unsigned>(context.role)-1] : files.get();
    }
    ~ReaderState() {
        auto& shared = cache(); std::lock_guard<std::mutex> lock(shared.mutex);
        if (shared.owner == this) shared.clear(); // Cannot reuse this address with old plaintext.
    }
    HRESULT fail(HRESULT hr) noexcept {
        if (package) {
            HRESULT first = S_OK; package->failure.compare_exchange_strong(first, hr);
            hr = package->failure.load();
        }
        HRESULT expected = S_OK; failure.compare_exchange_strong(expected, hr);
        return failure.load();
    }
    HRESULT observedStatus() noexcept {
        if (package && FAILED(package->failure.load())) return fail(package->failure.load());
        if (cancellation->load()) return fail(HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED));
        return failure.load();
    }
    HRESULT status() noexcept {
        const auto observed = observedStatus(); if (FAILED(observed)) return observed;
        try {
            if (packed) {
                const auto checked = packed->checkRead();
                if (!checked.ok()) return fail(readError(checked.error, checked.nativeError));
            }
        } catch (const std::bad_alloc&) { return fail(E_OUTOFMEMORY); }
        catch (...) { return fail(E_UNEXPECTED); }
        return failure.load();
    }
};
static_assert(sizeof(ReaderState) <= 4096);
class Reader final : public IStream {
public:
    static void* operator new(std::size_t) { return CustodyAllocator<Reader>{}.allocate(1); }
    static void operator delete(void* memory) noexcept { CustodyAllocator<Reader>{}.deallocate(static_cast<Reader*>(memory), 1); }
    Reader(Pin&& pin, std::shared_ptr<ReaderState> state, std::uint64_t cursor = 0)
        : pin_(std::move(pin)), state_(std::move(state)), cursor_(cursor) {
        state_->readerInstances->fetch_add(1, std::memory_order_relaxed);
    }
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid, void** output) noexcept override {
        if (!output) return E_POINTER;
        *output = nullptr;
        if (iid != __uuidof(IUnknown) && iid != __uuidof(ISequentialStream) && iid != __uuidof(IStream)) return E_NOINTERFACE;
        *output = static_cast<IStream*>(this); AddRef(); return S_OK;
    }
    ULONG STDMETHODCALLTYPE AddRef() noexcept override { return ++references_; }
    ULONG STDMETHODCALLTYPE Release() noexcept override {
        const auto remaining = --references_;
        if (!remaining) {
            auto instances = state_->readerInstances;
            delete this; // Native state, pin and charged Reader memory leave before the signal.
            instances->fetch_sub(1, std::memory_order_release);
        }
        return remaining;
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
            const auto initial = state_->status(); if (FAILED(initial)) return initial;
            const auto length = state_->length();
            const auto count = static_cast<ULONG>(std::min<std::uint64_t>(requested, cursor_ < length ? length - cursor_ : 0));
            while (copied < count) {
                const auto active = state_->status(); if (FAILED(active)) return reject(active);
                const auto at = cursor_ + copied;
                const auto block = at / ProtectedCustodyCodec::blockBytes;
                const auto within = static_cast<std::size_t>(at % ProtectedCustodyCodec::blockBytes);
                const auto payload = static_cast<std::uint32_t>(std::min<std::uint64_t>(ProtectedCustodyCodec::blockBytes,
                    length - block * ProtectedCustodyCodec::blockBytes));
                const auto chunk = static_cast<ULONG>(std::min<std::size_t>(count - copied, payload - within));
                auto* destination = static_cast<std::uint8_t*>(output) + copied;
                if (!state_->packed && state_->snapshot.index.entries[static_cast<std::size_t>(block)].flags == 1)
                    std::memset(destination, 0, chunk); // Authenticated explicit v1 ZERO only.
                else {
                    if (shared.owner != state_.get() || shared.position != block) {
                        shared.clear();
                        if (state_->packed) {
                            auto plain = state_->packed->readBlock(block);
                            if (!plain.ok()) return reject(readError(plain.error, plain.nativeError));
                            shared.bytes = std::move(plain.value->bytes);
                        } else {
                            const auto& entry = state_->snapshot.index.entries[static_cast<std::size_t>(block)];
                            auto cipher = state_->flatFiles()->readBlock(block, entry.version, payload, entry.envelopeBytes);
                            if (!cipher.ok()) return reject(readError(cipher.error, cipher.nativeError));
                            auto plain = ProtectedCustodyCodec::openBlock(state_->context, block, entry.version, payload, *cipher.value);
                            if (!plain.ok()) return reject(plain.error == CustodyCodecError::allocationFailed ? E_OUTOFMEMORY : STG_E_READFAULT);
                            shared.bytes = std::move(*plain.value);
                        }
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
            const auto base = origin == STREAM_SEEK_SET ? 0ULL : origin == STREAM_SEEK_CUR ? cursor_ : state_->length();
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
        output->type = STGTY_STREAM; output->cbSize.QuadPart = state_->length();
        output->grfMode = STGM_READ; return S_OK;
    }
    HRESULT STDMETHODCALLTYPE Clone(IStream** output) noexcept override {
        if (!output) return STG_E_INVALIDPOINTER;
        *output = nullptr;
        try {
            std::lock_guard<std::mutex> lock(cache().mutex);
            const auto observed = state_->observedStatus(); if (FAILED(observed)) return observed;
            Pin pin; if (!pin) return STG_E_INSUFFICIENTMEMORY;
            // Reserve the clone before native validation: a refused allocation
            // is admission failure, not a fault in the existing reader's storage.
            Microsoft::WRL::ComPtr<IStream> clone;
            clone.Attach(new Reader(std::move(pin), state_, cursor_));
            const auto active = state_->status(); if (FAILED(active)) return active;
            *output = clone.Detach(); return S_OK;
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

struct ProtectedCustodyWriteStream::State {
    CustodyPin pin;
    std::mutex mutex;
    ProtectedCustodyWriter* writer = nullptr; // Borrowed from worker wrapper; cleared under mutex before worker release.
    std::shared_ptr<const std::atomic<bool>> cancellation;
    std::uint64_t cursor = 0;
    std::atomic<HRESULT> failure{S_OK};
    bool closed = false;
    explicit State(std::shared_ptr<const std::atomic<bool>> cancelled) : cancellation(std::move(cancelled)) {}
    HRESULT fail(HRESULT hr, CustodyFileError error = CustodyFileError::invalidInput, std::uint32_t native = 0) noexcept {
        HRESULT expected = S_OK;
        if (failure.compare_exchange_strong(expected, hr)) {
            if (writer) writer->failStream(error, native); // RAM-only sticky revocation; no IO/destructor flush.
        }
        return failure.load();
    }
    HRESULT reject(CustodyFileError error, std::uint32_t native, HRESULT fallback = STG_E_WRITEFAULT) noexcept {
        const auto hr = error == CustodyFileError::allocationFailed ? E_OUTOFMEMORY
            : native ? HRESULT_FROM_WIN32(native) : fallback;
        return fail(hr, error, native);
    }
    HRESULT status() {
        if (closed || !writer) return STG_E_REVERTED;
        if (FAILED(failure.load())) return failure.load();
        const auto ready = writer->streamReady();
        if (!ready.ok()) return reject(ready.error, ready.nativeError); // Existing shared-owner fault precedes cancellation/input.
        return cancellation->load() ? reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED) : S_OK;
    }
    template<class Operation> HRESULT invoke(Operation&& operation) noexcept {
        try {
            std::lock_guard<std::mutex> lock(mutex);
            try {
                const auto ready = status();
                return FAILED(ready) ? ready : operation();
            } catch (const std::bad_alloc&) { return fail(E_OUTOFMEMORY, CustodyFileError::allocationFailed); }
            catch (...) { return fail(E_UNEXPECTED, CustodyFileError::ioFailed); }
        } catch (...) {
            HRESULT expected = S_OK; failure.compare_exchange_strong(expected, E_UNEXPECTED);
            return failure.load(); // Lock failure cannot touch mutable Writer; worker close revokes it under the fence.
        }
    }
};

class ProtectedCustodyWriteStream::Stream final : public IStream {
public:
    static void* operator new(std::size_t) { return CustodyAllocator<Stream>{}.allocate(1); }
    static void operator delete(void* memory) noexcept { CustodyAllocator<Stream>{}.deallocate(static_cast<Stream*>(memory), 1); }
    explicit Stream(std::shared_ptr<State> state) : state_(std::move(state)) {}
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
        ULONG copied = 0;
        const auto hr = state_->invoke([&] {
            if (!output) return state_->fail(STG_E_INVALIDPOINTER);
            auto result = state_->writer->readAtImpl(state_->cursor, output, requested);
            if (!result.ok()) return state_->reject(result.error, result.nativeError, STG_E_READFAULT);
            if (*result.value > requested) return state_->fail(STG_E_READFAULT, CustodyFileError::invalidContent);
            copied = static_cast<ULONG>(*result.value);
            const auto completed = state_->status();
            if (FAILED(completed)) return completed;
            state_->cursor += *result.value;
            if (got) *got = static_cast<ULONG>(*result.value);
            return *result.value == requested ? S_OK : S_FALSE;
        });
        if (FAILED(hr) && copied) SecureZeroMemory(output, copied);
        return hr;
    }
    HRESULT STDMETHODCALLTYPE Write(const void* input, ULONG requested, ULONG* written) noexcept override {
        if (written) *written = 0;
        return state_->invoke([&] {
            if (!input) return state_->fail(STG_E_INVALIDPOINTER); // COM requires a pointer even for zero bytes.
            const auto limit = state_->writer->logicalLimit();
            if (state_->cursor > limit || requested > limit-state_->cursor) return state_->fail(STG_E_MEDIUMFULL);
            ULONG accepted = 0;
            while (accepted < requested) {
                const auto ready = state_->status(); if (FAILED(ready)) return ready;
                const auto chunk = static_cast<ULONG>(std::min<std::uint64_t>(requested-accepted,
                    ProtectedCustodyCodec::blockBytes-state_->cursor%ProtectedCustodyCodec::blockBytes));
                const auto result = state_->writer->writeAtImpl(state_->cursor, static_cast<const std::uint8_t*>(input)+accepted, chunk);
                if (!result.ok()) return state_->reject(result.error, result.nativeError);
                if (*result.value != chunk) return state_->fail(STG_E_WRITEFAULT, CustodyFileError::invalidContent);
                state_->cursor += chunk; accepted += chunk;
                if (written) *written = accepted;
                // On failure, only completed chunks advance/are acknowledged. A failed
                // chunk may have physical artifacts: sticky failure forbids retry/normal use.
            }
            return state_->status();
        });
    }
    HRESULT STDMETHODCALLTYPE Seek(LARGE_INTEGER offset, DWORD origin, ULARGE_INTEGER* position) noexcept override {
        if (position) position->QuadPart = 0;
        return state_->invoke([&] {
            if (origin != STREAM_SEEK_SET && origin != STREAM_SEEK_CUR && origin != STREAM_SEEK_END)
                return state_->fail(STG_E_INVALIDFUNCTION);
            const auto limit = state_->writer->logicalLimit();
            const auto base = origin == STREAM_SEEK_SET ? 0ULL : origin == STREAM_SEEK_CUR ? state_->cursor : state_->writer->sizeImpl();
            std::uint64_t next = 0;
            if (origin != STREAM_SEEK_SET && offset.QuadPart < 0) {
                const auto magnitude = static_cast<std::uint64_t>(-(offset.QuadPart+1))+1;
                if (magnitude > base) return state_->fail(STG_E_INVALIDFUNCTION);
                next = base-magnitude;
            } else {
                const auto forward = static_cast<std::uint64_t>(offset.QuadPart); // SET has unsigned COM semantics.
                if (base > limit || forward > limit-base) return state_->fail(STG_E_INVALIDFUNCTION);
                next = base+forward;
            }
            state_->cursor = next; if (position) position->QuadPart = next;
            return S_OK;
        });
    }
    HRESULT STDMETHODCALLTYPE SetSize(ULARGE_INTEGER length) noexcept override {
        return state_->invoke([&] {
            if (length.QuadPart > state_->writer->logicalLimit()) return state_->fail(STG_E_MEDIUMFULL);
            const auto resized = state_->writer->setSizeImpl(length.QuadPart);
            return resized.ok() ? state_->status() : state_->reject(resized.error, resized.nativeError);
        });
    }
    HRESULT STDMETHODCALLTYPE Commit(DWORD flags) noexcept override {
        return state_->invoke([&] {
            if (flags != STGC_DEFAULT) return state_->fail(STG_E_INVALIDFLAG);
            const auto committed = state_->writer->checkpointImpl();
            if (committed.state != CustodyCommitState::committed || committed.error != CustodyFileError::none)
                return state_->reject(committed.error == CustodyFileError::none ? CustodyFileError::writerFailed : committed.error, committed.nativeError);
            return state_->status(); // This byte checkpoint is NOT a sealed package/queue ACK.
        });
    }
    HRESULT STDMETHODCALLTYPE Stat(STATSTG* output, DWORD flags) noexcept override {
        if (output) *output = {};
        return state_->invoke([&] {
            if (!output) return state_->fail(STG_E_INVALIDPOINTER);
            if (flags != STATFLAG_DEFAULT && flags != STATFLAG_NONAME) return state_->fail(STG_E_INVALIDFLAG);
            output->type = STGTY_STREAM; output->cbSize.QuadPart = state_->writer->sizeImpl();
            output->grfMode = STGM_READWRITE; return S_OK; // Unnamed: never expose a private filesystem path.
        });
    }
    HRESULT STDMETHODCALLTYPE Clone(IStream** output) noexcept override {
        if (output) *output = nullptr;
        return state_->invoke([&] { return output ? STG_E_INVALIDFUNCTION : STG_E_INVALIDPOINTER; });
    }
    HRESULT STDMETHODCALLTYPE CopyTo(IStream*, ULARGE_INTEGER, ULARGE_INTEGER* read, ULARGE_INTEGER* written) noexcept override {
        if (read) read->QuadPart = 0;
        if (written) written->QuadPart = 0;
        return state_->invoke([] { return STG_E_INVALIDFUNCTION; }); // No second writer/cursor or callback under this mutex.
    }
    HRESULT STDMETHODCALLTYPE Revert() noexcept override { return state_->invoke([] { return STG_E_INVALIDFUNCTION; }); }
    HRESULT STDMETHODCALLTYPE LockRegion(ULARGE_INTEGER, ULARGE_INTEGER, DWORD) noexcept override {
        return state_->invoke([] { return STG_E_INVALIDFUNCTION; });
    }
    HRESULT STDMETHODCALLTYPE UnlockRegion(ULARGE_INTEGER, ULARGE_INTEGER, DWORD) noexcept override {
        return state_->invoke([] { return STG_E_INVALIDFUNCTION; });
    }
private:
    std::atomic<ULONG> references_{1};
    std::shared_ptr<State> state_; // No owning native reference, even after the worker wrapper is gone.
};

ProtectedCustodyWriteStream::ProtectedCustodyWriteStream(std::shared_ptr<ProtectedCustodyWriter> writer,
    std::shared_ptr<State> state) : writer_(std::move(writer)), state_(std::move(state)) {}
ProtectedCustodyWriteStream::~ProtectedCustodyWriteStream() { (void)close(); }
HRESULT ProtectedCustodyWriteStream::observedFailure() const noexcept { return state_->failure.load(); }
HRESULT ProtectedCustodyWriteStream::close() noexcept {
    // Like the retained Reader's destructor, a broken mutex terminates rather
    // than returning an unproven fence and leaving COM with a dangling native pointer.
    std::lock_guard<std::mutex> lock(state_->mutex);
    state_->closed = true;
    if (state_->writer) {
        if (FAILED(state_->failure.load())) state_->writer->failStream(CustodyFileError::writerFailed, 0);
        state_->writer->detachStream(); state_->writer = nullptr;
    }
    return state_->failure.load();
}
CustodyFileResult<std::shared_ptr<ProtectedCustodyWriteStream>> ProtectedCustodyWriteStream::open(
    std::shared_ptr<ProtectedCustodyWriter> writer, std::shared_ptr<const std::atomic<bool>> cancellation) try {
    if (!writer || !cancellation) return {std::nullopt, CustodyFileError::invalidInput, 0};
    if (cancellation->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    static_assert(sizeof(State) <= 4096);
    auto state = std::allocate_shared<State>(CustodyAllocator<State>{}, std::move(cancellation));
    if (!state->pin) return {std::nullopt, CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA};
    auto adapter = std::shared_ptr<ProtectedCustodyWriteStream>(new ProtectedCustodyWriteStream(writer, state),
        std::default_delete<ProtectedCustodyWriteStream>{}, CustodyAllocator<ProtectedCustodyWriteStream>{});
    adapter->stream_.Attach(new Stream(state));
    const auto attached = writer->attachStream(); // Last, after all charged allocations; no failed-open revocation.
    if (!attached.ok()) return {std::nullopt, attached.error, attached.nativeError};
    state->writer = writer.get();
    return {std::move(adapter), CustodyFileError::none, 0};
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }
  catch (const std::system_error& error) { return {std::nullopt, CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())}; }

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
    result.readerInstances = state->readerInstances;
    result.stream.Attach(new Reader(std::move(pin), std::move(state)));
    return {std::move(result), CustodyFileError::none, 0};
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }

CustodyFileResult<CustodyReader> openProtectedCustodyReader(std::shared_ptr<const ProtectedPackedCustodyTree> proof,
    std::shared_ptr<const std::atomic<bool>> cancelled) try {
    if (!proof || !cancelled) return {std::nullopt, CustodyFileError::invalidInput, 0};
    if (cancelled->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    Pin pin; if (!pin) return {std::nullopt, CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA};
    (void)cache();
    auto state = std::allocate_shared<ReaderState>(CustodyAllocator<ReaderState>{}, proof, cancelled);
    CustodyReader result;
    result.readerInstances = state->readerInstances;
    result.stream.Attach(new Reader(std::move(pin), std::move(state)));
    const auto checked = proof->checkRead();
    if (!checked.ok()) return {std::nullopt, checked.error, checked.nativeError};
    if (cancelled->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    result.state = CustodySnapshotState::verified;
    return {std::move(result), CustodyFileError::none, 0};
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }

CustodyFileResult<CustodyReader> openProtectedCustodyReader(const std::filesystem::path& root,
    std::shared_ptr<const ProtectedCustodyPackagePair> pair, std::uint32_t slot, std::size_t refIndex,
    std::shared_ptr<const std::atomic<bool>> cancelled) try {
    if (!pair || !cancelled || slot > 1 || refIndex >= pair->slots()[slot].refCount)
        return {std::nullopt, CustodyFileError::invalidInput, 0};
    const auto& ref = pair->slots()[slot].refs[refIndex];
    if (!ref.sealed || !ref.generation || !ref.length || !ref.sha256)
        return {std::nullopt, CustodyFileError::invalidInput, 0};
    auto batch = openProtectedCustodyReaders(root, std::move(pair), std::move(cancelled));
    if (!batch.ok()) return {std::nullopt, batch.error, batch.nativeError};
    return {std::move((*batch.value)[slot][refIndex]), CustodyFileError::none, 0};
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }

namespace {
template<class LoadFlat, class LoadPacked>
CustodyFileResult<CustodyPackageReaders> readPackageGroup(
    std::shared_ptr<PackageReadLease> group,
    std::shared_ptr<const std::atomic<bool>> cancelled, LoadFlat loadFlat, LoadPacked loadPacked) try {
    if (!group->pair || !cancelled) return {std::nullopt, CustodyFileError::invalidInput, 0};
    if (cancelled->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    (void)cache();
    // Preflight ALL edges before member IO, including the nonselected slot.
    for (const auto& value : group->pair->slots()) {
        if (value.refCount > 5) return {std::nullopt, CustodyFileError::invalidInput, 0};
        for (std::size_t i = 0; i < value.refCount; ++i) {
            const auto& ref = value.refs[i];
            const auto role = static_cast<unsigned>(ref.role);
            if (role < 1 || role > 5 || (ref.sealed ? !ref.generation || !ref.length || !ref.sha256
                : ref.generation || ref.length || ref.sha256))
                return {std::nullopt, CustodyFileError::invalidInput, 0};
            const auto previous = group->identities[role-1];
            if (previous && (previous->objectId != ref.objectId || previous->packed != ref.packed || previous->containerId != ref.containerId))
                return {std::nullopt, CustodyFileError::identityMismatch, 0};
            for (const auto identity : group->identities)
                if (identity && identity->role != ref.role && identity->objectId == ref.objectId)
                    return {std::nullopt, CustodyFileError::identityMismatch, 0};
            group->identities[role-1] = &ref;
        }
    }
    CustodyPackageReaders result;
    const auto first = group->pair->selectedSlot();
    for (const auto slot : {first, 1U-first}) for (std::size_t i = 0; i < group->pair->slots()[slot].refCount; ++i) {
        if (cancelled->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
        Pin pin; if (!pin) return {std::nullopt, CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA};
        const auto& value = group->pair->slots()[slot];
        const auto& ref = value.refs[i];
        const auto role = static_cast<unsigned>(ref.role)-1;
        const CustodyContext context{value.context.storeId, ref.objectId, ref.role};
        const std::string_view directory(value.directory.data(),
            static_cast<std::size_t>(std::find(value.directory.begin(), value.directory.end(), '\0')-value.directory.begin()));
        std::shared_ptr<ReaderState> state;
        if (ref.packed) {
            if (!ref.containerId || (ref.sealed && (!ref.committedExtent || !ref.rootRef)))
                return {std::nullopt, CustodyFileError::invalidInput, 0};
            const PackedCustodyContext packedContext{context, *ref.containerId};
            if (!group->owners[role]) {
                if (group->recording) return {std::nullopt, CustodyFileError::identityMismatch, 0};
                auto owner = loadPacked(directory, packedContext);
                if (!owner.ok()) return {std::nullopt, owner.error, owner.nativeError};
                group->owners[role] = std::move(*owner.value);
            }
            CustodyFileResult<std::shared_ptr<const ProtectedPackedCustodyTree>> proof;
            if (ref.sealed) {
                using Format = ProtectedPackedCustodyFormat;
                const auto decoded = Format::decodeReference(ref.rootRef->data(), ref.rootRef->size(),
                    {*ref.length ? PackedRecordKind::nodeL2 : PackedRecordKind::empty, 0,
                        *ref.generation, *ref.committedExtent, *ref.committedExtent});
                if (!decoded) return {std::nullopt, CustodyFileError::invalidContent, 0};
                const PackedRootDescriptor stamp{*ref.generation, *ref.length, *ref.committedExtent,
                    static_cast<std::uint32_t>((*ref.length+Format::blockBytes-1)/Format::blockBytes), *decoded};
                proof = ProtectedPackedCustodyTree::verifyRetained(group->owners[role], packedContext, stamp);
            } else proof = ProtectedPackedCustodyTree::verify(group->owners[role]);
            if (!proof.ok()) return {std::nullopt, proof.error, proof.nativeError};
            group->proofs[slot*5+i] = std::move(*proof.value);
            state = std::allocate_shared<ReaderState>(CustodyAllocator<ReaderState>{}, group->proofs[slot*5+i], cancelled);
        } else {
            CustodyNativeJob job; // Packed proofs and later stream hashes admit their own IO.
            if (!job) return {std::nullopt, CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA};
            if (!group->indices[role][0].generation) {
                const auto loaded = loadFlat(role, context, directory);
                if (!loaded.ok()) return {std::nullopt, loaded.error, loaded.nativeError};
            }
            const auto& indices = group->indices[role];
            const CustodyIndex* index = &indices[indices[1].generation > indices[0].generation ? 1 : 0];
            if (ref.sealed) {
                index = nullptr;
                for (const auto& candidate : indices) if (candidate.generation == *ref.generation) { index = &candidate; break; }
                if (!index) return {std::nullopt, CustodyFileError::recoveryRequired, 0};
                if (index->logicalLength != *ref.length)
                    return {std::nullopt, CustodyFileError::invalidContent, 0};
            }
            state = std::allocate_shared<ReaderState>(CustodyAllocator<ReaderState>{}, context,
                CustodySnapshot{*index, CustodySnapshotState::verified, CustodyFileError::none, 0}, nullptr, cancelled);
        }
        if (cancelled->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
        state->package = group;
        auto& reader = result[slot][i];
        reader.state = CustodySnapshotState::verified;
        reader.readerInstances = state->readerInstances;
        reader.stream.Attach(new Reader(std::move(pin), std::move(state)));
        if (ref.sealed) {
            const auto hash = sha256ProtectedStream(reader.stream.Get(), *ref.length, cancelled);
            if (!hash.ok()) return {std::nullopt, hash.error, hash.nativeError};
            if (*hash.value != *ref.sha256) return {std::nullopt, CustodyFileError::invalidContent, 0};
        }
        LARGE_INTEGER zero{}; ULARGE_INTEGER position{};
        const auto rewind = reader.stream->Seek(zero, STREAM_SEEK_SET, &position);
        if (FAILED(rewind)) return {std::nullopt, CustodyFileError::ioFailed, static_cast<std::uint32_t>(rewind)};
        if (rewind != S_OK || position.QuadPart) return {std::nullopt, CustodyFileError::invalidContent, 0};
        if (cancelled->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    }
    if (cancelled->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    if (FAILED(group->failure.load())) return {std::nullopt, CustodyFileError::ioFailed, static_cast<std::uint32_t>(group->failure.load())};
    return {std::move(result), CustodyFileError::none, 0};
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }
} // namespace

CustodyFileResult<CustodyPackageReaders> openProtectedCustodyReaders(const std::filesystem::path& root,
    std::shared_ptr<const ProtectedCustodyPackagePair> pair,
    std::shared_ptr<const std::atomic<bool>> cancelled) try {
    if (!pair || !cancelled) return {std::nullopt, CustodyFileError::invalidInput, 0};
    if (pair->retainedLease_ && (pair->origin_ != ProtectedCustodyPackagePair::LeaseOrigin::isolatedReadOnly ||
        pair->cancellation_.get() != cancelled.get() || pair->retainedLease_->trustedRoot() != root))
        return {std::nullopt, CustodyFileError::identityMismatch, 0};
    auto group = std::allocate_shared<PackageReadLease>(CustodyAllocator<PackageReadLease>{});
    group->pair = std::move(pair);
    const auto openFiles = [&](const CustodyContext& context, std::string_view directory) {
        return group->pair->retainedLease_
            ? ProtectedCustodyFiles::openPackageMember(group->pair->retainedLease_, context, cancelled)
            : ProtectedCustodyFiles::open(root, directory, context, CustodyFileAccess::writeExisting);
    };
    return readPackageGroup(group, cancelled,
        [&](unsigned role, const CustodyContext& context, std::string_view directory) -> CustodyFileResult<bool> {
            auto files = openFiles(context, directory);
            if (!files.ok()) return {std::nullopt, files.error, files.nativeError};
            CustodyIndex peer; std::uint32_t selected = 0;
            auto snapshot = (*files.value)->readValidatedSnapshotImpl(&peer, &selected);
            if (!snapshot.ok()) return {std::nullopt, snapshot.error, snapshot.nativeError};
            if (snapshot.value->state != CustodySnapshotState::verified)
                return {std::nullopt, snapshot.value->recoveryError, snapshot.value->nativeError};
            if (!peer.generation) return {std::nullopt, CustodyFileError::recoveryRequired, 0};
            group->indices[role][selected] = std::move(snapshot.value->index);
            group->indices[role][1-selected] = std::move(peer);
            (*files.value)->blockWrites();
            group->borrowedFiles[role] = files.value->get();
            group->files[role] = std::move(*files.value);
            return {true, CustodyFileError::none, 0};
        },
        [&](std::string_view directory, const PackedCustodyContext& context) {
            if (!group->pair->retainedLease_)
                return ProtectedPackedCustodyOwner::open(root, directory, context, CustodyFileAccess::readExisting);
            CustodyFileResult<std::unique_ptr<ProtectedCustodyFiles>> files;
            {
                CustodyNativeJob job;
                if (!job) return CustodyFileResult<std::shared_ptr<ProtectedPackedCustodyOwner>>{
                    std::nullopt, CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA};
                files = openFiles(context.object, directory);
            } // Physical packed-open admits its own job; do not nest admissions.
            if (!files.ok()) return CustodyFileResult<std::shared_ptr<ProtectedPackedCustodyOwner>>{
                std::nullopt, files.error, files.nativeError};
            return ProtectedPackedCustodyOwner::openImpl(root, directory, context,
                CustodyFileAccess::readExisting, &*files.value);
        });
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }

CustodyFileResult<CustodyPackageReaders> openProtectedCustodyReaders(
    std::shared_ptr<ProtectedCustodyRecordingPackage> package,
    std::shared_ptr<const ProtectedCustodyPackagePair> pair,
    std::shared_ptr<const std::atomic<bool>> cancelled) try {
    if (!package || !pair || !cancelled || package->failed_ ||
        pair->retainedLease_.get() != package->state_.get() || package->cancellation_->load() ||
        pair->current().context.storeId != package->context_.storeId ||
        pair->current().context.objectId != package->context_.objectId ||
        pair->current().context.role != package->context_.role || pair->current().generation != package->current_.generation)
        return {std::nullopt, CustodyFileError::identityMismatch, 0};
    for (const auto& value : pair->slots()) {
        const std::string_view directory(value.directory.data(),
            static_cast<std::size_t>(std::find(value.directory.begin(), value.directory.end(), '\0')-value.directory.begin()));
        if (value.refCount > 5 || directory != package->directory() ||
            value.context.storeId != package->context_.storeId || value.context.objectId != package->context_.objectId ||
            value.context.role != package->context_.role)
            return {std::nullopt, CustodyFileError::identityMismatch, 0};
        for (std::size_t i = 0; i < value.refCount; ++i) {
            const auto& ref = value.refs[i]; const auto role = static_cast<unsigned>(ref.role);
            if (role < 1 || role > 5 || ref.objectId != package->contexts_[role-1].objectId ||
                ref.packed != (role <= 3) || (ref.packed && (!ref.containerId || *ref.containerId != package->containers_[role-1])))
                return {std::nullopt, CustodyFileError::identityMismatch, 0};
        }
    }
    auto group = std::allocate_shared<PackageReadLease>(CustodyAllocator<PackageReadLease>{});
    group->recording = std::move(package); group->pair = std::move(pair);
    for (unsigned role = 0; role < 3; ++role) group->owners[role] = group->recording->packed_[role];
    for (unsigned role = 3; role < 5; ++role) group->borrowedFiles[role] = group->recording->roles_[role].get();
    return readPackageGroup(group, std::move(cancelled),
        [&](unsigned role, const CustodyContext&, std::string_view) -> CustodyFileResult<bool> {
            auto* files = group->borrowedFiles[role];
            if (!files) return {std::nullopt, CustodyFileError::identityMismatch, 0};
            CustodyIndex peer; std::uint32_t selected = 0;
            auto snapshot = files->readValidatedSnapshotImpl(&peer, &selected);
            if (!snapshot.ok()) return {std::nullopt, snapshot.error, snapshot.nativeError};
            if (snapshot.value->state != CustodySnapshotState::verified)
                return {std::nullopt, snapshot.value->recoveryError, snapshot.value->nativeError};
            if (!peer.generation) return {std::nullopt, CustodyFileError::recoveryRequired, 0};
            group->indices[role][selected] = std::move(snapshot.value->index);
            group->indices[role][1-selected] = std::move(peer);
            return {true, CustodyFileError::none, 0};
        },
        [](std::string_view, const PackedCustodyContext&) -> CustodyFileResult<std::shared_ptr<ProtectedPackedCustodyOwner>> {
            return {std::nullopt, CustodyFileError::identityMismatch, 0}; // Borrowed owners must already be held.
        });
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }

} // namespace graf::windows
#endif
