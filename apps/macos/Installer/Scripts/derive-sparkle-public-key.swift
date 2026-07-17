#!/usr/bin/env swift

import CryptoKit
import Darwin
import Foundation

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("Sparkle key validation failed: \(message)\n".utf8))
    exit(1)
}

guard CommandLine.arguments.count == 2 else {
    fail("expected one external private-key file")
}

do {
    let encodedSeed = try String(
        contentsOfFile: CommandLine.arguments[1],
        encoding: .utf8
    ).trimmingCharacters(in: .whitespacesAndNewlines)
    guard let seed = Data(base64Encoded: encodedSeed), seed.count == 32 else {
        fail("the private key must be a base64-encoded 32-byte Ed25519 seed")
    }
    let privateKey = try Curve25519.Signing.PrivateKey(rawRepresentation: seed)
    print(privateKey.publicKey.rawRepresentation.base64EncodedString())
} catch {
    fail("could not derive its public key")
}
