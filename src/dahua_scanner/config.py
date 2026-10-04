from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass, asdict

ROOT_CONFIG = Path(__file__).resolve().parent.parent.parent / "config.json"
SRC_CONFIG = Path(__file__).resolve().parent.parent / "config.json"


def get_config_file() -> Path:
    if ROOT_CONFIG.exists():
        return ROOT_CONFIG
    if SRC_CONFIG.exists():
        return SRC_CONFIG
    return SRC_CONFIG


@dataclass
class Config:
    # Telegram Bot
    tg_endpoint: str = "epic-scorpion-2212.p4lemoon.deno.net"
    bot_token: str = ""
    userid: str = ""
    send_tg: bool = True

    # Scanner Settings
    target_file: str = "input.txt"
    threads: int = 100
    timeout: int = 1000
    snapshots: bool = True
    make_import_file: bool = True
    max_entries: int = 64

    def save(self) -> None:
        target = get_config_file()
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=4, ensure_ascii=False)

    @property
    def clean_tg_endpoint(self) -> str:
        ep = (self.tg_endpoint or "api.telegram.org").strip()
        ep = ep.replace("https://", "").replace("http://", "").strip("/")
        return ep or "api.telegram.org"


def load_config() -> Config:
    target = get_config_file()
    if not target.exists():
        cfg = Config()
        cfg.save()
        return cfg

    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
        fields = Config.__dataclass_fields__
        valid_data = {}
        for k, v in data.items():
            if k in fields:
                ftype = fields[k].type
                if ftype == int:
                    try:
                        valid_data[k] = int(v)
                    except (ValueError, TypeError):
                        pass
                elif ftype == bool:
                    valid_data[k] = bool(v)
                elif ftype == str:
                    valid_data[k] = str(v)
                else:
                    valid_data[k] = v
        cfg = Config(**valid_data)
        cfg.save()
        return cfg
    except Exception as e:
        print(f"Ошибка загрузки конфигурации: {e}")
        return Config()


config = load_config()