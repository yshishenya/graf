#!/usr/bin/env swift
import AppKit
import Foundation

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data(("GRAF Dev lifecycle: \(message)\n").utf8))
    exit(1)
}

guard CommandLine.arguments.count == 3 else {
    fail("usage: dev-app-lifecycle.swift <status|terminate> <app-path>")
}

let expectedBundleIdentifier = "pro.2brain.graf.dev"
let action = CommandLine.arguments[1]
let requestedDestination = URL(fileURLWithPath: CommandLine.arguments[2]).standardizedFileURL
let destinationURL = requestedDestination.resolvingSymlinksInPath().standardizedFileURL
guard requestedDestination.path == destinationURL.path else {
    fail("Dev app destination must not be a symlink")
}
if FileManager.default.fileExists(atPath: destinationURL.path) {
    guard Bundle(url: destinationURL)?.bundleIdentifier == expectedBundleIdentifier else {
        fail("Dev app destination has an unexpected bundle identifier")
    }
}
let destination = destinationURL.path
let applications = NSWorkspace.shared.runningApplications.filter { application in
    application.bundleIdentifier == expectedBundleIdentifier &&
        application.bundleURL?.resolvingSymlinksInPath().standardizedFileURL.path == destination
}

switch action {
case "status":
    print(applications.isEmpty ? "stopped" : "running")
case "terminate":
    guard applications.allSatisfy({ $0.terminate() }) else {
        fail("application refused graceful termination")
    }
    print(applications.isEmpty ? "stopped" : "terminating")
default:
    fail("unsupported action: \(action)")
}
