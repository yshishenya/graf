import Foundation

enum LocalCacheAsyncTimeoutError: Error, Sendable {
    case timedOut
}

/// A bounded await that does not join an operation which ignores cancellation.
/// The operation runs in a detached task; the first result or the deadline
/// resumes the continuation exactly once.
enum LocalCacheAsyncTimeout {
    static func run<T: Sendable>(
        seconds: TimeInterval,
        operation: @escaping @Sendable () async throws -> T
    ) async throws -> T {
        let box = LocalCacheTimeoutContinuation<T>()
        let task = Task.detached(priority: .utility) {
            try await operation()
        }
        return try await withTaskCancellationHandler {
            try await withCheckedThrowingContinuation { continuation in
                box.install(continuation)
                Task.detached {
                    do {
                        box.resume(.success(try await task.value))
                    } catch {
                        box.resume(.failure(error))
                    }
                }
                Task.detached {
                    try? await Task.sleep(
                        nanoseconds: UInt64(max(0.001, seconds) * 1_000_000_000)
                    )
                    task.cancel()
                    box.resume(.failure(LocalCacheAsyncTimeoutError.timedOut))
                }
            }
        } onCancel: {
            task.cancel()
            box.resume(.failure(CancellationError()))
        }
    }
}

private final class LocalCacheTimeoutContinuation<T: Sendable>: @unchecked Sendable {
    private let lock = NSLock()
    private var continuation: CheckedContinuation<T, Error>?
    private var resumed = false

    func install(_ continuation: CheckedContinuation<T, Error>) {
        lock.lock()
        if resumed {
            lock.unlock()
            continuation.resume(throwing: CancellationError())
            return
        }
        self.continuation = continuation
        lock.unlock()
    }

    func resume(_ result: Result<T, Error>) {
        lock.lock()
        guard !resumed else {
            lock.unlock()
            return
        }
        resumed = true
        let continuation = continuation
        self.continuation = nil
        lock.unlock()
        continuation?.resume(with: result)
    }
}
