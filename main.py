import machine
import time
import network
import socket
import gc

gc.collect()
#Menghubungkan ke koneksi LAN
wlan = network.WLAN(network.STA_IF)
wifi_name = 'NAME'
password = 'PASSWORD'
if not wlan.isconnected():
    wlan.active(False)
    time.sleep_ms(100)
    wlan.active(True)
    wlan.connect(wifi_name, password)
    while not wlan.isconnected():
        pass
print('network config:', wlan.ifconfig())
m = wlan.config("mac")
mac = ('%02x:%02x:%02x:%02x:%02x:%02x').upper() %(m[0],m[1],m[2],m[3],m[4],m[5])
print("Local MAC: "+ mac)

def page():
    html ="""<!DOCTYPE html>
            <html lang="id">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>ESP32 Morse Server</title>
                <style>
                    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #1e1e24; color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                    .container { text-align: center; background: #2a2a35; padding: 30px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); width: 80%; max-width: 600px; }
                    h1 { color: #00bcd4; margin-bottom: 5px; }
                    .subtitle { color: #888; font-size: 14px; margin-bottom: 25px; }
                    .display-box { background: #111116; padding: 20px; border-radius: 10px; min-height: 80px; font-size: 26px; letter-spacing: 2px; border-left: 5px solid #00bcd4; word-wrap: break-word; text-align: left; }
                    .cursor { animation: blink 1s infinite; color: #00bcd4; font-weight: bold; }
                    @keyframes blink { 0%, 100% { opacity: 0; } 50% { opacity: 1; } }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>📻 Sistem Morse Mandiri</h1>
                    <div class="subtitle">Berjalan langsung dari Chip ESP32</div>
                    <div class="display-box" id="morse-output">Memuat data...</div>
                </div>
                <script>
                    // Meminta teks terbaru dari ESP32 setiap 1 detik tanpa me-refresh halaman
                    setInterval(function() {
                        fetch('/data')
                        .then(response => response.text())
                        .then(text => {
                            document.getElementById('morse-output').innerHTML = text + '<span class="cursor">|</span>';
                        });
                    }, 1000);
                </script>
            </body>
            </html>"""
    return html


print(f"Mencari Server di port 80...")
try:
    ip = wlan.ifconfig()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('10.194.25.118', 80))
    s.listen(5)
    s.setblocking(False)
except Exception as e:
    print(f"Gagal terkoneksi ke server: {e}")
    s.close()
    s = None

def send_to_server(data):
    global s
    if s is not None:
        try:
            s.send(data.encode('utf-8'))
            print("Data telah terkirim")
            return True
        except Exception as e:
            print("Jaringan tidak terhubung..")
            s.close()
            s = None
    return False

#Konfigurasi Tombol dari Mikrokontroler
PIN_TOMBOL_MORSE  = 5
PIN_TOMBOL_SUBMIT = 18
PIN_TOMBOL_SEND   = 19
PIN_BUZZER        = 22
PIN_LED           = 21

tombol_morse  = machine.Pin(PIN_TOMBOL_MORSE, machine.Pin.IN, machine.Pin.PULL_UP)
tombol_submit = machine.Pin(PIN_TOMBOL_SUBMIT, machine.Pin.IN, machine.Pin.PULL_UP)
tombol_send = machine.Pin(PIN_TOMBOL_SEND, machine.Pin.IN, machine.Pin.PULL_UP)
buzzer = machine.Pin(PIN_BUZZER, machine.Pin.OUT)
led    = machine.Pin(PIN_LED, machine.Pin.OUT)


#Pengaturan durasi menggunakan millisecond (ms)
DEBOUNCE = 0.05
DOT_MAX = 0.2   

#Menampung kode morse dan kalimat akhir
current_letter_code = ""  # Menampung dot/dash (misal: "-.-")
final_message = ""        # Menampung kalimat konversi (hasil kode morse yang telah diinput: "AK")

is_morse_pressed = False
last_morse_change = time.ticks_ms()

#Kamus standar internasional Kode Morse
MORSE_DICT = {
    ".-": "A", "-...": "B", "-.-.": "C", "-..": "D", ".": "E", "..-.": "F",
    "--.": "G", "....": "H", "..": "I", ".---": "J", "-.-": "K", ".-..": "L",
    "--": "M", "-.": "N", "---": "O", ".--.": "P", "--.-": "Q", ".-.": "R",
    "...": "S", "-": "T", "..-": "U", "...-": "V", ".--": "W", "-..-": "X",
    "-.--": "Y", "--..": "Z",
    ".----": "1", "..---": "2", "...--": "3", "....-": "4", ".....": "5",
    "-....": "6", "--...": "7", "---..": "8", "----.": "9", "-----": "0",
    ".-.-.-": ".", "--..--": ",", "..--..": "?", "-..-.": "/", "---...": ":"
}

def update_terminal_display():
    # \r mengembalikan kursor ke awal baris, end="" 
    print("\r" + final_message + current_letter_code + "", end="")
  
print(" A : .-     B : -...   C : -.-.   D : -..    E : .      F : ..-.")
print(" G : --.    H : ....   I : ..     J : .---   K : -.-    L : .-..")
print(" M : --     N : -.     O : ---    P : .--.   Q : --.-   R : .-.")
print(" S : ...    T : -      U : ..-    V : ...-   W : .--    X : -..-")
print(" Y : -.--   Z : --..")
print(" 1 : .----  2 : ..---  3 : ...--  4 : ....-  5 : .....")
print(" 6 : -....  7 : --...  8 : ---..  9 : ----.  0 : -----")
print(" . : .-.-.-   , : --..--   ? : uun--..   / : -..-.   : : ---...")
print("="*8)
print("Tekan:\n5: Input Kode\n1x 18: Konversi Kode Morse\n2x 18: Spasi\n")
print("="*8)
print("\tMasukkan Kode Morse:")
print("", end="")

#Untuk memberikan jeda pada program supaya bersifat synchronus
time.sleep(2) 
status = "Input Code..."

while True:
    current_time = time.ticks_ms()
    state_morse  = tombol_morse.value()   
    state_submit = tombol_submit.value()  
    state_send   = tombol_send.value() 
    try:
        conn, addr = s.accept()
        request = conn.recv(1024).decode('utf-8')

        if 'GET /data ' in request:
            response = 'HTTP/1.1 200 OK\nContent-Type: text/plain\nConnection: close\n\n' + status
            conn.send(response.encode('utf-8')) 
        else:
            response = 'HTTP/1.1 200 OK\nContent-Type: text/html\nConnection: close\n\n' + page()
            conn.send(response.encode('utf-8'))
        conn.close()
    except:
        pass

    #TOMBOL INPUT KODE 0 = MEMBACA, 1 = TIDAK MEMBACA
    if state_morse == 0 and not is_morse_pressed:
        is_morse_pressed = True
        buzzer.value(1) 
        led.value(1)    
        last_morse_change = current_time
        
    elif state_morse == 1 and is_morse_pressed:
        is_morse_pressed = False
        buzzer.value(0) 
        led.value(0)
        press_duration = time.ticks_diff(current_time, last_morse_change) / 1000.0
        
        if press_duration >= DEBOUNCE:
            if press_duration <= DOT_MAX:
                current_letter_code += "."
            else:
                current_letter_code += "-"
            
            # Segera update tampilan layar agar dot/dash muncul sebelum cursor
            update_terminal_display()
                
    # TOMBOL SUBMIT
    if state_submit == 0:
        # Efek klik balik suara pada buzzer
        buzzer.value(1)
        time.sleep_ms(50)
        buzzer.value(0)
        
        #TOMBOL KONVERSI
        if len(current_letter_code) > 0:
            translated_char = MORSE_DICT.get(current_letter_code, "(?)")
            final_message += translated_char    
            current_letter_code = "" 
                
        # TOMBOL SPASI
        else:
            if len(final_message) > 0 and not final_message.endswith(" "):
                final_message += " "
        print("\r" + " " * (len(final_message) + 10), end="")
        update_terminal_display()

        # Lock program selama tombol submit masih ditahan jari (anti-spam)
        while tombol_submit.value() == 0:
          time.sleep_ms(10)
    if state_send == 0:
        buzzer.value(1) 
        time.sleep_ms(60) 
        buzzer.value(0)
      
        if len(final_message.strip()) > 0:
            print(f"\n Teks publikasi ke web: {final_message}")
            status = final_message
            final_message = ""
            current_letter_code = ""
        else:
            print("\nDraf Kosong, tidak ada input")
        update_terminal_display()
        while tombol_send.value() == 0: 
          time.sleep_ms(10)
            

    time.sleep_ms(10) 
  
