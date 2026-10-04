from __future__ import annotations

from rich.console import Console
from rich.text import Text
from prompt_toolkit import Application, prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, Window
import shutil
import sys
import os
import requests
from . import get_logo
from . import palette
from . import scanner
from tqdm import tqdm

# визуалы
con = Console()
colors = palette.get()

ACCENT = colors[3]
ACCENT2 = colors[1]
HINT = "[up]/[down] - навигация   **   [enter] - выбрать   **   [c-c]/[0] - выйти"


def print_logo() -> None:
    size = shutil.get_terminal_size(fallback=(80, 24))
    raw_logo = get_logo.get(size.columns)
    lines = [line for line in raw_logo.strip('\r\n').splitlines() if line]

    for idx, line in enumerate(lines):
        color = colors[idx % len(colors)]
        con.print(Text(line, style=color))

    print()


# состояние или конфиг неебу  крч
cfg = {
    "target_file": "input.txt",
    "token": "",
    "chat_id": "",
    "send": True,
    "threads": 100,
    "timeout": 500,
    "snapshots": True,
    "make_import_file": True,
    "max_entries": 64
}

SECTIONS = [
    (f"[{ACCENT2}]1.[/] бот", [
        ("token", "token", "str"),
        ("chat_id", "chat id", "str"),
        ("send", "оповещать?", "bool"),
        ("test", "тестовое сообщение", "func"),
    ]),
    (f"[{ACCENT2}]2.[/] scanner", [
        ("target_file", "файл с целями", "str"),
        ("threads", "потоки", "int"),
        ("timeout", "таймаут (ms)", "int"),
        ("snapshots", "брать снимки?", "bool"),
        ("make_import_file", "делать файл для SmartPSS?", "bool"),
        ("max_entries", "кол-во камер в 1 файл", "int")
    ]),
]

ITEMS = [("scan", "старт скан", "action")] + [
    item for _, items in SECTIONS for item in items
]
LABEL_W = max(len(label) for _, label, _ in ITEMS) + 4
selected = 0


def show_value(key, kind) -> str:
    if kind == "func":
        return "<run>"
    v = cfg.get(key, "")
    if key == "token" and v:
        return "protected" if len(str(v)) > 8 else "***"
    return str(v) if v != "" else "<not set>"


def item_line(idx, key, kind, label, indent) -> Text:
    cur = idx == selected
    t = Text()
    t.append("> " if cur else "  ", style="bold")
    t.append(" " * indent)
    t.append(f"[ {label} ]".ljust(LABEL_W), style="bold" if cur else "")
    if kind != "action":
        t.append("  | ", style=ACCENT)
        t.append(show_value(key, kind), style="bold" if cur else "")
    return t


def render() -> None:
    con.clear()
    print_logo()

    key, label, kind = ITEMS[0]
    con.print(item_line(0, key, kind, label, 0))
    con.print("\n---- конфигурация -------\n")

    idx = 1
    for title, items in SECTIONS:
        con.print(f"[bold]{title}[/bold]")
        for key, label, kind in items:
            con.print(item_line(idx, key, kind, label, 2))
            idx += 1
        con.print()

    con.print(Text(HINT, style="dim"))


# бинды
kb = KeyBindings()


@kb.add("up")
@kb.add("k")
def _(event):
    global selected
    selected = (selected - 1) % len(ITEMS)
    event.app.exit(result="redraw")


@kb.add("down")
@kb.add("j")
def _(event):
    global selected
    selected = (selected + 1) % len(ITEMS)
    event.app.exit(result="redraw")


@kb.add("enter")
def _(event):
    event.app.exit(result="select")


@kb.add("0")
@kb.add("c-c")
def _(event):
    event.app.exit(result="quit")


def create_app() -> Application:
    return Application(
        layout=Layout(Window()),
        key_bindings=kb,
        full_screen=False,
        erase_when_done=True,
    )


# сама логика жтой дрочи
def func_test():
    token = str(cfg.get("token", "")).strip()
    chat_id = str(cfg.get("chat_id", "")).strip()
    if not token or not chat_id:
        con.print("\n[yellow]укажи token и chat_id[/yellow]")
        return

    con.print("\n[cyan]отправляю тестовое сообщение в телеграм[/cyan]")
    try:
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        resp = requests.post(
            url,
            data={
                "chat_id": chat_id,
                "photo": "https://i.pinimg.com/736x/51/1e/df/511edf96c4eaea8fe2612c45cda3304e.jpg",
                "caption": "<b>все работает :3</b>",
                "parse_mode": "HTML"
            },
            timeout=10
        )
        if resp.status_code == 200:
            con.print("[bold green]все работает, проверь бота[/bold green]")
        else:
            con.print(f"[bold red]ошибочка ({resp.status_code}): {resp.text}[/bold red]")
    except Exception as e:
        con.print(f"[bold red]ошибка соединения: {e}[/bold red]")


def run_scan() -> None:
    target_file = cfg.get("target_file", "input.txt").strip()
    if not os.path.exists(target_file):
        con.print(f"\n[bold red]файл с целями '{target_file}' не найден, глянь получше[/bold red]")
        con.print("создай файл или укажи правильный путь в конфиге")
        input("\nenter жмякни")
        return

    con.print(f"\n[bold cyan]запуск скана![/bold cyan]")
    con.print(f"цели: [green]{target_file}[/green] | потоки: [green]{cfg['threads']}[/green] | снимки: [green]{cfg['snapshots']}[/green] | кидать в тг?: [green]{cfg['send']}[/green]\n")

    def on_found(device):
        ip, port, login, password = device
        tqdm.write(f"\033[1;32mопа, нашел: {ip}:{port} -> {login}:{password}\033[0m")

    try:
        results = scanner.brute(
            token=cfg["token"] if cfg["send"] else None,
            id=cfg["chat_id"] if cfg["send"] else None,
            brute_file_path=target_file,
            dosnap=cfg["snapshots"],
            threads=cfg["threads"],
            notify=cfg["send"],
            status_callback=on_found,
            make_import_file=cfg.get("make_import_file", True),
            max_entries=cfg.get("max_entries", 64)
        )
        con.print(f"\n[bold green]сканирование завершено, удалось найти {len(results)} устройств[/bold green]")
        if results:
            con.print("[cyan]список найденных устройств сохранён в found_devices.txt[/cyan]")
            if cfg.get("make_import_file", True):
                from . import save_to_xml
                saved_xmls = save_to_xml.save_xml(results, max_xml_entries=cfg.get("max_entries", 64))
                if saved_xmls:
                    con.print(f"[bold cyan]файлы для импорта в SmartPSS созданы [/bold cyan] {', '.join(saved_xmls)}")
    except Exception as e:
        con.print(f"\n[bold red]ошибочка во время сканирования: {e}[/bold red]")

    input("\nenter жмякни")


def edit(key, kind) -> None:
    if kind == "bool":
        cfg[key] = not cfg[key]
        return

    if kind == "func":
        func = globals().get(f"func_{key}")
        if func:
            func()
        else:
            con.print(f"[red]функции func_{key} не существует[/red]")
        input("\nenter жмякни")
        return

    while True:
        val = prompt(f"{key}: ", default=str(cfg.get(key, "")))
        if kind == "int" and not val.isdigit():
            con.print("[red]это не число[/red]")
            continue
        cfg[key] = int(val) if kind == "int" else val
        return


def activate() -> None:
    key, _, kind = ITEMS[selected]
    if kind == "action":
        run_scan()
    else:
        edit(key, kind)


def main() -> None:
    app = create_app()
    while True:
        render()
        result = app.run()
        if result == "quit":
            sys.exit(0)
        if result == "select":
            activate()


if __name__ == "__main__":
    main()