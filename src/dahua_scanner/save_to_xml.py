from __future__ import annotations

import xml.etree.ElementTree as ElTree
from pathlib import Path
from datetime import datetime


def save_xml(results: list, max_xml_entries: int = 64, folder: Path | str = Path("reports")) -> list[str]:
    if not results:
        return []

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)

    max_entries = max(1, int(max_xml_entries))
    chunks = [results[i:i + max_entries] for i in range(0, len(results), max_entries)]
    single_file = len(chunks) == 1

    saved_files: list[str] = []

    for idx, part in enumerate(chunks, start=1):
        root = ElTree.Element('Organization')
        dev_list = ElTree.SubElement(root, 'Department')
        dev_list.set('name', 'root')

        for host in part:
            ip = str(host[0])
            port = str(host[1])
            user = str(host[2])
            password = str(host[3])
            model = str(host[4]) if len(host) > 4 and host[4] else ""

            device = ElTree.SubElement(dev_list, 'Device')
            title = f"{ip}_{user}:{password}" + (f" [{model}]" if model else "")
            device.set('title', title)
            device.set('ip', ip)
            device.set('port', port)
            device.set('user', user)
            device.set('password', password)
            if model:
                device.set('model', model)

        filename = "save.xml" if single_file else f"save_part_{idx}.xml"
        file_path = folder / filename

        tree = ElTree.ElementTree(root)
        if hasattr(ElTree, 'indent'):
            ElTree.indent(tree, space="  ")

        with open(file_path, "wb") as f:
            tree.write(f, encoding="utf-8", xml_declaration=True)

        saved_files.append(str(file_path))

    return saved_files
