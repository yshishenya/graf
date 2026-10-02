import CoreAudio
import Darwin
import Foundation

/// Current input IO metadata only; this neither captures audio nor requests permission.
public enum MacOSAudioInputActivitySnapshot {
    public static func activeBundleIDs() -> Set<String>? {
        var address = property(kAudioHardwarePropertyProcessObjectList)
        var size: UInt32 = 0
        guard AudioObjectGetPropertyDataSize(AudioObjectID(kAudioObjectSystemObject), &address, 0, nil, &size) == noErr else { return nil }
        guard size > 0 else { return [] }
        var processes = [AudioObjectID](repeating: 0, count: Int(size) / MemoryLayout<AudioObjectID>.size)
        let status = processes.withUnsafeMutableBytes {
            AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &address, 0, nil, &size, $0.baseAddress!)
        }
        guard status == noErr else { return nil }
        var bundles: Set<String> = []
        for process in processes.prefix(Int(size) / MemoryLayout<AudioObjectID>.size) {
            var running: UInt32 = 0
            guard read(process, selector: kAudioProcessPropertyIsRunningInput, into: &running) else { return nil }
            guard running == 1 else { continue }
            var pid: pid_t = 0
            guard read(process, selector: kAudioProcessPropertyPID, into: &pid), pid > 0 else { return nil }
            var path = [CChar](repeating: 0, count: 4 * Int(MAXPATHLEN))
            guard proc_pidpath(pid, &path, UInt32(path.count)) > 0 else { return nil }
            let executable = URL(fileURLWithPath: String(cString: path))
            // A known executable outside an app cannot match the verified app registry.
            guard let appURL = containingApplicationURL(for: executable) else { continue }
            guard let bundleID = Bundle(url: appURL)?.bundleIdentifier else { return nil }
            bundles.insert(bundleID)
        }
        return bundles
    }

    static func containingApplicationURL(for executable: URL) -> URL? {
        let components = executable.standardizedFileURL.pathComponents
        guard let index = components.firstIndex(where: { $0.hasSuffix(".app") }) else { return nil }
        return URL(fileURLWithPath: NSString.path(withComponents: Array(components.prefix(index + 1))), isDirectory: true)
    }

    private static func property(_ selector: AudioObjectPropertySelector) -> AudioObjectPropertyAddress {
        .init(mSelector: selector, mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
    }

    private static func read<T>(_ process: AudioObjectID, selector: AudioObjectPropertySelector, into value: inout T) -> Bool {
        var address = property(selector)
        var size = UInt32(MemoryLayout<T>.size)
        return withUnsafeMutableBytes(of: &value) {
            AudioObjectGetPropertyData(process, &address, 0, nil, &size, $0.baseAddress!) == noErr
        }
    }
}
