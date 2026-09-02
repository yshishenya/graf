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

let action = CommandLine.arguments[1]
let destination = URL(fileURLWithPath: CommandLine.arguments[2])
    .resolvingSymlinksInPath()
    .standardizedFileURL.path
let applications = NSWorkspace.shared.runningApplications.filter { application in
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
