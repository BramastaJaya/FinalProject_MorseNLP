# Source - https://stackoverflow.com/a/61678130
# Posted by Trick
# Retrieved 2026-05-23, License - CC BY-SA 4.0
import network
import ubinascii

sta_if = network.WLAN(network.STA_IF)
if not sta_if.isconnected():
    print("connecting to network...")
    sta_if.active(False)
    sta_if.active(True)
    sta_if.connect("Bi", "31031202")
    while not sta_if.isconnected():
        pass
raw_mac = sta_if.config("mac")
print("network config:", sta_if.ifconfig())
hex_mac = ubinascii.hexlify(raw_mac, ":").decode().upper()
print("--- MAC ADDRESS ESP32 PENERIMA ---")
print("Format String (untuk dicatat):", hex_mac)
print("Format Bytes (untuk dimasukkan ke variabel peer_mac):")
print("b'" + "".join(["\\x" + hex_mac.split(":")[i] for i in range(6)]) + "'")
