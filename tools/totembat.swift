import CoreBluetooth
import Foundation

let BAT_SERVICE = CBUUID(string: "180F")
let BAT_LEVEL = CBUUID(string: "2A19")

class Reader: NSObject, CBCentralManagerDelegate, CBPeripheralDelegate {
    var central: CBCentralManager!
    var totem: CBPeripheral?
    var pending = 0
    var found = 0

    override init() {
        super.init()
        central = CBCentralManager(delegate: self, queue: nil)
    }

    func centralManagerDidUpdateState(_ c: CBCentralManager) {
        guard c.state == .poweredOn else {
            if c.state == .unauthorized { print("ERROR: sin permiso de Bluetooth para el terminal"); exit(1) }
            return
        }
        let connected = c.retrieveConnectedPeripherals(withServices: [BAT_SERVICE])
        if let t = connected.first(where: { $0.name == "TOTEM" }) ?? connected.first {
            print("conectando a \(t.name ?? "?")...")
            totem = t
            t.delegate = self
            c.connect(t)
        } else {
            print("ERROR: no hay ningún periférico conectado con servicio de batería")
            exit(1)
        }
    }

    func centralManager(_ c: CBCentralManager, didConnect p: CBPeripheral) {
        p.discoverServices([BAT_SERVICE])
    }

    func peripheral(_ p: CBPeripheral, didDiscoverServices error: Error?) {
        let bats = p.services?.filter { $0.uuid == BAT_SERVICE } ?? []
        print("servicios de batería encontrados: \(bats.count)")
        pending = bats.count
        for s in bats { p.discoverCharacteristics([BAT_LEVEL], for: s) }
        if bats.isEmpty { exit(0) }
    }

    func peripheral(_ p: CBPeripheral, didDiscoverCharacteristicsFor s: CBService, error: Error?) {
        for ch in s.characteristics ?? [] where ch.uuid == BAT_LEVEL { p.readValue(for: ch) }
    }

    func peripheral(_ p: CBPeripheral, didUpdateValueFor ch: CBCharacteristic, error: Error?) {
        found += 1
        let pct = ch.value?.first.map(String.init) ?? "?"
        let name = found == 1 ? "izquierda (central)" : "derecha (periférica)"
        print("batería \(found) [\(name)]: \(pct)%")
        pending -= 1
        if pending <= 0 { exit(0) }
    }
}

let r = Reader()
RunLoop.main.run(until: Date(timeIntervalSinceNow: 20))
print("fin (timeout)")
