// keyglow: streams key presses to the TOTEM cheatsheet widget so it can light up keys.
//
// - Listen-only CGEventTap (needs Input Monitoring permission). Secure Input (password
//   fields) hides keystrokes from it, as with any event tap.
// - Each press is translated into the labels drawn on the cheatsheet SVG ("Q", "{", "RET",
//   "⌘⇧3", "⏯"...) using the active macOS keyboard layout, and pushed as Server-Sent Events.
// - Serves only on 127.0.0.1, only to the Übersicht page origin and only with the per-run
//   token from keyglow.token (0600). Web pages and sandboxed apps cannot subscribe; any
//   unsandboxed process running as this user could still read the token file.
// - Caveat: terminals like kitty do not enable Secure Input, so a sudo password typed
//   there does pass through the stream. Stop keyglow if that matters to you.
//
// Build: swiftc -O keyglow.swift -o keyglow

import AppKit
import Carbon
import Network

let port: NWEndpoint.Port = 41427
let allowedOrigin = "http://127.0.0.1:41416" // Übersicht's page

// A fresh random token per run, readable only by this user (0600). The widget's shell
// command reads it and passes it as ?t=…; without it the stream is refused.
let tokenURL = URL(fileURLWithPath: CommandLine.arguments[0])
  .deletingLastPathComponent().appendingPathComponent("keyglow.token")
let token: String = {
  var bytes = [UInt8](repeating: 0, count: 24)
  guard SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes) == errSecSuccess else {
    fatalError("keyglow: no randomness for token")
  }
  let t = bytes.map { String(format: "%02x", $0) }.joined()
  FileManager.default.createFile(atPath: tokenURL.path, contents: Data(t.utf8),
                                 attributes: [.posixPermissions: 0o600])
  return t
}()

// MARK: - Server-Sent Events server

final class SSEServer {
  private var listener: NWListener!
  private var clients: [ObjectIdentifier: NWConnection] = [:]
  private let queue = DispatchQueue(label: "keyglow.sse")

  func start() throws {
    let params = NWParameters.tcp
    params.requiredLocalEndpoint = NWEndpoint.hostPort(host: "127.0.0.1", port: port)
    params.allowLocalEndpointReuse = true
    listener = try NWListener(using: params)
    listener.newConnectionHandler = { [weak self] c in self?.accept(c) }
    listener.start(queue: queue)
    // Keep-alive comment so dead connections get noticed and dropped.
    Timer.scheduledTimer(withTimeInterval: 20, repeats: true) { [weak self] _ in
      self?.broadcast(raw: ": ping\n\n")
    }
  }

  private func accept(_ c: NWConnection) {
    c.start(queue: queue)
    c.receive(minimumIncompleteLength: 1, maximumLength: 8192) { [weak self] data, _, _, _ in
      guard let self, let data, let req = String(data: data, encoding: .utf8) else { c.cancel(); return }
      let origin = req.split(separator: "\r\n")
        .first { $0.lowercased().hasPrefix("origin:") }
        .map { $0.dropFirst("origin:".count).trimmingCharacters(in: .whitespaces) }
      let requestLine = req.split(separator: "\r\n").first ?? ""
      let hasToken = requestLine.hasPrefix("GET /?t=\(token) ")
      guard origin == allowedOrigin, hasToken else {
        let deny = "HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
        c.send(content: deny.data(using: .utf8), completion: .contentProcessed { _ in c.cancel() })
        return
      }
      let head = "HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nCache-Control: no-cache\r\n"
        + "Access-Control-Allow-Origin: \(allowedOrigin)\r\nConnection: keep-alive\r\n\r\n"
      c.send(content: head.data(using: .utf8), completion: .contentProcessed { _ in })
      let id = ObjectIdentifier(c)
      self.clients[id] = c
      c.stateUpdateHandler = { [weak self] state in
        switch state {
        case .failed, .cancelled: self?.queue.async { self?.clients[id] = nil }
        default: break
        }
      }
    }
  }

  func send(_ event: [String: Any]) {
    guard let json = try? JSONSerialization.data(withJSONObject: event),
          let s = String(data: json, encoding: .utf8) else { return }
    broadcast(raw: "data: \(s)\n\n")
  }

  private func broadcast(raw: String) {
    let data = raw.data(using: .utf8)
    queue.async { [self] in
      for (id, c) in clients {
        c.send(content: data, completion: .contentProcessed { [weak self] err in
          if err != nil { self?.queue.async { self?.clients[id] = nil }; c.cancel() }
        })
      }
    }
  }
}

// MARK: - Key code → cheatsheet label

let namedKeys: [Int64: String] = [
  36: "RET", 48: "TAB", 53: "ESC", 51: "⌫", 117: "DEL", 49: "SPC", 57: "Caps",
  123: "←", 124: "→", 125: "↓", 126: "↑", 116: "Pg↑", 121: "Pg↓",
  122: "F1", 120: "F2", 99: "F3", 118: "F4", 96: "F5", 97: "F6",
  98: "F7", 100: "F8", 101: "F9", 109: "F10", 103: "F11", 111: "F12",
]

// Glyph used for a key inside shortcut labels like "⌃⌘␣" or "⌃↑".
let comboGlyph: [Int64: String] = [49: "␣", 123: "←", 124: "→", 125: "↓", 126: "↑"]

/// Character the active layout produces for `code` with only Shift/Option applied,
/// ignoring dead-key state (so the dead ´ key reports "´", not nothing).
func layoutChar(_ code: Int64, shift: Bool, option: Bool) -> String? {
  guard let src = TISCopyCurrentKeyboardLayoutInputSource()?.takeRetainedValue(),
        let ptr = TISGetInputSourceProperty(src, kTISPropertyUnicodeKeyLayoutData) else { return nil }
  let data = Unmanaged<CFData>.fromOpaque(ptr).takeUnretainedValue() as Data
  var mods: UInt32 = 0
  if shift { mods |= UInt32(shiftKey >> 8) }
  if option { mods |= UInt32(optionKey >> 8) }
  var dead: UInt32 = 0
  var chars = [UniChar](repeating: 0, count: 4)
  var len = 0
  let status = data.withUnsafeBytes { buf -> OSStatus in
    let layout = buf.bindMemory(to: UCKeyboardLayout.self).baseAddress!
    return UCKeyTranslate(layout, UInt16(code), UInt16(kUCKeyActionDisplay), mods,
                          UInt32(LMGetKbdType()), OptionBits(kUCKeyTranslateNoDeadKeysMask),
                          &dead, 4, &len, &chars)
  }
  guard status == noErr, len > 0 else { return nil }
  return String(utf16CodeUnits: chars, count: len)
}

func labels(code: Int64, flags: CGEventFlags) -> [String] {
  let shift = flags.contains(.maskShift), option = flags.contains(.maskAlternate)
  let cmd = flags.contains(.maskCommand), ctrl = flags.contains(.maskControl)
  var out: [String] = []
  if let name = namedKeys[code] {
    out.append(name)
  } else if let c = layoutChar(code, shift: shift, option: option) {
    out.append(c.uppercased())
  }
  if cmd || ctrl {
    let base = comboGlyph[code] ?? namedKeys[code]
      ?? layoutChar(code, shift: false, option: false)?.uppercased() ?? ""
    out.append((ctrl ? "⌃" : "") + (cmd ? "⌘" : "") + (shift ? "⇧" : "") + base)
  }
  return out
}

// Media keys arrive as NX_SYSDEFINED events (subtype 8).
let mediaKeys: [Int: String] = [
  0: "Vol+", 1: "Vol−", 7: "Mute", 2: "☀+", 3: "☀−",
  16: "⏯", 17: "⏭", 19: "⏭", 18: "⏮", 20: "⏮",
]

// Modifier key codes → (side, glyph as drawn on the home-row hold labels).
let modifierKeys: [Int64: (String, String, CGEventFlags)] = [
  55: ("L", "⌘", .maskCommand), 54: ("R", "⌘", .maskCommand),
  58: ("L", "⌥", .maskAlternate), 61: ("R", "⌥", .maskAlternate),
  59: ("L", "⌃", .maskControl), 62: ("R", "⌃", .maskControl),
  56: ("L", "⇧", .maskShift), 60: ("R", "⇧", .maskShift),
]

// MARK: - Event tap

let server = SSEServer()
var tap: CFMachPort?

let callback: CGEventTapCallBack = { _, type, event, _ in
  switch type {
  case .tapDisabledByTimeout, .tapDisabledByUserInput:
    if let tap { CGEvent.tapEnable(tap: tap, enable: true) }
  case .keyDown, .keyUp:
    if type == .keyDown && event.getIntegerValueField(.keyboardEventAutorepeat) != 0 { break }
    let code = event.getIntegerValueField(.keyboardEventKeycode)
    server.send(["t": type == .keyDown ? "down" : "up", "id": "k\(code)",
                 "labels": type == .keyDown ? labels(code: code, flags: event.flags) : []])
  case .flagsChanged:
    let code = event.getIntegerValueField(.keyboardEventKeycode)
    if let (side, glyph, mask) = modifierKeys[code] {
      server.send(["t": "mod", "side": side, "mod": glyph, "down": event.flags.contains(mask)])
    }
  default:
    if type.rawValue == 14, let ns = NSEvent(cgEvent: event), ns.subtype.rawValue == 8 {
      let key = (ns.data1 & 0xFFFF_0000) >> 16
      let down = ((ns.data1 & 0xFF00) >> 8) == 0xA
      let repeated = (ns.data1 & 0x1) != 0
      if let label = mediaKeys[key], !(down && repeated) {
        server.send(["t": down ? "down" : "up", "id": "m\(key)", "labels": down ? [label] : []])
      }
    }
  }
  return Unmanaged.passUnretained(event)
}

func installTap() -> Bool {
  let mask: CGEventMask = (1 << CGEventType.keyDown.rawValue) | (1 << CGEventType.keyUp.rawValue)
    | (1 << CGEventType.flagsChanged.rawValue) | (1 << 14)
  guard let t = CGEvent.tapCreate(tap: .cgSessionEventTap, place: .headInsertEventTap,
                                  options: .listenOnly, eventsOfInterest: mask,
                                  callback: callback, userInfo: nil) else { return false }
  tap = t
  CFRunLoopAddSource(CFRunLoopGetMain(), CFMachPortCreateRunLoopSource(nil, t, 0), .commonModes)
  CGEvent.tapEnable(tap: t, enable: true)
  return true
}

do { try server.start() } catch {
  FileHandle.standardError.write("keyglow: cannot listen on \(port): \(error)\n".data(using: .utf8)!)
  exit(1)
}

if !CGPreflightListenEventAccess() { CGRequestListenEventAccess() }
if !installTap() {
  FileHandle.standardError.write("keyglow: waiting for Input Monitoring permission…\n".data(using: .utf8)!)
  Timer.scheduledTimer(withTimeInterval: 3, repeats: true) { timer in
    if installTap() {
      FileHandle.standardError.write("keyglow: event tap installed\n".data(using: .utf8)!)
      timer.invalidate()
    }
  }
}

RunLoop.main.run()
