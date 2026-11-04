// wallsnap: snapshot of the main display's wallpaper for the widget's frosted glass.
//
// Finds the Dock's on-screen "Wallpaper-…" window at the main display's origin, captures it
// with ScreenCaptureKit (fast; `screencapture -l` takes seconds on recent macOS), downscaled,
// and compares a tiny thumbnail with the last one. Only when it differs noticeably does it
// rewrite wall.jpg (atomically). It always prints the current wallpaper's stamp, which the widget uses as the
// image's cache-buster: an unchanged wallpaper means unchanged output, so no re-render.
//
// Prints "0" when there is no snapshot at all (e.g. no Screen Recording permission).
// Build: swiftc -O wallsnap.swift -o wallsnap

import AppKit
import CoreGraphics
import Foundation
import ImageIO
import ScreenCaptureKit
import UniformTypeIdentifiers

let width = 900.0 // it gets blurred anyway; small keeps capture + hashing cheap
let dir = URL(fileURLWithPath: CommandLine.arguments[0]).deletingLastPathComponent()
let jpgURL = dir.appendingPathComponent("wall.jpg")
let stampURL = dir.appendingPathComponent("wall.stamp")

func previous() -> String {
  let s = (try? String(contentsOf: stampURL, encoding: .utf8))?.trimmingCharacters(in: .whitespacesAndNewlines)
  return (s?.isEmpty == false && FileManager.default.fileExists(atPath: jpgURL.path)) ? s! : "0"
}

// Tiny 16×10 RGB thumbnail: captures are not bit-identical between runs (resampling noise),
// so "changed" means the thumbnails differ noticeably, not that the bytes differ.
let thumbW = 16, thumbH = 10
let thumbURL = dir.appendingPathComponent("wall.thumb")

func thumbnail(_ image: CGImage) -> [UInt8]? {
  var px = [UInt8](repeating: 0, count: thumbW * thumbH * 4)
  let ok = px.withUnsafeMutableBytes { buf -> Bool in
    guard let ctx = CGContext(data: buf.baseAddress, width: thumbW, height: thumbH, bitsPerComponent: 8,
                              bytesPerRow: thumbW * 4, space: CGColorSpaceCreateDeviceRGB(),
                              bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else { return false }
    ctx.interpolationQuality = .medium
    ctx.draw(image, in: CGRect(x: 0, y: 0, width: thumbW, height: thumbH))
    return true
  }
  return ok ? px : nil
}

// Mean absolute difference per channel, 0–255.
func distance(_ a: [UInt8], _ b: [UInt8]) -> Double {
  guard a.count == b.count, !a.isEmpty else { return .infinity }
  var sum = 0
  for i in 0..<a.count where i % 4 != 3 { sum += abs(Int(a[i]) - Int(b[i])) }
  return Double(sum) / Double(a.count / 4 * 3)
}

// Short id for the URL cache-buster (FNV-1a of the thumbnail).
func stampOf(_ t: [UInt8]) -> String {
  var h: UInt64 = 0xcbf2_9ce4_8422_2325
  for b in t { h = (h ^ UInt64(b)) &* 0x100_0000_01b3 }
  return String(h, radix: 16)
}

func writeJPEG(_ image: CGImage) -> Bool {
  let tmp = dir.appendingPathComponent("wall.tmp.jpg")
  guard let dest = CGImageDestinationCreateWithURL(tmp as CFURL, UTType.jpeg.identifier as CFString, 1, nil)
  else { return false }
  CGImageDestinationAddImage(dest, image, [kCGImageDestinationLossyCompressionQuality: 0.8] as CFDictionary)
  guard CGImageDestinationFinalize(dest) else { return false }
  return (try? FileManager.default.replaceItemAt(jpgURL, withItemAt: tmp)) != nil
}

func snap() async -> String {
  do {
    let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)
    guard let win = content.windows.first(where: {
      $0.owningApplication?.bundleIdentifier == "com.apple.dock"
        && ($0.title ?? "").hasPrefix("Wallpaper-") && $0.frame.origin == .zero
    }) else { return previous() }
    let cfg = SCStreamConfiguration()
    cfg.width = Int(width)
    cfg.height = Int((width * win.frame.height / win.frame.width).rounded())
    cfg.showsCursor = false
    let image = try await SCScreenshotManager.captureImage(
      contentFilter: SCContentFilter(desktopIndependentWindow: win), configuration: cfg)
    guard let thumb = thumbnail(image) else { return previous() }
    let old = (try? Data(contentsOf: thumbURL)).map { [UInt8]($0) } ?? []
    if previous() != "0" && distance(thumb, old) < 4 { return previous() } // same wallpaper
    guard writeJPEG(image) else { return previous() }
    let fp = stampOf(thumb)
    try? Data(thumb).write(to: thumbURL, options: .atomic)
    try? fp.write(to: stampURL, atomically: true, encoding: .utf8)
    return fp
  } catch {
    return previous()
  }
}

// ScreenCaptureKit needs the app's window-server connection set up and a live main run loop.
_ = NSApplication.shared
Task {
  print(await snap())
  exit(0)
}
DispatchQueue.main.asyncAfter(deadline: .now() + 5) { print(previous()); exit(0) } // never hang the widget
dispatchMain()
