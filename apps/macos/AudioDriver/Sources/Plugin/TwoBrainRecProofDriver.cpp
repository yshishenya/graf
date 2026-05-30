#include <CoreAudio/AudioHardware.h>
#include <CoreAudio/AudioServerPlugIn.h>
#include <CoreFoundation/CoreFoundation.h>

#include "../Bridge/SharedAudioBuffer.hpp"
#include "../Device/VirtualDeviceRegistry.hpp"

#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

#include <mach/mach_time.h>

#include <atomic>
#include <cstring>
#include <ctime>

extern AudioServerPlugInDriverInterface gDriverInterface;
extern AudioServerPlugInDriverInterface* gDriverInterfacePointer;

namespace {

constexpr AudioObjectID kPlugInObject = kAudioObjectPlugInObject;
constexpr Float64 kSampleRate = 48000.0;
constexpr UInt32 kBufferFrameSize = 512;
constexpr UInt32 kZeroTimeStampPeriod = 24000;
constexpr UInt32 kPrivateTapListSelector = 'taps';
constexpr UInt32 kPrivateConfigurationSizeSelector = 'cfsz';
constexpr UInt32 kPrivateSingleInputSingleOutputSelector = 'siso';
constexpr UInt32 kPrivateAggregateRelatedSelector = 'aerE';
constexpr UInt32 kPrivateDataSourceOrderingSelector = 'dsOr';
constexpr const char* kVerboseTraceFlagPath = "/tmp/2brain-rec-proof-driver.verbose";

std::atomic<UInt32> gReferenceCount{1};
AudioServerPlugInHostRef gHost = nullptr;
TwoBrainRec::SharedAudioBuffer* gShared = nullptr;
int gShmFD = -1;
bool gShmOwner = false;

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

bool VerboseTraceEnabled() {
    static std::atomic<int> enabled{-1};
    int current = enabled.load();
    if (current == -1) {
        current = access(kVerboseTraceFlagPath, F_OK) == 0 ? 1 : 0;
        enabled.store(current);
    }
    return current == 1;
}

void TraceVerbose(const char* message) {
    if (VerboseTraceEnabled()) {
        Trace(message);
    }
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
        TraceVerbose(operation);
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
    TraceVerbose(buffer);
}

__attribute__((constructor)) void TraceBundleLoaded() {
    Trace("bundle constructor loaded");
}

__attribute__((destructor)) void CleanupSharedMemory() {
    if (gShared != nullptr) {
        munmap(gShared, sizeof(TwoBrainRec::SharedAudioBuffer));
        gShared = nullptr;
    }
    if (gShmOwner) {
        shm_unlink(TwoBrainRec::kShmName);
    }
}

bool IsDevice(AudioObjectID object_id) {
    return TwoBrainRec::AudioDriver::IsVirtualDevice(object_id);
}

bool IsStream(AudioObjectID object_id) {
    return TwoBrainRec::AudioDriver::IsVirtualStream(object_id);
}

CFStringRef CopyString(const char* value) {
    return CFStringCreateWithCString(kCFAllocatorDefault, value, kCFStringEncodingUTF8);
}

const char* DeviceName(AudioObjectID object_id) {
    return TwoBrainRec::AudioDriver::VirtualDeviceName(object_id);
}

const char* DeviceUID(AudioObjectID object_id) {
    return TwoBrainRec::AudioDriver::VirtualDeviceUID(object_id);
}

AudioObjectID OwnerForObject(AudioObjectID object_id) {
    if (IsDevice(object_id)) {
        return kPlugInObject;
    }
    if (IsStream(object_id)) {
        return TwoBrainRec::AudioDriver::OwnerForVirtualObject(object_id);
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
    return TwoBrainRec::AudioDriver::StreamCountForVirtualDevice(device_id, scope);
}

AudioObjectID DeviceStream(AudioObjectID device_id) {
    return TwoBrainRec::AudioDriver::StreamForVirtualDevice(device_id);
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
    case kAudioObjectPropertyListenerAdded:
    case kAudioObjectPropertyListenerRemoved:
    case kAudioObjectPropertyOwner:
    case kAudioObjectPropertyName:
    case kAudioObjectPropertyModelName:
    case kAudioObjectPropertyManufacturer:
    case kAudioObjectPropertyElementName:
    case kAudioObjectPropertyElementCategoryName:
    case kAudioObjectPropertyElementNumberName:
    case kAudioObjectPropertyIdentify:
    case kAudioObjectPropertySerialNumber:
    case kAudioObjectPropertyFirmwareVersion:
    case kAudioObjectPropertyOwnedObjects:
        return true;
    default:
        break;
    }

    if (object_id == kPlugInObject) {
        switch (address->mSelector) {
        case kAudioPlugInPropertyBundleID:
        case kAudioPlugInPropertyResourceBundle:
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
        case kPrivateAggregateRelatedSelector:
        case kPrivateConfigurationSizeSelector:
        case kPrivateDataSourceOrderingSelector:
        case kPrivateSingleInputSingleOutputSelector:
        case kAudioDevicePropertyDeviceUID:
        case kAudioDevicePropertyModelUID:
        case kAudioDevicePropertyTransportType:
        case kAudioDevicePropertyClockDomain:
        case kAudioDevicePropertyDeviceIsAlive:
        case kAudioDevicePropertyDeviceIsRunning:
        case kAudioDevicePropertyDeviceCanBeDefaultDevice:
        case kAudioDevicePropertyDeviceCanBeDefaultSystemDevice:
        case kAudioDevicePropertyLatency:
        case kAudioDevicePropertyStreams:
        case kAudioObjectPropertyControlList:
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
        case kPrivateTapListSelector:
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

    // Create or open shared memory
    gShmFD = shm_open(TwoBrainRec::kShmName, O_CREAT | O_RDWR, 0666);
    if (gShmFD < 0) {
        Trace("Initialize: shm_open failed");
        return kAudioHardwareUnspecifiedError;
    }

    // Check if we created it (file size will be 0 on fresh creation)
    struct stat st;
    if (fstat(gShmFD, &st) == 0 && st.st_size == 0) {
        ftruncate(gShmFD, sizeof(TwoBrainRec::SharedAudioBuffer));
        gShmOwner = true;
    }

    gShared = static_cast<TwoBrainRec::SharedAudioBuffer*>(
        mmap(nullptr, sizeof(TwoBrainRec::SharedAudioBuffer),
             PROT_READ | PROT_WRITE, MAP_SHARED, gShmFD, 0)
    );

    if (gShared == MAP_FAILED) {
        Trace("Initialize: mmap failed");
        close(gShmFD);
        shm_unlink(TwoBrainRec::kShmName);
        gShared = nullptr;
        gShmFD = -1;
        return kAudioHardwareUnspecifiedError;
    }

    close(gShmFD);

    if (gShmOwner) {
        std::memset(gShared, 0, sizeof(TwoBrainRec::SharedAudioBuffer));
    }

    return kAudioHardwareNoError;
}

OSStatus CreateDevice(AudioServerPlugInDriverRef, CFDictionaryRef, const AudioServerPlugInClientInfo*, AudioObjectID*) {
    return kAudioHardwareUnsupportedOperationError;
}

OSStatus DestroyDevice(AudioServerPlugInDriverRef, AudioObjectID) {
    return kAudioHardwareUnsupportedOperationError;
}

OSStatus AddDeviceClient(AudioServerPlugInDriverRef, AudioObjectID in_device_id, const AudioServerPlugInClientInfo*) {
    char buf[64];
    snprintf(buf, sizeof(buf), "AddDeviceClient device=%u", in_device_id);
    Trace(buf);
    return kAudioHardwareNoError;
}

OSStatus RemoveDeviceClient(AudioServerPlugInDriverRef, AudioObjectID in_device_id, const AudioServerPlugInClientInfo*) {
    char buf[64];
    snprintf(buf, sizeof(buf), "RemoveDeviceClient device=%u", in_device_id);
    Trace(buf);
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
    TraceVerbose(has_property ? "HasProperty result=true" : "HasProperty result=false");
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
    *out_is_settable = in_address->mSelector == kAudioObjectPropertyListenerAdded ||
        in_address->mSelector == kAudioObjectPropertyListenerRemoved;
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
    case kAudioObjectPropertyListenerAdded:
    case kAudioObjectPropertyListenerRemoved:
        *out_data_size = sizeof(AudioObjectPropertyAddress);
        return kAudioHardwareNoError;
    case kAudioObjectPropertyBaseClass:
    case kAudioObjectPropertyClass:
    case kAudioObjectPropertyOwner:
    case kAudioObjectPropertyIdentify:
    case kAudioDevicePropertyTransportType:
    case kAudioDevicePropertyClockDomain:
    case kPrivateAggregateRelatedSelector:
    case kPrivateConfigurationSizeSelector:
    case kPrivateDataSourceOrderingSelector:
    case kPrivateSingleInputSingleOutputSelector:
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
    case kPrivateTapListSelector:
        *out_data_size = 0;
        return kAudioHardwareNoError;
    case kAudioObjectPropertyName:
    case kAudioObjectPropertyModelName:
    case kAudioObjectPropertyManufacturer:
    case kAudioObjectPropertyElementName:
    case kAudioObjectPropertyElementCategoryName:
    case kAudioObjectPropertyElementNumberName:
    case kAudioObjectPropertySerialNumber:
    case kAudioObjectPropertyFirmwareVersion:
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
    case kAudioObjectPropertyControlList:
        *out_data_size = 0;
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
    case kAudioObjectPropertyListenerAdded:
    case kAudioObjectPropertyListenerRemoved:
        return kAudioHardwareIllegalOperationError;
    case kAudioObjectPropertyBaseClass:
        return WriteScalar(in_data_size, out_data_size, out_data, BaseClassForObject(in_object_id));
    case kAudioObjectPropertyClass:
        return WriteScalar(in_data_size, out_data_size, out_data, ClassForObject(in_object_id));
    case kAudioObjectPropertyOwner:
        return WriteScalar(in_data_size, out_data_size, out_data, OwnerForObject(in_object_id));
    case kAudioObjectPropertyIdentify:
        return WriteScalar(in_data_size, out_data_size, out_data, static_cast<UInt32>(0));
    case kAudioObjectPropertyName:
        if (in_object_id == kPlugInObject) {
            return WriteCFString(in_data_size, out_data_size, out_data, CopyString("2brain Rec Proof Driver"));
        }
        if (IsDevice(in_object_id)) {
            return WriteCFString(in_data_size, out_data_size, out_data, CopyString(DeviceName(in_object_id)));
        }
        return WriteCFString(in_data_size, out_data_size, out_data, CopyString(TwoBrainRec::AudioDriver::VirtualStreamName(in_object_id)));
    case kAudioObjectPropertyModelName:
        return WriteCFString(in_data_size, out_data_size, out_data, CopyString("2brain Rec Proof Audio Device"));
    case kAudioObjectPropertyManufacturer:
        return WriteCFString(in_data_size, out_data_size, out_data, CopyString("2brain"));
    case kAudioObjectPropertyElementName:
        return WriteCFString(in_data_size, out_data_size, out_data, CopyString("Main"));
    case kAudioObjectPropertyElementCategoryName:
        return WriteCFString(in_data_size, out_data_size, out_data, CopyString("Audio"));
    case kAudioObjectPropertyElementNumberName:
        return WriteCFString(in_data_size, out_data_size, out_data, CopyString("1"));
    case kAudioObjectPropertySerialNumber:
        return WriteCFString(in_data_size, out_data_size, out_data, CopyString("2brain-rec-proof"));
    case kAudioObjectPropertyFirmwareVersion:
        return WriteCFString(in_data_size, out_data_size, out_data, CopyString("0.1.0-proof"));
    case kAudioObjectPropertyOwnedObjects:
        if (in_object_id == kPlugInObject) {
            return WriteObjectList(
                in_data_size,
                out_data_size,
                out_data,
                TwoBrainRec::AudioDriver::VirtualDeviceObjectIDs(),
                TwoBrainRec::AudioDriver::VirtualDeviceCount()
            );
        }
        if (IsDevice(in_object_id)) {
            const AudioObjectID stream = DeviceStream(in_object_id);
            return WriteObjectList(in_data_size, out_data_size, out_data, &stream, 1);
        }
        return WriteEmptyList(out_data_size);
    case kAudioPlugInPropertyBundleID:
        return WriteCFString(in_data_size, out_data_size, out_data, CopyString("pro.2brain.rec.proof.driver"));
    case kAudioPlugInPropertyResourceBundle:
        return WriteCFString(in_data_size, out_data_size, out_data, CopyString("."));
    case kAudioPlugInPropertyDeviceList: {
        return WriteObjectList(
            in_data_size,
            out_data_size,
            out_data,
            TwoBrainRec::AudioDriver::VirtualDeviceObjectIDs(),
            TwoBrainRec::AudioDriver::VirtualDeviceCount()
        );
    }
    case kAudioPlugInPropertyBoxList:
        return WriteEmptyList(out_data_size);
    case kAudioPlugInPropertyTranslateUIDToDevice: {
        AudioObjectID translated = kAudioObjectUnknown;
        if (in_qualifier_data_size == sizeof(CFStringRef) && in_qualifier_data != nullptr) {
            auto uid = *reinterpret_cast<const CFStringRef*>(in_qualifier_data);
            if (CFStringCompare(uid, CFSTR("pro.2brain.rec.microphone"), 0) == kCFCompareEqualTo) {
                translated = TwoBrainRec::AudioDriver::kMicrophoneDeviceObjectID;
            } else if (CFStringCompare(uid, CFSTR("pro.2brain.rec.speaker"), 0) == kCFCompareEqualTo) {
                translated = TwoBrainRec::AudioDriver::kSpeakerDeviceObjectID;
            }
        }
        return WriteScalar(in_data_size, out_data_size, out_data, translated);
    }
    case kAudioObjectPropertyControlList:
        return WriteEmptyList(out_data_size);
    case kAudioDevicePropertyDeviceUID:
        return WriteCFString(in_data_size, out_data_size, out_data, CopyString(DeviceUID(in_object_id)));
    case kAudioDevicePropertyModelUID:
        return WriteCFString(in_data_size, out_data_size, out_data, CopyString("pro.2brain.rec.proof.model"));
    case kAudioDevicePropertyTransportType:
        return WriteScalar(in_data_size, out_data_size, out_data, static_cast<UInt32>(kAudioDeviceTransportTypeVirtual));
    case kPrivateAggregateRelatedSelector:
    case kPrivateDataSourceOrderingSelector:
    case kPrivateSingleInputSingleOutputSelector:
        return WriteScalar(in_data_size, out_data_size, out_data, static_cast<UInt32>(0));
    case kPrivateConfigurationSizeSelector:
        return WriteScalar(in_data_size, out_data_size, out_data, kBufferFrameSize);
    case kAudioDevicePropertyClockDomain:
        return WriteScalar(in_data_size, out_data_size, out_data, static_cast<UInt32>(0));
    case kAudioDevicePropertyDeviceIsAlive:
    case kAudioDevicePropertyClockIsStable:
        return WriteScalar(in_data_size, out_data_size, out_data, static_cast<UInt32>(1));
    case kAudioDevicePropertyDeviceCanBeDefaultDevice:
        return WriteScalar(in_data_size, out_data_size, out_data, static_cast<UInt32>(0));
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
        return WriteScalar(
            in_data_size,
            out_data_size,
            out_data,
            static_cast<UInt32>(TwoBrainRec::AudioDriver::VirtualStreamIsInput(in_object_id) ? 1 : 0)
        );
    case kAudioStreamPropertyTerminalType:
        return WriteScalar(
            in_data_size,
            out_data_size,
            out_data,
            static_cast<UInt32>(
                TwoBrainRec::AudioDriver::VirtualStreamIsInput(in_object_id)
                    ? kAudioStreamTerminalTypeMicrophone
                    : kAudioStreamTerminalTypeSpeaker
            )
        );
    case kAudioStreamPropertyStartingChannel:
        return WriteScalar(in_data_size, out_data_size, out_data, static_cast<UInt32>(1));
    case kPrivateTapListSelector:
        return WriteEmptyList(out_data_size);
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

OSStatus SetPropertyData(AudioServerPlugInDriverRef, AudioObjectID in_object_id, pid_t, const AudioObjectPropertyAddress* in_address, UInt32, const void*, UInt32, const void*) {
    TraceProperty("SetPropertyData called", in_object_id, in_address);
    if (in_address != nullptr &&
        (in_address->mSelector == kAudioObjectPropertyListenerAdded ||
         in_address->mSelector == kAudioObjectPropertyListenerRemoved)) {
        return kAudioHardwareNoError;
    }
    return kAudioHardwareIllegalOperationError;
}

OSStatus StartIO(AudioServerPlugInDriverRef, AudioObjectID in_device_id, UInt32) {
    Trace("StartIO called");
    char buf[64];
    snprintf(buf, sizeof(buf), "StartIO device=%u", in_device_id);
    TraceVerbose(buf);
    return kAudioHardwareNoError;
}

OSStatus StopIO(AudioServerPlugInDriverRef, AudioObjectID in_device_id, UInt32) {
    char buf[64];
    snprintf(buf, sizeof(buf), "StopIO device=%u", in_device_id);
    TraceVerbose(buf);
    return kAudioHardwareNoError;
}

namespace {
    UInt64 gSampleTime = 0;
    bool gZtsInitialized = false;
}

OSStatus GetZeroTimeStamp(AudioServerPlugInDriverRef, AudioObjectID in_device_id, UInt32, Float64* out_sample_time, UInt64* out_host_time, UInt64* out_seed) {
    if (out_sample_time == nullptr || out_host_time == nullptr || out_seed == nullptr) {
        return kAudioHardwareIllegalOperationError;
    }

    if (!gZtsInitialized) {
        gSampleTime = 0;
        gZtsInitialized = true;
    }

    *out_sample_time = static_cast<Float64>(gSampleTime);
    *out_host_time = mach_absolute_time();
    *out_seed = 1;

    // Advance timestamps to signal IO progress to coreaudiod
    gSampleTime += kZeroTimeStampPeriod;

    char buf[128];
    snprintf(buf, sizeof(buf), "GetZeroTimeStamp device=%u sample=%.0f host=%llu",
             in_device_id, *out_sample_time, *out_host_time);
    TraceVerbose(buf);

    return kAudioHardwareNoError;
}

OSStatus WillDoIOOperation(AudioServerPlugInDriverRef, AudioObjectID in_device_id, UInt32, UInt32 in_operation_id, Boolean* out_will_do, Boolean* out_will_do_in_place) {
    if (out_will_do == nullptr || out_will_do_in_place == nullptr) {
        return kAudioHardwareIllegalOperationError;
    }
    *out_will_do = (in_operation_id == kAudioServerPlugInIOOperationReadInput ||
                    in_operation_id == kAudioServerPlugInIOOperationWriteMix);
    *out_will_do_in_place = true;

    char buf[128];
    snprintf(buf, sizeof(buf), "WillDoIOOperation device=%u op=%s will_do=%d",
             in_device_id,
             in_operation_id == kAudioServerPlugInIOOperationReadInput ? "ReadInput" :
             in_operation_id == kAudioServerPlugInIOOperationWriteMix ? "WriteMix" : "other",
             *out_will_do);
    TraceVerbose(buf);

    return kAudioHardwareNoError;
}

OSStatus BeginIOOperation(AudioServerPlugInDriverRef, AudioObjectID in_device_id, UInt32 in_stream_id, UInt32, UInt32, const AudioServerPlugInIOCycleInfo*) {
    char buf[128];
    snprintf(buf, sizeof(buf), "BeginIOOperation device=%u stream=%u", in_device_id, in_stream_id);
    TraceVerbose(buf);
    return kAudioHardwareNoError;
}

OSStatus DoIOOperation(AudioServerPlugInDriverRef, AudioObjectID in_device_id, AudioObjectID, UInt32, UInt32 in_operation_id, UInt32 in_io_buffer_frame_size, const AudioServerPlugInIOCycleInfo*, void* io_main_buffer, void*) {
    if (io_main_buffer == nullptr || gShared == nullptr) {
        TraceVerbose("DoIOOperation: null buffer or gShared");
        return kAudioHardwareNoError;
    }

    size_t sample_count = in_io_buffer_frame_size * 2;

    char buf[256];
    snprintf(buf, sizeof(buf), "DoIOOperation device=%u op=%s frames=%u samples=%zu",
             in_device_id,
             in_operation_id == kAudioServerPlugInIOOperationReadInput ? "ReadInput" :
             in_operation_id == kAudioServerPlugInIOOperationWriteMix ? "WriteMix" : "other",
             in_io_buffer_frame_size, sample_count);
    TraceVerbose(buf);

    if (in_device_id == TwoBrainRec::AudioDriver::kMicrophoneDeviceObjectID &&
        in_operation_id == kAudioServerPlugInIOOperationReadInput) {
        auto avail = gShared->MicAvailable();
        snprintf(buf, sizeof(buf), "MicReadInput: avail=%zu sample_count=%zu", avail, sample_count);
        TraceVerbose(buf);

        if (avail >= sample_count) {
            gShared->Read(gShared->mic_buffer, gShared->mic_write_idx, gShared->mic_read_idx,
                          static_cast<float*>(io_main_buffer), sample_count);
            TraceVerbose("MicReadInput: read OK");
        } else {
            std::memset(io_main_buffer, 0, sample_count * sizeof(Float32));
            TraceVerbose("MicReadInput: no data, zero-fill");
        }
    }
    else if (in_device_id == TwoBrainRec::AudioDriver::kSpeakerDeviceObjectID &&
             in_operation_id == kAudioServerPlugInIOOperationWriteMix) {
        float* src = static_cast<float*>(io_main_buffer);
        gShared->Write(gShared->speaker_buffer, gShared->speaker_write_idx, gShared->speaker_read_idx,
                       src, sample_count);
        gShared->Write(gShared->capture_buffer, gShared->capture_write_idx, gShared->capture_read_idx,
                       src, sample_count);

        snprintf(buf, sizeof(buf), "SpeakerWriteMix: wrote %zu samples", sample_count);
        TraceVerbose(buf);
    }

    return kAudioHardwareNoError;
}

OSStatus EndIOOperation(AudioServerPlugInDriverRef, AudioObjectID in_device_id, UInt32, UInt32, UInt32, const AudioServerPlugInIOCycleInfo*) {
    char buf[64];
    snprintf(buf, sizeof(buf), "EndIOOperation device=%u", in_device_id);
    TraceVerbose(buf);
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
