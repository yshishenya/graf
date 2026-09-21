#!/usr/bin/env swift
import AppKit
import Darwin
import Foundation

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data(("GRAF Dev lifecycle: \(message)\n").utf8))
    exit(1)
}

let expectedBundleIdentifier = "pro.2brain.graf.dev"
let expectedDevDestination = URL(fileURLWithPath: "/Applications/GRAF Dev.app").standardizedFileURL
let arguments = CommandLine.arguments
guard arguments.count == 3 || (arguments.count == 4 && arguments[1] == "swap") else {
    fail("usage: dev-app-lifecycle.swift <status|terminate> <app-path> | swap <staged-app-path> <installed-app-path>")
}

func assertDevBundle(_ url: URL, label: String) {
    guard Bundle(url: url)?.bundleIdentifier == expectedBundleIdentifier else {
        fail("\(label) has an unexpected bundle identifier")
    }
}

let action = arguments[1]
if action == "swap" {
    let staged = URL(fileURLWithPath: arguments[2]).standardizedFileURL
    let installed = URL(fileURLWithPath: arguments[3]).standardizedFileURL
    guard staged.path == staged.resolvingSymlinksInPath().standardizedFileURL.path,
          installed.path == installed.resolvingSymlinksInPath().standardizedFileURL.path else {
        fail("app swap paths must not be symlinks")
    }
    guard installed.path == expectedDevDestination.path else {
        fail("app swap destination must be /Applications/GRAF Dev.app")
    }
    assertDevBundle(staged, label: "staged Dev app")
    assertDevBundle(installed, label: "installed Dev app")
    var stagedIsDirectory = ObjCBool(false)
    var installedIsDirectory = ObjCBool(false)
    guard FileManager.default.fileExists(atPath: staged.path, isDirectory: &stagedIsDirectory), stagedIsDirectory.boolValue,
          FileManager.default.fileExists(atPath: installed.path, isDirectory: &installedIsDirectory), installedIsDirectory.boolValue else {
        fail("app swap requires two existing app directories")
    }
    let result = renameatx_np(
        AT_FDCWD,
        staged.path,
        AT_FDCWD,
        installed.path,
        UInt32(RENAME_SWAP)
    )
    guard result == 0 else {
        fail("atomic app swap failed: \(String(cString: strerror(errno)))")
    }
    exit(0)
}

guard arguments.count == 3 else {
    fail("usage: dev-app-lifecycle.swift <status|terminate> <app-path>")
}

let requestedDestination = URL(fileURLWithPath: arguments[2]).standardizedFileURL
let destinationURL = requestedDestination.resolvingSymlinksInPath().standardizedFileURL
guard requestedDestination.path == destinationURL.path else {
    fail("Dev app destination must not be a symlink")
}
if FileManager.default.fileExists(atPath: destinationURL.path) {
    assertDevBundle(destinationURL, label: "Dev app destination")
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
