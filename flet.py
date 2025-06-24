import sys
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QLabel, QStackedWidget, QLineEdit, QPushButton,
    QTabWidget, QTextEdit, QComboBox, QMessageBox, QFormLayout, QCheckBox
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QColor, QPalette
import socket
import threading

CONFIG_PATH = Path("rp_config.json")
PHRASES_PATH = Path("rp_phrases.json")
FORMATS_PATH = Path("formats.json")

DEFAULT_CONFIG = {
    "org": "Полиция",
    "rang": "Офицер",
    "name": "Анна",
    "case": "nominative",  # падеж
    "server_ip": "109.73.204.176",
    "server_port": 12345
}

CASE_OPTIONS = {
    "nominative": "Именительный",
    "genitive": "Родительный",
    "dative": "Дательный",
    "accusative": "Винительный",
    "instrumental": "Творительный",
    "prepositional": "Предложный"
}

# ---------------------------------------
# Утилиты для загрузки и сохранения конфига и фраз
def load_json(path, default=None):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    else:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------------------------------------
# Автоматическая подстановка падежа (заглушка — можно расширить)
def apply_case(text, config):
    # Тут можно добавить более сложную логику падежей
    # Сейчас просто заменим {org} и {rang} и {name} без изменений
    text = text.replace("{org}", config.get("org", ""))
    text = text.replace("{rang}", config.get("rang", ""))
    text = text.replace("{name}", config.get("name", ""))
    return text

# ---------------------------------------
# Кастомные стили в формате QSS для светлой темы и минимализма
STYLE_SHEET = """
QWidget {
    background-color: #f9f9f9;
    font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
    font-size: 14px;
    color: #222222;
}
QListWidget {
    background-color: white;
    border: 1px solid #ccc;
}
QListWidget::item:selected {
    background-color: #5a9def;
    color: white;
}
QTabWidget::pane {
    border: 1px solid #ccc;
    top:-1px;
    background: white;
}
QTabBar::tab {
    background: #ddd;
    border: 1px solid #ccc;
    padding: 6px 12px;
    margin-right: 2px;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background: white;
    border-bottom: 1px solid white;
}
QLineEdit, QComboBox, QTextEdit {
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 4px;
}
QPushButton {
    background-color: #5a9def;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    color: white;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #3b7dd8;
}
QPushButton:disabled {
    background-color: #a0c1f7;
}
"""

# ---------------------------------------
class RPClient(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RP Клиент")
        self.resize(900, 600)
        self.config = load_json(CONFIG_PATH, DEFAULT_CONFIG)
        self.phrases = load_json(PHRASES_PATH, {})
        self.formats = load_json(FORMATS_PATH, {})
        self.socket = None
        self.connected = False
        self.receive_thread = None

        self.init_ui()
        self.apply_styles()
        self.load_categories()
        self.connect_to_server_auto()

    def apply_styles(self):
        self.setStyleSheet(STYLE_SHEET)

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Табовый виджет
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Вкладка РП
        self.tab_rp = QWidget()
        self.tabs.addTab(self.tab_rp, "РП Отыгровки")

        rp_layout = QHBoxLayout(self.tab_rp)

        # Списки
        self.list_categories = QListWidget()
        self.list_subcategories = QListWidget()
        self.list_subsubcategories = QListWidget()
        self.list_phrases = QListWidget()

        self.list_categories.setMaximumWidth(180)
        self.list_subcategories.setMaximumWidth(180)
        self.list_subsubcategories.setMaximumWidth(180)

        rp_layout.addWidget(self.list_categories)
        rp_layout.addWidget(self.list_subcategories)
        rp_layout.addWidget(self.list_subsubcategories)
        rp_layout.addWidget(self.list_phrases)

        self.list_categories.currentItemChanged.connect(self.on_category_selected)
        self.list_subcategories.currentItemChanged.connect(self.on_subcategory_selected)
        self.list_subsubcategories.currentItemChanged.connect(self.on_subsubcategory_selected)
        self.list_phrases.itemDoubleClicked.connect(self.on_phrase_double_clicked)

        # Вкладка Настройки
        self.tab_settings = QWidget()
        self.tabs.addTab(self.tab_settings, "Настройки")

        settings_layout = QFormLayout(self.tab_settings)

        self.input_org = QLineEdit(self.config.get("org", ""))
        self.input_rang = QLineEdit(self.config.get("rang", ""))
        self.input_name = QLineEdit(self.config.get("name", ""))
        self.combo_case = QComboBox()
        for k, v in CASE_OPTIONS.items():
            self.combo_case.addItem(v, k)
        case_idx = list(CASE_OPTIONS.keys()).index(self.config.get("case", "nominative"))
        self.combo_case.setCurrentIndex(case_idx)

        settings_layout.addRow("Организация:", self.input_org)
        settings_layout.addRow("Звание/Ранг:", self.input_rang)
        settings_layout.addRow("Имя:", self.input_name)
        settings_layout.addRow("Падеж:", self.combo_case)

        self.btn_save_settings = QPushButton("Сохранить настройки")
        self.btn_save_settings.clicked.connect(self.save_settings)
        settings_layout.addRow(self.btn_save_settings)

        # Вкладка Сервер
        self.tab_server = QWidget()
        self.tabs.addTab(self.tab_server, "Сервер")

        server_layout = QVBoxLayout(self.tab_server)

        form_server = QFormLayout()
        self.input_ip = QLineEdit(self.config.get("server_ip", ""))
        self.input_port = QLineEdit(str(self.config.get("server_port", 12345)))
        form_server.addRow("IP сервера:", self.input_ip)
        form_server.addRow("Порт сервера:", self.input_port)
        server_layout.addLayout(form_server)

        self.btn_connect = QPushButton("Подключиться")
        self.btn_connect.clicked.connect(self.connect_to_server_manual)
        server_layout.addWidget(self.btn_connect)

        self.label_status = QLabel("Статус: Отключено")
        server_layout.addWidget(self.label_status)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        server_layout.addWidget(self.log_console)

        self.tabs.currentChanged.connect(self.on_tab_changed)

    def log(self, text):
        self.log_console.append(text)
        print(text)

    def load_categories(self):
        self.list_categories.clear()
        if not self.phrases:
            return
        for cat in sorted(self.phrases.keys()):
            item = QListWidgetItem(cat)
            self.list_categories.addItem(item)

        self.list_subcategories.clear()
        self.list_subsubcategories.clear()
        self.list_phrases.clear()

    def on_category_selected(self, current, previous=None):
        self.list_subcategories.clear()
        self.list_subsubcategories.clear()
        self.list_phrases.clear()
        if not current:
            return
        cat = current.text()
        subcats = self.phrases.get(cat, {})
        if isinstance(subcats, dict):
            for subcat in sorted(subcats.keys()):
                # Проверяем, что подкатегория не содержит строки, а словарь с фразами
                if isinstance(subcats[subcat], dict) or isinstance(subcats[subcat], list):
                    item = QListWidgetItem(subcat)
                    self.list_subcategories.addItem(item)
        else:
            # Если нет подкатегорий, возможно сразу список фраз
            if isinstance(subcats, list):
                self.fill_phrases(subcats)

    def on_subcategory_selected(self, current, previous=None):
        self.list_subsubcategories.clear()
        self.list_phrases.clear()
        if not current:
            return
        cat = self.list_categories.currentItem()
        if not cat:
            return
        cat = cat.text()
        subcat = current.text()

        data = self.phrases.get(cat, {}).get(subcat, {})
        if isinstance(data, dict):
            for key in sorted(data.keys()):
                # Пропускаем метаданные типа prefix/suffix
                if key.lower() in ["prefix", "suffix"]:
                    continue
                # Если это список фраз
                if isinstance(data[key], list):
                    item = QListWidgetItem(key)
                    self.list_subsubcategories.addItem(item)
        elif isinstance(data, list):
            # Это список фраз без под-подкатегорий
            self.fill_phrases(data)

    def on_subsubcategory_selected(self, current, previous=None):
        self.list_phrases.clear()
        if not current:
            return
        cat = self.list_categories.currentItem()
        subcat = self.list_subcategories.currentItem()
        if not cat or not subcat:
            return
        cat = cat.text()
        subcat = subcat.text()
        subsubcat = current.text()

        data = self.phrases.get(cat, {}).get(subcat, {}).get(subsubcat, [])
        if isinstance(data, list):
            self.fill_phrases(data)

    def fill_phrases(self, phrases):
        self.list_phrases.clear()
        for phrase in phrases:
            item = QListWidgetItem(phrase)
            self.list_phrases.addItem(item)

    @Slot(QListWidgetItem)
    def on_phrase_double_clicked(self, item):
        text = item.text()
        # Подставляем переменные из настроек
        text = apply_case(text, self.config)
        self.send_text(text)

    def send_text(self, text):
        if not self.connected or not self.socket:
            QMessageBox.warning(self, "Ошибка", "Не подключено к серверу.")
            return
        try:
            self.socket.sendall(text.encode("utf-8"))
            self.log(f"Отправлено: {text}")
        except Exception as e:
            self.log(f"Ошибка отправки: {e}")

    def connect_to_server_auto(self):
        ip = self.config.get("server_ip", "")
        port = self.config.get("server_port", 0)
        if ip and port:
            threading.Thread(target=self.connect_to_server, args=(ip, port), daemon=True).start()

    def connect_to_server_manual(self):
        ip = self.input_ip.text().strip()
        try:
            port = int(self.input_port.text().strip())
        except:
            QMessageBox.warning(self, "Ошибка", "Неверный порт.")
            return
        threading.Thread(target=self.connect_to_server, args=(ip, port), daemon=True).start()

    def connect_to_server(self, ip, port):
        if self.connected:
            self.log("Уже подключены.")
            return
        try:
            self.log(f"Подключение к {ip}:{port} ...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((ip, port))
            # Отправляем тип клиента
            self.socket.sendall(b"sender\n")
            self.connected = True
            self.label_status.setText(f"Статус: Подключено к {ip}:{port}")
            self.log("Подключено.")

            self.receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
            self.receive_thread.start()
        except Exception as e:
            self.log(f"Ошибка подключения: {e}")
            self.label_status.setText("Статус: Ошибка подключения")

    def receive_messages(self):
        try:
            while self.connected:
                data = self.socket.recv(4096)
                if not data:
                    break
                msg = data.decode("utf-8").strip()
                self.log(f"Получено: {msg}")
        except Exception as e:
            self.log(f"Ошибка приёма: {e}")
        finally:
            self.connected = False
            self.socket.close()
            self.label_status.setText("Статус: Отключено")
            self.log("Отключено от сервера.")

    def save_settings(self):
        self.config["org"] = self.input_org.text().strip()
        self.config["rang"] = self.input_rang.text().strip()
        self.config["name"] = self.input_name.text().strip()
        self.config["case"] = self.combo_case.currentData()
        self.config["server_ip"] = self.input_ip.text().strip()
        try:
            self.config["server_port"] = int(self.input_port.text().strip())
        except:
            QMessageBox.warning(self, "Ошибка", "Порт должен быть числом.")
            return
        save_json(CONFIG_PATH, self.config)
        QMessageBox.information(self, "Сохранено", "Настройки сохранены.")

    def on_tab_changed(self, index):
        # При смене вкладки сбрасываем доступ к серверу (отключаемся)
        if self.connected and self.tabs.widget(index) != self.tab_server:
            self.disconnect_from_server()

    def disconnect_from_server(self):
        if self.connected and self.socket:
            self.connected = False
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
                self.socket.close()
            except:
                pass
            self.label_status.setText("Статус: Отключено")
            self.log("Отключено от сервера.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    client = RPClient()
    client.show()
    sys.exit(app.exec())
