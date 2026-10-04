import json
from pathlib import Path
from dataclasses import dataclass, asdict

CONFIG_FILE = Path(__file__).parent.parent / "config.json"

@dataclass
class Config:
    tg_endpoint: str
    bot_token: str
    userid: int

    def save(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=4, ensure_ascii=False)

def load_config() -> Config:
    if not CONFIG_FILE.exists():
        cfg = Config(tg_endpoint="api.telegram.org", bot_token="", userid=1234567890)
        cfg.save()
        return cfg
    
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Config(**data)

config = load_config()