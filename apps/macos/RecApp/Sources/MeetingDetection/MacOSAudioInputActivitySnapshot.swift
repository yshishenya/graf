import CoreAudio
import Darwin
import Foundation

/// Current input IO metadata only; this neither captures audio nor requests permission.
public enum MacOSAudioInputActivitySnapshot {
    public struct Value: Equatable, Sendable {
        public let activeBundleIDs: Set<String>
        public let isComplete: Bool

        public init(activeBundleIDs: Set<String>, isComplete: Bool = true) {
            self.activeBundleIDs = activeBundleIDs
            self.isComplete = isComplete
        }
    }

    struct Readings: Sendable {
        var propertyData: @Sendable (AudioObjectID, AudioObjectPropertySelector) -> Data?
        var executableURL: @Sendable (pid_t) -> URL?
        var applicationBundleID: @Sendable (URL) -> String?
        var processBundleID: @Sendable (AudioObjectID) -> String? = { _ in nil }

        static var live: Self {
            Self(propertyData: readPropertyData, executableURL: { pid in
                var path = [CChar](repeating: 0, count: 4 * Int(MAXPATHLEN))
                guard proc_pidpath(pid, &path, UInt32(path.count)) > 0 else { return nil }
                return URL(fileURLWithPath: String(cString: path))
            }, applicationBundleID: { Bundle(url: $0)?.bundleIdentifier }, processBundleID: readProcessBundleID)
        }
    }

    public static func activeBundleIDs() -> Value? {
        activeBundleIDs(readings: .live)
    }

    static func activeBundleIDs(readings: Readings) -> Value? {
        guard let data = readings.propertyData(AudioObjectID(kAudioObjectSystemObject), kAudioHardwarePropertyProcessObjectList),
              data.count % MemoryLayout<AudioObjectID>.size == 0 else { return nil }
        let processes = data.withUnsafeBytes { bytes in
            stride(from: 0, to: data.count, by: MemoryLayout<AudioObjectID>.size).map {
                bytes.loadUnaligned(fromByteOffset: $0, as: AudioObjectID.self)
            }
        }
        var bundles: Set<String> = []
        var isComplete = true
        for process in processes {
            guard let running: UInt32 = scalar(process, selector: kAudioProcessPropertyIsRunningInput, readings: readings),
                  running == 0 || running == 1 else {
                isComplete = false
                continue
            }
            guard running == 1 else { continue }
            let pid: pid_t? = scalar(process, selector: kAudioProcessPropertyPID, readings: readings)
            if let pid, pid > 0, let executable = readings.executableURL(pid) {
                // A known executable outside an app cannot match the verified app registry.
                guard let appURL = containingApplicationURL(for: executable) else { continue }
                // The outer app is authoritative, even when CoreAudio names its nested helper.
                guard let bundleID = validBundleID(readings.applicationBundleID(appURL)) else {
                    isComplete = false
                    continue
                }
                bundles.insert(bundleID)
            } else {
                isComplete = false
                // This is exact current process metadata, never a guess from a helper's name.
                if let bundleID = validBundleID(readings.processBundleID(process)) {
                    bundles.insert(bundleID)
                }
            }
        }
        return Value(activeBundleIDs: bundles, isComplete: isComplete)
    }

    private static func validBundleID(_ value: String?) -> String? {
        guard let value, value.split(separator: ".", omittingEmptySubsequences: false).allSatisfy({ !$0.isEmpty }),
              value.contains("."), value.utf8.allSatisfy({
                  (65...90).contains($0) || (97...122).contains($0) || (48...57).contains($0) || $0 == 45 || $0 == 46 || $0 == 95
              }) else { return nil }
        return value
    }

    static func containingApplicationURL(for executable: URL) -> URL? {
        let components = executable.standardizedFileURL.pathComponents
        guard let index = components.firstIndex(where: { $0.hasSuffix(".app") }) else { return nil }
        return URL(fileURLWithPath: NSString.path(withComponents: Array(components.prefix(index + 1))), isDirectory: true)
    }

    private static func property(_ selector: AudioObjectPropertySelector) -> AudioObjectPropertyAddress {
        .init(mSelector: selector, mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
    }

    private static func scalar<T>(_ process: AudioObjectID, selector: AudioObjectPropertySelector, readings: Readings) -> T? {
        guard let data = readings.propertyData(process, selector), data.count == MemoryLayout<T>.size else { return nil }
        return data.withUnsafeBytes { $0.loadUnaligned(as: T.self) }
    }

    private static func readProcessBundleID(_ process: AudioObjectID) -> String? {
        var address = property(kAudioProcessPropertyBundleID)
        var value: Unmanaged<CFString>?
        var size = UInt32(MemoryLayout.size(ofValue: value))
        let status = withUnsafeMutablePointer(to: &value) {
            AudioObjectGetPropertyData(process, &address, 0, nil, &size, $0)
        }
        guard status == noErr, size == MemoryLayout.size(ofValue: value) else { return nil }
        // CoreAudio transfers this returned CFObject to the caller.
        return value?.takeRetainedValue() as String?
    }

    private static func readPropertyData(_ object: AudioObjectID, _ selector: AudioObjectPropertySelector) -> Data? {
        var address = property(selector)
        var size: UInt32 = 0
        guard AudioObjectGetPropertyDataSize(object, &address, 0, nil, &size) == noErr else { return nil }
        guard size > 0 else { return Data() }
        var data = Data(count: Int(size))
        let status = data.withUnsafeMutableBytes {
            AudioObjectGetPropertyData(object, &address, 0, nil, &size, $0.baseAddress!)
        }
        guard status == noErr, size <= data.count else { return nil }
        data.count = Int(size)
        return data
    }
}
