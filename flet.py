import sys
import socket
import threading
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLabel, QTabWidget, QListWidget, QListWidgetItem,
    QComboBox, QLineEdit, QGroupBox, QFormLayout, QMessageBox,
    QSizePolicy
)
from PySide6.QtCore import Qt, Slot


CONFIG_PATH = Path("rp_config.json")
PHRASES_PATH = Path("rp_phrases.json")
FORMATS_PATH = Path("formats.json")


class RPClient(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RP Client - Отправка реплик")
        self.resize(1100, 700)

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
        self.populate_categories()
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
        self.setStyleSheet("""
            QWidget {
                background-color: #f9f9f9;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 14px;
                color: #222;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                background: white;
            }
            QTabBar::tab {
                background: #eee;
                border: 1px solid #ccc;
                padding: 8px 18px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                min-width: 80px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom-color: white;
                font-weight: 600;
            }
            QListWidget {
                background: white;
                border: 1px solid #ccc;
                border-radius: 6px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px 8px;
            }
            QListWidget::item:selected {
                background-color: #3399ff;
                color: white;
            }
            QPushButton {
                background-color: #3399ff;
                border: none;
                padding: 8px 20px;
                border-radius: 6px;
                color: white;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2a80d6;
            }
            QLineEdit, QComboBox {
                background: white;
                border: 1px solid #ccc;
                border-radius: 6px;
                padding: 5px 8px;
            }
            QTextEdit {
                background: white;
                border: 1px solid #ccc;
                border-radius: 6px;
                padding: 6px;
                font-family: Consolas, monospace;
                font-size: 13px;
            }
            QLabel {
                font-weight: 600;
            }
            QGroupBox {
                border: 1px solid #ddd;
                border-radius: 6px;
                margin-top: 10px;
                padding: 10px;
            }
            QGroupBox:title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 3px;
            }
        """)

        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Вкладка Реплики с 4 колонками
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
        layout = QHBoxLayout(self.tab_phrases)

        # 4 QListWidget для 4 колонок
        self.list_categories = QListWidget()
        self.list_categories.setMaximumWidth(200)
        self.list_categories.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.list_categories.setSelectionMode(QListWidget.SingleSelection)
        layout.addWidget(self.list_categories)

        self.list_subcategories1 = QListWidget()
        self.list_subcategories1.setMaximumWidth(200)
        self.list_subcategories1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.list_subcategories1.setSelectionMode(QListWidget.SingleSelection)
        layout.addWidget(self.list_subcategories1)

        self.list_subcategories2 = QListWidget()
        self.list_subcategories2.setMaximumWidth(200)
        self.list_subcategories2.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.list_subcategories2.setSelectionMode(QListWidget.SingleSelection)
        layout.addWidget(self.list_subcategories2)

        self.list_phrases = QListWidget()
        self.list_phrases.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.list_phrases)

        # Лог сообщений под колонками
        log_layout = QVBoxLayout()
        main_v_layout = QVBoxLayout()
        main_v_layout.addLayout(layout)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(140)
        main_v_layout.addWidget(self.log_text)

        self.tab_phrases.setLayout(main_v_layout)

        # Связываем выборы
        self.list_categories.itemClicked.connect(self.on_category_selected)
        self.list_subcategories1.itemClicked.connect(self.on_subcategory1_selected)
        self.list_subcategories2.itemClicked.connect(self.on_subcategory2_selected)
        self.list_phrases.itemDoubleClicked.connect(self.on_phrase_double_clicked)

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

    def populate_categories(self):
        # Заполняем первую колонку категориями
        self.list_categories.clear()
        cats = sorted(self.phrases.keys())
        self.list_categories.addItems(cats)

        self.list_subcategories1.clear()
        self.list_subcategories2.clear()
        self.list_phrases.clear()

    @Slot()
    def on_category_selected(self, item: QListWidgetItem):
        cat = item.text()
        self.list_subcategories1.clear()
        self.list_subcategories2.clear()
        self.list_phrases.clear()

        subcats = []
        data_cat = self.phrases.get(cat, {})
        if isinstance(data_cat, dict):
            subcats = sorted(data_cat.keys())
        self.list_subcategories1.addItems(subcats)

    @Slot()
    def on_subcategory1_selected(self, item: QListWidgetItem):
        cat_item = self.list_categories.currentItem()
        if not cat_item:
            return
        cat = cat_item.text()
        subcat1 = item.text()

        self.list_subcategories2.clear()
        self.list_phrases.clear()

        data_subcat = self.phrases.get(cat, {}).get(subcat1, {})
        if isinstance(data_subcat, dict):
            subsubcats = sorted(k for k in data_subcat.keys() if k != "Фразы")
            self.list_subcategories2.addItems(subsubcats)

            # Если есть "Фразы" на этом уровне, сразу покажем их
            if "Фразы" in data_subcat and isinstance(data_subcat["Фразы"], list):
                self.list_phrases.addItems(data_subcat["Фразы"])
        elif isinstance(data_subcat, list):
            self.list_phrases.addItems(data_subcat)

    @Slot()
    def on_subcategory2_selected(self, item: QListWidgetItem):
        cat_item = self.list_categories.currentItem()
        subcat1_item = self.list_subcategories1.currentItem()
        if not cat_item or not subcat1_item:
            return
        cat = cat_item.text()
        subcat1 = subcat1_item.text()
        subcat2 = item.text()

        self.list_phrases.clear()

        data_subsubcat = self.phrases.get(cat, {}).get(subcat1, {}).get(subcat2, {})
        if isinstance(data_subsubcat, dict):
            # если словарь с ключом "Фразы"
            if "Фразы" in data_subsubcat and isinstance(data_subsubcat["Фразы"], list):
                self.list_phrases.addItems(data_subsubcat["Фразы"])
        elif isinstance(data_subsubcat, list):
            self.list_phrases.addItems(data_subsubcat)

    @Slot()
    def on_phrase_double_clicked(self, item: QListWidgetItem):
        phrase = item.text()

        cat_item = self.list_categories.currentItem()
        subcat1_item = self.list_subcategories1.currentItem()
        subcat2_item = self.list_subcategories2.currentItem()

        cat = cat_item.text() if cat_item else None
        subcat1 = subcat1_item.text() if subcat1_item else None
        subcat2 = subcat2_item.text() if subcat2_item else None

        prefix = ""
        suffix = ""

        # Поиск формата
        fmt_level = self.formats.get(cat, {})
        if subcat1:
            fmt_level = fmt_level.get(subcat1, {})
        if subcat2:
            fmt_level = fmt_level.get(subcat2, {})

        prefix = fmt_level.get("prefix", "")
        suffix = fmt_level.get("suffix", "")

        # Подстановка переменных
        org = self.config.get("org", "Полиция")
        rang = self.config.get("rang", "Офицер")
        name = self.config.get("name", "Анна")

        text = f"{prefix}{phrase}{suffix}"
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
