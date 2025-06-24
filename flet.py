import flet as ft
import json
import socket
import threading
from pathlib import Path

CONFIG_PATH = Path("rp_config.json")
FORMATS_PATH = Path("formats.json")
PHRASES_PATH = Path("rp_phrases.json")

DEFAULT_CONFIG = {
    "org": "Полиция",
    "rang": "Офицер",
    "name": "Анна",
    "server_ip": "127.0.0.1",
    "server_port": 12345
}

DEFAULT_FORMATS = {
    "Фразы": {"prefix": "", "suffix": ""},
    "Рация": {"prefix": "Рация {org}: ", "suffix": ""},
    "me": {"prefix": "*", "suffix": "*"},
    "НонРП": {"prefix": "//", "suffix": ""}
}

# Загрузка настроек
if not CONFIG_PATH.exists():
    CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2))
if not FORMATS_PATH.exists():
    FORMATS_PATH.write_text(json.dumps(DEFAULT_FORMATS, ensure_ascii=False, indent=2))

CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
FORMATS = json.loads(FORMATS_PATH.read_text(encoding="utf-8"))
PHRASES = json.loads(Path(PHRASES_PATH).read_text(encoding="utf-8")) if PHRASES_PATH.exists() else {}

client_socket = None
connected = False


def apply_format(text, category):
    prefix = FORMATS.get(category, {}).get("prefix", "")
    suffix = FORMATS.get(category, {}).get("suffix", "")
    return f"{prefix}{text}{suffix}".replace("{org}", CONFIG['org']).replace("{rang}", CONFIG['rang']).replace("{name}", CONFIG['name'])


def connect():
    global client_socket, connected
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((CONFIG["server_ip"], CONFIG["server_port"]))
        client_socket.sendall(b"sender")
        connected = True
        return "Подключено"
    except Exception as e:
        connected = False
        return f"Ошибка подключения: {e}"


def send_message(text):
    if connected:
        client_socket.sendall((text + "\n").encode("utf-8"))


def ui(page: ft.Page):
    page.title = "RP Отправитель"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 10
    page.bgcolor = ft.colors.WHITE

    log_console = ft.Text("Журнал", size=12)
    category_column = ft.Column(auto_scroll=True)
    subcategory_column = ft.Column(auto_scroll=True)
    subsubcategory_column = ft.Column(auto_scroll=True)
    phrases_column = ft.Column(auto_scroll=True)

    def refresh_subcategories(cat):
        subcategory_column.controls.clear()
        for sub in PHRASES[cat]:
            btn = ft.TextButton(text=sub, on_click=lambda e, s=sub: refresh_subsubcategories(cat, s))
            subcategory_column.controls.append(btn)
        page.update()

    def refresh_subsubcategories(cat, sub):
        subsubcategory_column.controls.clear()
        subcat = PHRASES[cat][sub]
        if isinstance(subcat, dict):
            for subsub in subcat:
                btn = ft.TextButton(text=subsub, on_click=lambda e, s=subsub: show_phrases(cat, sub, s))
                subsubcategory_column.controls.append(btn)
        else:
            show_phrases(cat, sub)
        page.update()

    def show_phrases(cat, sub, subsub=None):
        phrases_column.controls.clear()
        data = PHRASES[cat][sub][subsub] if subsub else PHRASES[cat][sub]
        if isinstance(data, list):
            for phrase in data:
                btn = ft.TextButton(text=phrase, on_click=lambda e, p=phrase, s=sub: send_and_log(p, s))
                phrases_column.controls.append(btn)
        elif isinstance(data, dict):
            for k in data:
                for phrase in data[k]:
                    btn = ft.TextButton(text=phrase, on_click=lambda e, p=phrase, s=k: send_and_log(p, s))
                    phrases_column.controls.append(btn)
        page.update()

    def send_and_log(text, category):
        formatted = apply_format(text, category)
        send_message(formatted)
        log_console.value += f"\nОтправлено: {formatted}"
        page.update()

    def open_settings():
        def save(e):
            CONFIG["org"] = org_input.value
            CONFIG["rang"] = rang_input.value
            CONFIG["name"] = name_input.value
            CONFIG["server_ip"] = ip_input.value
            CONFIG["server_port"] = int(port_input.value)
            CONFIG_PATH.write_text(json.dumps(CONFIG, ensure_ascii=False, indent=2))
            dlg.open = False
            page.update()

        org_input = ft.TextField(label="Организация", value=CONFIG["org"])
        rang_input = ft.TextField(label="Звание", value=CONFIG["rang"])
        name_input = ft.TextField(label="Имя", value=CONFIG["name"])
        ip_input = ft.TextField(label="IP сервера", value=CONFIG["server_ip"])
        port_input = ft.TextField(label="Порт", value=str(CONFIG["server_port"]))

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Настройки"),
            content=ft.Column([org_input, rang_input, name_input, ip_input, port_input]),
            actions=[ft.TextButton("Сохранить", on_click=save)]
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    conn_status = connect()
    page.add(
        ft.Row([
            ft.Column([ft.Text("Категории"), category_column]),
            ft.Column([ft.Text("Подкатегории"), subcategory_column]),
            ft.Column([ft.Text("Действия"), subsubcategory_column]),
            ft.Column([ft.Text("Фразы"), phrases_column]),
        ], scroll="auto"),
        ft.Row([
            ft.Text(conn_status),
            ft.ElevatedButton("Настройки", on_click=lambda e: open_settings())
        ]),
        log_console
    )

    for cat in PHRASES:
        category_column.controls.append(ft.TextButton(text=cat, on_click=lambda e, c=cat: refresh_subcategories(c)))
    page.update()

ft.app(target=ui)
