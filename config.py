"""Конфигурация приложения."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_SCHEMA = os.getenv("DB_SCHEMA", "Wildberries")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Wildberries API
WB_API_KEY = os.getenv("WB_API_KEY", "")
WB_BASE_URL = "https://finance-api.wildberries.ru"
WB_DEFAULT_START_DATE = os.getenv("WB_DEFAULT_START_DATE", "2025-01-01")

# Лимиты API Wildberries
LIST_LIMIT = 1000  # максимум отчётов в одном запросе списка
DETAIL_LIMIT = 100000  # максимум строк детализации в одном запросе

# Rate limiting (согласно документации WB: 1 запрос в минуту)
REQUEST_DELAY = 65  # задержка между запросами в секундах (60 + запас 5 сек)
MAX_RETRIES = 3  # количество повторных попыток при ошибке 429
RETRY_DELAY = 60  # задержка перед повтором при 429

# Папки
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "./backups"))
EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "./exports"))
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# Лимиты API для поставок
SUPPLY_LIST_LIMIT = 1000
SUPPLY_GOODS_LIMIT = 1000

# Rate limiting для поставок (30 запросов в минуту = 1 запрос в 2 сек)
SUPPLY_REQUEST_DELAY = 3  # задержка между запросами в секундах (2 + запас 1 сек)
SUPPLY_MAX_RETRIES = 3
SUPPLY_RETRY_DELAY = 60

# Лимиты API для поставок
SUPPLY_LIST_LIMIT = 1000
SUPPLY_GOODS_LIMIT = 1000

# Rate limiting для поставок (30 запросов в минуту = 1 запрос в 2 сек)
SUPPLY_REQUEST_DELAY = 3  # задержка между запросами в секундах (2 + запас 1 сек)
SUPPLY_MAX_RETRIES = 3
SUPPLY_RETRY_DELAY = 60