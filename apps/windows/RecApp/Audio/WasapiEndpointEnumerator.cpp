#include "WasapiEndpointEnumerator.h"

#include <algorithm>
#include <cctype>

#ifdef _WIN32
#include <audioclient.h>
#include <functiondiscoverykeys_devpkey.h>
#include <mmdeviceapi.h>
#include <propvarutil.h>
#include <wrl/client.h>
#include <windows.h>
#endif

namespace graf::windows {
namespace {

#ifdef _WIN32
bool containsFolded(std::string value, const char* needle) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    std::string foldedNeedle(needle);
    std::transform(foldedNeedle.begin(), foldedNeedle.end(), foldedNeedle.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return value.find(foldedNeedle) != std::string::npos;
}
#endif

#ifdef _WIN32
std::string narrow(const wchar_t* value) {
    if (value == nullptr) return {};
    const int size = WideCharToMultiByte(CP_UTF8, 0, value, -1, nullptr, 0, nullptr, nullptr);
    if (size <= 1) return {};
    std::string result(static_cast<std::size_t>(size - 1), '\0');
    WideCharToMultiByte(CP_UTF8, 0, value, -1, result.data(), static_cast<int>(result.size()), nullptr, nullptr);
    return result;
}

std::string deviceId(Microsoft::WRL::ComPtr<IMMDevice> device) {
    LPWSTR raw = nullptr;
    if (FAILED(device->GetId(&raw)) || raw == nullptr) return {};
    std::string result = narrow(raw);
    CoTaskMemFree(raw);
    return result;
}

std::string propertyString(Microsoft::WRL::ComPtr<IPropertyStore> properties, REFPROPERTYKEY key) {
    PROPVARIANT value;
    PropVariantInit(&value);
    std::string result;
    if (SUCCEEDED(properties->GetValue(key, &value)) && value.vt == VT_LPWSTR) {
        result = narrow(value.pwszVal);
    }
    PropVariantClear(&value);
    return result;
}
#endif

} // namespace

EndpointEnumerationResult WasapiEndpointEnumerator::snapshot() const {
#ifndef _WIN32
    return {EndpointEnumerationError::platformUnavailable, {}};
#else
    EndpointEnumerationResult result;
    Microsoft::WRL::ComPtr<IMMDeviceEnumerator> enumerator;
    if (FAILED(CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr, CLSCTX_ALL,
                                IID_PPV_ARGS(&enumerator)))) {
        result.error = EndpointEnumerationError::enumerationFailed;
        return result;
    }

    for (const auto flow : {WasapiDataFlow::render, WasapiDataFlow::capture}) {
        const EDataFlow nativeFlow = flow == WasapiDataFlow::render ? eRender : eCapture;
        Microsoft::WRL::ComPtr<IMMDevice> defaultDevice;
        const bool hasDefault = SUCCEEDED(enumerator->GetDefaultAudioEndpoint(nativeFlow, eConsole,
                                                                                &defaultDevice));
        const auto defaultId = hasDefault ? deviceId(defaultDevice) : std::string{};
        Microsoft::WRL::ComPtr<IMMDeviceCollection> collection;
        if (FAILED(enumerator->EnumAudioEndpoints(nativeFlow, DEVICE_STATE_ACTIVE, &collection))) {
            result.error = EndpointEnumerationError::enumerationFailed;
            return result;
        }
        UINT count = 0;
        collection->GetCount(&count);
        for (UINT index = 0; index < count; ++index) {
            Microsoft::WRL::ComPtr<IMMDevice> device;
            if (FAILED(collection->Item(index, &device))) continue;
            Microsoft::WRL::ComPtr<IPropertyStore> properties;
            if (FAILED(device->OpenPropertyStore(STGM_READ, &properties))) continue;
            WasapiEndpointSnapshot item;
            item.flow = flow;
            item.stableId = deviceId(device);
            item.friendlyName = propertyString(properties, PKEY_Device_FriendlyName);
            item.isDefault = !item.stableId.empty() && item.stableId == defaultId;
            item.isPhysicalMicrophone = flow == WasapiDataFlow::capture &&
                !containsFolded(item.friendlyName, "stereo mix") &&
                !containsFolded(item.friendlyName, "virtual") &&
                !containsFolded(item.friendlyName, "cable");
            item.routeGeneration = 1;
            result.endpoints.push_back(std::move(item));
        }
    }
    if (result.endpoints.empty()) result.error = EndpointEnumerationError::noDefaultEndpoint;
    return result;
#endif
}

bool WasapiEndpointEnumerator::isAllowedMicrophone(const WasapiEndpointSnapshot& endpoint) noexcept {
    return endpoint.flow == WasapiDataFlow::capture && endpoint.isPhysicalMicrophone &&
           !endpoint.stableId.empty();
}

} // namespace graf::windows
