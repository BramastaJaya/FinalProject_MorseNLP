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
BACKEND_HOST = "10.120.161.13"
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


def conn(data):
    path = "/api/esp32?text=" + url_encode(data)
    request = (
        "GET {} HTTP/1.0\r\n"
        "Host: {}:{}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).format(path, BACKEND_HOST, BACKEND_PORT)
    client = None
    sent = False
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5)
        terminal_log("Menghubungkan ke backend...")
        client.connect((BACKEND_HOST, BACKEND_PORT))
        terminal_log("Mengirim data ke backend...")
        if hasattr(client, "sendall"):
            client.sendall(request.encode("utf-8"))
        else:
            client.send(request.encode("utf-8"))
        sent = True
        terminal_log("Data telah terkirim ke backend FastAPI")
        return True
    except Exception as e:
        if sent:
            terminal_log("Backend menutup koneksi setelah menerima data: " + str(e))
            return True
        terminal_log("Gagal mengirim data ke backend: " + str(e))
    finally:
        if client is not None:
            client.close()
    return False

#Konfigurasi input dari Mikrokontroler
PIN_IR_MORSE      = 5
PIN_TOMBOL_SUBMIT = 18
PIN_PIR_SEND      = 19
PIN_BUZZER        = 22
PIN_LED           = 21
IR_ACTIVE         = 0 
PIR_SEND_ACTIVE   = 1

ir_morse      = machine.Pin(PIN_IR_MORSE, machine.Pin.IN, machine.Pin.PULL_UP)
tombol_submit = machine.Pin(PIN_TOMBOL_SUBMIT, machine.Pin.IN, machine.Pin.PULL_UP)
pir_send = machine.Pin(PIN_PIR_SEND, machine.Pin.IN)
buzzer = machine.Pin(PIN_BUZZER, machine.Pin.OUT)
led    = machine.Pin(PIN_LED, machine.Pin.OUT)


#Pengaturan durasi menggunakan millisecond (ms)
DEBOUNCE = 0.05
DOT_MAX = 0.2   

#Menampung kode morse dan kalimat akhir
current_letter_code = ""  # Menampung dot/dash (misal: "-.-")
final_message = ""        # Menampung kalimat konversi (hasil kode morse yang telah diinput: "AK")
status_message = ""

is_morse_pressed = False
last_morse_change = time.ticks_ms()
pir_send_was_active = False

#Kamus standar internasional Kode Morse
MORSE_DICT = {
    ".-": "A", "-...": "B", "-.-.": "C", "-..": "D", ".": "E", "..-.": "F",
    "--.": "G", "....": "H", "..": "I", ".---": "J", "-.-": "K", ".-..": "L",
    "--": "M", "-.": "N", "---": "O", ".--.": "P", "--.-": "Q", ".-.": "R",
    "...": "S", "-": "T", "..-": "U", "...-": "V", ".--": "W", "-..-": "X",
    "-.--": "Y", "--..": "Z",
    ".----": "1", "..---": "2", "...--": "3", "....-": "4", ".....": "5",
    "-....": "6", "--...": "7", "---..": "8", "----.": "9", "-----": "0",
    ".-.-.-": ".", "--..--": ",", "-..-.": "/", "---...": ":"
}

Morse = [
    "A .-     B -...   C -.-.   D -..    E .      F ..-.",
    "G --.    H ....   I ..     J .---   K -.-    L .-..",
    "M --     N -.     O ---    P .--.   Q --.-   R .-.",
    "S ...    T -      U ..-    V ...-   W .--    X -..-",
    "Y -.--   Z --..",
    "1 .----  2 ..---  3 ...--  4 ....-  5 .....",
    "6 -....  7 --...  8 ---..  9 ----.  0 -----",
    ". .-.-.-   , --..--   / -..-.   : ---...",
    "IR pin 5: Kode Morse | 18: Konversi/Spasi | PIR pin 19: Kirim",
]

def render_screen():
    print("\033[2J\033[H", end="")
    print(status_message)
    print("Input: " + final_message + current_letter_code)
    for line in Morse:
        print(line)

def terminal_log(message):
    global status_message
    status_message = message
    render_screen()

render_screen()

#Untuk memberikan jeda pada program supaya bersifat synchronus
time.sleep(2) 

try:
  while True:
      current_time = time.ticks_ms()
      state_morse  = ir_morse.value()   
      state_submit = tombol_submit.value()  
      state_send   = pir_send.value() 
  
      # IR INPUT: aktif saat sensor mendeteksi pantulan/halangan
      if state_morse == IR_ACTIVE and not is_morse_pressed:
          is_morse_pressed = True
          buzzer.value(1) 
          led.value(1)    
          last_morse_change = current_time
          
      elif state_morse != IR_ACTIVE and is_morse_pressed:
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
              render_screen()
                  
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
          render_screen()
  
          # Lock program selama tombol submit masih ditahan jari (anti-spam)
          while tombol_submit.value() == 0:
            time.sleep_ms(10)
      pir_send_active = state_send == PIR_SEND_ACTIVE
      if pir_send_active and not pir_send_was_active:
          buzzer.value(1) 
          time.sleep_ms(60) 
          buzzer.value(0)
        
          if len(final_message.strip()) > 0:
              terminal_log("Teks publikasi ke web: " + final_message)
              conn(final_message)
              final_message = ""
              current_letter_code = ""
          else:
              terminal_log("Draf Kosong, tidak ada input")
          render_screen()
      pir_send_was_active = pir_send_active
      time.sleep_ms(10) 

except Exception as e:
  terminal_log("Bye bye")
  wlan.active(False)
