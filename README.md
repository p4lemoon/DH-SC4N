<a id="readme-top"></a>

<!-- SHIELDS -->
[![Python][python-shield]][python-url]
[![uv][uv-shield]][uv-url]
[![MIT License][license-shield]][license-url]
[![Issues][issues-shield]][issues-url]
[![Stars][stars-shield]][stars-url]



<!-- LOGO -->
<br />
<div align="center">
<pre>
██████╗ ██╗  ██╗   ███████╗ ██████╗██╗  ██╗███╗   ██╗
██╔══██╗██║  ██║██╗██╔════╝██╔════╝██║  ██║████╗  ██║
██║  ██║███████║╚═╝███████╗██║     ███████║██╔██╗ ██║
██║  ██║██╔══██║██╗╚════██║██║     ╚════██║██║╚██╗██║
██████╔╝██║  ██║╚═╝███████║╚██████╗     ██║██║ ╚████║
╚═════╝ ╚═╝  ╚═╝   ╚══════╝ ╚═════╝     ╚═╝╚═╝  ╚═══╝
</pre>

<h3>DH:SC4N — Dahua CCTV Scanner</h3>

<p>
  Сканер и брутфорсер стандартных учётных данных для устройств Dahua.<br/>
  Интерактивный TUI · Снятие снимков · Уведомления в Telegram · Экспорт в SmartPSS
  <br/><br/>
  <a href="https://github.com/p4lemoon/DH-SC4N/issues/new?labels=bug">🐛 Сообщить об ошибке</a>
  &nbsp;·&nbsp;
  <a href="https://github.com/p4lemoon/DH-SC4N/issues/new?labels=enhancement">💡 Предложить улучшение</a>
</p>
</div>

<br/>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Содержание</summary>
  <ol>
    <li><a href="#возможности">Возможности</a></li>
    <li>
      <a href="#начало-работы">Начало работы</a>
      <ul>
        <li><a href="#требования">Требования</a></li>
        <li><a href="#установка">Установка</a></li>
      </ul>
    </li>
    <li><a href="#использование">Использование</a></li>
    <li><a href="#конфигурация">Конфигурация</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#дисклеймер">Дисклеймер</a></li>
    <li><a href="#лицензия">Лицензия</a></li>
  </ol>
</details>

---

## Возможности

| | Фича | Описание |
|:---:|:---|:---|
| 🔐 | **Протокол Dahua** | Нативная бинарная авторизация на порту 37777 — работает даже без HTTP-доступа |
| 📸 | **Снятие снимков** | Автоматически сохраняет JPEG-кадры с каждого канала в папку `snapshots/` |
| 📨 | **Telegram-уведомления** | Мгновенная отправка IP, логина, пароля и фотоснимка в указанный чат |
| 📋 | **Экспорт для SmartPSS** | Генерация XML-файла для быстрого импорта устройств в ПО Dahua SmartPSS |
| 📄 | **Поддержка Masscan** | Принимает сырой вывод masscan — текстовый и JSON-форматы |
| ⚡ | **Многопоточность** | Настраиваемое количество воркеров и таймаутов |
| 🎨 | **Интерактивный TUI** | Красивое терминальное меню на `rich` + `prompt_toolkit` с рандомной цветовой темой |

<p align="right">(<a href="#readme-top">вернуться наверх</a>)</p>

---

## Начало работы

### Требования

- **Python** `>= 3.9`

### Установка

#### Вариант 1 — через `uv` (рекомендуется)

[uv](https://docs.astral.sh/uv/) — современный быстрый менеджер пакетов Python. Устанавливает зависимости из `uv.lock`, гарантируя воспроизводимость.

```sh
# 1. Установка uv (если ещё нет)
# Windows (PowerShell):
irm https://astral.sh/uv/install.ps1 | iex

# Linux / macOS:
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Клонировать репозиторий
git clone https://github.com/p4lemoon/DH-SC4N.git
cd DH-SC4N

# 3. Установить зависимости (виртуальное окружение создаётся автоматически)
uv sync
```

#### Вариант 2 — через `pip`

```sh
git clone https://github.com/p4lemoon/DH-SC4N.git
cd DH-SC4N

python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

Отредактируй `input.txt` — добавь адреса в формате `IP:PORT`, по одному на строку:
```
192.168.1.100:37777
10.0.0.55:37777
```
> Также поддерживается прямой вывод `masscan` в текстовом или JSON-формате.

<p align="right">(<a href="#readme-top">вернуться наверх</a>)</p>

---

## Использование

```sh
# Через CLI-команду (только uv)
uv run dahua-scanner

# Через модуль (uv или активированный venv)
python -m dahua_scanner

# Через корневой файл
python main.py
```

Навигация:

| Клавиша | Действие |
|:---:|:---|
| `↑` / `↓` или `k` / `j` | Навигация по меню |
| `Enter` | Выбрать / изменить пункт |
| `0` или `Ctrl+C` | Выйти |

**Выходные файлы:**

| Путь | Содержимое |
|:---|:---|
| `found_devices.txt` | Найденные устройства: `IP:port login:password` |
| `snapshots/` | JPEG-снимки с камер |
| `reports/save.xml` | XML для импорта в SmartPSS |
| `dahua_logs/` | Логи каждого запуска |

<p align="right">(<a href="#readme-top">вернуться наверх</a>)</p>

---

## Конфигурация

Все параметры настраиваются прямо в интерактивном меню при запуске.

**Секция «Бот»:**

| Параметр | По умолчанию | Описание |
|:---|:---:|:---|
| `token` | — | Токен Telegram-бота |
| `chat_id` | — | ID чата / пользователя для уведомлений |
| `send` | `True` | Включить отправку уведомлений |
| `test` | — | Отправить тестовое сообщение в бота |

**Секция «Scanner»:**

| Параметр | По умолчанию | Описание |
|:---|:---:|:---|
| `target_file` | `input.txt` | Путь к файлу со списком целей |
| `threads` | `100` | Количество параллельных потоков |
| `timeout` | `500` | Таймаут подключения, мс |
| `snapshots` | `True` | Сохранять снимки с камер |
| `make_import_file` | `True` | Создавать XML для SmartPSS |
| `max_entries` | `64` | Максимум устройств в одном XML-файле |

<p align="right">(<a href="#readme-top">вернуться наверх</a>)</p>

---

## Дисклеймер

> **⚠️ Только для авторизованного тестирования.**
>
> Данный инструмент предназначен **исключительно** для аудита безопасности собственной инфраструктуры или систем, на тестирование которых у вас есть явное разрешение.
>
> Несанкционированный доступ к чужим устройствам **является незаконным**. Автор не несёт никакой ответственности за неправомерное использование данного ПО.

<p align="right">(<a href="#readme-top">вернуться наверх</a>)</p>

---

## Лицензия

Распространяется под лицензией MIT. Подробнее см. файл `LICENSE`.

<p align="right">(<a href="#readme-top">вернуться наверх</a>)</p>



<!-- SHIELD LINKS -->
[python-shield]: https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white
[python-url]: https://python.org
[uv-shield]: https://img.shields.io/badge/uv-package%20manager-DE5FE9?style=for-the-badge&logo=astral&logoColor=white
[uv-url]: https://docs.astral.sh/uv/
[license-shield]: https://img.shields.io/github/license/p4lemoon/DH-SC4N?style=for-the-badge
[license-url]: https://github.com/p4lemoon/DH-SC4N/blob/master/LICENSE
[issues-shield]: https://img.shields.io/github/issues/p4lemoon/DH-SC4N?style=for-the-badge
[issues-url]: https://github.com/p4lemoon/DH-SC4N/issues
[stars-shield]: https://img.shields.io/github/stars/p4lemoon/DH-SC4N?style=for-the-badge
[stars-url]: https://github.com/p4lemoon/DH-SC4N/stargazers
