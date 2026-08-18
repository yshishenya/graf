import AppKit
import Foundation

guard CommandLine.arguments.count == 3,
      let base = NSImage(contentsOfFile: CommandLine.arguments[1])
else {
    exit(1)
}

let canvasSize = NSSize(width: 512, height: 512)
let canvas = NSImage(size: canvasSize)
canvas.lockFocus()
NSColor.clear.setFill()
NSRect(origin: .zero, size: canvasSize).fill()
base.draw(in: NSRect(origin: .zero, size: canvasSize), from: .zero, operation: .sourceOver, fraction: 1)

let badge = NSRect(x: 264, y: 18, width: 230, height: 118)
NSColor(calibratedRed: 0.98, green: 0.82, blue: 0.22, alpha: 1).setFill()
NSBezierPath(roundedRect: badge, xRadius: 24, yRadius: 24).fill()
let paragraph = NSMutableParagraphStyle()
paragraph.alignment = .center
let attributes: [NSAttributedString.Key: Any] = [
    .font: NSFont.boldSystemFont(ofSize: 52),
    .foregroundColor: NSColor.black,
    .paragraphStyle: paragraph
]
("DEV" as NSString).draw(in: badge.insetBy(dx: 10, dy: 26), withAttributes: attributes)
canvas.unlockFocus()

guard let tiff = canvas.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: tiff),
      let png = bitmap.representation(using: .png, properties: [:])
else {
    exit(1)
}
try png.write(to: URL(fileURLWithPath: CommandLine.arguments[2]))
