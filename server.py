import socket
import threading

HOST = "0.0.0.0"
PORT = 12345

clients_receivers = []
clients_senders = []

lock = threading.Lock()

def handle_client(conn, addr):
    print(f"[Сервер] Подключился {addr}")
    try:
        # Ожидаем первый пакет - тип клиента
        client_type = conn.recv(1024).decode("utf-8").strip().lower()
        print(f"[Сервер] Клиент {addr} тип: {client_type}")

        if client_type == "receiver":
            with lock:
                clients_receivers.append(conn)
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                # Можно реализовать heartbeat или команды для receiver, если нужно
        elif client_type == "sender":
            with lock:
                clients_senders.append(conn)
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                text = data.decode("utf-8").strip()
                print(f"[Сервер] Отправитель {addr} отправил: {text}")

                # Пересылаем всем приемникам
                with lock:
                    to_remove = []
                    for r in clients_receivers:
                        try:
                            r.sendall((text + "\n").encode("utf-8"))
                        except Exception as e:
                            print(f"[Сервер] Ошибка отправки приемнику: {e}")
                            to_remove.append(r)
                    for r in to_remove:
                        clients_receivers.remove(r)
        else:
            print(f"[Сервер] Неизвестный тип клиента от {addr}: {client_type}")

    except Exception as e:
        print(f"[Сервер] Ошибка с клиентом {addr}: {e}")
    finally:
        with lock:
            if conn in clients_receivers:
                clients_receivers.remove(conn)
            if conn in clients_senders:
                clients_senders.remove(conn)
        conn.close()
        print(f"[Сервер] Клиент {addr} отключился")

def start_server():
    print(f"[Сервер] Запуск на {HOST}:{PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()
