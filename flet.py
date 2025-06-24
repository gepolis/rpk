import sys
import socket
import threading
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLabel, QTabWidget, QListWidget, QListWidgetItem,
    QComboBox, QLineEdit, QGroupBox, QFormLayout, QMessageBox, QTreeWidget, QTreeWidgetItem
)
from PySide6.QtCore import Qt, Slot


CONFIG_PATH = Path("rp_config.json")
PHRASES_PATH = Path("rp_phrases.json")
FORMATS_PATH = Path("formats.json")


class RPClient(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RP Client - Отправка реплик")
        self.resize(900, 650)

        self.socket = None
        self.receive_thread = None
        self.connected = False

        # Загружаем конфиги
        self.config = self.load_json(CONFIG_PATH, default={
            "org": "Полиция",
            "rang": "Офицер",
            "name": "Анна",
            "server_ip": "109.73.204.176",
            "server_port": 12345,
            "declension": "nominative"
        })
        self.phrases = self.load_json(PHRASES_PATH, default={})
        self.formats = self.load_json(FORMATS_PATH, default={})

        self.init_ui()
        self.populate_settings()
        self.populate_phrases()
        self.connect_to_server_auto()

    def load_json(self, path: Path, default=None):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки {path}: {e}")
            return default or {}

    def save_config(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения конфигурации: {e}")

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Вкладка Реплики
        self.tab_phrases = QWidget()
        self.tabs.addTab(self.tab_phrases, "Реплики")
        self.create_phrases_tab()

        # Вкладка Настройки
        self.tab_settings = QWidget()
        self.tabs.addTab(self.tab_settings, "Настройки")
        self.create_settings_tab()

        # Вкладка Сервер
        self.tab_server = QWidget()
        self.tabs.addTab(self.tab_server, "Сервер")
        self.create_server_tab()

        self.tabs.currentChanged.connect(self.on_tab_changed)

    def create_phrases_tab(self):
        layout = QVBoxLayout(self.tab_phrases)

        # Используем QTreeWidget для вложенных категорий
        self.phrases_tree = QTreeWidget()
        self.phrases_tree.setHeaderHidden(True)
        layout.addWidget(self.phrases_tree)
        self.phrases_tree.itemDoubleClicked.connect(self.on_phrase_double_clicked)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        layout.addWidget(self.log_text)

    def create_settings_tab(self):
        layout = QVBoxLayout(self.tab_settings)

        group_user = QGroupBox("Параметры пользователя")
        form_user = QFormLayout()

        self.combo_org = QComboBox()
        self.combo_org.addItems(["Полиция", "ДПС", "ФСБ", "ФСО", "ФСИН", "ФССП", "Кошко-полиция"])
        form_user.addRow("Организация:", self.combo_org)

        self.combo_rang = QComboBox()
        self.combo_rang.addItems([
            "Рядовой", "Младший сержант", "Сержант", "Старший сержант",
            "Прапорщик", "Младший лейтенант", "Лейтенант", "Старший лейтенант",
            "Капитан", "Майор", "Подполковник", "Полковник", "Генерал"
        ])
        form_user.addRow("Звание:", self.combo_rang)

        self.edit_name = QLineEdit()
        form_user.addRow("Имя:", self.edit_name)

        self.combo_declension = QComboBox()
        self.combo_declension.addItems(["Именительный", "Родительный", "Дательный", "Винительный", "Творительный", "Предложный"])
        form_user.addRow("Падеж:", self.combo_declension)

        group_user.setLayout(form_user)
        layout.addWidget(group_user)
        layout.addStretch()

        # Сохраняем при изменениях
        self.combo_org.currentTextChanged.connect(self.on_setting_changed)
        self.combo_rang.currentTextChanged.connect(self.on_setting_changed)
        self.edit_name.textChanged.connect(self.on_setting_changed)
        self.combo_declension.currentTextChanged.connect(self.on_setting_changed)

    def create_server_tab(self):
        layout = QVBoxLayout(self.tab_server)

        form = QFormLayout()

        self.edit_ip = QLineEdit()
        self.edit_ip.setText(self.config.get("server_ip", "109.73.204.176"))
        form.addRow("IP сервера:", self.edit_ip)

        self.edit_port = QLineEdit()
        self.edit_port.setText(str(self.config.get("server_port", 12345)))
        form.addRow("Порт сервера:", self.edit_port)

        self.edit_access_code = QLineEdit()
        self.edit_access_code.setPlaceholderText("Введите код доступа")
        self.edit_access_code.setEchoMode(QLineEdit.Password)
        form.addRow("Код доступа:", self.edit_access_code)

        layout.addLayout(form)

        self.btn_connect = QPushButton("Подключиться")
        self.btn_connect.clicked.connect(self.on_connect_clicked)
        layout.addWidget(self.btn_connect)

        self.label_status = QLabel("Статус: Отключено")
        layout.addWidget(self.label_status)

        self.log_server = QTextEdit()
        self.log_server.setReadOnly(True)
        layout.addWidget(self.log_server)

    @Slot()
    def on_connect_clicked(self):
        code = self.edit_access_code.text().strip()
        if code != "6329":
            QMessageBox.warning(self, "Ошибка", "Неверный код доступа к настройкам сервера.")
            return
        ip = self.edit_ip.text().strip()
        try:
            port = int(self.edit_port.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Порт должен быть числом.")
            return

        self.config["server_ip"] = ip
        self.config["server_port"] = port
        self.save_config()

        self.disconnect_from_server()
        self.connect_to_server(ip, port)

    @Slot()
    def on_tab_changed(self, index):
        if self.tabs.tabText(index) != "Сервер":
            self.edit_access_code.clear()
            self.edit_ip.setEnabled(False)
            self.edit_port.setEnabled(False)
            self.btn_connect.setEnabled(False)
        else:
            self.edit_ip.setEnabled(True)
            self.edit_port.setEnabled(True)
            self.btn_connect.setEnabled(True)

    def log(self, message: str):
        self.log_text.append(message)
        self.log_server.append(message)

    def populate_settings(self):
        self.combo_org.setCurrentText(self.config.get("org", "Полиция"))
        self.combo_rang.setCurrentText(self.config.get("rang", "Офицер"))
        self.edit_name.setText(self.config.get("name", "Анна"))

        decl_map = {
            "nominative": "Именительный",
            "genitive": "Родительный",
            "dative": "Дательный",
            "accusative": "Винительный",
            "instrumental": "Творительный",
            "prepositional": "Предложный"
        }
        decl = self.config.get("declension", "nominative")
        self.combo_declension.setCurrentText(decl_map.get(decl, "Именительный"))

    def on_setting_changed(self):
        self.config["org"] = self.combo_org.currentText()
        self.config["rang"] = self.combo_rang.currentText()
        self.config["name"] = self.edit_name.text()
        decl_map_rev = {
            "Именительный": "nominative",
            "Родительный": "genitive",
            "Дательный": "dative",
            "Винительный": "accusative",
            "Творительный": "instrumental",
            "Предложный": "prepositional"
        }
        self.config["declension"] = decl_map_rev.get(self.combo_declension.currentText(), "nominative")
        self.save_config()

    def connect_to_server_auto(self):
        ip = self.config.get("server_ip", "109.73.204.176")
        port = self.config.get("server_port", 12345)
        self.connect_to_server(ip, port)

    def connect_to_server(self, ip, port):
        if self.connected:
            self.log("Уже подключены к серверу.")
            return
        try:
            self.log(f"Подключение к серверу {ip}:{port}...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((ip, port))
            self.socket.settimeout(None)

            self.socket.sendall(b"sender\n")

            self.connected = True
            self.label_status.setText(f"Статус: Подключено к {ip}:{port}")
            self.log("Подключение успешно.")

            self.receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
            self.receive_thread.start()
        except Exception as e:
            self.log(f"Ошибка подключения: {e}")
            self.label_status.setText("Статус: Отключено")
            self.connected = False
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None

    def disconnect_from_server(self):
        if not self.connected:
            return
        self.connected = False
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        except Exception as e:
            self.log(f"Ошибка при отключении: {e}")
        self.socket = None
        self.label_status.setText("Статус: Отключено")
        self.log("Отключено от сервера.")

    def receive_messages(self):
        try:
            while self.connected:
                data = self.socket.recv(4096)
                if not data:
                    self.log("Соединение с сервером разорвано.")
                    break
                msg = data.decode("utf-8").strip()
                self.log(f"Получено: {msg}")
        except Exception as e:
            if self.connected:
                self.log(f"Ошибка приема данных: {e}")
        finally:
            self.connected = False
            if self.socket:
                try:
                    self.socket.shutdown(socket.SHUT_RDWR)
                    self.socket.close()
                except:
                    pass
                self.socket = None
            self.label_status.setText("Статус: Отключено")
            self.log("Отключено от сервера.")

    def populate_phrases(self):
        self.phrases_tree.clear()

        def add_phrases_recursive(parent, data):
            # data - dict or list
            if isinstance(data, dict):
                for key, value in data.items():
                    # Если value словарь с ключами "Фразы" или "/me", считаем, что лист
                    if isinstance(value, dict) and any(k in value for k in ("Фразы", "/me")):
                        # Создаем подкатегорию и добавляем туда фразы
                        cat_item = QTreeWidgetItem(parent, [key])
                        # Добавляем все фразы
                        for phrase in value.get("Фразы", []):
                            phrase_item = QTreeWidgetItem(cat_item, [phrase])
                            phrase_item.setData(0, Qt.UserRole, phrase)
                        # Можно /me в будущем использовать при отправке
                    else:
                        # Подкатегория с вложенностями
                        cat_item = QTreeWidgetItem(parent, [key])
                        add_phrases_recursive(cat_item, value)
            elif isinstance(data, list):
                for phrase in data:
                    phrase_item = QTreeWidgetItem(parent, [phrase])
                    phrase_item.setData(0, Qt.UserRole, phrase)

        add_phrases_recursive(self.phrases_tree.invisibleRootItem(), self.phrases)

        self.phrases_tree.expandToDepth(0)

    @Slot()
    def on_phrase_double_clicked(self, item: QTreeWidgetItem, column: int):
        # Отправлять только если это лист (нет дочерних элементов)
        if item.childCount() > 0:
            return

        text = item.data(0, Qt.UserRole)
        if not text:
            text = item.text(0)

        # Подставляем падеж и настройки в текст
        org = self.config.get("org", "Полиция")
        rang = self.config.get("rang", "Офицер")
        name = self.config.get("name", "Анна")
        decl = self.config.get("declension", "nominative")

        # Для простоты - вставляем без падежей, но можно добавить шаблоны для каждого падежа
        # Если в дальнейшем нужен сложный падеж - добавить логику здесь

        text = text.replace("{org}", org).replace("{rang}", rang).replace("{name}", name)

        self.send_message(text)

    def send_message(self, text: str):
        if not self.connected:
            self.log("Не подключены к серверу. Невозможно отправить сообщение.")
            return
        try:
            self.socket.sendall((text + "\n").encode("utf-8"))
            self.log(f"Отправлено: {text}")
        except Exception as e:
            self.log(f"Ошибка отправки: {e}")


def main():
    app = QApplication(sys.argv)
    client = RPClient()
    client.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
