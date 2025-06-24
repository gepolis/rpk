import socket
import keyboard  # pip install keyboard
import time

SERVER_IP = "109.73.204.176"
SERVER_PORT = 12345

def type_text_and_enter(text):
    for ch in text:
        keyboard.write(ch)
        time.sleep(0.01)  # задержка между символами
    time.sleep(0.2)  # пауза перед нажатием Enter
    keyboard.press_and_release('enter')

def receive_and_type(sock):
    try:
        while True:
            data = sock.recv(1024)
            if not data:
                print("[Приёмник] Соединение закрыто сервером")
                break
            text = data.decode("utf-8").strip()
            print(f"[Приёмник] Получено для ввода: {text}")

            type_text_and_enter(text)

    except Exception as e:
        print(f"[Приёмник] Ошибка при приёме или вводе: {e}")

def run_receiver():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVER_IP, SERVER_PORT))
        s.sendall(b"receiver\n")  # сообщаем серверу, что это клиент-приёмник
        print("[Приёмник] Подключён к серверу, ожидаю сообщения...")
        receive_and_type(s)

if __name__ == "__main__":
    run_receiver()
