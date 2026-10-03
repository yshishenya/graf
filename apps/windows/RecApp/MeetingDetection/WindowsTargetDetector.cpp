#include "WindowsTargetDetector.h"

#include "../Storage/Sha256.h"

#ifdef _WIN32
#include <windows.h>
#include <audiopolicy.h>
#include <mmdeviceapi.h>
#include <wintrust.h>
#include <softpub.h>
#include <bcrypt.h>
#include <wrl/client.h>

#include <array>
#include <map>
#endif

namespace graf::windows {
namespace {
#ifdef _WIN32
using Microsoft::WRL::ComPtr;

struct ScopedHandle {
    HANDLE value = nullptr;
    ~ScopedHandle() { if (value && value != INVALID_HANDLE_VALUE) CloseHandle(value); }
};

std::uint64_t creationTime(HANDLE process) {
    FILETIME created{}, exited{}, kernel{}, user{};
    if (!GetProcessTimes(process, &created, &exited, &kernel, &user) ||
        WaitForSingleObject(process, 0) != WAIT_TIMEOUT) return 0;
    return (static_cast<std::uint64_t>(created.dwHighDateTime) << 32) | created.dwLowDateTime;
}

std::uint64_t processCreationTime(DWORD pid) {
    ScopedHandle process{OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, FALSE, pid)};
    return process.value ? creationTime(process.value) : 0;
}

std::string hexDigest(const unsigned char* bytes, std::size_t count) {
    constexpr char digits[] = "0123456789abcdef";
    std::string result;
    result.reserve(count * 2);
    for (std::size_t i = 0; i < count; ++i) {
        result += digits[bytes[i] >> 4];
        result += digits[bytes[i] & 15];
    }
    return result;
}

// The existing sha256File reads the whole file into memory. Use the native
// streaming primitive for executable files, with a bounded file size/buffer.
std::string executableDigest(HANDLE file) {
    LARGE_INTEGER size{};
    if (!GetFileSizeEx(file, &size) || size.QuadPart <= 0 || size.QuadPart > 256LL * 1024 * 1024) return {};
    LARGE_INTEGER beginning{};
    if (!SetFilePointerEx(file, beginning, nullptr, FILE_BEGIN)) return {};
    struct Hash {
        BCRYPT_ALG_HANDLE algorithm = nullptr;
        BCRYPT_HASH_HANDLE value = nullptr;
        ~Hash() {
            if (value) BCryptDestroyHash(value);
            if (algorithm) BCryptCloseAlgorithmProvider(algorithm, 0);
        }
    } hash;
    if (BCryptOpenAlgorithmProvider(&hash.algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0) < 0 ||
        BCryptCreateHash(hash.algorithm, &hash.value, nullptr, 0, nullptr, 0, 0) < 0) return {};
    std::array<unsigned char, 64 * 1024> buffer{};
    std::uint64_t total = 0;
    for (;;) {
        DWORD read = 0;
        if (!ReadFile(file, buffer.data(), static_cast<DWORD>(buffer.size()), &read, nullptr)) return {};
        if (read == 0) break;
        total += read;
        if (total > static_cast<std::uint64_t>(size.QuadPart) ||
            BCryptHashData(hash.value, buffer.data(), read, 0) < 0) return {};
    }
    std::array<unsigned char, 32> digest{};
    if (total != static_cast<std::uint64_t>(size.QuadPart) ||
        BCryptFinishHash(hash.value, digest.data(), static_cast<ULONG>(digest.size()), 0) < 0) return {};
    return hexDigest(digest.data(), digest.size());
}

std::string verifiedSigner(HANDLE file, const wchar_t* path) {
    LARGE_INTEGER beginning{};
    if (!SetFilePointerEx(file, beginning, nullptr, FILE_BEGIN)) return {};
    WINTRUST_FILE_INFO information{};
    information.cbStruct = sizeof(information);
    information.pcwszFilePath = path;
    information.hFile = file;
    struct Trust {
        GUID action = WINTRUST_ACTION_GENERIC_VERIFY_V2;
        WINTRUST_DATA data{};
        ~Trust() {
            data.dwStateAction = WTD_STATEACTION_CLOSE;
            WinVerifyTrust(nullptr, &action, &data);
        }
    } trust;
    trust.data.cbStruct = sizeof(trust.data);
    trust.data.dwUIChoice = WTD_UI_NONE;
    trust.data.fdwRevocationChecks = WTD_REVOKE_WHOLECHAIN;
    trust.data.dwUnionChoice = WTD_CHOICE_FILE;
    trust.data.pFile = &information;
    trust.data.dwStateAction = WTD_STATEACTION_VERIFY;
    // No network request or trust dialog from background detection. Missing
    // cached revocation/chain proof is a rejection, never a guessed publisher.
    trust.data.dwProvFlags = WTD_CACHE_ONLY_URL_RETRIEVAL | WTD_REVOCATION_CHECK_CHAIN_EXCLUDE_ROOT;
    if (WinVerifyTrust(nullptr, &trust.action, &trust.data) != ERROR_SUCCESS) return {};
    auto* provider = WTHelperProvDataFromStateData(trust.data.hWVTStateData);
    auto* signer = provider ? WTHelperGetProvSignerFromChain(provider, 0, FALSE, 0) : nullptr;
    auto* certificate = signer ? WTHelperGetProvCertFromChain(signer, 0) : nullptr;
    if (!certificate || !certificate->pCert || certificate->pCert->cbCertEncoded == 0 ||
        certificate->pCert->cbCertEncoded > 64 * 1024) return {};
    return sha256(std::string_view(reinterpret_cast<const char*>(certificate->pCert->pbCertEncoded),
                                  certificate->pCert->cbCertEncoded));
}

struct ActiveSession {
    ComPtr<IAudioSessionControl2> control;
    DWORD processId = 0;
    std::uint64_t processCreatedAt = 0;
    EDataFlow flow = eRender;
};

bool collectSessions(IMMDeviceEnumerator* enumerator, EDataFlow flow, std::vector<ActiveSession>& result) {
    ComPtr<IMMDeviceCollection> devices;
    UINT count = 0;
    if (FAILED(enumerator->EnumAudioEndpoints(flow, DEVICE_STATE_ACTIVE, &devices)) ||
        FAILED(devices->GetCount(&count)) || count > 64) return false;
    for (UINT index = 0; index < count; ++index) {
        ComPtr<IMMDevice> device;
        ComPtr<IAudioSessionManager2> manager;
        ComPtr<IAudioSessionEnumerator> sessions;
        int sessionCount = 0;
        if (FAILED(devices->Item(index, &device)) ||
            FAILED(device->Activate(__uuidof(IAudioSessionManager2), CLSCTX_ALL, nullptr,
                                    reinterpret_cast<void**>(manager.GetAddressOf()))) ||
            FAILED(manager->GetSessionEnumerator(&sessions)) ||
            FAILED(sessions->GetCount(&sessionCount)) || sessionCount < 0 || sessionCount > 512) return false;
        for (int sessionIndex = 0; sessionIndex < sessionCount; ++sessionIndex) {
            ComPtr<IAudioSessionControl> control;
            ComPtr<IAudioSessionControl2> control2;
            AudioSessionState state{};
            DWORD pid = 0;
            if (FAILED(sessions->GetSession(sessionIndex, &control)) || FAILED(control.As(&control2)) ||
                FAILED(control2->GetState(&state))) return false;
            if (state != AudioSessionStateActive) continue;
            // AUDCLNT_S_NO_SINGLE_PROCESS is not exact ownership proof.
            if (control2->GetProcessId(&pid) != S_OK || pid == 0 || pid == GetCurrentProcessId() ||
                control2->IsSystemSoundsSession() != S_FALSE) continue;
            const auto created = processCreationTime(pid);
            if (!created) continue;
            if (result.size() >= 512) return false;
            result.push_back({control2, pid, created, flow});
        }
    }
    return true;
}
#endif
} // namespace

bool WindowsTargetDetector::isPromptCandidate(const TargetObservation& observation,
                                               const VerifiedTargetRegistry& registry) noexcept {
    return observation.processId != 0 && observation.processCreatedAt != 0 && observation.signatureVerified &&
        observation.hasRenderStream && observation.hasCaptureStream &&
        registry.contains(observation.identity);
}

std::optional<TargetObservation> WindowsTargetDetector::inspectProcess(std::uint32_t processId) {
#ifndef _WIN32
    (void)processId;
    return std::nullopt;
#else
    if (processId == 0 || processId == GetCurrentProcessId()) return std::nullopt;
    ScopedHandle process{OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, FALSE, processId)};
    if (!process.value) return std::nullopt;
    const auto created = creationTime(process.value);
    if (!created) return std::nullopt;
    std::array<wchar_t, 32768> path{};
    DWORD characters = static_cast<DWORD>(path.size());
    if (!QueryFullProcessImageNameW(process.value, 0, path.data(), &characters) || characters == 0 ||
        characters >= path.size()) return std::nullopt;
    // Hold the actual image file against writes/replacement through hashing and
    // signature validation; no live path is exported or logged.
    ScopedHandle file{CreateFileW(path.data(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING,
                                 FILE_FLAG_SEQUENTIAL_SCAN | FILE_FLAG_OPEN_REPARSE_POINT, nullptr)};
    BY_HANDLE_FILE_INFORMATION info{};
    if (file.value == INVALID_HANDLE_VALUE || !GetFileInformationByHandle(file.value, &info) ||
        (info.dwFileAttributes & (FILE_ATTRIBUTE_REPARSE_POINT | FILE_ATTRIBUTE_DIRECTORY)) != 0) return std::nullopt;
    const auto executable = executableDigest(file.value);
    if (executable.empty()) return std::nullopt;
    const auto publisher = verifiedSigner(file.value, path.data());
    if (publisher.empty() || creationTime(process.value) != created) return std::nullopt;
    TargetObservation observation;
    observation.identity.executableFingerprint = executable;
    observation.identity.publisherFingerprint = publisher;
    observation.processId = processId;
    observation.processCreatedAt = created;
    observation.signatureVerified = true;
    return observation;
#endif
}

TargetDetectionSnapshot WindowsTargetDetector::snapshot(const VerifiedTargetRegistry& registry) {
    TargetDetectionSnapshot result;
    result.observedAt = DetectionClock::now();
    if (registry.targets().empty()) {
        result.status = TargetDetectionStatus::noVerifiedTargets;
        return result;
    }
#ifdef _WIN32
    result.status = TargetDetectionStatus::enumerationFailed;
    const auto initialized = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    if (FAILED(initialized)) return result;
    struct Apartment { ~Apartment() { CoUninitialize(); } } apartment;
    ComPtr<IMMDeviceEnumerator> enumerator;
    if (FAILED(CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr, CLSCTX_ALL, IID_PPV_ARGS(&enumerator))))
        return result;
    std::vector<ActiveSession> sessions;
    if (!collectSessions(enumerator.Get(), eRender, sessions) || !collectSessions(enumerator.Get(), eCapture, sessions))
        return result;
    std::map<DWORD, unsigned> flows;
    for (const auto& session : sessions) flows[session.processId] |= session.flow == eRender ? 1U : 2U;
    for (const auto& [pid, activeFlows] : flows) {
        if (activeFlows != 3) continue; // Playback, notifications or mic-only activity are insufficient.
        auto observation = inspectProcess(pid);
        if (!observation) continue;
        const auto* approved = registry.find(observation->identity.executableFingerprint,
                                             observation->identity.publisherFingerprint);
        if (!approved) continue;
        observation->identity = *approved;
        // Recheck both sessions after potentially expensive signature work.
        for (const auto& session : sessions) {
            if (session.processId != pid || session.processCreatedAt != observation->processCreatedAt) continue;
            AudioSessionState state{};
            DWORD currentPid = 0;
            if (session.control->GetState(&state) != S_OK || state != AudioSessionStateActive ||
                session.control->GetProcessId(&currentPid) != S_OK || currentPid != pid) continue;
            if (session.flow == eRender) observation->hasRenderStream = true;
            else observation->hasCaptureStream = true;
        }
        if (processCreationTime(pid) == observation->processCreatedAt && isPromptCandidate(*observation, registry))
            result.observations.push_back(std::move(*observation));
    }
    result.status = TargetDetectionStatus::ready;
    result.observedAt = DetectionClock::now();
#endif
    return result;
}

} // namespace graf::windows
