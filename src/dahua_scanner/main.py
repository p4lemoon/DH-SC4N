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
from .config import config
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


CFG_CONFIG_MAP = {
    "token": "bot_token",
    "chat_id": "userid",
    "endpoint": "tg_endpoint",
    "send": "send_tg",
    "target_file": "target_file",
    "threads": "threads",
    "timeout": "timeout",
    "snapshots": "snapshots",
    "make_import_file": "make_import_file",
    "max_entries": "max_entries"
}

cfg = {
    "target_file": config.target_file,
    "token": config.bot_token,
    "chat_id": str(config.userid),
    "endpoint": config.tg_endpoint,
    "send": config.send_tg,
    "threads": config.threads,
    "timeout": config.timeout,
    "snapshots": config.snapshots,
    "make_import_file": config.make_import_file,
    "max_entries": config.max_entries
}

SECTIONS = [
    (f"[{ACCENT2}]1.[/] бот", [
        ("token", "токен", "str"),
        ("chat_id", "твой айди", "str"),
        ("endpoint", "кастомное тг зеркало", "str"),
        ("send", "оповещать?", "bool"),
        ("test", "тестовое сообщение", "func"),
    ]),
    (f"[{ACCENT2}]2.[/] сканнер", [
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
        s = str(v)
        return s[:6] + "..." + s[-4:] if len(s) > 10 else "protected"
    if kind == "bool":
        return "да" if v else "нет"
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


def func_test():
    token = str(cfg.get("token", "")).strip()
    chat_id = str(cfg.get("chat_id", "")).strip()
    if not token or not chat_id:
        con.print("\n[yellow]укажи token и chat_id[/yellow]")
        return

    endpoint = config.clean_tg_endpoint
    con.print(f"\n[cyan]отправляю тестовое сообщение в телеграм через {endpoint}...[/cyan]")
    try:
        url = f"https://{endpoint}/bot{token}/sendPhoto"
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
    con.print(
        f"цели: [green]{target_file}[/green] | "
        f"потоки: [green]{cfg['threads']}[/green] | "
        f"таймаут: [green]{cfg['timeout']} ms[/green] | "
        f"снимки: [green]{'да' if cfg['snapshots'] else 'нет'}[/green] | "
        f"кидать в тг?: [green]{'да' if cfg['send'] else 'нет'}[/green]\n"
    )

    if cfg["send"] and (not cfg["token"] or not cfg["chat_id"]):
        con.print("[yellow]оповещения в ТГ включены, но token или chat_id не заполнены[/yellow]\n")

    def on_found(device):
        ip, port, login, password = device[:4]
        model = device[4] if len(device) > 4 and device[4] else ""
        model_str = f" \033[1;36m[{model}]\033[0m" if model else ""
        tqdm.write(f"\033[1;32mнашел: {ip}:{port} -> {login}:{password}\033[0m{model_str}")

    try:
        results = scanner.brute(
            token=cfg["token"] if cfg["send"] else None,
            userid=cfg["chat_id"] if cfg["send"] else None,
            brute_file_path=target_file,
            dosnap=cfg["snapshots"],
            threads=cfg["threads"],
            timeout=cfg["timeout"],
            notify=cfg["send"],
            status_callback=on_found,
            make_import_file=cfg.get("make_import_file", True),
            max_entries=cfg.get("max_entries", 64)
        )
        con.print(f"\n[bold green]сканирование завершено, удалось найти {len(results)} устройств[/bold green]")
        if results:
            if scanner.last_report_dir:
                con.print(f"[cyan]папка с отчётом:[/] [bold green]{scanner.last_report_dir}[/bold green]")
                report_txt = scanner.last_report_dir / "found_devices.txt"
                if report_txt.exists():
                    con.print(f"[cyan]список устройств этого скана:[/] {report_txt}")
            con.print(f"[cyan]общий список обновлён в:[/] {scanner.FOUND_DEVICES_FILE}")
            if scanner.last_xml_files:
                con.print(f"[bold cyan]файлы импорта для SmartPSS:[/] {', '.join(scanner.last_xml_files)}")
    except Exception as e:
        con.print(f"\n[bold red]ошибочка во время сканирования: {e}[/bold red]")

    input("\nenter жмякни")


def edit(key, kind) -> None:
    if kind == "bool":
        cfg[key] = not cfg[key]
        attr = CFG_CONFIG_MAP.get(key)
        if attr and hasattr(config, attr):
            setattr(config, attr, cfg[key])
            config.save()
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
        if kind == "int":
            if not val.isdigit():
                con.print("[red]это не число[/red]")
                continue
            new_val = int(val)
        else:
            new_val = val

        cfg[key] = new_val
        attr = CFG_CONFIG_MAP.get(key)
        if attr and hasattr(config, attr):
            setattr(config, attr, new_val)
            config.save()
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