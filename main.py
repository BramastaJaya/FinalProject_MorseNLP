import machine
import time
import network
import espnow

#Menghubungkan ke koneksi LAN
wlan = network.WLAN(network.STA_IF)
wlan.active(False)
wlan.active(True)

#Konfigurasi Tombol dari Mikrokontroler
PIN_TOMBOL_MORSE  = 5
PIN_TOMBOL_SUBMIT = 18
PIN_BUZZER        = 22
PIN_LED           = 21
tombol_morse  = machine.Pin(PIN_TOMBOL_MORSE, machine.Pin.IN, machine.Pin.PULL_UP)
tombol_submit = machine.Pin(PIN_TOMBOL_SUBMIT, machine.Pin.IN, machine.Pin.PULL_UP)
buzzer = machine.Pin(PIN_BUZZER, machine.Pin.OUT)
led    = machine.Pin(PIN_LED, machine.Pin.OUT)

#Pengaturan durasi menggunakan millisecond (ms)
DEBOUNCE = 0.05
DOT_MAX = 0.2   

#Mengirim sinyal dari ESP32 ke web server (Laptop)
e = espnow.ESPNow()
e.active(True)

#Alamat yang digunakan untuk mengirim data
peer_mac = b'\xB0\xCB\xD8\xC8\x5F\xFC'

try:
    #Menghubungkan
    e.add_peer(peer_mac)
except:
    pass

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

#Menampung kode morse dan kalimat akhir
current_letter_code = ""  # Menampung dot/dash (misal: "-.-")
final_message = ""        # Menampung kalimat konversi (hasil kode morse yang telah diinput: "AK")

is_morse_pressed = False
last_morse_change = time.ticks_ms()

def update_terminal_display():
    # \r mengembalikan kursor ke awal baris, end="" 
    print("\r" + final_message + current_letter_code +] "", end="")
  
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

while True:
    current_time = time.ticks_ms()
    state_morse  = tombol_morse.value()   
    state_submit = tombol_submit.value()  
  
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
                
    # ==========================================
    # LOGIKA 2: MEMBACA TOMBOL KEDUA (SUBMIT / SPASI)
    # ==========================================
    if state_submit == 0:
        # Efek klik balik suara pada buzzer
        buzzer.value(1)
        time.sleep_ms(50)
        buzzer.value(0)
        
        # KONDISI A: Menerjemahkan kode Morse yang ada di samping cursor
        if len(current_letter_code) > 0:
            translated_char = MORSE_DICT.get(current_letter_code, "[?]")
            final_message += translated_char
            
            # Reset buffer kode karena sudah runtuh menyatu ke final_message
            current_letter_code = "" 
            
            # Kirim data kalimat terbaru via ESP-NOW
            try:
                e.send(peer_mac, final_message.encode())
            except:
                pass
                
        # KONDISI B: Tombol submit ditekan lagi saat buffer kosong (Tambah Spasi Kata)
        else:
            if len(final_message) > 0 and not final_message.endswith(" "):
                final_message += " "
                
                try:
                    e.send(peer_mac, final_message.encode())
                except:
                    pass
        
        # Bersihkan sisa karakter di terminal lama dengan menimpa baris baru secara bersih
        # Spasi kosong di ujung bertujuan menyapu bersih bekas sisa karakter panjang sebelumnya
        print("\r" + " " * (len(final_message) + 10), end="")
        
        # Tampilkan hasil perubahan terbaru dengan posisi cursor yang benar
        update_terminal_display()
                    
        # Lock program selama tombol submit masih ditahan jari (anti-spam)
        while tombol_submit.value() == 0:
            time.sleep_ms(10)
            
    time.sleep_ms(10) # Menjaga Core internal ESP32
  