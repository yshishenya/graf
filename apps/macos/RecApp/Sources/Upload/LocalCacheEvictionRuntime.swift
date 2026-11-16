import Foundation
import TwoBrainRecShared

/// Production wiring kept outside the view file so no render path starts a
/// directory scan. The provider runs on a detached task and fails closed.
public enum LocalCacheEvictionRuntime {
    public static func footprintProvider(
        rootURL: URL
    ) -> LocalCacheEvictionScheduler.FootprintProvider {
        {
            await Task.detached(priority: .utility) {
                do {
                    let snapshot = try LocalRecordingFootprintMeasurer.measure(at: rootURL)
                    return LocalCacheEvictionFootprint(
                        usedBytes: snapshot.bytes,
                        freeDiskBytes: try? LocalRecordingStorageProbe.measureAvailableBytes(at: rootURL),
                        diskCapacityBytes: try? LocalRecordingStorageProbe.measureCapacityBytes(at: rootURL)
                    )
                } catch {
                    return nil
                }
            }.value
        }
    }
}
