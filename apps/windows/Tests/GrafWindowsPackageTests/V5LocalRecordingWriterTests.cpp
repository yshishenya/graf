#include "../../RecApp/Recording/LocalRecordingPackage.h"
#include "../../RecApp/Storage/AtomicFileStore.h"
#include "../../RecApp/Upload/DesktopApiClient.h"
#include "../../RecApp/Upload/DesktopHttpTransport.h"
#include "../../RecApp/Storage/ProtectedCustodyWriter.h"
#include "../../RecApp/Storage/ProtectedPackedCustodyTree.h"
#include "../../RecApp/Upload/DesktopUploadQueueService.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include "../GeneratedRecordingFixtures.h"
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <fstream>
#include <limits>
#include <map>
#include <type_traits>
#include <mutex>
#include <vector>

#ifdef _WIN32
#include <shellapi.h>
#include <cmath>
#include <mfapi.h>
#include <mferror.h>
#include <mfidl.h>
#include <mfreadwrite.h>
#include <propvarutil.h>
#include <wrl/client.h>
#include <winternl.h>
namespace graf::windows {
// Retain the real prepared writer across failure; no fabricated package/proof.
struct V5RecoveryTestPeer {
    static auto prepare(std::shared_ptr<ProtectedCustodyStoreOwner> owner, std::string_view session,
        std::shared_ptr<const std::atomic<bool>> cancellation) {
        return V5LocalRecordingWriter::prepareRecovery(std::move(owner),session,std::move(cancellation));
    }
    static auto finish(std::shared_ptr<V5LocalRecordingWriter> writer) {
        return V5LocalRecordingWriter::finishRecovery(std::move(writer));
    }
};
}
namespace {
struct RecoveryEvent { unsigned role, operation, afterEvent=0; };
std::mutex recoveryEventMutex;
std::vector<RecoveryEvent> recoveryEvents;
std::wstring recoveryWatchedRoot;
std::ofstream recoveryChildProgress;
void recoveryChildPhase(const char* phase,unsigned ordinal=0,unsigned role=99,unsigned operation=99) {
    if(!recoveryChildProgress.is_open()) return;
    const auto error=GetLastError();
    recoveryChildProgress << phase << ' ' << GetTickCount64() << ' ' << ordinal << ' ' << role << ' ' << operation << '\n';
    recoveryChildProgress.flush(); assert(recoveryChildProgress.good());
    SetLastError(error);
}
unsigned recoveryKillAt = 0;
RecoveryEvent recoveryExpected{99,99};
RecoveryEvent recoveryFault{99,99};
unsigned recoveryFaultHits=0, recoveryReadAfterEvent=0;
bool recoveryReadArmed=false;
std::uint64_t recoveryFaultReadOffset=0;
DWORD recoveryFaultReadBytes=0;
std::atomic<bool>* recoveryReadCancellation=nullptr;
std::array<bool,3> recoveryWrote{}, recoveryFlushed{}, recoveryData{}, recoveryHeadPending{};
unsigned recoveryRole(HANDLE file) {
    if(recoveryWatchedRoot.empty()) return 99;
    wchar_t path[32768]{};
    const auto size=GetFinalPathNameByHandleW(file,path,32768,FILE_NAME_NORMALIZED|VOLUME_NAME_DOS);
    assert(size && size<32768);
    const std::wstring_view name(path,size);
    if(name.find(recoveryWatchedRoot)==std::wstring_view::npos) return 99;
    constexpr std::array<std::wstring_view,6> roles{L"\\canonical\\",L"\\media\\",L"\\playback\\",L"\\manifest\\",L"\\recovery\\",L"\\package-state\\"};
    for(unsigned role=0;role<roles.size();++role)
        if(name.find(roles[role])!=std::wstring_view::npos) return role;
    return 99;
}
bool recoveryFail(HANDLE file,unsigned operation) {
    if(operation!=recoveryFault.operation) return false;
    const auto error=GetLastError();
    const auto role=recoveryRole(file);
    std::lock_guard<std::mutex> lock(recoveryEventMutex);
    const bool eligible=operation==7 || operation==8 || operation==9 ? recoveryReadArmed :
        operation==5 ? role<3 && recoveryData[role] :
        operation==6 ? role<3 && recoveryData[role] && recoveryHeadPending[role] : true;
    const bool fail=!recoveryFaultHits && role==recoveryFault.role && operation==recoveryFault.operation && eligible &&
        recoveryEvents.size()>=recoveryFault.afterEvent;
    if(fail) ++recoveryFaultHits;
    SetLastError(error);
    return fail;
}
// Only this generated-data executable compiles the REAL file layer with local
// wrappers. No failure knobs or alternate persistence implementation ship.
void recoveryEvent(HANDLE file,unsigned operation) {
    if(recoveryWatchedRoot.empty()) return;
    const auto error=GetLastError();
    wchar_t path[32768]{};
    const auto size=GetFinalPathNameByHandleW(file,path,32768,FILE_NAME_NORMALIZED|VOLUME_NAME_DOS);
    assert(size && size<32768);
    const std::wstring_view name(path,size);
    if(name.find(recoveryWatchedRoot)!=std::wstring_view::npos) {
        constexpr std::array<std::wstring_view,6> roles{L"\\canonical\\",L"\\media\\",L"\\playback\\",L"\\manifest\\",L"\\recovery\\",L"\\package-state\\"};
        unsigned role=0;
        while(role<roles.size() && name.find(roles[role])==std::wstring_view::npos) ++role;
        if(role<roles.size()) {
            std::lock_guard<std::mutex> lock(recoveryEventMutex);
            bool observe=operation==2 || operation==3; // Every before/after metadata rename.
            if(operation!=2 && operation!=3 && role<3 && name.find(L"content.packed-v2")!=std::wstring_view::npos) {
                assert(role!=0 && "recovery_must_not_write_or_flush_canonical");
                // A complete reset HEAD exists before the first new DATA too.
                if(operation==5) { observe=true; recoveryHeadPending[role]=true; }
                else if(operation==6) { observe=recoveryHeadPending[role]; recoveryHeadPending[role]=false; }
                else {
                    auto& seen=operation==0 ? recoveryWrote[role] : operation==1 ? recoveryFlushed[role] : recoveryData[role];
                    observe=!seen; seen=true; // First actual birth write/flush and DATA append.
                }
            }
            if(observe) {
                assert(recoveryEvents.size()<256);
                recoveryEvents.push_back({role,operation});
                recoveryChildPhase("event",static_cast<unsigned>(recoveryEvents.size()),role,operation);
                if(recoveryReadAfterEvent && recoveryEvents.size()==recoveryReadAfterEvent) recoveryReadArmed=true;
                if(recoveryKillAt && recoveryEvents.size()==recoveryKillAt) {
                    assert(role==recoveryExpected.role && operation==recoveryExpected.operation && "child_must_reach_same_physical_event_as_baseline");
                    std::fprintf(stderr,"COLD_RECOVERY_CRASH hit=%u role=%u operation=%u destructors=0\n",recoveryKillAt,role,operation);
                    std::fflush(stderr);
                    assert(TerminateProcess(GetCurrentProcess(),88));
                    std::abort(); // Unreachable if the actual native termination succeeded.
                }
            }
        }
    }
    SetLastError(error);
}
enum class InitialCanonicalCut { none, data, node, head };
InitialCanonicalCut initialCanonicalCut=InitialCanonicalCut::none;
graf::windows::PackedCustodyContext initialCanonicalContext{};
std::uint64_t initialCanonicalAt=0, initialCanonicalEnd=0;
unsigned initialCanonicalRecords=0, initialCanonicalFlushes=0, initialCanonicalAckFrames=0;
// The public packed envelope framing is little-endian on this Windows target.
struct InitialCanonicalHeader {
    char magic[8];
    std::uint16_t version;
    std::uint8_t kind, role;
    std::uint32_t cipherBytes;
};
static_assert(sizeof(InitialCanonicalHeader)==16 && offsetof(InitialCanonicalHeader,version)==8 &&
    offsetof(InitialCanonicalHeader,kind)==10 && offsetof(InitialCanonicalHeader,role)==11 && offsetof(InitialCanonicalHeader,cipherBytes)==12);
BOOL WINAPI initialCanonicalWrite(HANDLE file,LPCVOID bytes,DWORD count,LPDWORD done,LPOVERLAPPED operation) {
    using namespace graf::windows;
    assert(operation && bytes && count && done);
    const auto offset=(static_cast<std::uint64_t>(operation->OffsetHigh)<<32)|operation->Offset;
    constexpr std::array<PackedRecordKind,5> kinds{PackedRecordKind::data,PackedRecordKind::nodeL0,
        PackedRecordKind::nodeL1,PackedRecordKind::nodeL2,PackedRecordKind::head};
    if(initialCanonicalAt==initialCanonicalEnd) {
        assert(initialCanonicalRecords<kinds.size());
        const auto append=initialCanonicalRecords ? ((initialCanonicalEnd+15)&~std::uint64_t{15}) : ProtectedPackedCustodyFormat::appendOffset;
        if(count<sizeof(InitialCanonicalHeader)) {
            assert(offset==initialCanonicalEnd && offset+count==append && initialCanonicalRecords<4);
            const auto* padding=static_cast<const std::uint8_t*>(bytes);
            assert(std::all_of(padding,padding+count,[](auto byte) { return byte==0; }));
            return WriteFile(file,bytes,count,done,operation);
        }
        InitialCanonicalHeader header{}; std::memcpy(&header,bytes,sizeof(header));
        const auto kind=static_cast<PackedRecordKind>(header.kind);
        assert(std::memcmp(header.magic,"GRFPEV2",8)==0 && header.version==2 &&
            header.role==static_cast<unsigned>(CustodyRole::canonical) && kind==kinds[initialCanonicalRecords]);
        const bool head=kind==PackedRecordKind::head;
        assert(offset==(head ? 16512 : append) && header.cipherBytes);
        const auto envelope=head ? std::uint64_t{16384} : sizeof(header)+std::uint64_t{header.cipherBytes};
        assert(header.cipherBytes<=envelope-sizeof(header) &&
            envelope<=(kind==PackedRecordKind::data ? ProtectedPackedCustodyFormat::blockBytes+4096ULL : head ? 16384ULL : 8192ULL));
        initialCanonicalAt=offset; initialCanonicalEnd=offset+envelope;
    }
    assert(offset==initialCanonicalAt && count<=initialCanonicalEnd-offset);
    const auto result=WriteFile(file,bytes,count,done,operation);
    assert(result && *done==count && "initial_canonical_cut_requires_complete_native_transfer");
    initialCanonicalAt+=*done;
    if(initialCanonicalAt==initialCanonicalEnd) {
        ++initialCanonicalRecords;
        if(initialCanonicalRecords==5) {
            assert(count==16384 && offset==16512 && initialCanonicalFlushes==1);
            CustodyBytes cell(static_cast<const std::uint8_t*>(bytes),static_cast<const std::uint8_t*>(bytes)+count);
            auto decoded=ProtectedPackedCustodyCodec::openHead(initialCanonicalContext,1,cell,2); assert(decoded.ok());
            LARGE_INTEGER size{}; assert(GetFileSizeEx(file,&size) && size.QuadPart>0);
            auto descriptor=ProtectedPackedCustodyFormat::decodeDescriptor(decoded.value->body.data(),decoded.value->body.size(),
                decoded.value->version,static_cast<std::uint64_t>(size.QuadPart));
            assert(descriptor && descriptor->generation==2 && descriptor->logicalBytes==ProtectedPackedCustodyFormat::blockBytes &&
                descriptor->blockCount==1 && descriptor->root.kind==PackedRecordKind::nodeL2);
        }
        const bool kill=(initialCanonicalCut==InitialCanonicalCut::data && initialCanonicalRecords==1) ||
            (initialCanonicalCut==InitialCanonicalCut::node && initialCanonicalRecords==4) ||
            (initialCanonicalCut==InitialCanonicalCut::head && initialCanonicalRecords==5);
        if(kill) {
            assert(initialCanonicalAckFrames==136 && initialCanonicalFlushes==(initialCanonicalRecords==5 ? 1U : 0U));
            recoveryChildPhase("initial_canonical_kill",initialCanonicalAckFrames,0,initialCanonicalRecords);
            std::fprintf(stderr,"INITIAL_CANONICAL_CRASH cut=%u records=%u flushes=%u ack_frames=136 destructors=0\n",
                static_cast<unsigned>(initialCanonicalCut),initialCanonicalRecords,initialCanonicalFlushes);
            std::fflush(stderr);
            assert(TerminateProcess(GetCurrentProcess(),88));
            std::abort();
        }
    }
    return result;
}
BOOL WINAPI initialCanonicalFlush(HANDLE file) {
    assert(initialCanonicalRecords==4 && initialCanonicalAt==initialCanonicalEnd && !initialCanonicalFlushes);
    const auto result=FlushFileBuffers(file); assert(result);
    ++initialCanonicalFlushes;
    return result;
}

BOOL WINAPI recoveryWrite(HANDLE file,LPCVOID bytes,DWORD count,LPDWORD done,LPOVERLAPPED operation) {
    const auto offset=operation ? (static_cast<std::uint64_t>(operation->OffsetHigh)<<32)|operation->Offset : 0;
    if(initialCanonicalCut!=InitialCanonicalCut::none && recoveryRole(file)==0)
        return initialCanonicalWrite(file,bytes,count,done,operation);
    if(recoveryFail(file,0) ||
        (operation && offset>=graf::windows::ProtectedPackedCustodyFormat::appendOffset && recoveryFail(file,4)) ||
        (operation && (offset==128 || offset==16512) && count==16384 && recoveryFail(file,5))) {
        if(done) *done=0;
        SetLastError(ERROR_DISK_FULL); return FALSE;
    }
    const auto result=WriteFile(file,bytes,count,done,operation);
    if(result && count && done && *done) {
        recoveryEvent(file,0);
        if(operation) {
            if(offset>=graf::windows::ProtectedPackedCustodyFormat::appendOffset) recoveryEvent(file,4);
            if((offset==128 || offset==16512) && count==16384) {
                assert(*done==count && "HEAD_crash_cut_requires_complete_native_transfer");
                recoveryEvent(file,5);
            }
        }
    }
    return result;
}
BOOL WINAPI recoveryFlush(HANDLE file) {
    if(initialCanonicalCut!=InitialCanonicalCut::none && recoveryRole(file)==0) return initialCanonicalFlush(file);
    if(recoveryFail(file,1) || recoveryFail(file,6)) { SetLastError(ERROR_WRITE_FAULT); return FALSE; }
    const auto result=FlushFileBuffers(file);
    if(result) { recoveryEvent(file,1); recoveryEvent(file,6); }
    return result;
}
NTSTATUS NTAPI recoveryRename(HANDLE file,PIO_STATUS_BLOCK io,PVOID info,ULONG length,FILE_INFORMATION_CLASS kind) {
    using Function=NTSTATUS(NTAPI*)(HANDLE,PIO_STATUS_BLOCK,PVOID,ULONG,FILE_INFORMATION_CLASS);
    const auto procedure=GetProcAddress(GetModuleHandleW(L"ntdll.dll"),"NtSetInformationFile"); assert(procedure);
    Function function=nullptr; static_assert(sizeof(function)==sizeof(procedure));
    std::memcpy(&function,&procedure,sizeof(function));
    recoveryEvent(file,2);
    if(recoveryFail(file,2)) return io->Status=static_cast<NTSTATUS>(0xc000007fUL); // Actual returned STATUS_DISK_FULL, no rename.
    const auto status=function(file,io,info,length,kind);
    if(status==0 && io->Status==0) recoveryEvent(file,3);
    if(status==0 && io->Status==0 && recoveryFail(file,3))
        return io->Status=static_cast<NTSTATUS>(0xc000007fUL); // The rename happened; its ACK is ambiguous.
    return status;
}
BOOL WINAPI recoveryRead(HANDLE file,LPVOID bytes,DWORD count,LPDWORD done,LPOVERLAPPED operation) {
    const auto recordRead=[&] {
        recoveryFaultReadOffset=operation ? (static_cast<std::uint64_t>(operation->OffsetHigh)<<32)|operation->Offset : 0;
        recoveryFaultReadBytes=count;
    };
    if(recoveryFail(file,7)) { recordRead(); if(done) *done=0; SetLastError(ERROR_READ_FAULT); return FALSE; }
    if(recoveryFail(file,8)) { recordRead(); assert(recoveryReadCancellation); recoveryReadCancellation->store(true); }
    if(recoveryFault.operation==9 && operation && count>=128 && recoveryRole(file)==0) {
        wchar_t path[32768]{};
        const auto size=GetFinalPathNameByHandleW(file,path,32768,FILE_NAME_NORMALIZED|VOLUME_NAME_DOS);
        assert(size && size<32768);
        constexpr std::wstring_view suffix=L"\\content.packed-v2";
        const std::wstring_view name(path,size);
        if(name.size()>=suffix.size() && name.substr(name.size()-suffix.size())==suffix && recoveryFail(file,9)) {
            recordRead(); assert(done);
            const auto result=ReadFile(file,bytes,count-1,done,operation);
            assert(result && *done==count-1 && *done>0); // Real short transfer, not a native error or fabricated bytes.
            return result;
        }
    }
    return ReadFile(file,bytes,count,done,operation);
}
FARPROC WINAPI recoveryProcedure(HMODULE module,LPCSTR name) {
    if(std::strcmp(name,"NtSetInformationFile")==0) {
        const auto function=&recoveryRename; FARPROC procedure=nullptr;
        static_assert(sizeof(function)==sizeof(procedure));
        std::memcpy(&procedure,&function,sizeof(function)); return procedure;
    }
    return GetProcAddress(module,name);
}
}
#define WriteFile recoveryWrite
#define ReadFile recoveryRead
#define FlushFileBuffers recoveryFlush
#define GetProcAddress recoveryProcedure
#include "../../RecApp/Storage/ProtectedCustodyFiles.cpp"
#undef GetProcAddress
#undef FlushFileBuffers
#undef WriteFile
#undef ReadFile
#if defined(_MSC_VER) && defined(_DEBUG)
#include <crtdbg.h>
namespace {
thread_local std::size_t resultAllocation = 0, denyResultAllocation = 0;
int resultAllocationHook(int kind, void*, std::size_t, int, long, const unsigned char*, int) {
    return kind != _HOOK_ALLOC || !denyResultAllocation || ++resultAllocation != denyResultAllocation;
}
void resultAllocationCuts() {
    static_assert(!std::is_nothrow_default_constructible_v<graf::windows::V5WriterResult>);
    const auto previous = _CrtSetAllocHook(resultAllocationHook);
    for (std::size_t cut = 1; cut != 33; ++cut) {
        resultAllocation = 0; denyResultAllocation = cut;
        try {
            graf::windows::V5WriterResult result;
            result.packageDirectory = L"generated-only";
            result.wavSha256.assign(64, 'a'); result.playbackSha256.assign(64, 'b');
            std::optional<graf::windows::V5WriterResult> completion;
            completion.emplace(std::move(result)); // Must remain catchable in Debug.
        } catch (const std::bad_alloc&) {}
        denyResultAllocation = 0;
    }
    _CrtSetAllocHook(previous);
}
}
#endif
#endif

#ifdef _WIN32
namespace {
std::string coldManifest(std::string_view session,std::string_view privacy) {
    return "{\"schema_version\":\""+std::string(graf::windows::kManifestSchemaVersion)+
        "\",\"canonical_mix_profile\":\""+std::string(graf::windows::kCanonicalMixProfile)+"\",\"source_kind\":\""+std::string(graf::windows::kV5SourceKind)+
        "\",\"media_scribe_source_mode\":\""+std::string(graf::windows::kV5MediaScribeSourceMode)+
        "\",\"capture_status\":\"normal\",\"capture_reason_code\":\"none\",\"duration_ms\":500,"+
        "\"started_at_ms\":1000,\"stopped_at_ms\":1500,\"display_timezone_offset_minutes\":180,\"sessionId\":\""+std::string(session)+"\",\"privacySegments\":"+std::string(privacy)+"}";
}
auto coldHashes(const std::filesystem::path& root) {
    std::map<std::filesystem::path,std::string> hashes;
    for(const auto& e:std::filesystem::recursive_directory_iterator(root))
        if(e.is_regular_file()) hashes.emplace(e.path(),graf::windows::sha256File(e.path()));
    return hashes;
}
auto coldOriginalHashes(const std::filesystem::path& package) {
    auto hashes=coldHashes(package/L".custody-v1");
    for(auto i=hashes.begin();i!=hashes.end();)
        if(i->first.filename()!=L"id.bin" && i->first.parent_path().filename()!=L"canonical") i=hashes.erase(i);
        else ++i;
    return hashes; // Whole canonical role and every original package/role identity.
}
auto coldCompletedHashes(const std::filesystem::path& package) {
    auto hashes=coldHashes(package/L".custody-v1");
    for(auto i=hashes.begin();i!=hashes.end();)
        if(i->first.parent_path().filename()==L"package-state" && i->first.filename()!=L"id.bin") i=hashes.erase(i);
        else ++i;
    return hashes;
}
void coldCrashFixture(const std::filesystem::path& root,std::string_view privacy="[]",bool wrongPcm=false,unsigned frames=100) {
    using namespace graf::windows;
    auto cancel=std::make_shared<std::atomic<bool>>(false);
    auto store=ProtectedCustodyStoreOwner::open(root,cancel); assert(store.ok());
    auto queue=(*store.value)->readQueueValue(cancel); assert(queue.ok());
    ProtectedUploadQueueValue candidate(**queue.value);
    constexpr auto session="44444444-4444-4444-8444-444444444444";
    assert((*store.value)->prepareRecordingReservation(candidate,session,"11111111-1111-4111-8111-111111111111","22222222-2222-4222-8222-222222222222",true,1000,cancel).ok());
    auto bytes=candidate.serialize(cancel); assert(bytes.ok());
    assert(commitProtectedCustodyMetadata(*store.value,(*store.value)->queueContext(),1,*bytes.value,cancel).state==CustodyCommitState::committed);
    auto package=(*store.value)->createPackage(session,cancel); assert(package.ok());
    auto writer=(*package.value)->createWriter(CustodyRole::canonical); assert(writer.ok());
    assert(frames && frames<=6000 && (!wrongPcm || frames==100));
    {
        CustodyBytes samples((static_cast<std::size_t>(frames)*480+47)*sizeof(float));
        std::uint32_t noise=0x200462;
        for(std::size_t at=0;at<samples.size();at+=sizeof(float)) {
            noise=noise*1664525U+1013904223U;
            const float sample=at+sizeof(float)==samples.size() ? std::numeric_limits<float>::quiet_NaN() :
                frames==100 ? 0.25F : static_cast<float>(noise>>8)/33554432.0F-0.25F;
            std::memcpy(samples.data()+at,&sample,sizeof(sample));
        }
        assert((*writer.value)->writeAt(0,samples.data(),samples.size()).ok());
    } // Charged allocation is wiped and released, including the incomplete tail.
    assert((*writer.value)->checkpoint().state==CustodyCommitState::committed);
    const auto manifest=coldManifest(session,privacy);
    assert((*package.value)->commitMetadata(CustodyRole::manifest,CustodyBytes(manifest.begin(),manifest.end())).state==CustodyCommitState::committed);
    if(wrongPcm) {
        // Genuine protected WAV with the correct 16kHz/mono/PCM16 header and
        // length, but zero PCM rather than canonical's 0.25F. No ciphertext tamper.
        constexpr std::array<std::uint8_t,44> header{'R','I','F','F',0x24,0x7d,0,0,
            'W','A','V','E','f','m','t',' ',16,0,0,0,1,0,1,0,0x80,0x3e,0,0,
            0,0x7d,0,0,2,0,16,0,'d','a','t','a',0,0x7d,0,0};
        CustodyBytes wav(32044,0); std::memcpy(wav.data(),header.data(),header.size());
        auto media=(*package.value)->createWriter(CustodyRole::media); assert(media.ok());
        assert((*media.value)->writeAt(0,wav.data(),wav.size()).ok());
        assert((*media.value)->checkpoint().state==CustodyCommitState::committed);
        auto proof=(*media.value)->committedPackedSnapshot(); assert(proof.ok() && (*proof.value)->logicalBytes()==wav.size());
        auto phase=(*package.value)->current(); ++phase.generation;
        phase.phase=CustodyPackagePhase::finalizing; phase.reason=ReasonCode::finalizationFailed;
        assert((*package.value)->commit(phase).state==CustodyCommitState::committed);
    }
}
void armRecoveryTrace(const std::filesystem::path& root,unsigned killAt) {
    recoveryEvents.clear(); recoveryEvents.reserve(256);
    recoveryWrote={}; recoveryFlushed={}; recoveryData={}; recoveryHeadPending={}; recoveryKillAt=killAt;
    recoveryWatchedRoot=(root/L"44444444-4444-4444-8444-444444444444"/L".custody-v1").wstring();
}
int coldCrashChild(const std::filesystem::path& root,unsigned cut,RecoveryEvent expected) {
    using namespace graf::windows;
    // Test metadata only, OUTSIDE the protected recording root/inventory.
    // Flushing this stream is diagnostic progress, never a custody/durability ACK.
    recoveryChildProgress.open(root.parent_path()/L"recovery-child-progress",std::ios::trunc);
    assert(recoveryChildProgress.is_open());
    recoveryChildPhase("store_open_begin");
    auto cancel=std::make_shared<std::atomic<bool>>(false);
    auto store=ProtectedCustodyStoreOwner::open(root,cancel); assert(store.ok());
    recoveryChildPhase("store_open_end");
    armRecoveryTrace(root,cut);
    recoveryExpected=expected;
    recoveryChildPhase("recover_begin");
    const auto recovered=V5LocalRecordingWriter::recover(*store.value,"44444444-4444-4444-8444-444444444444",cancel);
    recoveryChildPhase("recover_end");
    (void)recovered;
    return 89; // A missing physical event is NEVER accepted as the intended cut.
}
void crashRecoveryAt(const std::filesystem::path& root,unsigned cut,RecoveryEvent event) {
    wchar_t executable[32768]{}; const auto n=GetModuleFileNameW(nullptr,executable,32768); assert(n && n<32768);
    std::wstring command=L"\""+std::wstring(executable,n)+L"\" --cold-recovery-crash \""+root.wstring()+L"\" "+std::to_wstring(cut)+L" "+std::to_wstring(event.role)+L" "+std::to_wstring(event.operation);
    {
        std::ofstream progress(root.parent_path()/L"recovery-child-progress",std::ios::trunc);
        progress << "parent_launch " << GetTickCount64() << ' ' << cut << ' ' << event.role << ' ' << event.operation << '\n';
        assert(progress.good());
    } // A child that never enters main must not expose the previous child's log.
    STARTUPINFOW startup{}; startup.cb=sizeof(startup); PROCESS_INFORMATION child{};
    assert(CreateProcessW(executable,command.data(),nullptr,nullptr,FALSE,CREATE_NO_WINDOW,nullptr,nullptr,&startup,&child));
    CloseHandle(child.hThread);
    const auto wait=WaitForSingleObject(child.hProcess,60000);
    auto terminal=wait;
    if(wait!=WAIT_OBJECT_0) { TerminateProcess(child.hProcess,90); terminal=WaitForSingleObject(child.hProcess,10000); }
    DWORD exit=0; assert(GetExitCodeProcess(child.hProcess,&exit)); CloseHandle(child.hProcess);
    if(wait!=WAIT_OBJECT_0 || exit!=88) {
        std::fprintf(stderr,"COLD_RECOVERY_CHILD_FAILED cut=%u role=%u operation=%u wait=%lu exit=%lu\n",cut,event.role,event.operation,wait,exit);
        if(terminal==WAIT_OBJECT_0) {
            std::ifstream progress(root.parent_path()/L"recovery-child-progress",std::ios::binary);
            std::array<char,8192> bytes{}; progress.read(bytes.data(),bytes.size());
            const auto got=progress.gcount();
            assert(progress.eof() && got>0 && got<static_cast<std::streamsize>(bytes.size()));
            std::fprintf(stderr,"COLD_RECOVERY_CHILD_PROGRESS\n%.*s",static_cast<int>(got),bytes.data());
        }
    }
    assert(wait==WAIT_OBJECT_0 && exit==88 && "physical_recovery_cut_must_be_reached");
}
std::filesystem::path initialCanonicalNativePath(const std::filesystem::path& path) {
    assert(path.is_absolute());
    return std::filesystem::path(L"\\\\?\\"+path.wstring());
}
std::string initialCanonicalBytes(const std::filesystem::path& nativePath) {
    const auto file=CreateFileW(nativePath.c_str(),GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE,
        nullptr,OPEN_EXISTING,FILE_FLAG_OPEN_REPARSE_POINT,nullptr);
    assert(file!=INVALID_HANDLE_VALUE);
    LARGE_INTEGER size{}; assert(GetFileSizeEx(file,&size) && size.QuadPart>=0 && size.QuadPart<=1024*1024);
    std::string bytes(static_cast<std::size_t>(size.QuadPart),'\0');
    for(std::size_t at=0;at<bytes.size();) {
        const auto count=static_cast<DWORD>((std::min<std::size_t>)(65536,bytes.size()-at));
        DWORD got=0; assert(ReadFile(file,bytes.data()+at,count,&got,nullptr) && got==count); at+=got;
    }
    assert(CloseHandle(file));
    return bytes;
}
auto initialCanonicalSnapshot(const std::filesystem::path& root) {
    std::map<std::filesystem::path,std::optional<std::string>> snapshot;
    const auto native=initialCanonicalNativePath(root);
    for(const auto& entry:std::filesystem::recursive_directory_iterator(native)) {
        assert(!entry.is_symlink());
        const auto relative=entry.path().lexically_relative(native);
        if(entry.is_directory()) assert(snapshot.emplace(relative,std::nullopt).second);
        else {
            assert(entry.is_regular_file());
            assert(snapshot.emplace(relative,initialCanonicalBytes(entry.path())).second);
        }
    }
    assert(!snapshot.empty());
    return snapshot; // Wide paths and exact raw bytes, including long descendants.
}
std::string initialCanonicalBirthReceipt(const std::filesystem::path& root,InitialCanonicalCut cut) {
    using namespace graf::windows;
    std::string receipt;
    const auto canonical=std::filesystem::path(L"44444444-4444-4444-8444-444444444444")/L".custody-v1"/L"canonical"/L"content.packed-v2";
    for(const auto& entry:initialCanonicalSnapshot(root)) {
        const auto& path=entry.first.native();
        receipt+=sha256(std::string_view(reinterpret_cast<const char*>(path.data()),path.size()*sizeof(wchar_t)))+' ';
        if(!entry.second) { receipt+="directory\n"; continue; }
        auto bytes=std::string_view(*entry.second);
        if(entry.first==canonical) {
            assert(bytes.size()>=ProtectedPackedCustodyFormat::appendOffset);
            // Only the new g2 cell may change; prefix and g1 peer retain identity.
            bytes=bytes.substr(0,cut==InitialCanonicalCut::head ? 16512 : ProtectedPackedCustodyFormat::appendOffset);
        }
        receipt+=std::to_string(bytes.size())+' '+sha256(bytes)+'\n';
    }
    return receipt; // Hashes only: no content or absolute paths in receipts.
}
float initialCanonicalSample(std::uint64_t sample) {
    return static_cast<float>(static_cast<int>(sample%127)-63)/128.0F;
}
int initialCanonicalChild(const std::filesystem::path& root,InitialCanonicalCut cut) {
    using namespace graf::windows;
    recoveryChildProgress.open(initialCanonicalNativePath(root.parent_path()/L"initial-canonical-progress"),std::ios::trunc);
    assert(recoveryChildProgress.is_open()); recoveryChildPhase("initial_store_open");
    auto cancel=std::make_shared<std::atomic<bool>>(false);
    auto store=ProtectedCustodyStoreOwner::open(root,cancel); assert(store.ok());
    auto queue=(*store.value)->readQueueValue(cancel); assert(queue.ok());
    ProtectedUploadQueueValue reservation(**queue.value);
    constexpr auto session="44444444-4444-4444-8444-444444444444";
    assert((*store.value)->prepareRecordingReservation(reservation,session,"11111111-1111-4111-8111-111111111111",
        "22222222-2222-4222-8222-222222222222",true,1000,cancel).ok());
    auto serialized=reservation.serialize(cancel); assert(serialized.ok());
    assert(commitProtectedCustodyMetadata(*store.value,(*store.value)->queueContext(),1,*serialized.value,cancel).state==CustodyCommitState::committed);
    auto opened=V5LocalRecordingWriter::open(*store.value,session,cancel); assert(opened.ok());
    auto writer=*opened.value;
    const auto& birth=writer->package()->current();
    assert(birth.generation==1 && birth.phase==CustodyPackagePhase::capturing && birth.refCount==1);
    const auto& ref=birth.refs[0]; assert(ref.role==CustodyRole::canonical && ref.packed && ref.containerId && !ref.sealed);
    initialCanonicalContext={{birth.context.storeId,ref.objectId,CustodyRole::canonical},*ref.containerId};
    assert(std::filesystem::file_size(initialCanonicalNativePath(writer->package()->path()/L".custody-v1"/L"canonical"/L"content.packed-v2"))==ProtectedPackedCustodyFormat::appendOffset);
    {
        std::ofstream receipt(initialCanonicalNativePath(root.parent_path()/L"initial-canonical-birth"),std::ios::binary);
        receipt << initialCanonicalBirthReceipt(root,cut); receipt.flush(); assert(receipt.good());
    }
    armRecoveryTrace(root,0);
    initialCanonicalCut=cut;
    CanonicalAudioFrame frame;
    for(unsigned i=0;i<137;++i) {
        frame.ptsFrames=static_cast<std::int64_t>(i)*480;
        for(unsigned sample=0;sample<frame.mixed.size();++sample) frame.mixed[sample]=initialCanonicalSample(i*480ULL+sample);
        assert(writer->append(frame));
        ++initialCanonicalAckFrames;
    }
    recoveryChildPhase("initial_cut_not_reached",initialCanonicalAckFrames);
    return 89;
}
void initialCanonicalCrashAt(const std::filesystem::path& root,InitialCanonicalCut cut) {
    wchar_t executable[32768]{}; const auto n=GetModuleFileNameW(nullptr,executable,32768); assert(n && n<32768);
    std::wstring command=L"\""+std::wstring(executable,n)+L"\" --initial-canonical-crash \""+root.wstring()+L"\" "+std::to_wstring(static_cast<unsigned>(cut));
    STARTUPINFOW startup{}; startup.cb=sizeof(startup); PROCESS_INFORMATION child{};
    assert(CreateProcessW(executable,command.data(),nullptr,nullptr,FALSE,CREATE_NO_WINDOW,nullptr,nullptr,&startup,&child));
    CloseHandle(child.hThread);
    const auto wait=WaitForSingleObject(child.hProcess,60000);
    auto terminal=wait;
    if(wait!=WAIT_OBJECT_0) { TerminateProcess(child.hProcess,90); terminal=WaitForSingleObject(child.hProcess,10000); }
    DWORD exit=0; assert(GetExitCodeProcess(child.hProcess,&exit)); CloseHandle(child.hProcess);
    if(wait!=WAIT_OBJECT_0 || exit!=88) {
        std::fprintf(stderr,"INITIAL_CANONICAL_CHILD_FAILED cut=%u wait=%lu exit=%lu\n",static_cast<unsigned>(cut),wait,exit);
        if(terminal==WAIT_OBJECT_0 && std::filesystem::exists(initialCanonicalNativePath(root.parent_path()/L"initial-canonical-progress"))) {
            const auto progress=initialCanonicalBytes(initialCanonicalNativePath(root.parent_path()/L"initial-canonical-progress"));
            std::fprintf(stderr,"%s",progress.c_str());
        }
    }
    assert(wait==WAIT_OBJECT_0 && exit==88 && "initial_canonical_physical_cut_must_be_reached");
}
void initialCanonicalCrashCuts() {
    using namespace graf::windows;
    constexpr auto session="44444444-4444-4444-8444-444444444444";
    static_assert(ProtectedPackedCustodyFormat::blockBytes/1920==136 && ProtectedPackedCustodyFormat::blockBytes%1920==1024);
    const auto idle=CustodyOwnedMemory::usedBytes();
    for(const auto cut:{InitialCanonicalCut::data,InitialCanonicalCut::node,InitialCanonicalCut::head}) {
        testing::GeneratedRecordingRoot paths;
        const std::wstring suffix=L"-\u0437\u0430\u043f\u0438\u0441\u044c";
        const auto fixed=paths.parent.native().size()+suffix.size()+std::strlen(session)+13;
        assert(fixed<240);
        paths.root=paths.parent/(std::wstring(240-fixed,L'x')+suffix)/L"recordings";
        assert(std::filesystem::create_directory(initialCanonicalNativePath(paths.root.parent_path())));
        assert((paths.root/session).native().size()==240);
        assert((paths.root/session/L".custody-v1"/L"canonical"/L"content.packed-v2").native().size()>MAX_PATH);
        initialCanonicalCrashAt(paths.root,cut);
        const auto before=initialCanonicalSnapshot(paths.root);
        for(const auto& entry:before) {
            if(!entry.second) continue;
            const auto role=entry.first.parent_path().filename();
            if(role==L"media" || role==L"playback" || role==L"manifest" || role==L"recovery")
                assert(entry.first.filename()==L"id.bin" && "initial_capture_must_not_birth_recovery_outputs");
            if(role==L"canonical") assert(entry.first.filename()==L"id.bin" || entry.first.filename()==L"content.packed-v2");
        }
        const auto unchanged=[&] { assert(initialCanonicalSnapshot(paths.root)==before); };
        assert(initialCanonicalBirthReceipt(paths.root,cut)==initialCanonicalBytes(initialCanonicalNativePath(paths.root.parent_path()/L"initial-canonical-birth")));
        {
            auto cancel=std::make_shared<std::atomic<bool>>(false);
            auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok()); unchanged();
            auto queue=(*store.value)->readQueueValue(cancel); assert(queue.ok()); unchanged();
            assert((*queue.value)->items().size()==1 && (*store.value)->queueGeneration()==2);
            const auto& row=(*queue.value)->items()[0];
            assert(row.localRecordingId==session && row.directoryId==session && row.sessionId==session &&
                row.ownerUserId=="11111111-1111-4111-8111-111111111111" && row.ownerWorkspaceId=="22222222-2222-4222-8222-222222222222");
            assert(std::string_view(row.packageDirectory)==(paths.root/session).u8string());
            assert(row.status==UploadQueueStatus::quarantined && row.safeReason=="capture_prepared" && !hasUploadServerIdentity(row));
            {
                auto pair=(*store.value)->readPackage(session,cancel); assert(pair.ok()); unchanged();
                for(const auto& value:(*pair.value)->slots()) {
                    assert(value.generation==1 && value.phase==CustodyPackagePhase::capturing && value.refCount==1 && !value.shortRecordingDiscarded);
                    assert(value.context.storeId==(*store.value)->queueContext().storeId && std::string_view(value.directory.data())==session);
                    const auto& ref=value.refs[0];
                    assert(ref.role==CustodyRole::canonical && ref.packed && !ref.sealed && ref.containerId);
                    assert(ref.objectId==(*pair.value)->current().refs[0].objectId && ref.containerId==(*pair.value)->current().refs[0].containerId);
                }
            }
            {
                auto inspected=LocalRecordingPackage::inspectUnfinished(*store.value,session,cancel);
                if(cut==InitialCanonicalCut::head) assert(inspected.ok() && (*inspected.value)->completeFrames()==136);
                else assert(!inspected.ok() && inspected.error==CustodyFileError::invalidContent);
                unchanged();
            } // First content inspection is cold; independent byte checks follow last release.
            {
                auto pair=(*store.value)->readPackage(session,cancel); assert(pair.ok()); unchanged();
                {
                    auto readers=openProtectedCustodyReaders(paths.root,*pair.value,cancel); assert(readers.ok()); unchanged();
                    const auto length=cut==InitialCanonicalCut::head ? ProtectedPackedCustodyFormat::blockBytes : 0;
                    for(unsigned slot=0;slot<2;++slot) {
                        auto* stream=readers.value->at(slot)[0].stream.Get(); assert(stream);
                        STATSTG stat{}; assert(stream->Stat(&stat,STATFLAG_NONAME)==S_OK && stat.type==STGTY_STREAM && stat.cbSize.QuadPart==length);
                        std::array<float,480> samples{};
                        for(std::uint64_t at=0;at<length;) {
                            const auto count=static_cast<ULONG>((std::min<std::uint64_t>)(sizeof(samples),length-at));
                            ULONG got=0; assert(stream->Read(samples.data(),count,&got)==S_OK && got==count);
                            for(unsigned sample=0;sample<count/sizeof(float);++sample) {
                                const auto expected=initialCanonicalSample(at/sizeof(float)+sample);
                                assert(std::isfinite(samples[sample]) && std::memcmp(&samples[sample],&expected,sizeof(float))==0);
                            }
                            at+=count;
                        }
                        char byte=0; ULONG got=1; assert(stream->Read(&byte,1,&got)==S_FALSE && got==0);
                    }
                }
                unchanged();
                auto normal=LocalRecordingPackage::inspectProtected(paths.root,*pair.value,session,cancel);
                assert(!normal.ok() && normal.error==CustodyFileError::invalidInput); unchanged();
            }
        }
        unchanged();
        assert(CustodyOwnedMemory::usedBytes()==idle);
        { std::array<CustodyNativeJob,4> jobs; for(const auto& job:jobs) assert(job); assert(!CustodyNativeJob{}); }
        { std::array<CustodyPin,32> pins; for(const auto& pin:pins) assert(pin); assert(!CustodyPin{}); }
        std::fprintf(stderr,"INITIAL_CANONICAL_COLD cut=%u complete_frames=%u raw_unchanged=1 both=1 queue_ids=1 resources=baseline generated_audio=1 devices=0 network=0 power_loss_durability=unproven\n",
            static_cast<unsigned>(cut),cut==InitialCanonicalCut::head ? 136U : 0U);
        std::filesystem::remove_all(initialCanonicalNativePath(paths.root.parent_path()));
    }
}

enum class ColdRecoveryCuts { all, wav, playback, playbackRestart, terminalUnused };
std::shared_ptr<const graf::windows::ProtectedPackedCustodyTree> coldPackedProof(
    const std::filesystem::path& root,std::string_view session,const wchar_t* name,
    graf::windows::CustodyRole role,graf::windows::CustodyFileAccess access=graf::windows::CustodyFileAccess::readExisting,
    graf::windows::PackedReference* firstData=nullptr) {
    using namespace graf::windows;
    const auto directory=root/std::wstring(session.begin(),session.end())/L".custody-v1"/name;
    PackedCustodyContext context{{{}, {}, role}, {}};
    const auto readId=[](const std::filesystem::path& path,CustodyId& id,std::streamoff offset=0) {
        std::ifstream input(path,std::ios::binary); assert(input);
        input.seekg(offset); assert(input);
        input.read(reinterpret_cast<char*>(id.data()),16); assert(input.gcount()==16);
    };
    readId(root/L".custody-v1"/L"store.id",context.object.storeId);
    readId(directory/L"id.bin",context.object.objectId);
    // Candidate only: the real owner checks the prefix, then BOTH full closures
    // authenticate the measured generation. No guessed g2 or persisted authority.
    readId(directory/L"content.packed-v2",context.containerId,48);
    auto owner=ProtectedPackedCustodyOwner::open(root,session,context,access); assert(owner.ok());
    auto proof=ProtectedPackedCustodyTree::verify(*owner.value); assert(proof.ok());
    if(firstData) {
        const auto& descriptor=(*proof.value)->descriptor();
        auto reference=descriptor.root;
        for(const auto kind:{PackedRecordKind::nodeL2,PackedRecordKind::nodeL1,PackedRecordKind::nodeL0}) {
            assert(reference.kind==kind);
            auto cipher=(*owner.value)->readCiphertext(reference.offset,reference.envelopeBytes); assert(cipher.ok());
            auto decoded=ProtectedPackedCustodyCodec::openReferenced(context,0,reference,cipher.value->bytes); assert(decoded.ok());
            auto child=ProtectedPackedCustodyFormat::decodeChild(decoded.value->body.data(),64,descriptor,reference,0,0);
            std::fill(decoded.value->body.begin(),decoded.value->body.end(),std::uint8_t{0});
            assert(child); reference=*child;
        }
        assert(reference.kind==PackedRecordKind::data && reference.offset>=ProtectedPackedCustodyFormat::appendOffset &&
            reference.offset+reference.envelopeBytes<=descriptor.committedExtent);
        *firstData=reference; // Authenticated reachable DATA, not a guessed old/orphan append offset.
    }
    return *proof.value;
}
std::uint64_t coldTerminalUnusedShape(const std::filesystem::path& root,const std::string& privacy,unsigned cut) {
    using namespace graf::windows;
    constexpr auto session="44444444-4444-4444-8444-444444444444";
    const auto before=coldHashes(root);
    const auto custody=root/session/L".custody-v1";
    unsigned children=0;
    for(const auto& e:std::filesystem::directory_iterator(custody/L"recovery")) {
        assert(e.is_regular_file() && e.path().filename()==L"id.bin"); ++children;
    }
    assert(children==1 && "terminal_recovery_must_be_exact_unused_not_partial_birth");
    for(const auto role:{CustodyRole::canonical,CustodyRole::media,CustodyRole::playback}) {
        const auto name=role==CustodyRole::canonical ? L"canonical" : role==CustodyRole::media ? L"media" : L"playback";
        const auto proof=coldPackedProof(root,session,name,role);
        assert(proof->logicalBytes()>0);
    }
    std::uint64_t generation=0;
    {
        auto cancel=std::make_shared<std::atomic<bool>>(false);
        auto store=ProtectedCustodyStoreOwner::open(root,cancel); assert(store.ok());
        auto pair=(*store.value)->readPackage(session,cancel);
        assert(pair.ok() && (*pair.value)->current().phase==CustodyPackagePhase::finalizing);
        generation=(*pair.value)->current().generation;
        auto readers=openProtectedCustodyReaders(root,*pair.value,cancel); assert(readers.ok());
        unsigned manifests=0;
        for(unsigned slot=0;slot<2;++slot) {
            const auto& value=(*pair.value)->slots()[slot];
            assert(value.refCount==2);
            for(std::size_t i=0;i<value.refCount;++i) {
                const auto& ref=value.refs[i];
                if(ref.role==CustodyRole::canonical) { assert(ref.packed && !ref.sealed); continue; }
                assert(ref.role==CustodyRole::manifest && ref.sealed && !ref.packed && ref.length && *ref.length<=65536);
                CustodyBytes bytes(static_cast<std::size_t>(*ref.length)); ULONG got=0;
                assert((*readers.value)[slot][i].stream->Read(bytes.data(),static_cast<ULONG>(bytes.size()),&got)==S_OK && got==bytes.size());
                const std::string_view text(reinterpret_cast<const char*>(bytes.data()),bytes.size());
                const bool terminal=slot==(*pair.value)->selectedSlot();
                assert(text.find(terminal ? "\"capture_status\":\"degraded\"" : "\"capture_status\":\"normal\"")!=std::string_view::npos);
                assert((text.find("\"artifacts\":")!=std::string_view::npos)==terminal);
                assert(text.find("\"privacySegments\":"+privacy)!=std::string_view::npos); ++manifests;
            }
        }
        assert(manifests==2 && coldHashes(root)==before);
    } // No fixture qualification lease/proof crosses into the recovery child.
    assert(coldHashes(root)==before);
    std::fprintf(stderr,"COLD_TERMINAL_UNUSED_SHAPE cut=%u role=5 operation=3 both_bound_history=1 recovery_children=1 recovery_refs=0 packed_both=3 preflight_unchanged=1\n",cut);
    return generation;
}
auto coldTerminalOriginalHashes(const std::filesystem::path& package) {
    auto hashes=coldCompletedHashes(package);
    for(auto i=hashes.begin();i!=hashes.end();)
        if(i->first.parent_path().filename()==L"recovery" && i->first.filename()!=L"id.bin") i=hashes.erase(i);
        else ++i;
    return hashes; // All four completed members and every original identity.
}
void coldSealedInspection(const std::filesystem::path& root,
    const std::shared_ptr<const graf::windows::ProtectedCustodyPackagePair>& pair,std::string_view session,
    const std::shared_ptr<const std::atomic<bool>>& cancel,const std::string& privacy,bool checkPrivacy=true) {
    using namespace graf::windows;
    auto proof=LocalRecordingPackage::inspectProtected(root,pair,session,cancel);
    assert(proof.ok() && (*proof.value)->evidence().integrity==PackageIntegrity::degraded &&
        (*proof.value)->evidence().manifestSessionMatched && (*proof.value)->evidence().durationMs==1000 &&
        (*proof.value)->evidence().playback.decodedFrames && (*proof.value)->evidence().startedAtMs==1000 &&
        (*proof.value)->evidence().stoppedAtMs==1500);
    if(checkPrivacy) {
        assert((*proof.value)->evidence().displayTimezoneOffsetMinutes==180);
        proof.value.reset();
        auto readers=openProtectedCustodyReaders(root,pair,cancel); assert(readers.ok());
        unsigned manifests=0;
        for(std::size_t i=0;i<pair->current().refCount;++i) {
            const auto& ref=pair->current().refs[i];
            if(ref.role!=CustodyRole::manifest) continue;
            assert(ref.length && *ref.length<=65536);
            CustodyBytes bytes(static_cast<std::size_t>(*ref.length)); ULONG got=0;
            assert((*readers.value)[pair->selectedSlot()][i].stream->Read(bytes.data(),static_cast<ULONG>(bytes.size()),&got)==S_OK && got==bytes.size());
            const std::string_view text(reinterpret_cast<const char*>(bytes.data()),bytes.size());
            assert(text.find("\"privacySegments\":"+privacy)!=std::string_view::npos); ++manifests;
        }
        assert(manifests==1);
    }
}
void coldPlaybackRefusals(const std::vector<RecoveryEvent>& events) {
    using namespace graf::windows;
    constexpr auto session="44444444-4444-4444-8444-444444444444";
    const auto idle=CustodyOwnedMemory::usedBytes();
    for(unsigned fault=0;fault<10;++fault) {
        testing::GeneratedRecordingRoot paths; coldCrashFixture(paths.root);
        const RecoveryEvent wanted=fault==6 ? RecoveryEvent{4,2} : RecoveryEvent{2,6};
        unsigned cut=0;
        for(unsigned i=0;i<events.size();++i)
            if(events[i].role==wanted.role && events[i].operation==wanted.operation) { cut=i+1; break; }
        assert(cut); crashRecoveryAt(paths.root,cut,wanted);
        const auto custody=paths.root/session/L".custody-v1";
        const auto playback=custody/L"playback"/L"content.packed-v2";
        if(fault!=6) {
            const auto proof=coldPackedProof(paths.root,session,L"playback",CustodyRole::playback);
            assert(proof->logicalBytes()>0 && proof->logicalBytes()<ProtectedPackedCustodyFormat::blockBytes);
        }
        const auto flip=[](const std::filesystem::path& path,std::streamoff offset) {
            std::fstream file(path,std::ios::in|std::ios::out|std::ios::binary); assert(file);
            char byte=0; file.seekg(offset); assert(file.read(&byte,1));
            byte^=1; file.seekp(offset); assert(file.write(&byte,1));
        };
        if(fault==0) {
            // Valid live canonical, same identities/history/length, but no longer
            // the PCM used by the otherwise valid, already existing WAV/AAC.
            auto proof=coldPackedProof(paths.root,session,L"canonical",CustodyRole::canonical,CustodyFileAccess::writeExisting);
            auto writer=ProtectedCustodyWriter::open(proof,std::make_shared<std::atomic<bool>>(false)); assert(writer.ok());
            const float sample=0.5F;
            assert((*writer.value)->writeAt(0,&sample,sizeof(sample)).ok());
            assert((*writer.value)->checkpoint().state==CustodyCommitState::committed);
        } else if(fault==1) {
            std::ofstream tail(custody/L"media"/L"content.packed-v2",std::ios::binary|std::ios::app); assert(tail.put('x'));
        } else if(fault==2) flip(playback,128);
        else if(fault==3) std::filesystem::resize_file(playback,16576); // Partial second HEAD.
        else if(fault==4) flip(playback,ProtectedPackedCustodyFormat::appendOffset); // First reachable DATA.
        else if(fault==5) { std::ofstream extra(custody/L"playback"/L"extra.bin",std::ios::binary); assert(extra.put('x')); }
        else if(fault==7) flip(custody/L"playback"/L"id.bin",0);
        else if(fault==8) {
            unsigned changed=0;
            for(const auto& e:std::filesystem::directory_iterator(custody/L"manifest"))
                if(e.path().filename().wstring().find(L"block.")==0) { flip(e.path(),0); ++changed; }
            assert(changed && "manifest_history_fault_must_corrupt_real_envelopes");
        }
        const auto before=coldHashes(paths.root);
        {
            auto cancel=std::make_shared<std::atomic<bool>>(false);
            auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
            if(fault==9) cancel->store(true);
            auto refused=V5LocalRecordingWriter::recover(*store.value,session,cancel);
            assert(!refused.ok() && refused.error!=CustodyFileError::none);
            std::fprintf(stderr,"COLD_PLAYBACK_REFUSAL case=%u error=%u native=%08x\n",fault,static_cast<unsigned>(refused.error),refused.nativeError);
        }
        assert(coldHashes(paths.root)==before && CustodyOwnedMemory::usedBytes()==idle);
    }
}
std::string coldShortPlaybackBytes(const std::filesystem::path& path,std::uint64_t originalEof) {
    using graf::windows::ProtectedPackedCustodyFormat;
    // Only the generated one-second fixture: exclude the two mutable HEAD cells.
    assert(originalEof>=ProtectedPackedCustodyFormat::appendOffset && originalEof<1024*1024);
    std::ifstream input(path,std::ios::binary); assert(input);
    std::string bytes(128+static_cast<std::size_t>(originalEof-ProtectedPackedCustodyFormat::appendOffset),'\0');
    input.read(bytes.data(),128); assert(input.gcount()==128);
    input.seekg(ProtectedPackedCustodyFormat::appendOffset); assert(input);
    input.read(bytes.data()+128,static_cast<std::streamsize>(bytes.size()-128));
    assert(input.gcount()==static_cast<std::streamsize>(bytes.size()-128));
    return bytes;
}
auto coldPlaybackExtentHashes(const std::filesystem::path& path,std::uint64_t originalEof) {
    using graf::windows::ProtectedPackedCustodyFormat;
    assert(originalEof>=ProtectedPackedCustodyFormat::appendOffset && std::filesystem::file_size(path)>=originalEof);
    std::ifstream input(path,std::ios::binary); assert(input);
    std::array<char,65536> buffer{};
    std::vector<std::string> hashes;
    input.read(buffer.data(),128); assert(input.gcount()==128);
    hashes.push_back(graf::windows::sha256(std::string_view(buffer.data(),128)));
    input.seekg(ProtectedPackedCustodyFormat::appendOffset); assert(input);
    // Hash ALL old ciphertext through actual EOF, excluding only mutable HEADs.
    for(auto at=ProtectedPackedCustodyFormat::appendOffset;at<originalEof;) {
        const auto count=static_cast<std::streamsize>((std::min<std::uint64_t>)(buffer.size(),originalEof-at));
        input.read(buffer.data(),count); assert(input.gcount()==count);
        hashes.push_back(graf::windows::sha256(std::string_view(buffer.data(),static_cast<std::size_t>(count))));
        at+=static_cast<std::uint64_t>(count);
    }
    return hashes;
}
void coldRecoveryPlaybackPartial() {
    using namespace graf::windows;
    const auto started=GetTickCount64();
    const auto phase=[&](const char* name) {
        const auto error=GetLastError();
        std::fprintf(stderr,"COLD_PARTIAL_PHASE name=%s elapsed_ms=%llu\n",name,static_cast<unsigned long long>(GetTickCount64()-started));
        std::fflush(stderr);
        SetLastError(error);
    };
    constexpr auto session="44444444-4444-4444-8444-444444444444";
    const std::string privacy="[{\"segmentId\":\"original-segment\",\"sessionId\":\""+std::string(session)+
        "\",\"control\":\"pause\",\"startedAt\":\"2026-01-01T00:00:00Z\",\"startMonotonicMs\":100,"
        "\"endedAt\":\"2026-01-01T00:00:01Z\",\"endMonotonicMs\":1100,\"durationMs\":1000,"
        "\"localMicTreatment\":\"silenced\",\"initiator\":\"user\",\"diagnosticSafe\":true}]";
    const auto idle=CustodyOwnedMemory::usedBytes();
    std::uint64_t completeBytes=0;
    phase("baseline_fixture_begin");
    {
        testing::GeneratedRecordingRoot paths; coldCrashFixture(paths.root,privacy,false,6000);
        phase("baseline_fixture_ready");
        {
            auto cancel=std::make_shared<std::atomic<bool>>(false);
            auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
            armRecoveryTrace(paths.root,0);
            phase("baseline_prepare_begin");
            auto prepared=V5RecoveryTestPeer::prepare(*store.value,session,cancel); assert(prepared.ok());
            phase("baseline_prepared");
            auto recovered=V5RecoveryTestPeer::finish(std::move(*prepared.value));
            phase("baseline_finished");
            recoveryWatchedRoot.clear();
            assert(recovered.ok() && (*recovered.value)->finalize().semanticVerified);
        }
        phase("baseline_recovered");
        completeBytes=coldPackedProof(paths.root,session,L"playback",CustodyRole::playback)->logicalBytes();
        assert(completeBytes>2*ProtectedPackedCustodyFormat::blockBytes);
    }
    const auto events=recoveryEvents;
    unsigned cut=0, heads=0;
    for(unsigned i=0;i<events.size();++i)
        if(events[i].role==2 && events[i].operation==6 && ++heads==2) { cut=i+1; break; }
    assert(cut && "long_fixture_requires_second_actual_committed_playback_HEAD");
    phase("partial_fixture_begin");
    testing::GeneratedRecordingRoot paths; coldCrashFixture(paths.root,privacy,false,6000);
    phase("partial_fixture_ready");
    const auto original=coldOriginalHashes(paths.root/session);
    const auto queue=coldHashes(paths.root/L".custody-v1");
    crashRecoveryAt(paths.root,cut,events[cut-1]);
    phase("child_reached_cut");
    const auto before=coldHashes(paths.root);
    const auto custody=paths.root/session/L".custody-v1";
    const auto playback=custody/L"playback"/L"content.packed-v2";
    const auto mediaHash=sha256File(custody/L"media"/L"content.packed-v2");
    const auto oldEof=std::filesystem::file_size(playback);
    const auto oldBytes=coldPlaybackExtentHashes(playback,oldEof);
    std::uint64_t oldGeneration=0, partialBytes=0;
    {
        auto proof=coldPackedProof(paths.root,session,L"playback",CustodyRole::playback);
        oldGeneration=proof->generation(); partialBytes=proof->logicalBytes();
        assert(partialBytes>ProtectedPackedCustodyFormat::blockBytes && partialBytes<completeBytes);
        auto cancel=std::make_shared<std::atomic<bool>>(false);
        const auto decoded=LocalRecordingPackage::readProtectedPlayback(proof,60000,cancel);
        std::fprintf(stderr,"COLD_PARTIAL_OLD bytes=%llu complete_bytes=%llu generation=%llu decode_error=%u native=%08x\n",
            static_cast<unsigned long long>(partialBytes),static_cast<unsigned long long>(completeBytes),
            static_cast<unsigned long long>(oldGeneration),static_cast<unsigned>(decoded.error),decoded.nativeError);
        assert(!decoded.ok() && !cancel->load() &&
            ((decoded.error==CustodyFileError::invalidContent && decoded.nativeError==static_cast<std::uint32_t>(MF_E_INVALIDMEDIATYPE)) ||
             (decoded.error==CustodyFileError::ioFailed && (decoded.nativeError==static_cast<std::uint32_t>(MF_E_INVALID_FILE_FORMAT) ||
              decoded.nativeError==static_cast<std::uint32_t>(MF_E_UNSUPPORTED_BYTESTREAM_TYPE)))) &&
            "partial_AAC_requires_codec_content_failure_not_arbitrary_IO_or_quota");
    }
    assert(coldHashes(paths.root)==before);
    phase("old_partial_proved");
    {
        auto cancel=std::make_shared<std::atomic<bool>>(false);
        auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
        phase("partial_prepare_begin");
        auto prepared=V5RecoveryTestPeer::prepare(*store.value,session,cancel); assert(prepared.ok());
        phase("partial_prepared");
        auto recovered=V5RecoveryTestPeer::finish(std::move(*prepared.value));
        phase("partial_finished");
        assert(recovered.ok() && "verified_long_partial_AAC_must_recover");
        const auto result=(*recovered.value)->finalize();
        assert(result.semanticVerified && result.trustedPrefixRetained && result.durationMs==60000 &&
            result.packagePhase==CustodyPackagePhase::sealedDegraded && !result.normalPackage() && !result.keepablePackage());
    }
    phase("partial_recovered");
    assert(coldOriginalHashes(paths.root/session)==original && coldHashes(paths.root/L".custody-v1")==queue);
    assert(sha256File(custody/L"media"/L"content.packed-v2")==mediaHash);
    assert(std::filesystem::file_size(playback)>oldEof && coldPlaybackExtentHashes(playback,oldEof)==oldBytes);
    phase("old_extent_and_originals_verified");
    const auto sealed=coldHashes(paths.root);
    phase("sealed_hashes_ready");
    {
        auto cancel=std::make_shared<std::atomic<bool>>(false);
        auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
        phase("cold_store_opened");
        auto pair=(*store.value)->readPackage(session,cancel); assert(pair.ok());
        phase("cold_pair_read");
        unsigned found=0;
        for(std::size_t i=0;i<(*pair.value)->current().refCount;++i) {
            const auto& ref=(*pair.value)->current().refs[i];
            if(ref.role==CustodyRole::playback) { assert(ref.sealed && ref.generation && *ref.generation>oldGeneration); ++found; }
        }
        assert(found==1);
        phase("cold_inspection_begin");
        auto proof=LocalRecordingPackage::inspectProtected(paths.root,*pair.value,session,cancel); assert(proof.ok());
        phase("cold_inspection_complete");
        const auto& evidence=(*proof.value)->evidence();
        assert(evidence.integrity==PackageIntegrity::degraded && evidence.durationMs==60000 && evidence.playback.decodedFrames &&
            evidence.manifestSessionMatched && evidence.startedAtMs==1000 && evidence.stoppedAtMs==1500 &&
            evidence.displayTimezoneOffsetMinutes==180);
        proof.value.reset();
        auto readers=openProtectedCustodyReaders(paths.root,*pair.value,cancel); assert(readers.ok());
        unsigned manifests=0;
        for(std::size_t i=0;i<(*pair.value)->current().refCount;++i) {
            const auto& ref=(*pair.value)->current().refs[i];
            if(ref.role!=CustodyRole::manifest) continue;
            assert(ref.length && *ref.length<=65536);
            CustodyBytes bytes(static_cast<std::size_t>(*ref.length)); ULONG got=0;
            assert((*readers.value)[(*pair.value)->selectedSlot()][i].stream->Read(bytes.data(),static_cast<ULONG>(bytes.size()),&got)==S_OK && got==bytes.size());
            const std::string_view text(reinterpret_cast<const char*>(bytes.data()),bytes.size());
            assert(text.find("\"privacySegments\":"+privacy)!=std::string_view::npos); ++manifests;
        }
        assert(manifests==1);
        phase("privacy_reinspected");
    }
    assert(coldHashes(paths.root)==sealed && CustodyOwnedMemory::usedBytes()==idle);
    phase("readonly_and_idle_verified");
    {std::array<CustodyNativeJob,4> jobs;for(const auto& job:jobs) assert(job);}
    {std::array<CustodyPin,32> pins;for(const auto& pin:pins) assert(pin);}
    std::fprintf(stderr,"COLD_PARTIAL_RECOVERED cut=%u role=2 operation=6 child_exit=88 duration_ms=60000 immutable_old_extent=1 readonly_unchanged=1 audio=0 network=0\n",cut);
}
void coldRecoveryCrashCuts(ColdRecoveryCuts selected=ColdRecoveryCuts::all) {
    using namespace graf::windows;
    const bool wavOnly=selected==ColdRecoveryCuts::wav, playbackOnly=selected==ColdRecoveryCuts::playback;
    const bool terminalOnly=selected==ColdRecoveryCuts::terminalUnused;
    const bool repeated=selected==ColdRecoveryCuts::playbackRestart || terminalOnly;
    constexpr auto session="44444444-4444-4444-8444-444444444444";
    const std::string privacy=repeated ? "[{\"segmentId\":\"original-segment\",\"sessionId\":\""+std::string(session)+
        "\",\"control\":\"pause\",\"startedAt\":\"2026-01-01T00:00:00Z\",\"startMonotonicMs\":100,"
        "\"endedAt\":\"2026-01-01T00:00:01Z\",\"endMonotonicMs\":1100,\"durationMs\":1000,"
        "\"localMicTreatment\":\"silenced\",\"initiator\":\"user\",\"diagnosticSafe\":true}]" : "[]";
    unsigned initialPlaybackCut=0;
    for(unsigned pass=0;pass<(repeated?2U:1U);++pass) {
        testing::GeneratedRecordingRoot paths; coldCrashFixture(paths.root,privacy);
        if(pass) crashRecoveryAt(paths.root,initialPlaybackCut,{2,6});
        auto cancel=std::make_shared<std::atomic<bool>>(false);
        auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
        armRecoveryTrace(paths.root,0);
        auto recovered=V5LocalRecordingWriter::recover(*store.value,session,cancel);
        recoveryWatchedRoot.clear();
        assert(recovered.ok() && (*recovered.value)->finalize().trustedPrefixRetained);
        if(repeated && !pass) {
            for(unsigned i=0;i<recoveryEvents.size();++i)
                if(recoveryEvents[i].role==2 && recoveryEvents[i].operation==6) { initialPlaybackCut=i+1; break; }
            assert(initialPlaybackCut);
        }
    }
    const auto events=recoveryEvents;
    assert(!events.empty());
    if(repeated) {
        // Fixed plan462-U1/468-U2 oracle, checked BEFORE any crash result is observed.
        constexpr std::array<RecoveryEvent,19> expected{{{2,1},{2,0},{2,5},{2,6},{2,4},{2,5},{2,6},
            {5,2},{5,3},{3,2},{3,3},{5,2},{5,3},{4,2},{4,3},{4,2},{4,3},{5,2},{5,3}}};
        assert(events.size()==expected.size());
        for(std::size_t i=0;i<expected.size();++i)
            assert(events[i].role==expected[i].role && events[i].operation==expected[i].operation);
    } else assert(events.size()==24 && events[0].role==5 && events[0].operation==2 &&
        events[1].role==5 && events[1].operation==3);
    std::array<unsigned,6> renameCounts{};
    std::array<std::array<unsigned,7>,6> shape{};
    std::size_t playbackBegin=events.size(), manifestBegin=events.size();
    for(const auto& event:events) {
        const auto ordinal=static_cast<std::size_t>(&event-events.data());
        if(event.role==2 && playbackBegin==events.size()) playbackBegin=ordinal;
        if(event.role==3 && manifestBegin==events.size()) manifestBegin=ordinal;
        ++shape[event.role][event.operation];
        if(event.operation==2) ++renameCounts[event.role];
        std::fprintf(stderr,"COLD_RECOVERY_TRACE ordinal=%zu role=%u operation=%u\n",static_cast<std::size_t>(&event-events.data()+1),event.role,event.operation);
    }
    assert(renameCounts[3] && renameCounts[4]==2 && renameCounts[5]>=2);
    for(const auto role:{3U,4U,5U}) assert(shape[role][2]==shape[role][3]);
    for(const auto role:{1U,2U}) {
        if(repeated && role==1) { for(const auto count:shape[role]) assert(count==0); }
        else assert(shape[role][0]==1 && shape[role][1]==1 && shape[role][4]==1 && shape[role][5] && shape[role][5]==shape[role][6]);
    }
    assert(playbackBegin<manifestBegin && manifestBegin-playbackBegin==(repeated?9U:7U));
    if(playbackOnly) coldPlaybackRefusals(events);
    const auto idle=CustodyOwnedMemory::usedBytes();
    unsigned sealedCold=0, continued=0, unusedRecovered=0, refused=0, rebuilt=0, completedCount=0, terminalCount=0;
    for(unsigned cut=1;cut<=events.size();++cut) {
        // Process crash preserves OS cache; op5 may leave a complete HEAD
        // without a prior flush/checkpoint ACK. Both cuts require fresh proof,
        // not power-loss durability. Keep tests-first filtered CLI at op6.
        const bool wavReady=events[cut-1].role==1 &&
            (events[cut-1].operation==5 || events[cut-1].operation==6);
        // Complete birth is one native write of prefix+BOTH g1 HEADs, so its
        // process-crash cut is valid empty playback, not incomplete birth.
        // AAC birth/append/HEAD and old-history retire before manifest publish
        // all require R under plan462; the fresh proof below measures each one.
        const bool playbackReady=!wavOnly && cut-1>=playbackBegin && cut-1<manifestBegin;
        const bool derivedReady=wavReady || playbackReady;
        const bool unusedReady=!repeated && cut<=2; // Initial finalizing publication, no derived member exists yet.
        const bool terminalReady=cut+6==events.size(); // Same shape: repeated13 / original18.
        if(terminalOnly && !terminalReady) continue;
        if(wavOnly && (!wavReady || events[cut-1].operation!=6)) continue;
        if(playbackOnly && (!playbackReady || events[cut-1].role!=2 || events[cut-1].operation!=6)) continue;
        testing::GeneratedRecordingRoot paths; coldCrashFixture(paths.root,privacy);
        const auto canonical=paths.root/session/L".custody-v1"/L"canonical"/L"content.packed-v2";
        const auto canonicalHash=sha256File(canonical);
        const auto originalBefore=coldOriginalHashes(paths.root/session);
        const auto queueBefore=coldHashes(paths.root/L".custody-v1");
        const auto custody=paths.root/session/L".custody-v1";
        const auto media=custody/L"media"/L"content.packed-v2";
        const auto playback=custody/L"playback"/L"content.packed-v2";
        if(repeated) crashRecoveryAt(paths.root,initialPlaybackCut,{2,6});
        const auto firstWavHash=repeated ? sha256File(media) : std::string{};
        const auto firstEof=repeated ? std::filesystem::file_size(playback) : std::uint64_t{0};
        const auto firstPlayback=repeated ? coldShortPlaybackBytes(playback,firstEof) : std::string{};
        std::uint64_t firstGeneration=0;
        if(repeated) {
            const auto proof=coldPackedProof(paths.root,session,L"playback",CustodyRole::playback);
            assert(proof->logicalBytes()>0 && proof->logicalBytes()<ProtectedPackedCustodyFormat::blockBytes);
            firstGeneration=proof->generation();
        } // Release full BOTH proof before the next child takes native ownership.
        crashRecoveryAt(paths.root,cut,events[cut-1]);
        assert(sha256File(canonical)==canonicalHash && coldHashes(paths.root/L".custody-v1")==queueBefore);
        assert(coldOriginalHashes(paths.root/session)==originalBefore);
        const auto afterCrash=coldHashes(paths.root);
        const auto members=coldCompletedHashes(paths.root/session);
        std::uint64_t terminalGeneration=0;
        if(terminalReady) {
            assert(events[cut-1].role==5 && events[cut-1].operation==3);
            terminalGeneration=coldTerminalUnusedShape(paths.root,privacy,cut);
            assert(coldHashes(paths.root)==afterCrash);
        }
        const auto wavHash=derivedReady ? sha256File(media) : std::string{};
        if(repeated) {
            assert(sha256File(media)==firstWavHash && std::filesystem::file_size(playback)>=firstEof &&
                coldShortPlaybackBytes(playback,firstEof)==firstPlayback);
        }
        const auto playbackEof=playbackReady ? std::filesystem::file_size(playback) : std::uint64_t{0};
        const auto playbackBefore=playbackReady ? coldShortPlaybackBytes(playback,playbackEof) : std::string{};
        const auto playbackGeneration=playbackReady ? coldPackedProof(paths.root,session,L"playback",CustodyRole::playback)->generation() : 0;
        if(playbackReady) {
            assert(playbackGeneration && coldHashes(paths.root)==afterCrash);
            if(repeated && cut<=5) {
                const auto proof=coldPackedProof(paths.root,session,L"playback",CustodyRole::playback);
                assert(proof->generation()==firstGeneration+(cut==1?0U:1U));
                assert((proof->logicalBytes()==0)==(cut!=1));
            }
            std::fprintf(stderr,"COLD_PLAYBACK_OLD_GENERATION generation=%llu\n",static_cast<unsigned long long>(playbackGeneration));
        }
        const bool completed=cut+2==events.size() || cut+1==events.size(); // After recovery's second index, before the final seal.
        bool started=false;
        for(const auto role:{L"media",L"playback",L"recovery"})
            for(const auto& e:std::filesystem::directory_iterator(paths.root/session/L".custody-v1"/role))
                if(e.path().filename()!=L"id.bin") started=true;
        {
            auto cancel=std::make_shared<std::atomic<bool>>(false);
            auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
            {
                auto pair=(*store.value)->readPackage(session,cancel);
                if(pair.ok()) {
                    assert((*pair.value)->current().phase!=CustodyPackagePhase::sealedNormal);
                    if((*pair.value)->current().phase==CustodyPackagePhase::sealedDegraded) {
                        ++sealedCold;
                        auto proof=LocalRecordingPackage::inspectProtected(paths.root,*pair.value,session,cancel);
                        assert(proof.ok() && (*proof.value)->evidence().integrity==PackageIntegrity::degraded && (*proof.value)->evidence().durationMs==1000 && (*proof.value)->evidence().playback.decodedFrames);
                    }
                }
            }
            const auto recovered=V5LocalRecordingWriter::recover(*store.value,session,cancel);
            if(completed || derivedReady || terminalReady) {
                if(terminalReady) assert(recovered.ok() && "terminal_bound_unused_recovery_must_finish_without_reencoding");
                if(playbackReady) assert(recovered.ok() && "verified_started_playback_must_rebuild_after_process_crash");
                assert(started && recovered.ok() && "verified_derived_or_terminal_outputs_must_continue_after_process_crash");
                const auto result=(*recovered.value)->finalize();
                assert(result.semanticVerified && result.trustedPrefixRetained && result.packagePhase==CustodyPackagePhase::sealedDegraded &&
                    !result.normalPackage() && !result.keepablePackage() && result.durationMs==1000);
                if(completed) assert(coldCompletedHashes(paths.root/session)==members);
                if(terminalReady) {
                    assert(result.packageGeneration==terminalGeneration+1);
                    assert(coldTerminalOriginalHashes(paths.root/session)==members); ++terminalCount;
                }
                if(derivedReady) assert(sha256File(media)==wavHash);
                if(playbackReady) {
                    assert(std::filesystem::file_size(playback)>playbackEof);
                    assert(coldShortPlaybackBytes(playback,playbackEof)==playbackBefore);
                }
                ++continued;
                if(completed) ++completedCount;
                else if(playbackReady) ++rebuilt;
            } else if(started) {
                assert(!recovered.ok() && "started_outputs_must_not_be_repaired_or_overwritten");
                assert(coldHashes(paths.root)==afterCrash);
                ++refused;
            } else {
                assert(unusedReady && recovered.ok() && "unused_outputs_must_recover_before_derived_birth");
                const auto result=(*recovered.value)->finalize();
                assert(result.semanticVerified && result.trustedPrefixRetained && result.packagePhase==CustodyPackagePhase::sealedDegraded &&
                    !result.normalPackage() && !result.keepablePackage() && result.durationMs==1000);
                ++unusedRecovered;
            }
        }
        assert(sha256File(canonical)==canonicalHash && coldHashes(paths.root/L".custody-v1")==queueBefore);
        assert(coldOriginalHashes(paths.root/session)==originalBefore);
        if(repeated) assert(sha256File(media)==firstWavHash && std::filesystem::file_size(playback)>=firstEof &&
            coldShortPlaybackBytes(playback,firstEof)==firstPlayback);
        const bool accepted=derivedReady || unusedReady || terminalReady || (repeated && (completed || cut==events.size()));
        const auto sealed=accepted ? coldHashes(paths.root) : decltype(afterCrash){};
        if(accepted) {
            auto cancel=std::make_shared<std::atomic<bool>>(false);
            auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
            auto pair=(*store.value)->readPackage(session,cancel); assert(pair.ok());
            if(playbackReady) {
                unsigned found=0;
                for(std::size_t i=0;i<(*pair.value)->current().refCount;++i) {
                    const auto& ref=(*pair.value)->current().refs[i];
                    if(ref.role==CustodyRole::playback) {
                        assert(ref.sealed && ref.generation && *ref.generation>playbackGeneration); ++found;
                    }
                }
                assert(found==1);
            }
            coldSealedInspection(paths.root,*pair.value,session,cancel,privacy,repeated);
        }
        if(accepted) assert(coldHashes(paths.root)==sealed);
        assert(CustodyOwnedMemory::usedBytes()==idle);
        std::fprintf(stderr,"COLD_RECOVERY_CUT ordinal=%u role=%u operation=%u child_exit=88 waited=1 canonical_queue_unchanged=1 started=%u continued=%u wav_ready=%u playback_started=%u unused_ready=%u terminal_unused=%u\n",cut,events[cut-1].role,events[cut-1].operation,started?1U:0U,(completed||derivedReady||unusedReady||terminalReady)?1U:0U,wavReady?1U:0U,playbackReady?1U:0U,unusedReady?1U:0U,terminalReady?1U:0U);
    }
    {std::array<CustodyNativeJob,4> jobs;for(const auto& job:jobs) assert(job);}
    {std::array<CustodyPin,32> pins;for(const auto& pin:pins) assert(pin);}
    assert((terminalOnly ? !sealedCold && !rebuilt && !completedCount && !refused && continued==1 && terminalCount==1 && !unusedRecovered :
        repeated ? sealedCold==1 && rebuilt==9 && completedCount==2 && refused==7 && continued==12 && terminalCount==1 && !unusedRecovered :
        (wavOnly||playbackOnly) ? !sealedCold && continued==1 && !unusedRecovered : sealedCold && continued==12 && terminalCount==1 && unusedRecovered==2) &&
        "wav_and_terminal_boundaries_must_be_checked");
    if(repeated && !terminalOnly) std::fprintf(stderr,"COLD_REPEATED_CRASH cuts=19 rebuild=9 completed=2 terminal_unused=1 refused=6 sealed_readonly=1 first_child_exit=88 second_child_exit=88 old_extent_unchanged=1 audio=0 network=0\n");
    if(terminalOnly) std::fprintf(stderr,"COLD_TERMINAL_UNUSED cuts=1 continued=1 four_members_ids_queue_unchanged=1 cold_aac_privacy=1 audio=0 network=0\n");
    std::fprintf(stderr,"COLD_RECOVERY_CUTS trace_events=%zu executed_cuts=%zu sealed_cold_decode=%u continued=%u recovered_unused=%u process_crash=1 power_loss=0 audio=0 network=0\n",events.size(),(wavOnly||playbackOnly||terminalOnly)?std::size_t{1}:events.size(),sealedCold,continued,unusedRecovered);
}
void coldTerminalUnusedCrashCuts(bool refusalsOnly=false,bool returnedFaultsOnly=false) {
    using namespace graf::windows;
    constexpr auto session="44444444-4444-4444-8444-444444444444";
    // Empty cache entries retain no allocation; compare recovery with the cold baseline.
    // Measure a standalone Debug proxy independently, without allowing it as a leak.
    const auto cold=CustodyOwnedMemory::usedBytes();
    std::size_t emptyProxy=0;
    {
        CustodyBytes empty;
        assert(empty.empty() && empty.capacity()==0 && CustodyOwnedMemory::usedBytes()>=cold);
        emptyProxy=CustodyOwnedMemory::usedBytes()-cold;
    }
    assert(CustodyOwnedMemory::usedBytes()==cold);
    {
        testing::GeneratedRecordingRoot paths; coldCrashFixture(paths.root);
        assert(CustodyOwnedMemory::usedBytes()==cold);
        const auto proof=coldPackedProof(paths.root,session,L"canonical",CustodyRole::canonical);
        auto cancel=std::make_shared<std::atomic<bool>>(false);
        const auto beforeReader=CustodyOwnedMemory::usedBytes();
        {
            auto reader=openProtectedCustodyReader(proof,cancel);
            assert(reader.ok() && reader.value->state==CustodySnapshotState::verified && reader.value->stream);
        } // Retire the entire result, including its weak reader observation.
        assert(CustodyOwnedMemory::usedBytes()==beforeReader);
    }
    assert(CustodyOwnedMemory::usedBytes()==cold);
    const auto idle=CustodyOwnedMemory::usedBytes();
    std::fprintf(stderr,"COLD_TERMINAL_CACHE cold=%zu empty_proxy=%zu idle=%zu exact=1 reader_content_read=0\n",cold,emptyProxy,idle);
    const std::string privacy="[{\"segmentId\":\"original-segment\",\"sessionId\":\""+std::string(session)+
        "\",\"control\":\"pause\",\"startedAt\":\"2026-01-01T00:00:00Z\",\"startMonotonicMs\":100,"
        "\"endedAt\":\"2026-01-01T00:00:01Z\",\"endMonotonicMs\":1100,\"durationMs\":1000,"
        "\"localMicTreatment\":\"silenced\",\"initiator\":\"user\",\"diagnosticSafe\":true}]";
    // Independent plan468-U2 oracle, fixed before any new crash outcome.
    constexpr std::array<RecoveryEvent,24> original{{{5,2},{5,3},
        {1,0},{1,1},{1,4},{1,5},{1,6},{2,0},{2,1},{2,4},{2,5},{2,6},
        {5,2},{5,3},{3,2},{3,3},{5,2},{5,3},{4,2},{4,3},{4,2},{4,3},{5,2},{5,3}}};
    constexpr unsigned terminalCut=18;
    constexpr std::array<RecoveryEvent,6> expected{{{4,2},{4,3},{4,2},{4,3},{5,2},{5,3}}};
    constexpr std::array<char,6> outcomes{'D','D','D','C','C','S'};
    const auto checkTrace=[](const auto& fixed) {
        assert(recoveryEvents.size()==fixed.size());
        for(std::size_t i=0;i<fixed.size();++i)
            assert(recoveryEvents[i].role==fixed[i].role && recoveryEvents[i].operation==fixed[i].operation);
    };
    {
        testing::GeneratedRecordingRoot paths; coldCrashFixture(paths.root,privacy);
        auto cancel=std::make_shared<std::atomic<bool>>(false);
        auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
        armRecoveryTrace(paths.root,0);
        auto recovered=V5LocalRecordingWriter::recover(*store.value,session,cancel);
        recoveryWatchedRoot.clear();
        assert(recovered.ok() && (*recovered.value)->finalize().trustedPrefixRetained);
        checkTrace(original);
        assert(original[terminalCut-1].role==5 && original[terminalCut-1].operation==3);
    }
    std::fprintf(stderr,"COLD_TERMINAL_MEMORY phase=normal_baseline idle=%zu actual=%zu\n",idle,CustodyOwnedMemory::usedBytes());
    const auto prepareTerminal=[&](const std::filesystem::path& root) {
        coldCrashFixture(root,privacy);
        const auto originalIds=coldOriginalHashes(root/session), queue=coldHashes(root/L".custody-v1");
        crashRecoveryAt(root,terminalCut,original[terminalCut-1]);
        assert(coldOriginalHashes(root/session)==originalIds && coldHashes(root/L".custody-v1")==queue);
        return coldTerminalUnusedShape(root,privacy,terminalCut);
    };
    {
        testing::GeneratedRecordingRoot paths;
        const auto generation=prepareTerminal(paths.root);
        const auto members=coldTerminalOriginalHashes(paths.root/session), queue=coldHashes(paths.root/L".custody-v1");
        {
            auto cancel=std::make_shared<std::atomic<bool>>(false);
            auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
            armRecoveryTrace(paths.root,0); // Fixture child/events are NOT part of U's trace.
            auto recovered=V5LocalRecordingWriter::recover(*store.value,session,cancel);
            recoveryWatchedRoot.clear();
            assert(recovered.ok());
            const auto result=(*recovered.value)->finalize();
            assert(result.semanticVerified && result.trustedPrefixRetained && !result.normalPackage() && !result.keepablePackage() &&
                result.packagePhase==CustodyPackagePhase::sealedDegraded && result.packageGeneration==generation+1 && result.durationMs==1000);
            checkTrace(expected); // No audio/manifest publication or extra metadata event is allowed.
        }
        assert(coldTerminalOriginalHashes(paths.root/session)==members && coldHashes(paths.root/L".custody-v1")==queue);
        const auto sealed=coldHashes(paths.root);
        {
            auto cancel=std::make_shared<std::atomic<bool>>(false);
            auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
            auto pair=(*store.value)->readPackage(session,cancel); assert(pair.ok());
            coldSealedInspection(paths.root,*pair.value,session,cancel,privacy);
        }
        assert(coldHashes(paths.root)==sealed);
    } // Both baseline traces/semantic checks finish BEFORE the six crash cases.
    std::fprintf(stderr,"COLD_TERMINAL_MEMORY phase=terminal_baseline idle=%zu actual=%zu\n",idle,CustodyOwnedMemory::usedBytes());
    assert(CustodyOwnedMemory::usedBytes()==idle);
    if(returnedFaultsOnly) {
        constexpr std::array<RecoveryEvent,14> faults{{{4,0},{4,1},{4,2},{4,3},{4,2,2},{4,3,4},
            {5,0,4},{5,1,4},{5,2,4},{5,3,6},{0,7,4},{0,7,6},{0,8,6},{0,9,4}}};
        for(unsigned n=0;n<faults.size();++n) {
            {
                testing::GeneratedRecordingRoot paths; prepareTerminal(paths.root);
                const auto members=coldTerminalOriginalHashes(paths.root/session), queue=coldHashes(paths.root/L".custody-v1");
                decltype(coldHashes(paths.root)) afterFailure;
                {
                    auto cancel=std::make_shared<std::atomic<bool>>(false);
                    auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
                    auto prepared=V5RecoveryTestPeer::prepare(*store.value,session,cancel); assert(prepared.ok());
                    auto writer=*prepared.value;
                    auto package=writer->package(); assert(package && package->reference(CustodyRole::canonical).ok());
                    prepared.value.reset(); // Only the genuine retained writer/package, never a fresh reopen.
                    const auto fault=faults[n];
                    armRecoveryTrace(paths.root,0);
                    recoveryFault=fault; recoveryFaultHits=0;
                    recoveryReadAfterEvent=fault.operation>=7 ? fault.afterEvent : 0;
                    recoveryReadArmed=false; recoveryReadCancellation=cancel.get();
                    const auto failed=V5RecoveryTestPeer::finish(writer);
                    assert(recoveryFaultHits==1 && !failed.ok() && !failed.value && failed.error!=CustodyFileError::none);
                    const auto native=fault.operation==2 || fault.operation==3 ? 0xc000007fUL :
                        fault.operation==8 ? ERROR_OPERATION_ABORTED : fault.operation==7 || fault.operation==9 ? ERROR_READ_FAULT :
                        fault.operation==1 ? ERROR_WRITE_FAULT : ERROR_DISK_FULL;
                    assert(failed.nativeError==native || failed.nativeError==static_cast<std::uint32_t>(HRESULT_FROM_WIN32(native)));
                    assert(cancel->load()==(fault.operation==8));
                    if(fault.afterEvent>=4) {
                        assert(recoveryEvents.size()>=4);
                        for(unsigned i=0;i<4;++i)
                            assert(recoveryEvents[i].role==expected[i].role && recoveryEvents[i].operation==expected[i].operation);
                        const auto recovery=paths.root/session/L".custody-v1"/L"recovery";
                        assert(std::filesystem::is_regular_file(recovery/L"index.0") && std::filesystem::is_regular_file(recovery/L"index.1"));
                    } // These faults occur after actual BOTH recovery index publication.
                    recoveryFault={99,99}; recoveryReadAfterEvent=0; recoveryReadCancellation=nullptr;
                    cancel->store(false); // Subsequent refusals must be sticky, not an active IO fault/cancel.
                    afterFailure=coldHashes(paths.root);
                    const auto events=recoveryEvents.size();
                    const auto unchanged=[&] { assert(recoveryEvents.size()==events && coldHashes(paths.root)==afterFailure); };
                    const auto retry=V5RecoveryTestPeer::finish(writer);
                    assert(!retry.ok() && !retry.value && retry.error==CustodyFileError::invalidInput);
                    unchanged();
                    const auto identity=package->reference(CustodyRole::canonical);
                    assert(!identity.ok() && identity.error==CustodyFileError::recoveryRequired); unchanged();
                    const auto pair=package->readPair();
                    assert(!pair.ok() && pair.error==CustodyFileError::recoveryRequired); unchanged();
                    const auto output=package->createWriter(CustodyRole::media);
                    assert(!output.ok() && output.error==CustodyFileError::recoveryRequired); unchanged();
                    const auto metadata=package->commitMetadata(CustodyRole::recovery,CustodyBytes{'x'});
                    assert(metadata.state==CustodyCommitState::notCommitted && !metadata.snapshot && metadata.error==CustodyFileError::recoveryRequired); unchanged();
                    auto candidate=package->current(); ++candidate.generation;
                    const auto state=package->commit(candidate);
                    assert(state.state==CustodyCommitState::notCommitted && !state.snapshot && state.error==CustodyFileError::recoveryRequired); unchanged();
                    assert(writer->package().get()==package.get() && !writer->healthy());
                    assert(recoveryEvents.size()==events && coldHashes(paths.root)==afterFailure);
                    assert(coldTerminalOriginalHashes(paths.root/session)==members && coldHashes(paths.root/L".custody-v1")==queue);
                    recoveryWatchedRoot.clear();
                    std::fprintf(stderr,"COLD_TERMINAL_STICKY case=%u role=%u operation=%u after_event=%u hit=1 error=%u native=%08x same_writer=1 same_package=1 sticky_refusals=5 no_retry_effect=1\n",
                        n,fault.role,fault.operation,fault.afterEvent,static_cast<unsigned>(failed.error),failed.nativeError);
                } // Include destruction of the failed writer/package and their retained proofs.
                assert(coldHashes(paths.root)==afterFailure && coldTerminalOriginalHashes(paths.root/session)==members && coldHashes(paths.root/L".custody-v1")==queue);
            }
            assert(CustodyOwnedMemory::usedBytes()==idle);
            {std::array<CustodyNativeJob,4> jobs;for(const auto& job:jobs) assert(job);}
            {std::array<CustodyPin,32> pins;for(const auto& pin:pins) assert(pin);}
        }
        std::fprintf(stderr,"COLD_TERMINAL_STICKY cases=14 same_package=1 exact_memory=1 four_members_ids_queue_unchanged=1 jobs_pins_returned=1 audio=0 network=0\n");
        return;
    }
    if(refusalsOnly) {
        constexpr std::array<const char*,10> names{"canonical_pcm","non_finite_prefix","wav_pcm","unknown_extent",
            "aac_data","canonical_data","recovery_orphan","recovery_singleton","cancelled","manifest_unbound"};
        for(unsigned fault=0;fault<names.size();++fault) {
            {
                assert(recoveryWatchedRoot.empty());
                testing::GeneratedRecordingRoot paths; prepareTerminal(paths.root);
                const auto custody=paths.root/session/L".custody-v1";
                if(fault<3) {
                    {
                        const auto role=fault==2 ? CustodyRole::media : CustodyRole::canonical;
                        const auto proof=coldPackedProof(paths.root,session,fault==2 ? L"media" : L"canonical",role,CustodyFileAccess::writeExisting);
                        auto writer=ProtectedCustodyWriter::open(proof,std::make_shared<std::atomic<bool>>(false)); assert(writer.ok());
                        if(fault==2) {
                            const std::int16_t sample=0;
                            assert((*writer.value)->writeAt(44,&sample,sizeof(sample)).ok());
                        } else {
                            const float sample=fault==0 ? 0.5F : std::numeric_limits<float>::quiet_NaN();
                            assert((*writer.value)->writeAt(fault==0 ? 0 : 67200,&sample,sizeof(sample)).ok());
                        }
                        assert((*writer.value)->checkpoint().state==CustodyCommitState::committed);
                        assert((*writer.value)->size()==proof->logicalBytes());
                    }
                    coldTerminalUnusedShape(paths.root,privacy,terminalCut); // Still genuine BOTH closures and bound metadata.
                } else if(fault==3) {
                    const auto file=custody/L"media"/L"content.packed-v2";
                    const auto size=std::filesystem::file_size(file);
                    {std::ofstream tail(file,std::ios::binary|std::ios::app); assert(tail.put('x'));}
                    assert(std::filesystem::file_size(file)==size+1);
                } else if(fault==4 || fault==5) {
                    PackedReference data;
                    const auto name=fault==4 ? L"playback" : L"canonical";
                    {
                        const auto proof=coldPackedProof(paths.root,session,name,fault==4 ? CustodyRole::playback : CustodyRole::canonical,
                            CustodyFileAccess::readExisting,&data);
                        assert(proof->logicalBytes()>0 && data.payloadBytes>0);
                    }
                    std::fstream file(custody/name/L"content.packed-v2",std::ios::in|std::ios::out|std::ios::binary); assert(file);
                    char byte=0; file.seekg(static_cast<std::streamoff>(data.offset)); assert(file.read(&byte,1));
                    byte^=1; file.seekp(static_cast<std::streamoff>(data.offset)); assert(file.write(&byte,1));
                } else if(fault==6) {
                    std::ofstream extra(custody/L"recovery"/L"extra.generated",std::ios::binary); assert(extra.put('x'));
                } else if(fault==7) {
                    assert(expected[1].role==4 && expected[1].operation==3);
                    const auto state=coldHashes(custody/L"package-state");
                    crashRecoveryAt(paths.root,2,expected[1]); // Genuine first-index publication, not fabricated ciphertext.
                    assert(std::filesystem::is_regular_file(custody/L"recovery"/L"index.0") &&
                        !std::filesystem::exists(custody/L"recovery"/L"index.1") && coldHashes(custody/L"package-state")==state);
                } else if(fault==9) {
                    CustodyContext context{}; std::uint64_t generation=0;
                    CustodyBytes bytes;
                    const auto state=coldHashes(custody/L"package-state");
                    auto cancel=std::make_shared<std::atomic<bool>>(false);
                    {
                        auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
                        auto pair=(*store.value)->readPackage(session,cancel); assert(pair.ok());
                        auto readers=openProtectedCustodyReaders(paths.root,*pair.value,cancel); assert(readers.ok());
                        for(std::size_t i=0;i<(*pair.value)->current().refCount;++i) {
                            const auto& ref=(*pair.value)->current().refs[i];
                            if(ref.role==CustodyRole::manifest) {
                                assert(ref.generation && ref.length && *ref.length<=65536); generation=*ref.generation;
                                context={(*pair.value)->current().context.storeId,ref.objectId,ref.role};
                                bytes.resize(static_cast<std::size_t>(*ref.length)); ULONG got=0;
                                assert((*readers.value)[(*pair.value)->selectedSlot()][i].stream->Read(bytes.data(),static_cast<ULONG>(bytes.size()),&got)==S_OK &&
                                    got==bytes.size());
                            }
                        }
                        assert(generation);
                    }
                    const auto committed=commitProtectedCustodyMetadata(paths.root,session,context,generation,bytes,cancel);
                    assert(committed.state==CustodyCommitState::committed && committed.targetGeneration==generation+1 &&
                        coldHashes(custody/L"package-state")==state);
                }
                const auto before=coldHashes(paths.root), queue=coldHashes(paths.root/L".custody-v1");
                {
                    auto cancel=std::make_shared<std::atomic<bool>>(false);
                    auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
                    if(fault==8) cancel->store(true);
                    armRecoveryTrace(paths.root,0);
                    const auto refused=V5LocalRecordingWriter::recover(*store.value,session,cancel);
                    recoveryWatchedRoot.clear();
                    assert(!refused.ok() && !refused.value && refused.error!=CustodyFileError::none);
                    if(fault<3) assert(refused.error==CustodyFileError::invalidContent);
                    if(fault==8) assert(refused.error==CustodyFileError::ioFailed && refused.nativeError==ERROR_OPERATION_ABORTED);
                    assert(recoveryEvents.empty() && coldHashes(paths.root)==before);
                    std::fprintf(stderr,"COLD_TERMINAL_REFUSAL case=%u name=%s error=%u native=%08x publication_events=0\n",
                        fault,names[fault],static_cast<unsigned>(refused.error),refused.nativeError);
                }
                assert(coldHashes(paths.root)==before && coldHashes(paths.root/L".custody-v1")==queue);
            }
            assert(CustodyOwnedMemory::usedBytes()==idle);
            {std::array<CustodyNativeJob,4> jobs;for(const auto& job:jobs) assert(job);}
            {std::array<CustodyPin,32> pins;for(const auto& pin:pins) assert(pin);}
        }
        std::fprintf(stderr,"COLD_TERMINAL_REFUSALS cases=10 semantic=3 unchanged_disk=1 exact_memory=1 jobs_pins_returned=1 audio=0 network=0\n");
        return;
    }
    unsigned refused=0, completed=0, sealedCount=0;
    for(unsigned cut=1;cut<=expected.size();++cut) {
        {
            testing::GeneratedRecordingRoot paths;
            const auto generation=prepareTerminal(paths.root);
            const auto members=coldTerminalOriginalHashes(paths.root/session), queue=coldHashes(paths.root/L".custody-v1");
            crashRecoveryAt(paths.root,cut,expected[cut-1]);
            assert(coldTerminalOriginalHashes(paths.root/session)==members && coldHashes(paths.root/L".custody-v1")==queue);
            const auto afterCrash=coldHashes(paths.root), completedMembers=coldCompletedHashes(paths.root/session);
            {
                auto cancel=std::make_shared<std::atomic<bool>>(false);
                auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
                {
                    auto pair=(*store.value)->readPackage(session,cancel); assert(pair.ok());
                    assert((*pair.value)->current().generation==generation+(outcomes[cut-1]=='S' ? 1U : 0U));
                    assert((*pair.value)->current().phase==(outcomes[cut-1]=='S' ? CustodyPackagePhase::sealedDegraded : CustodyPackagePhase::finalizing));
                    if(outcomes[cut-1]=='S') coldSealedInspection(paths.root,*pair.value,session,cancel,privacy);
                } // Retire readonly pair/readers before a fresh recovery acquisition.
                auto recovered=V5LocalRecordingWriter::recover(*store.value,session,cancel);
                if(outcomes[cut-1]=='C') {
                    assert(recovered.ok() && "complete_U_recovery_BOTH_must_finish_without_reencoding");
                    const auto result=(*recovered.value)->finalize();
                    assert(result.semanticVerified && result.trustedPrefixRetained && !result.normalPackage() && !result.keepablePackage() &&
                        result.packagePhase==CustodyPackagePhase::sealedDegraded && result.packageGeneration==generation+1 && result.durationMs==1000);
                    assert(coldCompletedHashes(paths.root/session)==completedMembers); ++completed;
                } else {
                    assert(!recovered.ok() && recovered.error!=CustodyFileError::none);
                    assert(coldHashes(paths.root)==afterCrash);
                    if(outcomes[cut-1]=='D') ++refused; else ++sealedCount;
                }
            }
            if(outcomes[cut-1]!='C') assert(coldHashes(paths.root)==afterCrash); // Include failed/sealed owner destruction.
            assert(coldTerminalOriginalHashes(paths.root/session)==members && coldHashes(paths.root/L".custody-v1")==queue);
            if(outcomes[cut-1]!='D') {
                const auto sealed=coldHashes(paths.root);
                {
                    auto cancel=std::make_shared<std::atomic<bool>>(false);
                    auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
                    {
                        auto pair=(*store.value)->readPackage(session,cancel); assert(pair.ok());
                        assert((*pair.value)->current().phase==CustodyPackagePhase::sealedDegraded &&
                            (*pair.value)->current().generation==generation+1 && (*pair.value)->current().refCount==5);
                        unsigned recoveries=0;
                        for(std::size_t i=0;i<(*pair.value)->current().refCount;++i) {
                            const auto& ref=(*pair.value)->current().refs[i];
                            if(ref.role==CustodyRole::recovery) { assert(ref.sealed && !ref.packed && ref.generation==1); ++recoveries; }
                        }
                        assert(recoveries==1);
                        coldSealedInspection(paths.root,*pair.value,session,cancel,privacy);
                    }
                    assert(!V5LocalRecordingWriter::recover(*store.value,session,cancel).ok());
                }
                assert(coldHashes(paths.root)==sealed);
            }
            std::fprintf(stderr,"COLD_TERMINAL_UNUSED_CUT ordinal=%u role=%u operation=%u outcome=%c fixture_child_exit=88 U_child_exit=88 four_members_ids_queue_unchanged=1\n",
                cut,expected[cut-1].role,expected[cut-1].operation,outcomes[cut-1]);
        }
        assert(CustodyOwnedMemory::usedBytes()==idle);
        {std::array<CustodyNativeJob,4> jobs;for(const auto& job:jobs) assert(job);}
        {std::array<CustodyPin,32> pins;for(const auto& pin:pins) assert(pin);}
    }
    assert(refused==3 && completed==2 && sealedCount==1);
    std::fprintf(stderr,"COLD_TERMINAL_UNUSED_CRASH cuts=6 refused=3 completed=2 sealed_readonly=1 oracle=DDDCCS exact_memory=1 audio=0 network=0 process_crash=1 power_loss=0\n");
}
void coldWavRefusals() {
    using namespace graf::windows;
    constexpr auto session="44444444-4444-4444-8444-444444444444";
    const auto events=recoveryEvents; // Actual trace from the preceding positive fixture.
    const auto idle=CustodyOwnedMemory::usedBytes();
    for(unsigned fault=0;fault<7;++fault) {
        testing::GeneratedRecordingRoot paths; coldCrashFixture(paths.root,"[]",fault==1);
        if(fault!=1) {
            const RecoveryEvent wanted=fault==4 ? RecoveryEvent{2,0} : fault==5 ? RecoveryEvent{4,2} : RecoveryEvent{1,6};
            unsigned cut=0;
            for(unsigned i=0;i<events.size();++i)
                if(events[i].role==wanted.role && events[i].operation==wanted.operation) { cut=i+1; break; }
            assert(cut); crashRecoveryAt(paths.root,cut,wanted);
        }
        const auto media=paths.root/session/L".custody-v1"/L"media"/L"content.packed-v2";
        if(fault==0) {
            std::ofstream tail(media,std::ios::binary|std::ios::app); assert(tail.put('x'));
        } else if(fault==2) {
            std::fstream peer(media,std::ios::in|std::ios::out|std::ios::binary);
            char byte=0; peer.seekg(128); assert(peer.read(&byte,1));
            byte^=1; peer.seekp(128); assert(peer.write(&byte,1));
        } else if(fault==3) std::filesystem::resize_file(media,16576); // Partial second HEAD.
        else if(fault==4) {
            const auto playback=paths.root/session/L".custody-v1"/L"playback"/L"content.packed-v2";
            {
                const auto proof=coldPackedProof(paths.root,session,L"playback",CustodyRole::playback);
                assert(proof->generation()==1 && proof->logicalBytes()==0);
            }
            std::filesystem::resize_file(playback,16576); // NOW incomplete birth: second HEAD torn.
            assert(std::filesystem::file_size(playback)==16576);
        }
        const auto before=coldHashes(paths.root);
        {
            auto cancel=std::make_shared<std::atomic<bool>>(false);
            auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
            if(fault==6) cancel->store(true);
            auto refused=V5LocalRecordingWriter::recover(*store.value,session,cancel);
            assert(!refused.ok() && refused.error!=CustodyFileError::none);
            std::fprintf(stderr,"COLD_WAV_REFUSAL case=%u error=%u native=%08x\n",fault,static_cast<unsigned>(refused.error),refused.nativeError);
        }
        assert(coldHashes(paths.root)==before && CustodyOwnedMemory::usedBytes()==idle);
    }
    std::fprintf(stderr,"COLD_WAV_REFUSALS cases=7 unknown_tail=1 valid_wrong_pcm=1 invalid_partial_peer=3 started_outputs=1 cancelled=1 unchanged_disk=1 audio=0 network=0\n");
}
void coldRecoveryReturnedFaults(bool playbackStarted=false) {
    using namespace graf::windows;
    constexpr auto session="44444444-4444-4444-8444-444444444444";
    unsigned playbackCut=0;
    for(unsigned pass=0;pass<(playbackStarted?2U:1U);++pass) {
        // The first trace locates the genuine initial playback HEAD. The second
        // measures reset/readback/seal events on an already-started AAC instead.
        testing::GeneratedRecordingRoot paths; coldCrashFixture(paths.root);
        if(pass) crashRecoveryAt(paths.root,playbackCut,{2,6});
        auto cancel=std::make_shared<std::atomic<bool>>(false);
        auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
        armRecoveryTrace(paths.root,0);
        auto recovered=V5LocalRecordingWriter::recover(*store.value,session,cancel);
        recoveryWatchedRoot.clear();
        assert(recovered.ok() && (*recovered.value)->finalize().trustedPrefixRetained);
        if(playbackStarted && !pass) {
            for(unsigned i=0;i<recoveryEvents.size();++i)
                if(recoveryEvents[i].role==2 && recoveryEvents[i].operation==6) { playbackCut=i+1; break; }
            assert(playbackCut);
        }
    }
    const auto sealedEvent=static_cast<unsigned>(recoveryEvents.size());
    assert(sealedEvent && recoveryEvents.back().role==5 && recoveryEvents.back().operation==3);
    unsigned resetReadEvent=0;
    if(playbackStarted) {
        for(unsigned i=0;i<recoveryEvents.size();++i)
            if(recoveryEvents[i].role==2 && recoveryEvents[i].operation==1) { resetReadEvent=i+1; break; }
        // This is the reset's pre-HEAD flush. Its next playback ReadFile is
        // HEAD readback, not a fresh package-open or a canonical read.
        assert(resetReadEvent && resetReadEvent<sealedEvent);
    }
    std::vector<RecoveryEvent> faults;
    for(const auto role:{1U,2U})
        if(!playbackStarted || role==2)
            for(const auto operation:{0U,1U,4U,5U,6U}) faults.push_back({role,operation});
    for(const auto role:{3U,4U,5U})
        for(const auto operation:{0U,1U,2U,3U}) faults.push_back({role,operation});
    faults.push_back({0,7}); // Read fails only AFTER actual sealedDegraded publication.
    faults.push_back({5,2,sealedEvent-1}); // Final seal attempt, not the first finalizing transition.
    faults.push_back({5,3,sealedEvent});
    faults.push_back({0,8}); // Real late cancellation; ReadFile itself is not made to fail.
    if(playbackStarted) {
        faults.push_back({2,7,resetReadEvent});
        faults.push_back({2,8,resetReadEvent});
    }
    assert(faults.size()==(playbackStarted?23U:26U));
    const auto idle=CustodyOwnedMemory::usedBytes();
    for(const auto fault:faults) {
        {
            testing::GeneratedRecordingRoot paths; coldCrashFixture(paths.root);
            if(playbackStarted) crashRecoveryAt(paths.root,playbackCut,{2,6});
            const auto original=coldOriginalHashes(paths.root/session);
            const auto queue=coldHashes(paths.root/L".custody-v1");
            const auto custody=paths.root/session/L".custody-v1";
            const auto playback=custody/L"playback"/L"content.packed-v2";
            const auto oldEof=playbackStarted ? std::filesystem::file_size(playback) : 0;
            const auto oldPlayback=playbackStarted ? coldShortPlaybackBytes(playback,oldEof) : std::string{};
            const auto mediaHash=playbackStarted ? sha256File(custody/L"media"/L"content.packed-v2") : std::string{};
            if(playbackStarted) {
                const auto proof=coldPackedProof(paths.root,session,L"playback",CustodyRole::playback);
                assert(proof->logicalBytes()>0 && proof->logicalBytes()<ProtectedPackedCustodyFormat::blockBytes);
            }
            {
                auto cancel=std::make_shared<std::atomic<bool>>(false);
                auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
                armRecoveryTrace(paths.root,0);
                recoveryFault=fault; recoveryFaultHits=0;
                recoveryFaultReadOffset=0; recoveryFaultReadBytes=0;
                recoveryReadAfterEvent=fault.operation>=7 ? (fault.afterEvent ? fault.afterEvent : sealedEvent) : 0;
                recoveryReadArmed=false;
                recoveryReadCancellation=cancel.get();
                const auto recovered=V5LocalRecordingWriter::recover(*store.value,session,cancel);
                recoveryWatchedRoot.clear(); recoveryFault={99,99}; recoveryReadAfterEvent=0; recoveryReadCancellation=nullptr;
                std::fprintf(stderr,"COLD_RECOVERY_RETURN role=%u operation=%u after_event=%u hit=%u rejected=%u error=%u native=%08x\n",
                    fault.role,fault.operation,fault.afterEvent,recoveryFaultHits,recovered.ok()?0U:1U,
                    static_cast<unsigned>(recovered.error),recovered.nativeError);
                assert(recoveryFaultHits==1 && "returned_fault_must_hit_real_IO_not_an_early_guard");
                if(playbackStarted && fault.role==2 && fault.operation>=7)
                    assert((recoveryFaultReadOffset==128 || recoveryFaultReadOffset==16512) &&
                        recoveryFaultReadBytes==16384 && "reset_fault_must_hit_actual_HEAD_readback");
                assert(!recovered.ok() && recovered.error!=CustodyFileError::none &&
                    "failed_recovery_must_not_publish_an_accepted_playable_result");
                const auto expected=fault.operation==2 || fault.operation==3 ? 0xc000007fUL :
                    fault.operation==8 ? ERROR_OPERATION_ABORTED : fault.operation==7 ? ERROR_READ_FAULT :
                    fault.operation==1 || fault.operation==6 ? ERROR_WRITE_FAULT : ERROR_DISK_FULL;
                assert(cancel->load()==(fault.operation==8));
                assert((recovered.nativeError==expected ||
                    recovered.nativeError==static_cast<std::uint32_t>(HRESULT_FROM_WIN32(expected))) &&
                    "physical_native_error_must_not_be_replaced_by_generic_conflict");
            } // Release actual failed owner before cold reopen; no retry on a poisoned lease.
            assert(coldOriginalHashes(paths.root/session)==original && coldHashes(paths.root/L".custody-v1")==queue);
            if(playbackStarted) {
                assert(sha256File(custody/L"media"/L"content.packed-v2")==mediaHash);
                assert(std::filesystem::file_size(playback)>=oldEof && coldShortPlaybackBytes(playback,oldEof)==oldPlayback);
            }
            const auto afterFailure=coldHashes(paths.root);
            {
                auto cancel=std::make_shared<std::atomic<bool>>(false);
                auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
                auto pair=(*store.value)->readPackage(session,cancel);
                if(pair.ok()) assert((*pair.value)->current().phase!=CustodyPackagePhase::sealedNormal);
                if(fault.role==5 && fault.afterEvent) assert(pair.ok() && (*pair.value)->current().phase==
                    (fault.operation==2 ? CustodyPackagePhase::finalizing : CustodyPackagePhase::sealedDegraded));
                if((fault.role==0 && fault.operation>=7) || (fault.role==5 && fault.afterEvent==sealedEvent)) {
                    assert(pair.ok() && (*pair.value)->current().phase==CustodyPackagePhase::sealedDegraded);
                    auto proof=LocalRecordingPackage::inspectProtected(paths.root,*pair.value,session,cancel);
                    assert(proof.ok() && (*proof.value)->evidence().integrity==PackageIntegrity::degraded &&
                        (*proof.value)->evidence().durationMs==1000 && (*proof.value)->evidence().playback.decodedFrames &&
                        (*proof.value)->evidence().manifestSessionMatched &&
                        (*proof.value)->evidence().startedAtMs==1000 && (*proof.value)->evidence().stoppedAtMs==1500);
                }
            }
            assert(coldHashes(paths.root)==afterFailure && "cold_observation_must_not_repair_or_remove_artifacts");
        } // Fixture destruction is included in the exact resource assertion.
        assert(CustodyOwnedMemory::usedBytes()==idle);
        {std::array<CustodyNativeJob,4> jobs;for(const auto& job:jobs) assert(job);}
        {std::array<CustodyPin,32> pins;for(const auto& pin:pins) assert(pin);}
    }
    std::fprintf(stderr,"%s cases=%zu exact_memory=1 canonical_ids_queue_unchanged=1 late_seal_cold_decode=1 audio=0 network=0\n",
        playbackStarted ? "COLD_PLAYBACK_RETURNS" : "COLD_RECOVERY_RETURNS",faults.size());
}
void coldRecoveryCompletion() {
    using namespace graf::windows;
    constexpr auto session="44444444-4444-4444-8444-444444444444";
    { // Obtain the real final publication boundary, not a fabricated package.
        testing::GeneratedRecordingRoot paths; coldCrashFixture(paths.root);
        auto cancel=std::make_shared<std::atomic<bool>>(false);
        auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
        armRecoveryTrace(paths.root,0);
        auto recovered=V5LocalRecordingWriter::recover(*store.value,session,cancel);
        recoveryWatchedRoot.clear(); assert(recovered.ok());
    }
    const auto sealedEvent=static_cast<unsigned>(recoveryEvents.size());
    assert(sealedEvent && recoveryEvents.back().role==5 && recoveryEvents.back().operation==3);
    const auto idle=CustodyOwnedMemory::usedBytes();
    for(unsigned fault=0;fault<5;++fault) {
        const std::string privacy="[{\"segmentId\":\"original-segment\",\"sessionId\":\""+std::string(session)+
            "\",\"control\":\"pause\",\"startedAt\":\"2026-01-01T00:00:00Z\",\"startMonotonicMs\":100,"+
            (fault==4 ? "\"endedAt\":\"2026-01-01T00:00:01Z\",\"endMonotonicMs\":1100,\"durationMs\":1000," : "\"durationMs\":0,")+
            "\"localMicTreatment\":\"silenced\",\"initiator\":\"user\",\"diagnosticSafe\":true}]";
        testing::GeneratedRecordingRoot paths; coldCrashFixture(paths.root,privacy);
        {
            auto cancel=std::make_shared<std::atomic<bool>>(false);
            auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
            armRecoveryTrace(paths.root,0); recoveryFault={5,2,sealedEvent-1}; recoveryFaultHits=0;
            const auto failed=V5LocalRecordingWriter::recover(*store.value,session,cancel);
            recoveryWatchedRoot.clear(); recoveryFault={99,99};
            assert(recoveryFaultHits==1 && !failed.ok() && failed.nativeError==0xc000007fUL);
        } // Actual failed owner is gone before fresh acquisition.
        if (fault==1) {
            std::ofstream extra(paths.root/session/L".custody-v1"/L"media"/L"unknown-generated-only");
            extra << "generated"; assert(extra.good());
        } else if (fault==2 || fault==3) {
            const auto file=paths.root/session/L".custody-v1"/(fault==2 ? L"playback" : L"recovery")/
                (fault==2 ? L"content.packed-v2" : L"index.1");
            std::fstream stream(file,std::ios::in|std::ios::out|std::ios::binary);
            const auto position=fault==2 ? 128 : 0;
            char byte=0; stream.seekg(position); assert(stream.read(&byte,1));
            byte^=1; stream.seekp(position); assert(stream.write(&byte,1));
        }
        if (fault>=1 && fault<=3) {
            const auto unchanged=coldHashes(paths.root);
            {
                auto cancel=std::make_shared<std::atomic<bool>>(false);
                auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
                const auto refused=V5LocalRecordingWriter::recover(*store.value,session,cancel);
                assert(!refused.ok() && refused.error!=CustodyFileError::none);
                std::fprintf(stderr,"COLD_RECOVERY_COMPLETION_REFUSAL case=%u error=%u unchanged_disk=1\n",fault,static_cast<unsigned>(refused.error));
            }
            assert(coldHashes(paths.root)==unchanged);
            continue;
        }
        const auto members=[&] { return coldCompletedHashes(paths.root/session); };
        const auto before=members(), queue=coldHashes(paths.root/L".custody-v1");
        std::uint64_t generation=0;
        {
            auto cancel=std::make_shared<std::atomic<bool>>(false);
            auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
            {
                auto pair=(*store.value)->readPackage(session,cancel);
                assert(pair.ok() && (*pair.value)->current().phase==CustodyPackagePhase::finalizing);
                generation=(*pair.value)->current().generation;
            }
            auto recovered=V5LocalRecordingWriter::recover(*store.value,session,cancel);
            std::fprintf(stderr,"COLD_RECOVERY_COMPLETION accepted=%u error=%u native=%08x\n",recovered.ok()?1U:0U,static_cast<unsigned>(recovered.error),recovered.nativeError);
            assert(recovered.ok() && "completed_recovery_must_finish_without_reencoding_members");
            const auto result=(*recovered.value)->finalize();
            assert(result.semanticVerified && result.trustedPrefixRetained && !result.normalPackage() && !result.keepablePackage() &&
                result.packagePhase==CustodyPackagePhase::sealedDegraded && result.packageGeneration==generation+1 && result.durationMs==1000);
        }
        assert(members()==before && coldHashes(paths.root/L".custody-v1")==queue);
        const auto sealed=coldHashes(paths.root);
        {
            auto cancel=std::make_shared<std::atomic<bool>>(false);
            auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
            {
                auto pair=(*store.value)->readPackage(session,cancel); assert(pair.ok());
                auto proof=LocalRecordingPackage::inspectProtected(paths.root,*pair.value,session,cancel);
                assert(proof.ok() && (*proof.value)->evidence().manifestSessionMatched &&
                    (*proof.value)->evidence().durationMs==1000 && (*proof.value)->evidence().playback.decodedFrames &&
                    (*proof.value)->evidence().startedAtMs==1000 && (*proof.value)->evidence().stoppedAtMs==1500);
            }
            assert(!V5LocalRecordingWriter::recover(*store.value,session,cancel).ok());
        }
        assert(coldHashes(paths.root)==sealed);
    }
    assert(CustodyOwnedMemory::usedBytes()==idle);
    {std::array<CustodyNativeJob,4> jobs;for(const auto& job:jobs) assert(job);}
    {std::array<CustodyPin,32> pins;for(const auto& pin:pins) assert(pin);}
    std::fprintf(stderr,"COLD_RECOVERY_COMPLETION cases=5 positive=2 preserved_refusals=3 generation_plus_one=1 five_members_ids_queue_unchanged=1 cold_aac_open_closed_history=1 exact_memory=1 audio=0 network=0\n");
}
void coldPlayablePrefix() {
    using namespace graf::windows;
    { // Warm common reader/MF caches independently of the new recovery path.
        testing::GeneratedProtectedRecording warm("cold-playable-warm"); warm.append(100);
        assert(warm.writer->finalize().normalPackage());
    }
    const auto idle=CustodyOwnedMemory::usedBytes();
    const std::string session="44444444-4444-4444-8444-444444444444";
    const std::string user="11111111-1111-4111-8111-111111111111", workspace="22222222-2222-4222-8222-222222222222";
    for (unsigned mode=0; mode<3; ++mode) {
        testing::GeneratedRecordingRoot paths;
        auto cancel=std::make_shared<std::atomic<bool>>(false);
        std::string privacy="[]";
        if (mode) privacy="[{\"segmentId\":\"original-segment\",\"sessionId\":\""+session+
            "\",\"control\":\"pause\",\"startedAt\":\"2026-01-01T00:00:00Z\",\"startMonotonicMs\":100,"+
            (mode==2 ? "\"endedAt\":\"2026-01-01T00:00:01Z\",\"endMonotonicMs\":1100,\"durationMs\":1000," : "\"durationMs\":0,")+
            "\"localMicTreatment\":\"silenced\",\"initiator\":\"user\",\"diagnosticSafe\":true}]";
        {
            auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
            auto queue=(*store.value)->readQueueValue(cancel); assert(queue.ok());
            ProtectedUploadQueueValue candidate(**queue.value);
            assert((*store.value)->prepareRecordingReservation(candidate,session,user,workspace,true,1000,cancel).ok());
            auto bytes=candidate.serialize(cancel); assert(bytes.ok());
            assert(commitProtectedCustodyMetadata(*store.value,(*store.value)->queueContext(),1,*bytes.value,cancel).state==CustodyCommitState::committed);
            auto package=(*store.value)->createPackage(session,cancel); assert(package.ok());
            auto writer=(*package.value)->createWriter(CustodyRole::canonical); assert(writer.ok());
            std::array<float,100*480+47> samples{}; samples.fill(0.25F); samples.back()=std::numeric_limits<float>::quiet_NaN();
            assert((*writer.value)->writeAt(0,samples.data(),sizeof(samples)).ok());
            assert((*writer.value)->checkpoint().state==CustodyCommitState::committed);
            if (mode) {
                const auto manifest=coldManifest(session,privacy);
                assert((*package.value)->commitMetadata(CustodyRole::manifest,CustodyBytes(manifest.begin(),manifest.end())).state==CustodyCommitState::committed);
            }
            if (mode==2) {
                auto value=(*package.value)->current(); ++value.generation; value.phase=CustodyPackagePhase::finalizing;
                assert((*package.value)->commit(value).state==CustodyCommitState::committed);
            }
        }
        const auto canonical=paths.root/session/L".custody-v1"/L"canonical"/L"content.packed-v2";
        const auto canonicalHash=sha256File(canonical);
        const auto queueBefore=coldHashes(paths.root/L".custody-v1");
        {
            auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
            auto recovered=V5LocalRecordingWriter::recover(*store.value,session,cancel);
            std::fprintf(stderr,"COLD_PLAYABLE recovered=%u expected=1 mode=%u error=%u native=%u\n",recovered.ok()?1U:0U,mode,static_cast<unsigned>(recovered.error),recovered.nativeError); std::fflush(stderr);
            assert(recovered.ok() && "cold_prefix_must_become_playable_degraded");
            const auto result=(*recovered.value)->finalize();
            assert(result.semanticVerified && result.trustedPrefixRetained && result.durationMs==1000 && result.packagePhase==CustodyPackagePhase::sealedDegraded);
            assert(!result.normalPackage() && !result.keepablePackage() && !(*recovered.value)->healthy());
            CanonicalAudioFrame frame; assert(!(*recovered.value)->append(frame));
            auto queue=(*store.value)->readQueueValue(cancel); assert(queue.ok() && (*queue.value)->items().size()==1);
            const auto& row=(*queue.value)->items()[0];
            assert(row.ownerUserId==user.c_str() && row.ownerWorkspaceId==workspace.c_str() && row.status==UploadQueueStatus::quarantined && row.safeReason=="capture_prepared");
        }
        assert(sha256File(canonical)==canonicalHash);
        assert(coldHashes(paths.root/L".custody-v1")==queueBefore);
        {
            auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
            auto pair=(*store.value)->readPackage(session,cancel); assert(pair.ok());
            auto proof=LocalRecordingPackage::inspectProtected(paths.root,*pair.value,session,cancel);
            assert(proof.ok() && (*proof.value)->evidence().integrity==PackageIntegrity::degraded && (*proof.value)->evidence().playback.decodedFrames>0);
            assert((*proof.value)->evidence().durationMs==1000 && (*proof.value)->evidence().startedAtMs==(mode?1000:0) && (*proof.value)->evidence().stoppedAtMs==(mode?1500:0));
            assert((*proof.value)->evidence().displayTimezoneOffsetMinutes==(mode?180:0));
            proof.value.reset();
            auto readers=openProtectedCustodyReaders(paths.root,*pair.value,cancel); assert(readers.ok());
            const auto& value=(*pair.value)->current();
            bool manifestSeen=false;
            for(std::size_t i=0;i<value.refCount;++i) if(value.refs[i].role==CustodyRole::manifest) {
                manifestSeen=true;
                CustodyBytes bytes(static_cast<std::size_t>(*value.refs[i].length)); ULONG got=0;
                assert((*readers.value)[(*pair.value)->selectedSlot()][i].stream->Read(bytes.data(),static_cast<ULONG>(bytes.size()),&got)==S_OK && got==bytes.size());
                const std::string_view text(reinterpret_cast<const char*>(bytes.data()),bytes.size());
                assert(text.find("\"privacySegments\":"+privacy)!=std::string_view::npos);
                for(const auto field:{"\"started_at_ms\":","\"stopped_at_ms\":","\"display_timezone_offset_minutes\":"})
                    assert((text.find(field)!=std::string_view::npos)==(mode!=0));
            }
            assert(manifestSeen);
        }
        assert(CustodyOwnedMemory::usedBytes()==idle);
    }
    {std::array<CustodyNativeJob,4> jobs;for(const auto& job:jobs) assert(job);}
    {std::array<CustodyPin,32> pins;for(const auto& pin:pins) assert(pin);}
    std::fprintf(stderr,"COLD_PLAYABLE cases=3 canonical_unchanged=1 owner_queue_unchanged=1 cold_aac_decode=1 history_exact=1 audio=0 network=0\n");
}
void coldPlayableRefusals() {
    using namespace graf::windows;
    const auto idle=CustodyOwnedMemory::usedBytes();
    for(unsigned fault=0;fault<15;++fault) {
        testing::GeneratedRecordingRoot paths;
        auto cancel=std::make_shared<std::atomic<bool>>(false);
        const std::string session="cold-playable-refusal";
        CustodyContext manifestContext{};
        {
            auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
            auto package=(*store.value)->createPackage(session,cancel); assert(package.ok());
            auto writer=(*package.value)->createWriter(CustodyRole::canonical); assert(writer.ok());
            if(fault!=8) {
                std::array<float,100*480> samples{}; samples.fill(0.25F);
                if(fault==7) samples.back()=std::numeric_limits<float>::quiet_NaN();
                assert((*writer.value)->writeAt(0,samples.data(),sizeof(samples)).ok());
                assert((*writer.value)->checkpoint().state==CustodyCommitState::committed);
            }
            if(fault==1 || fault==14) assert((*package.value)->createWriter(CustodyRole::media).ok());
            if(fault==2) {
                auto value=(*package.value)->current(); ++value.generation; value.phase=CustodyPackagePhase::finalizing;
                assert((*package.value)->commit(value).state==CustodyCommitState::committed);
            }
            if((fault>=2 && fault<=6) || fault==13) {
                const auto text=coldManifest(fault==5 ? "wrong-session" : session,fault==6 ? "[{}]" : "[]");
                const auto committed=(*package.value)->commitMetadata(CustodyRole::manifest,CustodyBytes(text.begin(),text.end()));
                assert(committed.state==CustodyCommitState::committed);
                manifestContext=committed.context;
            }
            if(fault==13) {
                auto value=(*package.value)->current(); ++value.generation; value.phase=CustodyPackagePhase::finalizing; value.refCount=1;
                assert(value.refs[0].role==CustodyRole::canonical);
                assert((*package.value)->commit(value).state==CustodyCommitState::committed);
            }
        }
        const auto custody=paths.root/session/L".custody-v1";
        if(fault==0) assert(std::filesystem::remove(custody/L"media"/L"id.bin"));
        if(fault==3) assert(std::filesystem::remove(custody/L"manifest"/L"index.0"));
        if(fault==4) {
            const auto text=coldManifest(session,"[]");
            const auto committed=commitProtectedCustodyMetadata(paths.root,session,manifestContext,1,CustodyBytes(text.begin(),text.end()),cancel);
            assert(committed.state==CustodyCommitState::committed && committed.targetGeneration==2);
        }
        if(fault==14) std::filesystem::resize_file(custody/L"media"/L"content.packed-v2",128);
        const auto before=coldHashes(paths.root);
        {
            auto store=ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
            if(fault==9) cancel->store(true);
            {
                std::optional<std::array<CustodyNativeJob,4>> jobs;
                std::optional<std::array<CustodyPin,32>> pins;
                CustodyBytes pressure;
                if(fault==10) jobs.emplace();
                if(fault==11) pins.emplace();
                if(fault==12) pressure.resize(CustodyOwnedMemory::limit-CustodyOwnedMemory::usedBytes());
                auto result=V5LocalRecordingWriter::recover(*store.value,session,cancel);
                std::fprintf(stderr,"COLD_PLAYABLE_REFUSAL case=%u rejected=%u error=%u native=%u\n",fault,result.ok()?0U:1U,static_cast<unsigned>(result.error),result.nativeError);
                assert(!result.ok());
                if(fault>=10 && fault<=12) assert(result.error==CustodyFileError::allocationFailed);
            }
            cancel->store(false);
            if(fault>=9 && fault<=12) {
                auto readable=LocalRecordingPackage::inspectUnfinished(*store.value,session,cancel);
                assert(readable.ok() && (*readable.value)->completeFrames()==100);
            }
        }
        assert(coldHashes(paths.root)==before && CustodyOwnedMemory::usedBytes()==idle);
    }
    {std::array<CustodyNativeJob,4> jobs;for(const auto& job:jobs) assert(job);}
    {std::array<CustodyPin,32> pins;for(const auto& pin:pins) assert(pin);}
    std::fprintf(stderr,"COLD_PLAYABLE_REFUSALS cases=15 unchanged_disk=1 exact_memory=1 all_jobs_pins_returned=1 audio=0 network=0\n");
}
void coldUnfinishedPrefix() {
    using namespace graf::windows;
    static_assert(!std::is_default_constructible_v<LocalRecordingPackage::UnfinishedInspection>);
    static_assert(!std::is_convertible_v<std::shared_ptr<const LocalRecordingPackage::UnfinishedInspection>,
        std::shared_ptr<const LocalRecordingPackage::ProtectedInspection>>);
    for (const bool finalizing : {false,true}) {
        testing::GeneratedRecordingRoot paths;
        auto cancel = std::make_shared<std::atomic<bool>>(false);
        const std::string session = "cold-complete480";
        {
            auto store = ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
            auto package = (*store.value)->createPackage(session,cancel); assert(package.ok());
            auto writer = (*package.value)->createWriter(CustodyRole::canonical); assert(writer.ok());
            std::array<float,3*480+47> samples{}; samples.fill(0.25F);
            // A non-audio tail does not invalidate the finite complete prefix.
            samples.back() = std::numeric_limits<float>::quiet_NaN();
            assert((*writer.value)->writeAt(0,samples.data(),sizeof(samples)).ok());
            assert((*writer.value)->checkpoint().state == CustodyCommitState::committed);
            std::array<float,480> dirty{};
            assert((*writer.value)->writeAt(sizeof(samples),dirty.data(),sizeof(dirty)).ok());
            if (finalizing) {
                auto value = (*package.value)->current(); ++value.generation;
                value.phase = CustodyPackagePhase::finalizing;
                assert((*package.value)->commit(value).state == CustodyCommitState::committed);
            }
        } // All birth/dirty writers and native owners are gone; no destructor flush.
        const auto snapshot = [&] {
            std::map<std::filesystem::path,std::string> files;
            for (const auto& entry : std::filesystem::recursive_directory_iterator(paths.root))
                if (entry.is_regular_file()) files.emplace(entry.path(),sha256File(entry.path()));
            return files;
        };
        const auto before = snapshot();
        {
            auto store = ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
            auto inspected = LocalRecordingPackage::inspectUnfinished(*store.value,session,cancel);
            const auto frames = inspected.ok() ? (*inspected.value)->completeFrames() : 0;
            std::fprintf(stderr,"COLD_PREFIX phase=%s complete_frames=%llu expected=3\n",
                finalizing ? "finalizing" : "capturing",static_cast<unsigned long long>(frames));
            std::fflush(stderr);
            assert(frames == 3 && "cold_complete480_prefix_must_survive_restart");
        }
        assert(snapshot() == before);
    }
    const auto idle = CustodyOwnedMemory::usedBytes(); // Common reader cache was warmed by the positives.
    for (unsigned phase = 0; phase < 3; ++phase) {
        testing::GeneratedProtectedRecording capture("cold-sealed-refusal");
        capture.append(100);
        const auto sealed = capture.writer->finalize(phase == 1 ? ReasonCode::clockDiscontinuity : ReasonCode::none,
            phase == 2 ? RecordingStopReason::userRequested : RecordingStopReason::interruption);
        std::fprintf(stderr,"COLD_SEALED case=%u actual_phase=%u semantic=%u\n",phase,
            static_cast<unsigned>(sealed.packagePhase),sealed.semanticVerified ? 1U : 0U);
        assert(sealed.semanticVerified);
        assert(sealed.packagePhase == (phase == 0 ? CustodyPackagePhase::sealedNormal :
            phase == 1 ? CustodyPackagePhase::sealedDegraded : CustodyPackagePhase::discardPending));
        capture.writer.reset(); capture.store.reset();
        std::map<std::filesystem::path,std::string> before;
        for (const auto& entry : std::filesystem::recursive_directory_iterator(capture.paths.root))
            if (entry.is_regular_file()) before.emplace(entry.path(),sha256File(entry.path()));
        {
            auto store = ProtectedCustodyStoreOwner::open(capture.paths.root,capture.cancel); assert(store.ok());
            auto rejected = LocalRecordingPackage::inspectUnfinished(*store.value,capture.session,capture.cancel);
            assert(!rejected.ok() && rejected.error == CustodyFileError::invalidInput);
        }
        std::map<std::filesystem::path,std::string> after;
        for (const auto& entry : std::filesystem::recursive_directory_iterator(capture.paths.root))
            if (entry.is_regular_file()) after.emplace(entry.path(),sha256File(entry.path()));
        assert(before == after && CustodyOwnedMemory::usedBytes() == idle);
    }
    for (unsigned fault = 0; fault < 9; ++fault) {
        testing::GeneratedRecordingRoot paths;
        auto cancel = std::make_shared<std::atomic<bool>>(false);
        const std::string session = "cold-prefix-refusal";
        {
            auto store = ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
            auto package = (*store.value)->createPackage(session,cancel); assert(package.ok());
            auto writer = (*package.value)->createWriter(CustodyRole::canonical); assert(writer.ok());
            std::array<float,35*480> samples{};
            const std::size_t bytes = fault == 0 ? 0 : fault == 1 ? 1916 : sizeof(samples);
            if (fault == 2) samples[34*480] = std::numeric_limits<float>::quiet_NaN(); // Beyond the first64KiB.
            if (bytes) {
                assert((*writer.value)->writeAt(0,samples.data(),bytes).ok());
                assert((*writer.value)->checkpoint().state == CustodyCommitState::committed);
            }
        }
        if (fault == 3) {
            // Damage the nonselected g1 head, not the selected healthy g2.
            const auto file = paths.root/session/L".custody-v1"/L"canonical"/L"content.packed-v2";
            std::fstream stream(file,std::ios::in|std::ios::out|std::ios::binary);
            char byte = 0; stream.seekg(128); assert(stream.read(&byte,1));
            byte ^= 1; stream.seekp(128); assert(stream.write(&byte,1));
        }
        if (fault == 4) assert(std::filesystem::remove(paths.root/session/L".custody-v1"/L"package-state"/L"index.0"));
        std::map<std::filesystem::path,std::string> before;
        for (const auto& entry : std::filesystem::recursive_directory_iterator(paths.root))
            if (entry.is_regular_file()) before.emplace(entry.path(),sha256File(entry.path()));
        {
            auto store = ProtectedCustodyStoreOwner::open(paths.root,cancel); assert(store.ok());
            if (fault == 5) cancel->store(true);
            {
                std::optional<std::array<CustodyNativeJob,4>> jobs;
                std::optional<std::array<CustodyPin,32>> pins;
                CustodyBytes pressure;
                if (fault == 6) jobs.emplace();
                if (fault == 7) pins.emplace();
                if (fault == 8) pressure.resize(CustodyOwnedMemory::limit-CustodyOwnedMemory::usedBytes());
                auto result = LocalRecordingPackage::inspectUnfinished(*store.value,session,cancel);
                assert(!result.ok());
                if (fault >= 6) assert(result.error == CustodyFileError::allocationFailed);
            }
            if (fault >= 5) {
                cancel->store(false);
                auto result = LocalRecordingPackage::inspectUnfinished(*store.value,session,cancel);
                assert(result.ok() && (*result.value)->completeFrames() == 35);
            }
        }
        std::map<std::filesystem::path,std::string> after;
        for (const auto& entry : std::filesystem::recursive_directory_iterator(paths.root))
            if (entry.is_regular_file()) after.emplace(entry.path(),sha256File(entry.path()));
        assert(before == after);
        assert(CustodyOwnedMemory::usedBytes() == idle);
    }
    assert(!LocalRecordingPackage::inspectUnfinished({},"none",std::make_shared<std::atomic<bool>>(false)).ok());
    { std::array<CustodyNativeJob,4> jobs; for (const auto& job : jobs) assert(job); }
    { std::array<CustodyPin,32> pins; for (const auto& pin : pins) assert(pin); }
    std::fprintf(stderr,"COLD_PREFIX refusals=9 sealed_phases_refused=3 unchanged_disk=1 exact_memory=1 all_jobs_pins_returned=1 audio=0 network=0\n");
}
}
#endif

int main(int argc,char** argv) {
    using namespace graf::windows;
#ifdef _MSC_VER
    _set_error_mode(_OUT_TO_STDERR);
    _set_abort_behavior(0, _WRITE_ABORT_MSG | _CALL_REPORTFAULT);
#endif
#if defined(_MSC_VER) && defined(_DEBUG)
    _CrtSetReportMode(_CRT_ASSERT, _CRTDBG_MODE_FILE);
    _CrtSetReportFile(_CRT_ASSERT, _CRTDBG_FILE_STDERR);
    resultAllocationCuts();
#endif
#ifdef _WIN32
    if(argc>=2 && std::string_view(argv[1]).find("--initial-canonical")==0) {
        int count=0;
        struct WideArgs { LPWSTR* values; ~WideArgs() { if(values) LocalFree(values); } } args{CommandLineToArgvW(GetCommandLineW(),&count)};
        if(!args.values) return 2;
        if(count==2 && std::wstring_view(args.values[1])==L"--initial-canonical-crash-cuts") {
            initialCanonicalCrashCuts(); return 0;
        }
        if(count==4 && std::wstring_view(args.values[1])==L"--initial-canonical-crash" &&
            std::wstring_view(args.values[3]).size()==1 && args.values[3][0]>=L'1' && args.values[3][0]<=L'3')
            return initialCanonicalChild(std::filesystem::path(args.values[2]),static_cast<InitialCanonicalCut>(args.values[3][0]-L'0'));
        return 2;
    }
    if(argc==2 && std::string_view(argv[1])=="--cold-recovery-wav") {
        coldRecoveryCrashCuts(ColdRecoveryCuts::wav); coldWavRefusals(); return 0;
    }
    if(argc==2 && std::string_view(argv[1])=="--cold-recovery-playback") {
        coldRecoveryCrashCuts(ColdRecoveryCuts::playback); return 0;
    }
    if(argc==2 && std::string_view(argv[1])=="--cold-recovery-playback-restart") {
        coldRecoveryCrashCuts(ColdRecoveryCuts::playbackRestart); return 0;
    }
    if(argc==2 && std::string_view(argv[1])=="--cold-recovery-terminal-unused") {
        coldRecoveryCrashCuts(ColdRecoveryCuts::terminalUnused); return 0;
    }
    if(argc==2 && std::string_view(argv[1])=="--cold-recovery-terminal-unused-crash") {
        coldTerminalUnusedCrashCuts(); return 0;
    }
    if(argc==2 && std::string_view(argv[1])=="--cold-recovery-terminal-unused-refusals") {
        coldTerminalUnusedCrashCuts(true); return 0;
    }
    if(argc==2 && std::string_view(argv[1])=="--cold-recovery-terminal-unused-sticky") {
        coldTerminalUnusedCrashCuts(false,true); return 0;
    }
    if(argc==2 && std::string_view(argv[1])=="--cold-recovery-playback-partial") {
        coldRecoveryPlaybackPartial(); return 0;
    }
    if(argc==2 && std::string_view(argv[1])=="--cold-recovery-completion") {
        coldRecoveryCompletion(); return 0;
    }
    if(argc==2 && std::string_view(argv[1])=="--cold-recovery-returned-faults") {
        coldRecoveryReturnedFaults(); return 0;
    }
    if(argc==2 && std::string_view(argv[1])=="--cold-recovery-playback-returned-faults") {
        coldRecoveryReturnedFaults(true); return 0;
    }
    if(argc==6 && std::string_view(argv[1])=="--cold-recovery-crash") {
        int count=0;
        struct WideArgs { LPWSTR* values; ~WideArgs() { if (values) LocalFree(values); } } args{CommandLineToArgvW(GetCommandLineW(),&count)};
        if (!args.values || count!=6 || std::wstring_view(args.values[1])!=L"--cold-recovery-crash") return 89;
        return coldCrashChild(std::filesystem::path(args.values[2]),static_cast<unsigned>(std::stoul(args.values[3])),
            {static_cast<unsigned>(std::stoul(args.values[4])),static_cast<unsigned>(std::stoul(args.values[5]))});
    }
    initialCanonicalCrashCuts();
    coldPlayablePrefix();
    coldPlayableRefusals();
    coldUnfinishedPrefix();
    coldRecoveryCrashCuts();
#else
    (void)argc; (void)argv;
#endif
    const auto directory = std::filesystem::temp_directory_path() / "graf-feature-200-writer";
    const auto custodyRoot = directory / "custody";
    const auto escape = directory.parent_path() / "graf-feature-200-writer-escape";
    std::filesystem::remove_all(directory);
    std::filesystem::remove_all(escape);
    std::filesystem::create_directories(custodyRoot);
    assert(!AtomicFileStore::isWithinRoot(custodyRoot, escape));
#ifdef _WIN32
    {
        testing::GeneratedProtectedRecording capture("actual-native-aac");
        // Caller path strings cannot create storage authority or escape root.
        assert(!V5LocalRecordingWriter::open(capture.store, "../escape", capture.cancel).ok());
        assert(!std::filesystem::exists(capture.paths.parent/"escape"));
        capture.append(100);
        const auto result = capture.writer->finalize();
        assert(result.normalPackage() && result.durationMs == 1000);
        assert(result.wavBytes == 32044 && result.playbackBytes && result.semanticVerified);
        assert(result.startedAtMs && result.stoppedAtMs >= result.startedAtMs);
        assert(result.displayTimezoneOffsetMinutes >= -840 && result.displayTimezoneOffsetMinutes <= 840);
        const auto seconds = static_cast<std::time_t>(result.startedAtMs/1000);
        std::tm local{}; assert(localtime_s(&local,&seconds) == 0);
        char minute[32]{}; assert(std::strftime(minute,sizeof(minute),"%Y-%m-%d %H:%M",&local));
        assert(DesktopApiClient::formatDisplayMinute(result.startedAtMs,result.displayTimezoneOffsetMinutes) == minute);
        assert(!capture.writer->append(CanonicalAudioFrame{}));
        const auto repeated = capture.writer->finalize();
        assert(repeated.packageGeneration == result.packageGeneration && repeated.wavSha256 == result.wavSha256);
        auto pair = capture.coldPair(); assert(pair.ok());
        auto inspection = LocalRecordingPackage::inspectProtected(capture.paths.root,*pair.value,capture.session,capture.cancel);
        assert(inspection.ok() && (*inspection.value)->evidence().integrity == PackageIntegrity::valid);
        assert((*inspection.value)->evidence().durationMs == result.durationMs);
        assert((*inspection.value)->evidence().manifestSessionMatched);
        inspection.value.reset();
        const auto& package = (*pair.value)->current();
        const auto playback = std::find_if(package.refs.begin(), package.refs.begin()+package.refCount,
            [](const auto& ref) { return ref.role == CustodyRole::playback; });
        assert(playback != package.refs.begin()+package.refCount && playback->packed && playback->sealed &&
            playback->length && *playback->length && playback->generation && *playback->generation &&
            playback->containerId && playback->rootRef && playback->sha256);
        for (const bool busy : {false, true}) {
            std::optional<std::array<CustodyNativeJob, 2>> jobs;
            if (busy) { jobs.emplace(); for (const auto& job : *jobs) assert(job); }
            const auto decoded = LocalRecordingPackage::readProtectedPlayback(
                capture.paths.root, *pair.value, result.durationMs, capture.cancel);
            jobs.reset();
            std::fprintf(stderr, "PROTECTED_PLAYBACK held_jobs=%u ok=%u error=%u native=%u frames=%llu\n",
                busy ? 2U : 0U, decoded.ok() ? 1U : 0U, static_cast<unsigned>(decoded.error), decoded.nativeError,
                static_cast<unsigned long long>(decoded.ok() ? decoded.value->decodedFrames : 0));
            std::fflush(stderr);
            assert(decoded.ok() && decoded.value->decodedFrames > 0 &&
                "protected_pair_playback_must_fit_two_available_native_jobs");
        }
        for (const auto& entry : std::filesystem::recursive_directory_iterator(capture.paths.root)) {
            const auto name = entry.path().filename().string();
            assert(name != ".canonical-mix.f32.tmp" && name != "meeting-transcription.wav" &&
                name != "meeting-review.m4a" && name != "manifest.json" && name != "capture-recovery.json");
        }
    }
    {
        testing::GeneratedProtectedRecording capture("invalid-cleaned-frame");
        capture.append(1);
        CanonicalAudioFrame bad; bad.mixed[0] = std::numeric_limits<float>::quiet_NaN();
        assert(!capture.writer->append(bad) && !capture.writer->append(CanonicalAudioFrame{}));
        const auto retained = capture.writer->finalize(ReasonCode::aecUnavailable);
        assert(!retained.normalPackage() && retained.trustedPrefixRetained && retained.durationMs == 10);
        auto pair = capture.coldPair(); assert(pair.ok());
        auto inspected = LocalRecordingPackage::inspectProtected(capture.paths.root,*pair.value,capture.session,capture.cancel);
        assert(inspected.ok() && (*inspected.value)->evidence().trustedPrefixFrames == 1);
    }
    {
        testing::GeneratedProtectedRecording capture("interrupted-owner");
        capture.append(140); // Cross the full canonical block checkpoint.
        const auto context = capture.writer->packageContext();
        const auto snapshot = [&] {
            std::map<std::filesystem::path,std::string> result;
            for (const auto& entry : std::filesystem::recursive_directory_iterator(capture.paths.root))
                if (entry.is_regular_file()) {
                    const auto hash = sha256File(entry.path()); assert(!hash.empty());
                    result.emplace(entry.path(),hash);
                }
            return result;
        };
        const auto before = snapshot();
        assert(!V5LocalRecordingWriter::open(capture.store,capture.session,capture.cancel).ok());
        capture.writer.reset(); capture.store.reset();
        assert(snapshot() == before); // Destructor does no flush/recovery/IO.
        auto pair = ProtectedCustodyPackagePair::read(capture.paths.root,capture.session,context,capture.cancel);
        assert(pair.ok() && (*pair.value)->current().phase == CustodyPackagePhase::capturing);
        assert(snapshot() == before);
    }
#else
    assert(!V5LocalRecordingWriter::open({}, "portable", {}).ok());
#endif
    // Compatibility parser inputs below are generated data, not production
    // writer outputs or encoder success evidence.
    const auto result = testing::makeGeneratedLegacyPackage(directory, 1,
        ReasonCode::none, RecordingStopReason::interruption, "m4a-fixture");
    assert(result.durationMs == 10 && result.wavBytes > 44 && !result.wavSha256.empty());
    const auto package = LocalRecordingPackage::inspect(directory);
    // A matching digest proves bytes, not a usable AAC container.
    assert(package.integrity == PackageIntegrity::malformed && package.durationMs == 10);
    assert(LocalRecordingPackage::inspect(directory, directory.parent_path()).integrity == PackageIntegrity::malformed);
    UploadCustodyItem uploadItem;
    uploadItem.localRecordingId = uploadItem.directoryId = uploadItem.sessionId = "synthetic-recording";
    uploadItem.packageDirectory = directory;
    uploadItem.ownerUserId = "11111111-1111-4111-8111-111111111111";
    uploadItem.ownerWorkspaceId = "22222222-2222-4222-8222-222222222222";
    DesktopHttpConfig uploadConfig;
    uploadConfig.sessionToken = "synthetic-token-not-a-credential";
    uploadConfig.workspaceId = uploadItem.ownerWorkspaceId;
    uploadConfig.confirmedIdentity = DesktopAccountIdentity{uploadItem.ownerUserId, uploadItem.ownerWorkspaceId};
    unsigned sends = 0;
    const DesktopHttpTransport::UploadSend send = [&](const auto&, const auto&) {
        ++sends;
        return DesktopHttpTransport::UploadResponse{503, ""};
    };
    assert(DesktopHttpTransport(uploadConfig).upload(uploadItem, send).status == DesktopTransportStatus::invalidPackage);
    assert(sends == 0 && std::filesystem::exists(result.wavPath) && std::filesystem::exists(result.playbackPath));
    // The first accepted frame carries the start; finalization closes the bounds.
    // Ten milliseconds of audio cannot outlive the recording that produced it.
    assert(result.startedAtMs != 0 && result.stoppedAtMs >= result.startedAtMs);
    assert(result.stoppedAtMs - result.startedAtMs < 60'000);
    assert(result.displayTimezoneOffsetMinutes >= -14 * 60 && result.displayTimezoneOffsetMinutes <= 14 * 60);
    assert(package.startedAtMs == result.startedAtMs && package.stoppedAtMs == result.stoppedAtMs);
    assert(package.displayTimezoneOffsetMinutes == result.displayTimezoneOffsetMinutes);
    {
        // The stored offset has to agree with the operating system for the same
        // instant. This is an independent path: localtime plus strftime, not the
        // arithmetic that produced the offset or the label.
        const auto seconds = static_cast<std::time_t>(result.startedAtMs / 1000);
        std::tm local{};
#ifdef _WIN32
        assert(localtime_s(&local, &seconds) == 0);
#else
        assert(localtime_r(&seconds, &local) != nullptr);
#endif
        char buffer[32] = {};
        assert(std::strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M", &local) > 0);
        assert(DesktopApiClient::formatDisplayMinute(result.startedAtMs, result.displayTimezoneOffsetMinutes) == buffer);
    }
    {
        // A package written before the bounds existed stays readable and simply
        // reports no time instead of a guessed one.
        std::ifstream input(result.manifestPath);
        const std::string original((std::istreambuf_iterator<char>(input)), {});
        input.close();
        const auto bounds = original.find(",\"started_at_ms\":");
        assert(bounds != std::string::npos);
        const auto artifacts = original.find(",\"artifacts\":", bounds);
        assert(artifacts != std::string::npos);
        auto legacyManifest = original;
        legacyManifest.erase(bounds, artifacts - bounds);
        { std::ofstream output(result.manifestPath); output << legacyManifest; }
        const auto legacy = LocalRecordingPackage::inspect(directory, directory.parent_path());
        assert(legacy.integrity == PackageIntegrity::malformed && legacy.durationMs == 10);
        assert(legacy.startedAtMs == 0 && legacy.stoppedAtMs == 0 && legacy.displayTimezoneOffsetMinutes == 0);
        // An impossible pair is dropped; a recording never ends before it starts.
        const auto stoppedAt = original.find("\"stopped_at_ms\":");
        assert(stoppedAt != std::string::npos);
        const auto stoppedEnd = original.find(',', stoppedAt);
        assert(stoppedEnd != std::string::npos);
        auto corrupted = original;
        corrupted.replace(stoppedAt, stoppedEnd - stoppedAt,
            "\"stopped_at_ms\":" + std::to_string(result.startedAtMs - 1));
        { std::ofstream output(result.manifestPath); output << corrupted; }
        const auto rejected = LocalRecordingPackage::inspect(directory, directory.parent_path());
        assert(rejected.integrity == PackageIntegrity::malformed);
        assert(rejected.startedAtMs == 0 && rejected.stoppedAtMs == 0);
        { std::ofstream output(result.manifestPath); output << original; }
        const auto restored = LocalRecordingPackage::inspect(directory, directory.parent_path());
        assert(restored.startedAtMs == result.startedAtMs && restored.stoppedAtMs == result.stoppedAtMs);
    }
    assert(!package.playbackAvailable); // No explicit custody root / no real AAC fixture.
    assert(!LocalRecordingPackage::inspect(directory, custodyRoot).playbackAvailable);
    {
        // Existing Windows packages predate explicit capture status. Their
        // verified WAV still supplies duration; a conflicting duration cannot.
        std::ifstream input(result.manifestPath);
        std::string manifest((std::istreambuf_iterator<char>(input)), {});
        input.close();
        const std::string status = ",\"capture_status\":\"normal\",\"capture_reason_code\":\"none\"";
        const auto offset = manifest.find(status);
        assert(offset != std::string::npos);
        manifest.erase(offset, status.size());
        { std::ofstream output(result.manifestPath); output << manifest; }
        const auto legacy = LocalRecordingPackage::inspect(directory, directory.parent_path());
        assert(legacy.integrity == PackageIntegrity::malformed && legacy.durationMs == 10);
        const auto durationOffset = manifest.find("\"duration_ms\":10");
        assert(durationOffset != std::string::npos);
        manifest.replace(durationOffset, std::string("\"duration_ms\":10").size(), "\"duration_ms\":9999");
        { std::ofstream output(result.manifestPath); output << manifest; }
        const auto inconsistent = LocalRecordingPackage::inspect(directory, directory.parent_path());
        assert(inconsistent.integrity == PackageIntegrity::malformed);
        assert(inconsistent.durationMs == 0 && !inconsistent.playbackAvailable);
    }
    const auto failedDirectory = custodyRoot / "failed";
    testing::writeGeneratedPrefix(failedDirectory, 1, ReasonCode::finalizationFailed);
    assert(!std::filesystem::exists(failedDirectory/"meeting-transcription.wav"));
    assert(!std::filesystem::exists(failedDirectory/"meeting-review.m4a"));
    assert(LocalRecordingPackage::inspect(failedDirectory).integrity == PackageIntegrity::degraded);

    const auto prefixDirectory = custodyRoot / "prefix";
    const auto retained = testing::makeGeneratedLegacyPackage(prefixDirectory, 1,
        ReasonCode::endpointInvalidated, RecordingStopReason::interruption, "synthetic-playback");
    const auto prefixSnapshot = LocalRecordingPackage::inspect(prefixDirectory, custodyRoot);
    assert(prefixSnapshot.integrity == PackageIntegrity::degraded && prefixSnapshot.durationMs == 10);
    assert(!prefixSnapshot.playbackAvailable); // Literal is deliberately not AAC.
    {
        std::ifstream input(retained.manifestPath);
        const std::string manifest((std::istreambuf_iterator<char>(input)), {});
        assert(manifest.find("\"capture_status\":\"degraded\"") != std::string::npos);
        assert(manifest.find("endpoint_invalidated") != std::string::npos);
    }
    assert(std::filesystem::file_size(prefixDirectory/".canonical-mix.f32.tmp") == 480*sizeof(float));
    const auto interruptedDirectory = custodyRoot / "interrupted";
    testing::writeGeneratedPrefix(interruptedDirectory, 1, ReasonCode::finalizationFailed);
    assert(std::filesystem::file_size(interruptedDirectory/".canonical-mix.f32.tmp") == 480*sizeof(float));
    assert(std::filesystem::exists(interruptedDirectory/"capture-recovery.json"));
    assert(LocalRecordingPackage::inspect(interruptedDirectory).integrity == PackageIntegrity::degraded);
    const auto interrupted = LocalRecordingPackage::inspect(interruptedDirectory, custodyRoot);
    assert(!interrupted.playbackAvailable && interrupted.durationMs == 0);
#ifdef _WIN32
    // Guest/Windows runner exercises the real AAC encoder and container, not the
    // portable synthetic encoder. No input or output device/hardware is involved.
    assert(SUCCEEDED(CoInitializeEx(nullptr, COINIT_MULTITHREADED)));
    assert(SUCCEEDED(MFStartup(MF_VERSION)));
    {
        const auto encoded = testing::makeGeneratedLegacyPackage(custodyRoot/"native-aac", 100);
        assert(encoded.durationMs == 1000);
        Microsoft::WRL::ComPtr<IMFSourceReader> reader;
        assert(SUCCEEDED(MFCreateSourceReaderFromURL(encoded.playbackPath.c_str(), nullptr, &reader)));
        PROPVARIANT duration;
        PropVariantInit(&duration);
        assert(SUCCEEDED(reader->GetPresentationAttribute(static_cast<DWORD>(MF_SOURCE_READER_MEDIASOURCE), MF_PD_DURATION, &duration)));
        assert(duration.vt == VT_UI8);
        const auto durationMs = duration.uhVal.QuadPart / 10'000;
        assert(durationMs >= 900 && durationMs <= 1100);
        PropVariantClear(&duration);
        const auto snapshot = LocalRecordingPackage::inspect(encoded.packageDirectory, custodyRoot);
        assert(snapshot.integrity == PackageIntegrity::valid && snapshot.playbackAvailable && snapshot.durationMs == 1000);
        assert((snapshot.trackBytes == std::array<std::uint64_t, 3>{
            std::filesystem::file_size(encoded.manifestPath), encoded.wavBytes, encoded.playbackBytes}));
        const auto metadataOnly = LocalRecordingPackage::inspect(encoded.packageDirectory);
        assert(metadataOnly.integrity == PackageIntegrity::valid && !metadataOnly.playbackAvailable);
        assert(!LocalRecordingPackage::inspect(encoded.packageDirectory, custodyRoot / "unrelated").playbackAvailable);
        reader.Reset();
        std::ifstream input(encoded.manifestPath);
        const std::string original((std::istreambuf_iterator<char>(input)), {});
        input.close();
        const auto bounds = original.find(",\"started_at_ms\":");
        const auto artifacts = original.find(",\"artifacts\":", bounds);
        assert(bounds != std::string::npos && artifacts != std::string::npos);
        auto legacy = original;
        legacy.erase(bounds, artifacts - bounds);
        { std::ofstream output(encoded.manifestPath); output << legacy; }
        const auto timeless = LocalRecordingPackage::inspect(encoded.packageDirectory, custodyRoot);
        assert(timeless.integrity == PackageIntegrity::valid && timeless.playbackAvailable && timeless.durationMs == 1000);
        assert(timeless.startedAtMs == 0 && timeless.stoppedAtMs == 0 && timeless.displayTimezoneOffsetMinutes == 0);
        const std::string status = ",\"capture_status\":\"normal\",\"capture_reason_code\":\"none\"";
        const auto statusOffset = legacy.find(status);
        assert(statusOffset != std::string::npos);
        legacy.erase(statusOffset, status.size());
        { std::ofstream output(encoded.manifestPath); output << legacy; }
        assert(LocalRecordingPackage::inspect(encoded.packageDirectory).integrity == PackageIntegrity::valid);
        auto impossible = original;
        const auto stopped = impossible.find("\"stopped_at_ms\":");
        const auto stoppedEnd = impossible.find(',', stopped);
        assert(stopped != std::string::npos && stoppedEnd != std::string::npos);
        impossible.replace(stopped, stoppedEnd - stopped, "\"stopped_at_ms\":" + std::to_string(encoded.startedAtMs - 1));
        { std::ofstream output(encoded.manifestPath); output << impossible; }
        const auto invalidTime = LocalRecordingPackage::inspect(encoded.packageDirectory);
        assert(invalidTime.integrity == PackageIntegrity::valid && invalidTime.startedAtMs == 0 && invalidTime.stoppedAtMs == 0);
        auto invalidOffset = original;
        const auto offset = invalidOffset.find("\"display_timezone_offset_minutes\":");
        const auto offsetEnd = invalidOffset.find(',', offset);
        assert(offset != std::string::npos && offsetEnd != std::string::npos);
        invalidOffset.replace(offset, offsetEnd - offset, "\"display_timezone_offset_minutes\":9999");
        { std::ofstream output(encoded.manifestPath); output << invalidOffset; }
        const auto invalidZone = LocalRecordingPackage::inspect(encoded.packageDirectory);
        assert(invalidZone.integrity == PackageIntegrity::valid && invalidZone.startedAtMs == 0 && invalidZone.stoppedAtMs == 0);
        { std::ofstream output(encoded.manifestPath); output << original; }
        assert(LocalRecordingPackage::inspect(encoded.packageDirectory).startedAtMs == encoded.startedAtMs);
    }
    {
        const auto source = testing::makeGeneratedLegacyPackage(custodyRoot/"longer-aac", 200);
        assert(LocalRecordingPackage::inspect(source.packageDirectory).integrity == PackageIntegrity::valid);
        std::ifstream sourceBytes(source.playbackPath, std::ios::binary);
        const std::string wrongDuration((std::istreambuf_iterator<char>(sourceBytes)), {});
        const auto encoded = testing::makeGeneratedLegacyPackage(custodyRoot/"duration-mismatch", 100,
            ReasonCode::none, RecordingStopReason::interruption, wrongDuration);
        assert(encoded.durationMs == 1000 && encoded.playbackSha256 == source.playbackSha256);
        for (const auto& root : {std::filesystem::path{}, custodyRoot}) {
            const auto snapshot = LocalRecordingPackage::inspect(encoded.packageDirectory, root);
            assert(snapshot.integrity == PackageIntegrity::malformed && snapshot.durationMs == 1000 && !snapshot.playbackAvailable);
        }
        uploadItem.packageDirectory = encoded.packageDirectory;
        assert(DesktopHttpTransport(uploadConfig).upload(uploadItem, send).status == DesktopTransportStatus::invalidPackage);
        assert(sends == 0 && std::filesystem::exists(encoded.wavPath) && std::filesystem::exists(encoded.playbackPath));
    }
    {
        const auto encoded = testing::makeGeneratedLegacyPackage(custodyRoot/"native-degraded", 100,
            ReasonCode::endpointInvalidated);
        const auto snapshot = LocalRecordingPackage::inspect(encoded.packageDirectory, custodyRoot);
        assert(snapshot.integrity == PackageIntegrity::degraded && snapshot.playbackAvailable && snapshot.durationMs == 1000);
        {
            std::ofstream corrupt(encoded.playbackPath, std::ios::binary | std::ios::app);
            corrupt << "synthetic-corruption";
        }
        assert(!LocalRecordingPackage::inspect(encoded.packageDirectory, custodyRoot).playbackAvailable);
    }
    MFShutdown();
    CoUninitialize();
#endif
    {
        std::ofstream corrupt(prefixDirectory / "meeting-review.m4a", std::ios::binary | std::ios::app);
        corrupt << "synthetic-corruption";
    }
    const auto corrupted = LocalRecordingPackage::inspect(prefixDirectory, custodyRoot);
    assert(corrupted.integrity == PackageIntegrity::malformed && !corrupted.playbackAvailable);
    assert(corrupted.durationMs == 10); // The independent canonical WAV still verifies.
    assert(LocalRecordingPackage::inspect(prefixDirectory, escape).integrity == PackageIntegrity::malformed);
#ifndef _WIN32
    // No path escape through an artifact symlink, even with unchanged digest.
    const auto movedPlayback = custodyRoot / "outside-package.m4a";
    std::filesystem::rename(prefixDirectory / "meeting-review.m4a", movedPlayback);
    std::filesystem::create_symlink(movedPlayback, prefixDirectory / "meeting-review.m4a");
    assert(!LocalRecordingPackage::inspect(prefixDirectory, custodyRoot).playbackAvailable);
    // Exercise confinement independently of both AAC decoding and a bad digest.
    const auto movedWav = custodyRoot / "outside-package.wav";
    std::filesystem::rename(prefixDirectory / "meeting-transcription.wav", movedWav);
    std::filesystem::create_symlink(movedWav, prefixDirectory / "meeting-transcription.wav");
    const auto escapedMedia = LocalRecordingPackage::inspect(prefixDirectory, custodyRoot);
    assert(escapedMedia.integrity == PackageIntegrity::malformed && escapedMedia.durationMs == 0);
#endif
    std::filesystem::remove_all(directory);
    std::filesystem::remove_all(escape);
    return 0;
}
