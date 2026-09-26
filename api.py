"""Работа с API Wildberries с учетом rate limiting."""
import logging
import time
from typing import List, Dict, Any, Optional

import requests

from config import (
    WB_API_KEY, WB_BASE_URL, LIST_LIMIT, DETAIL_LIMIT,
    MAX_RETRIES, RETRY_DELAY, REQUEST_DELAY,
    # Константы для поставок
    SUPPLY_LIST_LIMIT, SUPPLY_GOODS_LIMIT,
    SUPPLY_REQUEST_DELAY, SUPPLY_MAX_RETRIES, SUPPLY_RETRY_DELAY,
)

logger = logging.getLogger("wb_importer")

HEADERS = {
    "Authorization": WB_API_KEY,
    "Content-Type": "application/json",
}

# URL для API поставок (отдельный домен)
SUPPLIES_API_URL = "https://supplies-api.wildberries.ru"


def _request(method: str, path: str, payload: dict,
             expect_list: bool = True) -> Optional[List[Dict[str, Any]]]:
    """
    Универсальный запрос к API с обработкой повторов и rate limiting.
    
    ВАЖНО: После каждого успешного запроса делается пауза REQUEST_DELAY секунд
    для соблюдения лимита Wildberries (1 запрос в минуту).
    """
    url = f"{WB_BASE_URL}{path}"
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.debug(f"Запрос {attempt}/{MAX_RETRIES}: POST {path}")
            resp = requests.post(url, json=payload, headers=HEADERS, timeout=120)
        except requests.RequestException as e:
            logger.error(f"Ошибка соединения (попытка {attempt}): {e}")
            if attempt == MAX_RETRIES:
                return None
            time.sleep(RETRY_DELAY)
            continue

        # Обработка ответов API
        if resp.status_code == 200:
            data = resp.json()
            # Rate limiting: ждём перед следующим запросом
            time.sleep(REQUEST_DELAY)
            return data if expect_list else data
            
        if resp.status_code == 204:
            # Нет данных — тоже ждём (это считается как запрос)
            time.sleep(REQUEST_DELAY)
            return []
            
        if resp.status_code == 401:
            logger.error("❌ 401: неверный API-ключ. Проверьте .env")
            raise RuntimeError("Неверный API-ключ Wildberries")
            
        if resp.status_code == 402:
            logger.error("❌ 402: недостаточно средств на балансе WB")
            return None
            
        if resp.status_code == 429:
            logger.warning(f"⏳ 429: слишком много запросов. Ждём {RETRY_DELAY}с (попытка {attempt})")
            if attempt == MAX_RETRIES:
                return None
            time.sleep(RETRY_DELAY)
            continue
            
        if resp.status_code == 400:
            logger.error(f"❌ 400: {resp.text}")
            return None

        logger.error(f"Неожиданный код {resp.status_code}: {resp.text}")
        return None
        
    return None


def _request_supplies(method: str, path: str, 
                      params: dict = None, 
                      payload: dict = None) -> Optional[Any]:
    """
    Универсальный запрос к API поставок (supplies-api.wildberries.ru).
    
    Rate limiting: 30 запросов в минуту = 1 запрос в 2 секунды.
    """
    url = f"{SUPPLIES_API_URL}{path}"
    
    for attempt in range(1, SUPPLY_MAX_RETRIES + 1):
        try:
            logger.debug(f"Запрос поставок {attempt}/{SUPPLY_MAX_RETRIES}: {method} {path}")
            
            if method == "GET":
                resp = requests.get(url, params=params, headers=HEADERS, timeout=120)
            else:
                resp = requests.post(url, json=payload, headers=HEADERS, timeout=120)
                
        except requests.RequestException as e:
            logger.error(f"Ошибка соединения (попытка {attempt}): {e}")
            if attempt == SUPPLY_MAX_RETRIES:
                return None
            time.sleep(SUPPLY_RETRY_DELAY)
            continue

        # Обработка ответов API поставок
        if resp.status_code == 200:
            data = resp.json()
            # Rate limiting для поставок: 2 секунды между запросами
            time.sleep(SUPPLY_REQUEST_DELAY)
            return data
            
        if resp.status_code == 204:
            time.sleep(SUPPLY_REQUEST_DELAY)
            return []
            
        if resp.status_code == 401:
            logger.error("❌ 401: неверный API-ключ для API поставок")
            raise RuntimeError("Неверный API-ключ Wildberries")
            
        if resp.status_code == 402:
            logger.error("❌ 402: недостаточно средств на балансе WB")
            return None
            
        if resp.status_code == 429:
            logger.warning(f"⏳ 429: слишком много запросов к API поставок. Ждём {SUPPLY_RETRY_DELAY}с")
            if attempt == SUPPLY_MAX_RETRIES:
                return None
            time.sleep(SUPPLY_RETRY_DELAY)
            continue
            
        if resp.status_code == 400:
            logger.error(f" 400: {resp.text}")
            return None
            
        if resp.status_code == 404:
            logger.warning(f"️ 404: не найдено {path}")
            return None

        logger.error(f"Неожиданный код {resp.status_code}: {resp.text}")
        return None
        
    return None


# ========== СПИСКИ ОТЧЁТОВ ==========

def fetch_report_list(date_from: str, date_to: str,
                      period: str) -> List[Dict[str, Any]]:
    """
    Получить ВСЕ отчёты за период с пагинацией.
    
    Оптимизация: используем limit=1000, поэтому за 1.5 года данных
    потребуется всего 1 запрос (540 отчётов поместятся в один ответ).
    
    Returns: список отчётов
    """
    all_rows: List[Dict[str, Any]] = []
    offset = 0
    
    logger.info(f"Загрузка списков отчётов ({period}) с {date_from} по {date_to}...")
    
    while True:
        payload = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "limit": LIST_LIMIT,
            "offset": offset,
            "period": period,
        }
        
        rows = _request("POST", "/api/finance/v1/sales-reports/list", payload)
        
        if not rows:
            break
            
        all_rows.extend(rows)
        
        # Если получили меньше лимита — это последний запрос
        if len(rows) < LIST_LIMIT:
            break
            
        offset += LIST_LIMIT
        logger.info(f"  Загружено {len(all_rows)} отчётов... (продолжаем)")
    
    logger.info(f"  ✅ Всего загружено: {len(all_rows)} отчётов ({period})")
    return all_rows


# ========== ДЕТАЛИЗАЦИЯ ПО ПЕРИОДУ (ОПТИМИЗИРОВАНО!) ==========

def fetch_detail_by_period(date_from: str, date_to: str,
                           period: str) -> List[Dict[str, Any]]:
    """
    Получить ВСЮ детализацию за период с пагинацией.
    
    ОПТИМИЗАЦИЯ: Вместо запроса по каждому reportId (540 запросов),
    делаем один запрос за период с пагинацией по rrdId.
    
    Если данных > 100,000 строк, API сам разобьёт на несколько запросов.
    Каждый запрос = 1 минута ожидания.
    
    Returns: список строк детализации
    """
    all_rows: List[Dict[str, Any]] = []
    rrd_id = 0
    request_count = 0
    
    logger.info(f"Загрузка детализации ({period}) с {date_from} по {date_to}...")
    
    while True:
        payload = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "limit": DETAIL_LIMIT,
            "rrdId": rrd_id,
            "period": period,
        }
        
        rows = _request(
            "POST",
            "/api/finance/v1/sales-reports/detailed",
            payload,
        )
        
        if not rows:
            break
            
        request_count += 1
        all_rows.extend(rows)
        
        # Если получили меньше лимита — это последний запрос
        if len(rows) < DETAIL_LIMIT:
            break
            
        # Берём rrdId последней строки для следующего запроса
        rrd_id = rows[-1]["rrdId"]
        
        logger.info(f"  Загружено {len(all_rows):,} строк... (запросов: {request_count}, продолжаем)")
    
    logger.info(f"  ✅ Всего загружено: {len(all_rows):,} строк ({request_count} запросов, {period})")
    return all_rows


# ========== ДЕТАЛИЗАЦИЯ ПО ID ОТЧЁТА (для ручного импорта) ==========

def fetch_detail_by_report_id(report_id: int) -> List[Dict[str, Any]]:
    """
    Получить детализацию ОДНОГО отчёта по его ID.
    
    Используется ТОЛЬКО для команды import с указанием конкретных report_id.
    Для bulk update используйте fetch_detail_by_period!
    
    Returns: список строк детализации
    """
    all_rows: List[Dict[str, Any]] = []
    rrd_id = 0
    request_count = 0
    
    logger.info(f"Загрузка детализации отчёта {report_id}...")
    
    while True:
        payload = {
            "limit": DETAIL_LIMIT,
            "rrdId": rrd_id,
        }
        
        rows = _request(
            "POST",
            f"/api/finance/v1/sales-reports/detailed/{report_id}",
            payload,
        )
        
        if not rows:
            break
            
        request_count += 1
        all_rows.extend(rows)
        
        if len(rows) < DETAIL_LIMIT:
            break
            
        rrd_id = rows[-1]["rrdId"]
        logger.info(f"  Отчёт {report_id}: загружено {len(all_rows):,} строк...")
    
    logger.info(f"  ✅ Отчёт {report_id}: {len(all_rows):,} строк ({request_count} запросов)")
    return all_rows


# ========== ПОСТАВКИ ==========

def fetch_supply_list(dates: List[Dict] = None, 
                      status_ids: List[int] = None) -> List[Dict[str, Any]]:
    """
    Получить список поставок.
    
    Args:
        dates: Фильтр по датам [{"from": "2025-01-01", "till": "2026-06-22", "type": "factDate"}]
        status_ids: Фильтр по статусам [1, 2, 3, 4, 5, 6]
    
    Returns: список поставок (только с supplyID != null)
    """
    all_supplies: List[Dict[str, Any]] = []
    offset = 0
    
    logger.info("Загрузка списка поставок...")
    
    payload: Dict[str, Any] = {
        "limit": SUPPLY_LIST_LIMIT,
        "offset": offset,
    }
    
    if dates:
        payload["dates"] = dates
    if status_ids:
        payload["statusIDs"] = status_ids
    
    while True:
        payload["offset"] = offset
        
        supplies = _request_supplies(
            "POST", 
            "/api/v1/supplies",
            payload=payload
        )
        
        if not supplies:
            break
        
        # Фильтруем только фактические поставки (supplyID != null)
        actual_supplies = [s for s in supplies if s.get("supplyID") is not None]
        all_supplies.extend(actual_supplies)
        
        if len(supplies) < SUPPLY_LIST_LIMIT:
            break
            
        offset += SUPPLY_LIST_LIMIT
        logger.info(f"  Загружено {len(all_supplies)} поставок... (продолжаем)")
    
    logger.info(f"  ✅ Всего загружено: {len(all_supplies)} поставок")
    return all_supplies


def fetch_supply_details(supply_id: int) -> Optional[Dict[str, Any]]:
    """
    Получить детали поставки по ID.
    
    Returns: детали поставки или None
    """
    logger.info(f"Загрузка деталей поставки {supply_id}...")
    
    params = {"isPreorderID": False}
    
    details = _request_supplies(
        "GET", 
        f"/api/v1/supplies/{supply_id}",
        params=params
    )
    
    if details:
        logger.info(f"  ✅ Детали поставки {supply_id} загружены")
    else:
        logger.warning(f"  ️ Не удалось загрузить детали поставки {supply_id}")
    
    return details


def fetch_supply_goods(supply_id: int) -> List[Dict[str, Any]]:
    """
    Получить товары поставки.
    
    Returns: список товаров в поставке
    """
    all_goods: List[Dict[str, Any]] = []
    offset = 0
    
    logger.info(f"Загрузка товаров поставки {supply_id}...")
    
    while True:
        params = {
            "limit": SUPPLY_GOODS_LIMIT,
            "offset": offset,
            "isPreorderID": False,
        }
        
        goods = _request_supplies(
            "GET", 
            f"/api/v1/supplies/{supply_id}/goods",
            params=params
        )
        
        if not goods:
            break
        
        all_goods.extend(goods)
        
        if len(goods) < SUPPLY_GOODS_LIMIT:
            break
            
        offset += SUPPLY_GOODS_LIMIT
        logger.info(f"  Загружено {len(all_goods)} товаров... (продолжаем)")
    
    logger.info(f"  ✅ Всего товаров в поставке {supply_id}: {len(all_goods)}")
    return all_goods