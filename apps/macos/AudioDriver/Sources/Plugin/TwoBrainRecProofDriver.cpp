#include <CoreAudio/AudioHardware.h>
#include <CoreAudio/AudioServerPlugIn.h>
#include <CoreFoundation/CoreFoundation.h>

#include <fcntl.h>
#include <unistd.h>

#include <atomic>
#include <cstring>
#include <ctime>

extern AudioServerPlugInDriverInterface gDriverInterface;
extern AudioServerPlugInDriverInterface* gDriverInterfacePointer;

namespace {

constexpr AudioObjectID kPlugInObject = kAudioObjectPlugInObject;
constexpr AudioObjectID kMicDevice = 2;
constexpr AudioObjectID kSpeakerDevice = 3;
constexpr AudioObjectID kMicStream = 4;
constexpr AudioObjectID kSpeakerStream = 5;
constexpr Float64 kSampleRate = 48000.0;
constexpr UInt32 kBufferFrameSize = 512;
constexpr UInt32 kZeroTimeStampPeriod = 24000;

std::atomic<UInt32> gReferenceCount{1};
AudioServerPlugInHostRef gHost = nullptr;

void Trace(const char* message) {
    const int fd = open("/tmp/2brain-rec-proof-driver.trace", O_CREAT | O_WRONLY | O_APPEND, 0644);
    if (fd < 0) {
        return;
    }

    std::time_t now = std::time(nullptr);
    char buffer[512];
    const int count = snprintf(buffer, sizeof(buffer), "%lld %s\n", static_cast<long long>(now), message);
    if (count > 0) {
        write(fd, buffer, static_cast<size_t>(count));
    }
    close(fd);
}

void FourCC(UInt32 value, char out[5]) {
    out[0] = static_cast<char>((value >> 24) & 0xFF);
    out[1] = static_cast<char>((value >> 16) & 0xFF);
    out[2] = static_cast<char>((value >> 8) & 0xFF);
    out[3] = static_cast<char>(value & 0xFF);
    out[4] = '\0';
    for (int index = 0; index < 4; ++index) {
        if (out[index] < 32 || out[index] > 126) {
            out[index] = '?';
        }
    }
}

void TraceProperty(const char* operation, AudioObjectID object_id, const AudioObjectPropertyAddress* address) {
    if (address == nullptr) {
        Trace(operation);
        return;
    }

    char selector[5];
    char scope[5];
    FourCC(address->mSelector, selector);
    FourCC(address->mScope, scope);

    char buffer[256];
    snprintf(
        buffer,
        sizeof(buffer),
        "%s object=%u selector=%s scope=%s element=%u",
        operation,
        object_id,
        selector,
        scope,
        address->mElement
    );
    Trace(buffer);
}

__attribute__((constructor)) void TraceBundleLoaded() {
    Trace("bundle constructor loaded");
}

bool IsDevice(AudioObjectID object_id) {
    return object_id == kMicDevice || object_id == kSpeakerDevice;
}

bool IsStream(AudioObjectID object_id) {
    return object_id == kMicStream || object_id == kSpeakerStream;
}

bool IsInputScope(AudioObjectPropertyScope scope) {
    return scope == kAudioObjectPropertyScopeInput || scope == kAudioObjectPropertyScopeGlobal;
}

bool IsOutputScope(AudioObjectPropertyScope scope) {
    return scope == kAudioObjectPropertyScopeOutput || scope == kAudioObjectPropertyScopeGlobal;
}

CFStringRef CopyString(const char* value) {
    return CFStringCreateWithCString(kCFAllocatorDefault, value, kCFStringEncodingUTF8);
}

const char* DeviceName(AudioObjectID object_id) {
    return object_id == kMicDevice ? "2brain Rec Microphone" : "2brain Rec Speaker";
}

const char* DeviceUID(AudioObjectID object_id) {
    return object_id == kMicDevice ? "pro.2brain.rec.microphone" : "pro.2brain.rec.speaker";
}

AudioObjectID OwnerForObject(AudioObjectID object_id) {
    if (IsDevice(object_id)) {
        return kPlugInObject;
    }
    if (object_id == kMicStream) {
        return kMicDevice;
    }
    if (object_id == kSpeakerStream) {
        return kSpeakerDevice;
    }
    return kAudioObjectUnknown;
}

AudioClassID ClassForObject(AudioObjectID object_id) {
    if (object_id == kPlugInObject) {
        return kAudioPlugInClassID;
    }
    if (IsDevice(object_id)) {
        return kAudioDeviceClassID;
    }
    if (IsStream(object_id)) {
        return kAudioStreamClassID;
    }
    return kAudioObjectClassIDWildcard;
}

AudioClassID BaseClassForObject(AudioObjectID object_id) {
    if (object_id == kPlugInObject) {
        return kAudioObjectClassID;
    }
    if (IsDevice(object_id) || IsStream(object_id)) {
        return kAudioObjectClassID;
    }
    return kAudioObjectClassIDWildcard;
}

AudioStreamBasicDescription StreamFormat() {
    AudioStreamBasicDescription format{};
    format.mSampleRate = kSampleRate;
    format.mFormatID = kAudioFormatLinearPCM;
    format.mFormatFlags = kAudioFormatFlagIsFloat | kAudioFormatFlagIsPacked | kAudioFormatFlagsNativeEndian;
    format.mBytesPerPacket = sizeof(Float32) * 2;
    format.mFramesPerPacket = 1;
    format.mBytesPerFrame = sizeof(Float32) * 2;
    format.mChannelsPerFrame = 2;
    format.mBitsPerChannel = sizeof(Float32) * 8;
    return format;
}

template <typename T>
OSStatus WriteScalar(UInt32 in_data_size, UInt32* out_data_size, void* out_data, T value) {
    if (in_data_size < sizeof(T)) {
        return kAudioHardwareBadPropertySizeError;
    }
    *reinterpret_cast<T*>(out_data) = value;
    *out_data_size = sizeof(T);
    return kAudioHardwareNoError;
}

OSStatus WriteCFString(UInt32 in_data_size, UInt32* out_data_size, void* out_data, CFStringRef value) {
    if (in_data_size < sizeof(CFStringRef)) {
        CFRelease(value);
        return kAudioHardwareBadPropertySizeError;
    }
    *reinterpret_cast<CFStringRef*>(out_data) = value;
    *out_data_size = sizeof(CFStringRef);
    return kAudioHardwareNoError;
}

OSStatus WriteObjectList(UInt32 in_data_size, UInt32* out_data_size, void* out_data, const AudioObjectID* objects, UInt32 count) {
    const UInt32 byte_count = count * sizeof(AudioObjectID);
    if (in_data_size < byte_count) {
        return kAudioHardwareBadPropertySizeError;
    }
    if (byte_count > 0) {
        std::memcpy(out_data, objects, byte_count);
    }
    *out_data_size = byte_count;
    return kAudioHardwareNoError;
}

OSStatus WriteEmptyList(UInt32* out_data_size) {
    *out_data_size = 0;
    return kAudioHardwareNoError;
}

UInt32 DeviceStreamCount(AudioObjectID device_id, AudioObjectPropertyScope scope) {
    if (device_id == kMicDevice && IsInputScope(scope)) {
        return 1;
    }
    if (device_id == kSpeakerDevice && IsOutputScope(scope)) {
        return 1;
    }
    return 0;
}

AudioObjectID DeviceStream(AudioObjectID device_id) {
    return device_id == kMicDevice ? kMicStream : kSpeakerStream;
}

OSStatus WriteStreamConfiguration(AudioObjectID device_id, AudioObjectPropertyScope scope, UInt32 in_data_size, UInt32* out_data_size, void* out_data) {
    const UInt32 stream_count = DeviceStreamCount(device_id, scope);
    const UInt32 byte_count = offsetof(AudioBufferList, mBuffers) + (stream_count == 0 ? 0 : sizeof(AudioBuffer));
    if (in_data_size < byte_count) {
        return kAudioHardwareBadPropertySizeError;
    }

    auto* buffer_list = reinterpret_cast<AudioBufferList*>(out_data);
    buffer_list->mNumberBuffers = stream_count;
    if (stream_count == 1) {
        buffer_list->mBuffers[0].mNumberChannels = 2;
        buffer_list->mBuffers[0].mDataByteSize = 0;
        buffer_list->mBuffers[0].mData = nullptr;
    }
    *out_data_size = byte_count;
    return kAudioHardwareNoError;
}

bool HasObject(AudioObjectID object_id) {
    return object_id == kPlugInObject || IsDevice(object_id) || IsStream(object_id);
}

bool HasPropertyForObject(AudioObjectID object_id, const AudioObjectPropertyAddress* address) {
    if (!HasObject(object_id) || address == nullptr) {
        return false;
    }

    switch (address->mSelector) {
    case kAudioObjectPropertyBaseClass:
    case kAudioObjectPropertyClass:
    case kAudioObjectPropertyOwner:
    case kAudioObjectPropertyName:
    case kAudioObjectPropertyManufacturer:
    case kAudioObjectPropertyOwnedObjects:
        return true;
    default:
        break;
    }

    if (object_id == kPlugInObject) {
        switch (address->mSelector) {
        case kAudioPlugInPropertyBundleID:
        case kAudioPlugInPropertyDeviceList:
        case kAudioPlugInPropertyBoxList:
        case kAudioPlugInPropertyTranslateUIDToDevice:
            return true;
        default:
            return false;
        }
    }

    if (IsDevice(object_id)) {
        switch (address->mSelector) {
        case kAudioDevicePropertyDeviceUID:
        case kAudioDevicePropertyModelUID:
        case kAudioDevicePropertyTransportType:
        case kAudioDevicePropertyDeviceIsAlive:
        case kAudioDevicePropertyDeviceIsRunning:
        case kAudioDevicePropertyDeviceCanBeDefaultDevice:
        case kAudioDevicePropertyDeviceCanBeDefaultSystemDevice:
        case kAudioDevicePropertyLatency:
        case kAudioDevicePropertyStreams:
        case kAudioDevicePropertySafetyOffset:
        case kAudioDevicePropertyNominalSampleRate:
        case kAudioDevicePropertyAvailableNominalSampleRates:
        case kAudioDevicePropertyStreamConfiguration:
        case kAudioDevicePropertyBufferFrameSize:
        case kAudioDevicePropertyBufferFrameSizeRange:
        case kAudioDevicePropertyZeroTimeStampPeriod:
        case kAudioDevicePropertyClockAlgorithm:
        case kAudioDevicePropertyClockIsStable:
        case kAudioDevicePropertyIsHidden:
            return true;
        default:
            return false;
        }
    }

    if (IsStream(object_id)) {
        switch (address->mSelector) {
        case kAudioStreamPropertyIsActive:
        case kAudioStreamPropertyDirection:
        case kAudioStreamPropertyTerminalType:
        case kAudioStreamPropertyStartingChannel:
        case kAudioStreamPropertyLatency:
        case kAudioStreamPropertyVirtualFormat:
        case kAudioStreamPropertyAvailableVirtualFormats:
        case kAudioStreamPropertyPhysicalFormat:
        case kAudioStreamPropertyAvailablePhysicalFormats:
            return true;
        default:
            return false;
        }
    }

    return false;
}

OSStatus QueryInterface(void*, REFIID in_uuid, LPVOID* out_interface) {
    Trace("QueryInterface called");
    if (out_interface == nullptr) {
        return E_POINTER;
    }
    *out_interface = nullptr;

    CFUUIDRef requested_uuid = CFUUIDCreateFromUUIDBytes(kCFAllocatorDefault, in_uuid);
    const Boolean matches_driver = CFEqual(requested_uuid, kAudioServerPlugInDriverInterfaceUUID);
    const Boolean matches_unknown = CFEqual(requested_uuid, IUnknownUUID);
    CFRelease(requested_uuid);

    if (matches_driver || matches_unknown) {
        gReferenceCount.fetch_add(1);
        *out_interface = &::gDriverInterfacePointer;
        return S_OK;
    }
    return E_NOINTERFACE;
}

ULONG AddRef(void*) {
    return gReferenceCount.fetch_add(1) + 1;
}

ULONG Release(void*) {
    const UInt32 count = gReferenceCount.fetch_sub(1) - 1;
    return count;
}

OSStatus Initialize(AudioServerPlugInDriverRef, AudioServerPlugInHostRef in_host) {
    Trace("Initialize called");
    gHost = in_host;
    return kAudioHardwareNoError;
}

OSStatus CreateDevice(AudioServerPlugInDriverRef, CFDictionaryRef, const AudioServerPlugInClientInfo*, AudioObjectID*) {
    return kAudioHardwareUnsupportedOperationError;
}

OSStatus DestroyDevice(AudioServerPlugInDriverRef, AudioObjectID) {
    return kAudioHardwareUnsupportedOperationError;
}

OSStatus AddDeviceClient(AudioServerPlugInDriverRef, AudioObjectID, const AudioServerPlugInClientInfo*) {
    return kAudioHardwareNoError;
}

OSStatus RemoveDeviceClient(AudioServerPlugInDriverRef, AudioObjectID, const AudioServerPlugInClientInfo*) {
    return kAudioHardwareNoError;
}

OSStatus PerformDeviceConfigurationChange(AudioServerPlugInDriverRef, AudioObjectID, UInt64, void*) {
    return kAudioHardwareNoError;
}

OSStatus AbortDeviceConfigurationChange(AudioServerPlugInDriverRef, AudioObjectID, UInt64, void*) {
    return kAudioHardwareNoError;
}

Boolean HasProperty(AudioServerPlugInDriverRef, AudioObjectID in_object_id, pid_t, const AudioObjectPropertyAddress* in_address) {
    TraceProperty("HasProperty called", in_object_id, in_address);
    const Boolean has_property = HasPropertyForObject(in_object_id, in_address);
    Trace(has_property ? "HasProperty result=true" : "HasProperty result=false");
    return has_property;
}

OSStatus IsPropertySettable(AudioServerPlugInDriverRef, AudioObjectID in_object_id, pid_t, const AudioObjectPropertyAddress* in_address, Boolean* out_is_settable) {
    TraceProperty("IsPropertySettable called", in_object_id, in_address);
    if (out_is_settable == nullptr) {
        return kAudioHardwareIllegalOperationError;
    }
    if (!HasPropertyForObject(in_object_id, in_address)) {
        return kAudioHardwareUnknownPropertyError;
    }
    *out_is_settable = false;
    return kAudioHardwareNoError;
}

OSStatus GetPropertyDataSize(AudioServerPlugInDriverRef, AudioObjectID in_object_id, pid_t, const AudioObjectPropertyAddress* in_address, UInt32, const void*, UInt32* out_data_size) {
    TraceProperty("GetPropertyDataSize called", in_object_id, in_address);
    if (out_data_size == nullptr || in_address == nullptr) {
        return kAudioHardwareIllegalOperationError;
    }
    if (!HasPropertyForObject(in_object_id, in_address)) {
        return kAudioHardwareUnknownPropertyError;
    }

    switch (in_address->mSelector) {
    case kAudioObjectPropertyBaseClass:
    case kAudioObjectPropertyClass:
    case kAudioObjectPropertyOwner:
    case kAudioDevicePropertyTransportType:
    case kAudioDevicePropertyDeviceIsAlive:
    case kAudioDevicePropertyDeviceIsRunning:
    case kAudioDevicePropertyDeviceCanBeDefaultDevice:
    case kAudioDevicePropertyDeviceCanBeDefaultSystemDevice:
    case kAudioDevicePropertyLatency:
    case kAudioDevicePropertySafetyOffset:
    case kAudioDevicePropertyBufferFrameSize:
    case kAudioDevicePropertyClockAlgorithm:
    case kAudioDevicePropertyClockIsStable:
    case kAudioDevicePropertyZeroTimeStampPeriod:
    case kAudioDevicePropertyIsHidden:
    case kAudioStreamPropertyIsActive:
    case kAudioStreamPropertyDirection:
    case kAudioStreamPropertyTerminalType:
    case kAudioStreamPropertyStartingChannel:
        *out_data_size = sizeof(UInt32);
        return kAudioHardwareNoError;
    case kAudioObjectPropertyName:
    case kAudioObjectPropertyManufacturer:
    case kAudioPlugInPropertyBundleID:
    case kAudioDevicePropertyDeviceUID:
    case kAudioDevicePropertyModelUID:
        *out_data_size = sizeof(CFStringRef);
        return kAudioHardwareNoError;
    case kAudioPlugInPropertyDeviceList:
        *out_data_size = sizeof(AudioObjectID) * 2;
        return kAudioHardwareNoError;
    case kAudioObjectPropertyOwnedObjects:
        if (in_object_id == kPlugInObject) {
            *out_data_size = sizeof(AudioObjectID) * 2;
        } else if (IsDevice(in_object_id)) {
            *out_data_size = sizeof(AudioObjectID);
        } else {
            *out_data_size = 0;
        }
        return kAudioHardwareNoError;
    case kAudioPlugInPropertyBoxList:
        *out_data_size = 0;
        return kAudioHardwareNoError;
    case kAudioPlugInPropertyTranslateUIDToDevice:
        *out_data_size = sizeof(AudioObjectID);
        return kAudioHardwareNoError;
    case kAudioDevicePropertyStreams:
        *out_data_size = sizeof(AudioObjectID) * DeviceStreamCount(in_object_id, in_address->mScope);
        return kAudioHardwareNoError;
    case kAudioDevicePropertyNominalSampleRate:
        *out_data_size = sizeof(Float64);
        return kAudioHardwareNoError;
    case kAudioDevicePropertyAvailableNominalSampleRates:
        *out_data_size = sizeof(AudioValueRange);
        return kAudioHardwareNoError;
    case kAudioDevicePropertyBufferFrameSizeRange:
        *out_data_size = sizeof(AudioValueRange);
        return kAudioHardwareNoError;
    case kAudioDevicePropertyStreamConfiguration:
        *out_data_size = offsetof(AudioBufferList, mBuffers) + (DeviceStreamCount(in_object_id, in_address->mScope) == 0 ? 0 : sizeof(AudioBuffer));
        return kAudioHardwareNoError;
    case kAudioStreamPropertyVirtualFormat:
    case kAudioStreamPropertyPhysicalFormat:
        *out_data_size = sizeof(AudioStreamBasicDescription);
        return kAudioHardwareNoError;
    case kAudioStreamPropertyAvailableVirtualFormats:
    case kAudioStreamPropertyAvailablePhysicalFormats:
        *out_data_size = sizeof(AudioStreamRangedDescription);
        return kAudioHardwareNoError;
    default:
        return kAudioHardwareUnknownPropertyError;
    }
}

OSStatus GetPropertyData(AudioServerPlugInDriverRef, AudioObjectID in_object_id, pid_t, const AudioObjectPropertyAddress* in_address, UInt32 in_qualifier_data_size, const void* in_qualifier_data, UInt32 in_data_size, UInt32* out_data_size, void* out_data) {
    TraceProperty("GetPropertyData called", in_object_id, in_address);
    if (out_data_size == nullptr || out_data == nullptr || in_address == nullptr) {
        return kAudioHardwareIllegalOperationError;
    }
    if (!HasPropertyForObject(in_object_id, in_address)) {
        return kAudioHardwareUnknownPropertyError;
    }

    switch (in_address->mSelector) {
    case kAudioObjectPropertyBaseClass:
        return WriteScalar(in_data_size, out_data_size, out_data, BaseClassForObject(in_object_id));
    case kAudioObjectPropertyClass:
        return WriteScalar(in_data_size, out_data_size, out_data, ClassForObject(in_object_id));
    case kAudioObjectPropertyOwner:
        return WriteScalar(in_data_size, out_data_size, out_data, OwnerForObject(in_object_id));
    case kAudioObjectPropertyName:
        if (in_object_id == kPlugInObject) {
            return WriteCFString(in_data_size, out_data_size, out_data, CopyString("2brain Rec Proof Driver"));
        }
        if (IsDevice(in_object_id)) {
            return WriteCFString(in_data_size, out_data_size, out_data, CopyString(DeviceName(in_object_id)));
        }
        return WriteCFString(in_data_size, out_data_size, out_data, CopyString(in_object_id == kMicStream ? "2brain Rec Microphone Stream" : "2brain Rec Speaker Stream"));
    case kAudioObjectPropertyManufacturer:
        return WriteCFString(in_data_size, out_data_size, out_data, CopyString("2brain"));
    case kAudioObjectPropertyOwnedObjects:
        if (in_object_id == kPlugInObject) {
            const AudioObjectID devices[] = {kMicDevice, kSpeakerDevice};
            return WriteObjectList(in_data_size, out_data_size, out_data, devices, 2);
        }
        if (IsDevice(in_object_id)) {
            const AudioObjectID stream = DeviceStream(in_object_id);
            return WriteObjectList(in_data_size, out_data_size, out_data, &stream, 1);
        }
        return WriteEmptyList(out_data_size);
    case kAudioPlugInPropertyBundleID:
        return WriteCFString(in_data_size, out_data_size, out_data, CopyString("pro.2brain.rec.proof.driver"));
    case kAudioPlugInPropertyDeviceList: {
        const AudioObjectID devices[] = {kMicDevice, kSpeakerDevice};
        return WriteObjectList(in_data_size, out_data_size, out_data, devices, 2);
    }
    case kAudioPlugInPropertyBoxList:
        return WriteEmptyList(out_data_size);
    case kAudioPlugInPropertyTranslateUIDToDevice: {
        AudioObjectID translated = kAudioObjectUnknown;
        if (in_qualifier_data_size == sizeof(CFStringRef) && in_qualifier_data != nullptr) {
            auto uid = *reinterpret_cast<const CFStringRef*>(in_qualifier_data);
            if (CFStringCompare(uid, CFSTR("pro.2brain.rec.microphone"), 0) == kCFCompareEqualTo) {
                translated = kMicDevice;
            } else if (CFStringCompare(uid, CFSTR("pro.2brain.rec.speaker"), 0) == kCFCompareEqualTo) {
                translated = kSpeakerDevice;
            }
        }
        return WriteScalar(in_data_size, out_data_size, out_data, translated);
    }
    case kAudioDevicePropertyDeviceUID:
        return WriteCFString(in_data_size, out_data_size, out_data, CopyString(DeviceUID(in_object_id)));
    case kAudioDevicePropertyModelUID:
        return WriteCFString(in_data_size, out_data_size, out_data, CopyString("pro.2brain.rec.proof.model"));
    case kAudioDevicePropertyTransportType:
        return WriteScalar(in_data_size, out_data_size, out_data, static_cast<UInt32>(kAudioDeviceTransportTypeVirtual));
    case kAudioDevicePropertyDeviceIsAlive:
    case kAudioDevicePropertyDeviceCanBeDefaultDevice:
    case kAudioDevicePropertyClockIsStable:
        return WriteScalar(in_data_size, out_data_size, out_data, static_cast<UInt32>(1));
    case kAudioDevicePropertyDeviceIsRunning:
    case kAudioDevicePropertyDeviceCanBeDefaultSystemDevice:
    case kAudioDevicePropertyLatency:
    case kAudioDevicePropertySafetyOffset:
    case kAudioDevicePropertyIsHidden:
        return WriteScalar(in_data_size, out_data_size, out_data, static_cast<UInt32>(0));
    case kAudioDevicePropertyStreams:
        if (DeviceStreamCount(in_object_id, in_address->mScope) == 0) {
            return WriteEmptyList(out_data_size);
        } else {
            const AudioObjectID stream = DeviceStream(in_object_id);
            return WriteObjectList(in_data_size, out_data_size, out_data, &stream, 1);
        }
    case kAudioDevicePropertyNominalSampleRate:
        return WriteScalar(in_data_size, out_data_size, out_data, kSampleRate);
    case kAudioDevicePropertyAvailableNominalSampleRates: {
        AudioValueRange range{kSampleRate, kSampleRate};
        return WriteScalar(in_data_size, out_data_size, out_data, range);
    }
    case kAudioDevicePropertyStreamConfiguration:
        return WriteStreamConfiguration(in_object_id, in_address->mScope, in_data_size, out_data_size, out_data);
    case kAudioDevicePropertyBufferFrameSize:
        return WriteScalar(in_data_size, out_data_size, out_data, kBufferFrameSize);
    case kAudioDevicePropertyBufferFrameSizeRange: {
        AudioValueRange range{128.0, 4096.0};
        return WriteScalar(in_data_size, out_data_size, out_data, range);
    }
    case kAudioDevicePropertyZeroTimeStampPeriod:
        return WriteScalar(in_data_size, out_data_size, out_data, kZeroTimeStampPeriod);
    case kAudioDevicePropertyClockAlgorithm:
        return WriteScalar(in_data_size, out_data_size, out_data, static_cast<UInt32>(kAudioDeviceClockAlgorithmRaw));
    case kAudioStreamPropertyIsActive:
        return WriteScalar(in_data_size, out_data_size, out_data, static_cast<UInt32>(1));
    case kAudioStreamPropertyDirection:
        return WriteScalar(in_data_size, out_data_size, out_data, static_cast<UInt32>(in_object_id == kMicStream ? 1 : 0));
    case kAudioStreamPropertyTerminalType:
        return WriteScalar(in_data_size, out_data_size, out_data, static_cast<UInt32>(in_object_id == kMicStream ? kAudioStreamTerminalTypeMicrophone : kAudioStreamTerminalTypeSpeaker));
    case kAudioStreamPropertyStartingChannel:
        return WriteScalar(in_data_size, out_data_size, out_data, static_cast<UInt32>(1));
    case kAudioStreamPropertyVirtualFormat:
    case kAudioStreamPropertyPhysicalFormat:
        return WriteScalar(in_data_size, out_data_size, out_data, StreamFormat());
    case kAudioStreamPropertyAvailableVirtualFormats:
    case kAudioStreamPropertyAvailablePhysicalFormats: {
        AudioStreamRangedDescription description{};
        description.mFormat = StreamFormat();
        description.mSampleRateRange = {kSampleRate, kSampleRate};
        return WriteScalar(in_data_size, out_data_size, out_data, description);
    }
    default:
        return kAudioHardwareUnknownPropertyError;
    }
}

OSStatus SetPropertyData(AudioServerPlugInDriverRef, AudioObjectID, pid_t, const AudioObjectPropertyAddress*, UInt32, const void*, UInt32, const void*) {
    return kAudioHardwareIllegalOperationError;
}

OSStatus StartIO(AudioServerPlugInDriverRef, AudioObjectID, UInt32) {
    return kAudioHardwareNoError;
}

OSStatus StopIO(AudioServerPlugInDriverRef, AudioObjectID, UInt32) {
    return kAudioHardwareNoError;
}

OSStatus GetZeroTimeStamp(AudioServerPlugInDriverRef, AudioObjectID, UInt32, Float64* out_sample_time, UInt64* out_host_time, UInt64* out_seed) {
    if (out_sample_time == nullptr || out_host_time == nullptr || out_seed == nullptr) {
        return kAudioHardwareIllegalOperationError;
    }
    *out_sample_time = 0;
    *out_host_time = 0;
    *out_seed = 1;
    return kAudioHardwareNoError;
}

OSStatus WillDoIOOperation(AudioServerPlugInDriverRef, AudioObjectID, UInt32, UInt32 in_operation_id, Boolean* out_will_do, Boolean* out_will_do_in_place) {
    if (out_will_do == nullptr || out_will_do_in_place == nullptr) {
        return kAudioHardwareIllegalOperationError;
    }
    *out_will_do = (in_operation_id == kAudioServerPlugInIOOperationReadInput ||
                    in_operation_id == kAudioServerPlugInIOOperationWriteMix);
    *out_will_do_in_place = true;
    return kAudioHardwareNoError;
}

OSStatus BeginIOOperation(AudioServerPlugInDriverRef, AudioObjectID, UInt32, UInt32, UInt32, const AudioServerPlugInIOCycleInfo*) {
    return kAudioHardwareNoError;
}

OSStatus DoIOOperation(AudioServerPlugInDriverRef, AudioObjectID, AudioObjectID, UInt32, UInt32, UInt32 in_io_buffer_frame_size, const AudioServerPlugInIOCycleInfo*, void* io_main_buffer, void*) {
    if (io_main_buffer != nullptr) {
        std::memset(io_main_buffer, 0, in_io_buffer_frame_size * 2 * sizeof(Float32));
    }
    return kAudioHardwareNoError;
}

OSStatus EndIOOperation(AudioServerPlugInDriverRef, AudioObjectID, UInt32, UInt32, UInt32, const AudioServerPlugInIOCycleInfo*) {
    return kAudioHardwareNoError;
}

}  // namespace

AudioServerPlugInDriverInterface gDriverInterface = {
    nullptr,
    QueryInterface,
    AddRef,
    Release,
    Initialize,
    CreateDevice,
    DestroyDevice,
    AddDeviceClient,
    RemoveDeviceClient,
    PerformDeviceConfigurationChange,
    AbortDeviceConfigurationChange,
    HasProperty,
    IsPropertySettable,
    GetPropertyDataSize,
    GetPropertyData,
    SetPropertyData,
    StartIO,
    StopIO,
    GetZeroTimeStamp,
    WillDoIOOperation,
    BeginIOOperation,
    DoIOOperation,
    EndIOOperation
};

AudioServerPlugInDriverInterface* gDriverInterfacePointer = &gDriverInterface;

extern "C" __attribute__((visibility("default"))) void* TwoBrainRecProofDriverFactory(CFAllocatorRef, CFUUIDRef in_type_uuid) {
    Trace("factory called");
    if (CFEqual(in_type_uuid, kAudioServerPlugInTypeUUID)) {
        gReferenceCount.fetch_add(1);
        return &gDriverInterfacePointer;
    }
    return nullptr;
}
