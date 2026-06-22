import machine
import time
import network
import socket
import gc

gc.collect()
#Menghubungkan ke koneksi LAN
wlan = network.WLAN(network.STA_IF)
wifi_name = 'Bi'
password = '31031202'
BACKEND_HOST = "10.230.213.13"
BACKEND_PORT = 8000
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

def url_encode(text):
    encoded = ""
    for byte in text.encode("utf-8"):
        char = chr(byte)
        if ("A" <= char <= "Z") or ("a" <= char <= "z") or ("0" <= char <= "9") or char in "-_.~":
            encoded += char
        elif char == " ":
            encoded += "%20"
        else:
            encoded += "%%%02X" % byte
    return encoded


def send_to_server(data):
    path = "/api/esp32?text=" + url_encode(data)
    request = (
        "GET {} HTTP/1.1\r\n"
        "Host: {}:{}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).format(path, BACKEND_HOST, BACKEND_PORT)
    client = None
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((BACKEND_HOST, BACKEND_PORT))
        client.send(request.encode("utf-8"))
        client.recv(128)
        print("Data telah terkirim ke backend FastAPI")
        return True
    except Exception as e:
        print("Gagal mengirim data ke backend:", e)
    finally:
        if client is not None:
            client.close()
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

try:
  while True:
      current_time = time.ticks_ms()
      state_morse  = tombol_morse.value()   
      state_submit = tombol_submit.value()  
      state_send   = tombol_send.value() 
  
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
              send_to_server(final_message)
              final_message = ""
              current_letter_code = ""
          else:
              print("\nDraf Kosong, tidak ada input")
          update_terminal_display()
          while tombol_send.value() == 0: 
            time.sleep_ms(10)
      time.sleep_ms(10) 

except Exception as e:
  print("Terminate terminal")
  wlan.active(False)
