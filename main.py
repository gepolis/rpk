import socket
import keyboard
import time

HOST = '0.0.0.0'
PORT = 12345

def simulate_typing(text):
    time.sleep(0.5)
    print(f"[DEBUG] Вводим символы:")
    for ch in text:
        print(f"[DEBUG] '{ch}'", end=' ', flush=True)
        keyboard.write(ch)
        time.sleep(0.03)
    print()
    keyboard.send('enter')

def start_server():
    print(f"[Сервер] Ожидание подключения на {HOST}:{PORT}...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        while True:
            conn, addr = s.accept()
            print(f"[Сервер] Подключён клиент: {addr}")
            with conn:
                buffer = ""
                while True:
                    data = conn.recv(1024)
                    if not data:
                        print(f"[Сервер] Клиент {addr} отключился")
                        break
                    buffer += data.decode('utf-8')
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.rstrip()
                        if line:
                            print(f"[Сервер] Вводим: '{line}'")
                            simulate_typing(line)

if __name__ == '__main__':
    start_server()
