#include "../../RecApp/Storage/ProtectedCustodyWriter.h"
#include "../../RecApp/Storage/ProtectedCustodyReader.h"
#include "../../RecApp/Storage/ProtectedPackedCustodyTree.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cstdio>
#include <cstdlib>
#if defined(_MSC_VER) && defined(_DEBUG)
#include <crtdbg.h>
#endif
#ifdef _WIN32
#include <windows.h>
#include <sddl.h>
#include <mfapi.h>
#include <mfidl.h>
#include <wrl/implements.h>
#include <array>
#include <limits>
#include <thread>
#include <vector>

namespace {
enum class MfIoCut { none, cancellation, writeFailure };
struct MfIoGate {
    HANDLE entered = CreateEventW(nullptr, TRUE, FALSE, nullptr);
    HANDLE resume = CreateEventW(nullptr, TRUE, FALSE, nullptr);
    std::atomic<bool> seen{false};
    std::atomic<DWORD> thread{0};
    MfIoCut cut = MfIoCut::none;
    MfIoGate() { assert(entered && resume); }
    ~MfIoGate() { assert(CloseHandle(entered)); assert(CloseHandle(resume)); }
};
std::atomic<MfIoGate*> mfIoGate{nullptr};
BOOL WINAPI mfControlledWrite(HANDLE file, LPCVOID bytes, DWORD count, LPDWORD written, LPOVERLAPPED operation) {
    auto* gate = mfIoGate.load();
    if (gate && !gate->seen.exchange(true)) {
        gate->thread.store(GetCurrentThreadId());
        assert(SetEvent(gate->entered));
        assert(WaitForSingleObject(gate->resume, 30'000) == WAIT_OBJECT_0);
        if (gate->cut == MfIoCut::writeFailure) {
            if (written) *written = 0;
            SetLastError(ERROR_WRITE_FAULT);
            return FALSE;
        }
    }
    return WriteFile(file, bytes, count, written, operation);
}
}
// Same executable-local native wrapper pattern as the existing file fault
// tests. Only this target replaces its usual Files object; production is intact.
#define WriteFile mfControlledWrite
#include "../../RecApp/Storage/ProtectedCustodyFiles.cpp"
#undef WriteFile

using namespace graf::windows;
namespace {
// Generated low-level media fixture only: it grants no package/account authority.
struct Fixture {
    std::filesystem::path root;
    PSECURITY_DESCRIPTOR descriptor = nullptr;
    PackedCustodyContext context{{{}, {}, CustodyRole::playback}, {}};
    Fixture() {
        HANDLE token = nullptr;
        assert(OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token));
        DWORD count = 0;
        assert(!GetTokenInformation(token, TokenUser, nullptr, 0, &count));
        assert(GetLastError() == ERROR_INSUFFICIENT_BUFFER);
        std::vector<std::uint8_t> bytes(count);
        assert(GetTokenInformation(token, TokenUser, bytes.data(), count, &count));
        assert(CloseHandle(token));
        LPWSTR sid = nullptr;
        assert(ConvertSidToStringSidW(reinterpret_cast<TOKEN_USER*>(bytes.data())->User.Sid, &sid));
        const auto sddl = std::wstring(L"D:P(A;OICI;FA;;;") + sid + L")";
        LocalFree(sid);
        assert(ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl.c_str(), SDDL_REVISION_1, &descriptor, nullptr));
        SECURITY_ATTRIBUTES security{sizeof(SECURITY_ATTRIBUTES), descriptor, FALSE};
        wchar_t temporary[MAX_PATH]{}, actual[MAX_PATH]{}, text[40]{};
        assert(GetTempPathW(MAX_PATH, temporary));
        assert(GetLongPathNameW(temporary, actual, MAX_PATH));
        GUID id{};
        assert(CoCreateGuid(&id) == S_OK && StringFromGUID2(id, text, 40));
        root = std::filesystem::path(actual) / (std::wstring(L"graf-write-stream-") + text);
        assert(CreateDirectoryW(root.c_str(), &security));
        assert(CreateDirectoryW((root / L".custody-v1").c_str(), &security));
        assert(CreateDirectoryW((root / L"package-a").c_str(), &security));
        context.object.storeId.fill(0x41);
        context.object.objectId.fill(0x52);
        context.containerId.fill(0x63);
        HANDLE file = CreateFileW((root / L".custody-v1" / L"store.id").c_str(), GENERIC_WRITE,
            0, &security, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr);
        assert(file != INVALID_HANDLE_VALUE);
        DWORD written = 0;
        assert(WriteFile(file, context.object.storeId.data(), 16, &written, nullptr) && written == 16);
        assert(FlushFileBuffers(file) && CloseHandle(file));
    }
    ~Fixture() {
        std::error_code error;
        std::filesystem::remove_all(root, error); // This exact generated private root only.
        assert(!error);
        LocalFree(descriptor);
    }
    auto writer(const std::shared_ptr<const std::atomic<bool>>& cancelled) const {
        auto owner = ProtectedPackedCustodyOwner::open(root, "package-a", context, CustodyFileAccess::createNew);
        assert(owner.ok());
        auto tree = ProtectedPackedCustodyTree::verify(*owner.value); assert(tree.ok());
        auto opened = ProtectedCustodyWriter::open(*tree.value, cancelled); assert(opened.ok());
        return std::shared_ptr<ProtectedCustodyWriter>(std::move(*opened.value));
    }
};
void seek(IStream* stream, LONGLONG offset, DWORD origin = STREAM_SEEK_SET) {
    LARGE_INTEGER move{}; move.QuadPart = offset;
    ULARGE_INTEGER at{};
    assert(stream->Seek(move, origin, &at) == S_OK);
}
void roundTrip() {
    Fixture fixture;
    auto cancel = std::make_shared<std::atomic<bool>>(false);
    auto writer = fixture.writer(cancel);
    assert(!writer->committedPackedSnapshot().ok()); // Open/tree proof alone is not Writer's checkpoint.
    auto opened = ProtectedCustodyWriteStream::open(writer, cancel); assert(opened.ok());
    auto adapter = std::move(*opened.value);
    IStream* stream = adapter->stream();
    Microsoft::WRL::ComPtr<IStream> queried;
    assert(stream->QueryInterface(IID_PPV_ARGS(&queried)) == S_OK);
    const std::array<std::uint8_t, 8> input{1,2,3,4,5,6,7,8};
    ULONG count = 99;
    assert(!writer->writeAt(0, input.data(), input.size()).ok());
    assert(!writer->readAt(0, nullptr, 0).ok());
    assert(!writer->setSize(0).ok());
    assert(writer->checkpoint().error == CustodyFileError::conflict);
    assert(!writer->committedPackedSnapshot().ok());
    assert(!ProtectedCustodyWriteStream::open(writer, cancel).ok());
    assert(stream->Write(input.data(), static_cast<ULONG>(input.size()), &count) == S_OK && count == input.size());
    seek(stream, 2);
    const std::uint8_t header = 0x9a;
    assert(stream->Write(&header, 1, &count) == S_OK && count == 1);
    ULARGE_INTEGER length{}; length.QuadPart = 12;
    assert(stream->SetSize(length) == S_OK);
    STATSTG stat{};
    assert(stream->Stat(&stat, STATFLAG_NONAME) == S_OK && stat.cbSize.QuadPart == 12 && stat.grfMode == STGM_READWRITE);
    seek(stream, 0);
    std::array<std::uint8_t, 16> output{};
    assert(stream->Read(output.data(), static_cast<ULONG>(output.size()), &count) == S_FALSE && count == 12);
    for (std::size_t i = 0; i < 12; ++i) assert(output[i] == (i == 2 ? header : i < input.size() ? input[i] : 0));
    assert(stream->Read(output.data(), 1, &count) == S_FALSE && count == 0);
    seek(stream, 100);
    assert(stream->Write(&header, 0, &count) == S_OK && count == 0);
    assert(stream->Stat(&stat, STATFLAG_NONAME) == S_OK && stat.cbSize.QuadPart == 12); // No implicit ZERO on empty Write.
    Microsoft::WRL::ComPtr<IStream> clone;
    assert(stream->Clone(&clone) == STG_E_INVALIDFUNCTION && !clone);
    assert(stream->Commit(STGC_DEFAULT) == S_OK);
    assert(adapter->close() == S_OK && adapter->close() == S_OK);
    assert(stream->Write(&header, 1, &count) == STG_E_REVERTED && count == 0);
    assert(stream->Read(output.data(), 1, &count) == STG_E_REVERTED && count == 0);
    assert(stream->SetSize(length) == STG_E_REVERTED);
    assert(stream->Stat(&stat, STATFLAG_NONAME) == STG_E_REVERTED);
    assert(writer->checkpoint().state == CustodyCommitState::committed);
    auto committed = writer->committedPackedSnapshot(); assert(committed.ok());
    assert((*committed.value)->logicalBytes() == 12 && (*committed.value)->generation() == writer->generation());
    auto reader = openProtectedCustodyReader(*committed.value, cancel); assert(reader.ok());
    assert(reader.value->stream->Read(output.data(), 16, &count) == S_FALSE && count == 12 && output[2] == header);
    assert(writer->writeAt(0, &header, 1).ok());
    assert(!writer->committedPackedSnapshot().ok()); // Never return a stamp for pending bytes.
}
void stickyErrors() {
    for (unsigned cut = 0; cut < 5; ++cut) {
        Fixture fixture;
        auto cancel = std::make_shared<std::atomic<bool>>(false);
        auto writer = fixture.writer(cancel);
        auto opened = ProtectedCustodyWriteStream::open(writer, cancel); assert(opened.ok());
        auto adapter = std::move(*opened.value);
        assert(adapter->observedFailure() == S_OK);
        auto* stream = adapter->stream();
        const std::uint8_t value = 7;
        ULONG count = 99;
        HRESULT failed = S_OK;
        if (cut == 0) { cancel->store(true); failed = stream->Write(&value, 1, &count); }
        if (cut == 1) failed = stream->Write(nullptr, 0, &count);
        if (cut == 2) { LARGE_INTEGER offset{}; offset.QuadPart = (std::numeric_limits<LONGLONG>::min)(); failed = stream->Seek(offset, STREAM_SEEK_CUR, nullptr); }
        if (cut == 3) { ULARGE_INTEGER length{}; length.QuadPart = (std::numeric_limits<ULONGLONG>::max)(); failed = stream->SetSize(length); }
        if (cut == 4) failed = stream->Commit(STGC_DANGEROUSLYCOMMITMERELYTODISKCACHE);
        assert(FAILED(failed));
        assert(adapter->observedFailure() == failed && adapter->observedFailure() == failed);
        cancel->store(false);
        assert(stream->Write(&value, 1, &count) == failed && count == 0);
        assert(stream->Commit(STGC_DEFAULT) == failed);
        assert(adapter->close() == failed);
        assert(adapter->observedFailure() == failed);
        assert(!writer->committedPackedSnapshot().ok());
        assert(writer->checkpoint().state != CustodyCommitState::committed);
    }
}
void serializedCursorAndClose() {
    Fixture fixture;
    auto cancel = std::make_shared<std::atomic<bool>>(false);
    auto writer = fixture.writer(cancel);
    auto opened = ProtectedCustodyWriteStream::open(writer, cancel); assert(opened.ok());
    auto adapter = std::move(*opened.value);
    Microsoft::WRL::ComPtr<IStream> stream(adapter->stream());
    constexpr unsigned producers = 4, calls = 64;
    std::array<std::thread, producers> threads;
    for (unsigned i = 0; i < producers; ++i) threads[i] = std::thread([stream, i, calls] {
        const std::uint8_t value = static_cast<std::uint8_t>(i + 1);
        for (unsigned j = 0; j < calls; ++j) { ULONG written = 0; assert(stream->Write(&value, 1, &written) == S_OK && written == 1); }
    });
    for (auto& thread : threads) thread.join();
    seek(stream.Get(), 0);
    std::array<std::uint8_t, producers*calls> output{};
    ULONG got = 0;
    assert(stream->Read(output.data(), static_cast<ULONG>(output.size()), &got) == S_OK && got == output.size());
    std::array<unsigned, producers> counts{};
    for (const auto byte : output) { assert(byte >= 1 && byte <= producers); ++counts[byte-1]; }
    for (const auto count : counts) assert(count == calls); // No torn/lost cursor advance.
    seek(stream.Get(), 0, STREAM_SEEK_END);
    std::atomic<bool> entered{false};
    std::atomic<unsigned> accepted{0};
    std::thread producer([stream, &entered, &accepted] {
        entered.store(true);
        const std::uint8_t value = 9;
        for (;;) {
            ULONG written = 0;
            const auto hr = stream->Write(&value, 1, &written);
            if (hr == STG_E_REVERTED) { assert(!written); break; }
            assert(hr == S_OK && written == 1); ++accepted;
            std::this_thread::yield();
        }
    });
    while (!entered.load()) std::this_thread::yield();
    assert(adapter->close() == S_OK);
    producer.join(); // close serializes with any whole active Write, no native access afterwards.
    assert(writer->size() == output.size()+accepted.load());
    assert(writer->checkpoint().state == CustodyCommitState::committed);
    const auto generation = writer->generation();
    assert(stream->Commit(STGC_DEFAULT) == STG_E_REVERTED && writer->generation() == generation);
}
void workerLastRelease() {
    Fixture fixture;
    auto cancel = std::make_shared<std::atomic<bool>>(false);
    auto original = fixture.writer(cancel);
    std::atomic<DWORD> lastRelease{0};
    const DWORD worker = GetCurrentThreadId();
    // Aliased control ownership observes real Writer destruction, not a fake writer.
    auto* pointer = original.get();
    std::shared_ptr<ProtectedCustodyWriter> writer(pointer, [held = std::move(original), &lastRelease](ProtectedCustodyWriter*) mutable {
        held.reset(); lastRelease.store(GetCurrentThreadId());
    });
    auto opened = ProtectedCustodyWriteStream::open(writer, cancel); assert(opened.ok());
    auto adapter = std::move(*opened.value);
    Microsoft::WRL::ComPtr<IStream> late(adapter->stream());
    writer.reset();
    assert(adapter->close() == S_OK);
    adapter.reset();
    assert(lastRelease.load() == worker); // Native writer lifetime ends on worker while COM still exists.
    std::thread consumer([late = std::move(late), &lastRelease, worker]() mutable {
        const std::uint8_t value = 1; ULONG written = 99;
        assert(late->Write(&value, 1, &written) == STG_E_REVERTED && !written);
        late.Reset();
        assert(lastRelease.load() == worker);
    });
    consumer.join();
}
// A real MF async callback owns the COM objects, never the native Writer.
// This checks that boundary, not SinkWriter callbacks or in-flight disk drain.
struct MfWriteObservation {
    HANDLE ended = CreateEventW(nullptr, TRUE, FALSE, nullptr);
    HANDLE resume = CreateEventW(nullptr, TRUE, FALSE, nullptr);
    HANDLE released = CreateEventW(nullptr, TRUE, FALSE, nullptr);
    std::atomic<HRESULT> result{E_PENDING}, lateResult{E_PENDING};
    std::atomic<ULONG> written{0}, lateWritten{99};
    std::atomic<DWORD> callbackThread{0}, releaseThread{0};
    MfWriteObservation() { assert(ended && resume && released); }
    ~MfWriteObservation() { assert(CloseHandle(ended)); assert(CloseHandle(resume)); assert(CloseHandle(released)); }
};
class MfWriteCallback final : public Microsoft::WRL::RuntimeClass<
    Microsoft::WRL::RuntimeClassFlags<Microsoft::WRL::ClassicCom>, IMFAsyncCallback> {
public:
    MfWriteCallback(IMFByteStream* bytes, IStream* late, MfWriteObservation& observation)
        : bytes_(bytes), late_(late), observation_(observation) {}
    ~MfWriteCallback() {
        bytes_.Reset(); late_.Reset();
        observation_.releaseThread.store(GetCurrentThreadId());
        assert(SetEvent(observation_.released));
    }
    HRESULT STDMETHODCALLTYPE GetParameters(DWORD*, DWORD*) override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE Invoke(IMFAsyncResult* result) override {
        observation_.callbackThread.store(GetCurrentThreadId());
        ULONG written = 0;
        observation_.result.store(bytes_->EndWrite(result, &written));
        observation_.written.store(written);
        assert(SetEvent(observation_.ended));
        assert(WaitForSingleObject(observation_.resume, 30'000) == WAIT_OBJECT_0);
        const std::uint8_t lateByte = 0x37;
        written = 99;
        observation_.lateResult.store(late_->Write(&lateByte, 1, &written));
        observation_.lateWritten.store(written);
        return S_OK;
    }
private:
    Microsoft::WRL::ComPtr<IMFByteStream> bytes_;
    Microsoft::WRL::ComPtr<IStream> late_;
    MfWriteObservation& observation_;
};
void mfAsyncLastNativeOwnerRelease() {
    assert(MFStartup(MF_VERSION) == S_OK);
    {
        Fixture fixture;
        MfWriteObservation observation;
        auto cancel = std::make_shared<std::atomic<bool>>(false);
        auto original = fixture.writer(cancel);
        const DWORD worker = GetCurrentThreadId();
        std::atomic<DWORD> lastRelease{0};
        auto* pointer = original.get();
        std::shared_ptr<ProtectedCustodyWriter> writer(pointer,
            [held = std::move(original), &lastRelease](ProtectedCustodyWriter*) mutable {
                held.reset(); lastRelease.store(GetCurrentThreadId());
            });
        const std::weak_ptr<ProtectedCustodyWriter> nativeOwner = writer;
        auto opened = ProtectedCustodyWriteStream::open(writer, cancel); assert(opened.ok());
        auto adapter = std::move(*opened.value);
        Microsoft::WRL::ComPtr<IMFByteStream> bytes;
        assert(MFCreateMFByteStreamOnStream(adapter->stream(), &bytes) == S_OK);
        auto callback = Microsoft::WRL::Make<MfWriteCallback>(bytes.Get(), adapter->stream(), observation);
        assert(callback);
        const std::array<BYTE, 1024> input{}; // Alive and unchanged through actual EndWrite.
        assert(bytes->BeginWrite(input.data(), static_cast<ULONG>(input.size()), callback.Get(), nullptr) == S_OK);
        assert(WaitForSingleObject(observation.ended, 30'000) == WAIT_OBJECT_0);
        assert(observation.result.load() == S_OK && observation.written.load() == input.size());
        assert(observation.callbackThread.load()); // No fixed MF OS-thread identity is assumed.
        STATSTG stat{};
        assert(adapter->stream()->Stat(&stat, STATFLAG_NONAME) == S_OK && stat.cbSize.QuadPart == input.size());
        assert(adapter->close() == S_OK);
        writer.reset(); adapter.reset();
        assert(nativeOwner.expired() && lastRelease.load() == worker);
        // Invoke is still held, with genuine MF/IStream references. Only it
        // releases these COM objects after the native owner has already died.
        bytes.Reset(); callback.Reset();
        assert(observation.releaseThread.load() == 0);
        assert(SetEvent(observation.resume));
        assert(WaitForSingleObject(observation.released, 30'000) == WAIT_OBJECT_0);
        assert(observation.lateResult.load() == STG_E_REVERTED && observation.lateWritten.load() == 0);
        assert(observation.releaseThread.load());
        std::fprintf(stderr, "MF_ASYNC_RELEASE worker=%lu callback=%lu com_release=%lu native_release=%lu late_closed=1\n",
            worker, observation.callbackThread.load(), observation.releaseThread.load(), lastRelease.load());
    }
    assert(MFShutdown() == S_OK);
}
void mfActiveWriteCloseFence() {
    assert(MFStartup(MF_VERSION) == S_OK);
    for (const auto cut : {MfIoCut::none, MfIoCut::cancellation, MfIoCut::writeFailure}) {
        Fixture fixture;
        MfIoGate gate;
        gate.cut = cut;
        MfWriteObservation observation;
        auto cancel = std::make_shared<std::atomic<bool>>(false);
        auto writer = fixture.writer(cancel);
        auto opened = ProtectedCustodyWriteStream::open(writer, cancel); assert(opened.ok());
        auto adapter = std::move(*opened.value);
        Microsoft::WRL::ComPtr<IMFByteStream> bytes;
        assert(MFCreateMFByteStreamOnStream(adapter->stream(), &bytes) == S_OK);
        auto callback = Microsoft::WRL::Make<MfWriteCallback>(bytes.Get(), adapter->stream(), observation);
        assert(callback);
        // A second dirty playback block forces actual ciphertext IO inside the
        // MF-invoked IStream operation, not merely a test thread before Write.
        const CustodyBytes input(2*ProtectedCustodyCodec::blockBytes, 0x29);
        mfIoGate.store(&gate);
        assert(bytes->BeginWrite(input.data(), static_cast<ULONG>(input.size()), callback.Get(), nullptr) == S_OK);
        assert(WaitForSingleObject(gate.entered, 30'000) == WAIT_OBJECT_0);
        assert(gate.seen.load() && gate.thread.load());
        HANDLE closing = CreateEventW(nullptr, TRUE, FALSE, nullptr);
        HANDLE closed = CreateEventW(nullptr, TRUE, FALSE, nullptr);
        assert(closing && closed);
        std::thread control([&] {
            assert(WaitForSingleObject(closing, 30'000) == WAIT_OBJECT_0);
            // Bounded concurrency attempt: the close-completion event remains
            // unsignalled while actual MF IO is held. This does not establish
            // that close has entered its mutex wait.
            assert(WaitForSingleObject(closed, 50) == WAIT_TIMEOUT);
            if (cut == MfIoCut::cancellation) cancel->store(true);
            assert(SetEvent(gate.resume));
        });
        assert(SetEvent(closing));
        const auto closeResult = adapter->close(); // Race owner close against actual MF IO.
        assert(SetEvent(closed));
        control.join();
        assert(CloseHandle(closing) && CloseHandle(closed));
        assert(WaitForSingleObject(observation.ended, 30'000) == WAIT_OBJECT_0);
        mfIoGate.store(nullptr); // No wrapper can retain the local gate beyond IO.
        const HRESULT expected = cut == MfIoCut::none ? S_OK : HRESULT_FROM_WIN32(
            cut == MfIoCut::cancellation ? ERROR_OPERATION_ABORTED : ERROR_WRITE_FAULT);
        // MF may report the completed first chunk as a successful SHORT write
        // instead of propagating IStream's later failure. That is not success
        // for this request: the exact sticky close error must still be retained.
        const bool expectedCompletion = observation.result.load() == expected ||
            (cut != MfIoCut::none && observation.result.load() == S_OK &&
             observation.written.load() == ProtectedCustodyCodec::blockBytes);
        if (closeResult != expected || !expectedCompletion)
            std::fprintf(stderr, "MF_ACTIVE_FAILURE cut=%u close=0x%08lx end=0x%08lx expected=0x%08lx written=%lu\n",
                static_cast<unsigned>(cut), static_cast<unsigned long>(closeResult),
                static_cast<unsigned long>(observation.result.load()), static_cast<unsigned long>(expected), observation.written.load());
        assert(closeResult == expected && expectedCompletion);
        cancel->store(false);
        const std::uint8_t lateByte = 0x41;
        ULONG written = 99;
        assert(adapter->stream()->Write(&lateByte, 1, &written) == STG_E_REVERTED && !written);
        if (cut == MfIoCut::none) {
            assert(observation.written.load() == input.size() && writer->size() == input.size());
            assert(writer->checkpoint().state == CustodyCommitState::committed);
            auto snapshot = writer->committedPackedSnapshot(); assert(snapshot.ok());
            auto reader = openProtectedCustodyReader(*snapshot.value, cancel); assert(reader.ok());
            CustodyBytes output(input.size());
            assert(reader.value->stream->Read(output.data(), static_cast<ULONG>(output.size()), &written) == S_OK);
            assert(written == output.size() && output == input); // Exact bytes, no lost second chunk.
        } else {
            // Removing the test cancellation cannot revive a failed writer.
            const auto denied = writer->writeAt(0, &lateByte, 1);
            assert(!denied.ok() && HRESULT_FROM_WIN32(denied.nativeError) == expected);
            const auto checkpoint = writer->checkpoint();
            assert(checkpoint.state != CustodyCommitState::committed && HRESULT_FROM_WIN32(checkpoint.nativeError) == expected);
            assert(!writer->committedPackedSnapshot().ok());
        }
        bytes.Reset(); callback.Reset();
        assert(SetEvent(observation.resume));
        assert(WaitForSingleObject(observation.released, 30'000) == WAIT_OBJECT_0);
        assert(observation.lateResult.load() == STG_E_REVERTED && !observation.lateWritten.load());
        std::fprintf(stderr, "MF_ACTIVE_WRITE cut=%u io_thread=%lu callback_thread=%lu close_completion_signal_absent_while_io_held=1 native_hr=0x%08lx\n",
            static_cast<unsigned>(cut), gate.thread.load(), observation.callbackThread.load(), static_cast<unsigned long>(closeResult));
    }
    assert(MFShutdown() == S_OK);
}
void quotaRefusal() {
    Fixture fixture;
    auto cancel = std::make_shared<std::atomic<bool>>(false);
    auto writer = fixture.writer(cancel);
    {
        CustodyBytes held;
        held.resize(CustodyOwnedMemory::limit-CustodyOwnedMemory::usedBytes());
        const auto denied = ProtectedCustodyWriteStream::open(writer, cancel);
        assert(!denied.ok() && denied.error == CustodyFileError::allocationFailed);
    }
    const std::uint8_t value = 11;
    assert(writer->writeAt(0, &value, 1).ok()); // Failed charged admission never installed/revoked a stream capability.
    assert(writer->checkpoint().state == CustodyCommitState::committed);
    assert(writer->committedPackedSnapshot().ok());
}
void partialWriteRefusal() {
    Fixture fixture;
    auto cancel = std::make_shared<std::atomic<bool>>(false);
    auto writer = fixture.writer(cancel);
    auto opened = ProtectedCustodyWriteStream::open(writer, cancel); assert(opened.ok());
    auto adapter = std::move(*opened.value);
    CustodyBytes input(2*ProtectedCustodyCodec::blockBytes, 0x17), held;
    // One pending playback block fits. Sealing it on the second chunk requires
    // another whole plaintext block and must fail before admitting that chunk.
    constexpr auto available = ProtectedCustodyCodec::blockBytes+192*1024;
    assert(CustodyOwnedMemory::limit-CustodyOwnedMemory::usedBytes() > available);
    held.resize(CustodyOwnedMemory::limit-CustodyOwnedMemory::usedBytes()-available);
    ULONG written = 99;
    const auto failed = adapter->stream()->Write(input.data(), static_cast<ULONG>(input.size()), &written);
    assert(failed == E_OUTOFMEMORY && written == ProtectedCustodyCodec::blockBytes);
    held.clear(); held.shrink_to_fit();
    assert(adapter->stream()->Write(input.data(), 1, &written) == failed && written == 0);
    assert(adapter->close() == failed);
    assert(writer->checkpoint().state != CustodyCommitState::committed);
    assert(!writer->committedPackedSnapshot().ok());
}
}
#endif
int main() {
#ifdef _MSC_VER
    _set_error_mode(_OUT_TO_STDERR);
    _set_abort_behavior(0, _WRITE_ABORT_MSG | _CALL_REPORTFAULT);
#ifdef _DEBUG
    _CrtSetReportMode(_CRT_ASSERT, _CRTDBG_MODE_FILE);
    _CrtSetReportFile(_CRT_ASSERT, _CRTDBG_FILE_STDERR);
#endif
#endif
#ifdef _WIN32
    assert(SUCCEEDED(CoInitializeEx(nullptr, COINIT_MULTITHREADED)));
    const auto before = CustodyOwnedMemory::usedBytes();
    std::size_t emptyCharge = 0;
    {
        const CustodyBytes empty;
        emptyCharge = CustodyOwnedMemory::usedBytes()-before;
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
    roundTrip();
    std::fprintf(stderr, "WRITE_STREAM_RELEASE stage=round_trip owned=%zu baseline=%zu empty_proxy=%zu\n",
        CustodyOwnedMemory::usedBytes(), before, emptyCharge);
    // The process-wide ReadCache survives empty until process exit. Its MSVC
    // Debug iterator proxy remains charged; no reader/writer bytes may remain.
    assert(CustodyOwnedMemory::usedBytes() == before+emptyCharge);
    stickyErrors(); serializedCursorAndClose(); workerLastRelease(); mfAsyncLastNativeOwnerRelease(); mfActiveWriteCloseFence(); quotaRefusal(); partialWriteRefusal();
    std::fprintf(stderr, "WRITE_STREAM_RELEASE stage=all_cases owned=%zu baseline=%zu empty_proxy=%zu\n",
        CustodyOwnedMemory::usedBytes(), before, emptyCharge);
    assert(CustodyOwnedMemory::usedBytes() == before+emptyCharge);
    CoUninitialize();
    std::puts("PASS: generated native writable stream, checkpoint snapshot, serialization and worker teardown");
#else
    std::puts("SKIP: writable COM stream requires Windows; portable run is not native acceptance");
#endif
}
