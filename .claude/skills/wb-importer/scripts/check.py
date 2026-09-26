"""Проверка репозитория WB Importer перед коммитом/публикацией.

Запуск из корня репозитория:  py .claude/skills/wb-importer/scripts/check.py
Код выхода 1, если есть ошибки (FAIL); предупреждения (WARN) не блокируют.
"""
import py_compile
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[4]
errors, warnings = [], []


def fail(msg):
    errors.append(msg)
    print(f"FAIL  {msg}")


def warn(msg):
    warnings.append(msg)
    print(f"WARN  {msg}")


def ok(msg):
    print(f"ok    {msg}")


def tracked_files():
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout
    return [line for line in out.splitlines() if line]


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


# 1. Компиляция
py_files = sorted(ROOT.glob("*.py"))
bad = []
for f in py_files:
    try:
        py_compile.compile(str(f), doraise=True)
    except py_compile.PyCompileError as e:
        bad.append(f.name)
        fail(f"синтаксическая ошибка: {e.msg}")
if not bad:
    ok(f"компиляция {len(py_files)} файлов")

# 2. Импорт модулей (без сети и БД: engine создаётся лениво)
res = subprocess.run(
    [sys.executable, "-c", "import config, models, mapping, api, db, cli, main"],
    cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
)
if res.returncode == 0:
    ok("импорт модулей")
else:
    tail = res.stderr.strip().splitlines()[-1] if res.stderr.strip() else "?"
    fail(f"импорт модулей: {tail}")

# 3. Команды main.py <-> README
readme = read("README.md")
commands = set(re.findall(r'cli\.add_command\(\w+,\s*"([\w-]+)"\)', read("main.py")))
documented = set(re.findall(r"py main\.py ([\w-]+)", readme)) - {"--help"}
for c in sorted(commands - documented):
    fail(f"команда '{c}' не описана в README (раздел «Использование»)")
for c in sorted(documented - commands):
    fail(f"README упоминает несуществующую команду '{c}'")
if commands == documented:
    ok(f"README описывает все {len(commands)} команд")

# 4. Ключи .env.example <-> config.py <-> README
example_keys = set(re.findall(r"^([A-Z_]+)=", read(".env.example"), re.M))
config_keys = set(re.findall(r'os\.getenv\("([A-Z_]+)"', read("config.py")))
for k in sorted(config_keys - example_keys):
    fail(f"config.py читает {k}, но его нет в .env.example")
for k in sorted(example_keys - config_keys):
    warn(f"{k} есть в .env.example, но не используется в config.py")
for k in sorted(example_keys):
    if k not in readme:
        warn(f"параметр {k} не описан в README (таблица параметров .env)")
if config_keys == example_keys:
    ok("ключи .env.example совпадают с config.py")

# 5. Что попало в git
files = tracked_files()
forbidden = re.compile(
    r"(^|/)\.env$|\.(csv|xlsx|log|pyc)$|^(backups|exports|Песочница|"
    r"Резервное копирование версий приложения|__pycache__)/"
)
leaked = [f for f in files if forbidden.search(f)]
for f in leaked:
    fail(f"в git отслеживается файл, которого там быть не должно: {f}")
if not leaked:
    ok(f"в git нет секретов и рабочих данных ({len(files)} файлов)")

# 6. Похожие на секреты строки
jwt = re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}")
hits = []
for f in files:
    p = ROOT / f
    if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".ico"}:
        continue
    try:
        text = p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    if jwt.search(text):
        hits.append(f)
for f in hits:
    fail(f"похоже на токен WB (JWT) в файле: {f}")
placeholders = {"", "your_password", "your_api_key_here"}
for key in ("DB_PASSWORD", "WB_API_KEY"):
    m = re.search(rf"^{key}=(.*)$", read(".env.example"), re.M)
    if m and m.group(1).strip() not in placeholders:
        fail(f".env.example: {key} похож на реальное значение, замените заглушкой")
if not hits:
    ok("токенов в отслеживаемых файлах не найдено")

# 7. Неотслеживаемые файлы — на заметку
status = subprocess.run(
    ["git", "-c", "core.quotepath=false", "status", "--porcelain"],
    cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
).stdout.strip()
if status:
    warn("есть незакоммиченные изменения:\n      " + status.replace("\n", "\n      "))

print()
print(f"Итого: {len(errors)} ошибок, {len(warnings)} предупреждений")
sys.exit(1 if errors else 0)
