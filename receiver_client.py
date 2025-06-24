import socket
import keyboard  # pip install keyboard
import threading

SERVER_IP = "ваш_серверный_ip"
SERVER_PORT = 12345

def receive_and_type(sock):
    try:
        while True:
            data = sock.recv(1024)
            if not data:
                print("[Приёмник] Соединение закрыто сервером")
                break
            text = data.decode("utf-8").strip()
            print(f"[Приёмник] Получено для ввода: {text}")

            # Вводим символы по одному
            for ch in text:
                keyboard.write(ch)
            keyboard.press_and_release('enter')
    except Exception as e:
        print(f"[Приёмник] Ошибка при приёме или вводе: {e}")

def run_receiver():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVER_IP, SERVER_PORT))
        s.sendall(b"receiver\n")
        print("[Приёмник] Подключён к серверу, ожидаю сообщения...")
        receive_and_type(s)

if __name__ == "__main__":
    run_receiver()
