from __future__ import annotations

import re
import json

def parse(filepath: str) -> list[str]:
    res = []

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        cont = f.read().strip()

    if cont.startswith('['):
        cont = cont.rstrip(',\n ]') + ']'
        try:
            data = json.loads(cont)
            for entry in data:
                ip = entry['ip']
                for port_info in entry['ports']:
                    res.append(f"{ip}:{port_info['port']}")
            return res
        except json.JSONDecodeError:
            pass

    for line in cont.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        match = re.search(r'Discovered open port (\d+)/\w+ on ([\d.]+)', line)
        if match:
            port, ip = match.group(1), match.group(2)
            res.append(f"{ip}:{port}")
            continue

        match = re.match(r'open\s+\w+\s+(\d+)\s+([\d.]+)', line)
        if match:
            port, ip = match.group(1), match.group(2)
            res.append(f"{ip}:{port}")
            continue

    return res