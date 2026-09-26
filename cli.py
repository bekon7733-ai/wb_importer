"""CLI-команды приложения."""
import logging
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple
from decimal import Decimal
import csv
from pathlib import Path
import click
from sqlalchemy import select, func, inspect
from sqlalchemy.dialects.postgresql import insert as pg_insert
from config import WB_DEFAULT_START_DATE, EXPORT_DIR, BACKUP_DIR
from db import (
    init_db, get_session, get_last_report_date, get_existing_report_ids,
    upsert_rows, backup_table, backup_all_tables, export_to_csv,
)
from models import PERIOD_MODELS
from api import (
    fetch_report_list, fetch_detail_by_report_id, fetch_detail_by_period,
    fetch_supply_list, fetch_supply_details, fetch_supply_goods,
)
from mapping import map_report_list, map_report_detail

logger = logging.getLogger("wb_importer")


def _resolve_period(period: str) -> List[str]:
    """Преобразовать строку периода в список."""
    if period == "all":
        return ["daily", "weekly"]
    if period not in ("daily", "weekly"):
        raise click.BadParameter("period должен быть daily, weekly или all")
    return [period]


def _ensure_parent_in_db(session, list_model, report_id: int,
                         report_row_api: dict) -> None:
    """Убедиться, что родительский отчёт есть в таблице списка."""
    existing = get_existing_report_ids(session, list_model)
    if report_id not in existing:
        mapped = map_report_list(report_row_api)
        upsert_rows(session, list_model, [mapped], pk_name="report_id")


# ========== init ==========

@click.command("init")
def cmd_init():
    """Инициализация БД: создание схемы и таблиц."""
    init_db()


# ========== update ==========

@click.command("update")
@click.option("--period", default="all",
              help="Период: daily / weekly / all (по умолчанию all)")
def cmd_update(period: str):
    """Автообновление всех таблиц от 'крайней' даты."""
    init_db()
    periods = _resolve_period(period)
    session = get_session()

    try:
        # Бэкап перед обновлением
        print("💾 Создание бэкапов...")
        paths = backup_all_tables(session, tag="update_")
        for p in paths:
            print(f"   {p}")
        if not paths:
            print("   (таблицы пусты, бэкап не создан)")

        for p in periods:
            list_m, detail_m = PERIOD_MODELS[p]
            
            # Определяем диапазон дат
            last_date = get_last_report_date(session, list_m)
            if last_date:
                # Продолжаем с последнего отчёта + 1 день
                date_from = (last_date + timedelta(days=1)).isoformat()
            else:
                # Первый запуск — с начальной даты
                date_from = WB_DEFAULT_START_DATE
                
            date_to = date.today().isoformat()
            
            print(f"\n🔄 Обновление ({p}): с {date_from} по {date_to}")
            print("=" * 60)

            # 1) Списки отчётов (1-2 запроса)
            print("📋 Загрузка списков отчётов...")
            reports = fetch_report_list(date_from, date_to, p)
            
            if not reports:
                print(f"   📭 Новых отчётов ({p}) нет.")
                continue
                
            mapped_lists = [map_report_list(r) for r in reports]
            n = upsert_rows(session, list_m, mapped_lists, pk_name="report_id")
            print(f"   ✅ Списков добавлено/обновлено: {n}")

            # 2) Детализация ВСЕХ отчётов ОДНИМ запросом за период!
            print(f"\n📥 Загрузка детализации ({p})...")
            print("   (это может занять время из-за лимитов API)")
            
            details = fetch_detail_by_period(date_from, date_to, p)
            
            if not details:
                print(f"   📭 Детализации ({p}) нет.")
                continue
                
            mapped_details = [map_report_detail(d) for d in details]
            
            # UPSERT детализации
            print(f"   💾 Сохранение {len(mapped_details):,} строк в БД...")
            upsert_rows(session, detail_m, mapped_details, pk_name="rrd_id")
            print(f"   ✅ Готово!")

        print("\n" + "=" * 60)
        print("✅ Обновление завершено!")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        logger.exception("Ошибка при update")
        raise
    finally:
        session.close()


# ========== list ==========

@click.command("list")
@click.option("--date-from", default=None, help="Начальная дата (ГГГГ-ММ-ДД)")
@click.option("--date-to", default=None, help="Конечная дата (ГГГГ-ММ-ДД)")
@click.option("--period", default="all",
              help="Период: daily / weekly / all")
def cmd_list(date_from: Optional[str], date_to: Optional[str], period: str):
    """Вывести список отчётов WB с отметкой загруженности."""
    init_db()
    periods = _resolve_period(period)
    today = date.today().isoformat()
    session = get_session()

    try:
        for p in periods:
            list_m, _ = PERIOD_MODELS[p]
            df = date_from or WB_DEFAULT_START_DATE
            dt = date_to or today
            
            print(f"\n📊 Отчёты ({p}) с {df} по {dt}:")
            print("=" * 80)
            
            reports = fetch_report_list(df, dt, p)
            
            if not reports:
                print("   (пусто)")
                continue
                
            loaded = get_existing_report_ids(session, list_m)
            
            print(f"{'ID':<12} {'От':<12} {'До':<12} {'К оплате':>14} {'Загружен'}")
            print("-" * 80)
            
            for r in reports:
                mark = "✓" if r["reportId"] in loaded else "  "
                print(
                    f"{r['reportId']:<12} "
                    f"{r.get('dateFrom',''):<12} "
                    f"{r.get('dateTo',''):<12} "
                    f"{str(r.get('bankPaymentSum','')):>14} "
                    f"  [{mark}]"
                )
                
    finally:
        session.close()


# ========== import ==========

@click.command("import")
@click.option("--report-id", multiple=True, type=int,
              help="ID отчёта (можно указывать несколько раз)")
@click.option("--date-from", default=None, help="Начальная дата")
@click.option("--date-to", default=None, help="Конечная дата")
@click.option("--period", default="daily", help="daily / weekly")
def cmd_import(report_id: Tuple[int, ...], date_from: Optional[str],
               date_to: Optional[str], period: str):
    """Загрузить отчёты в БД по ID или диапазону дат."""
    init_db()
    periods = _resolve_period(period)
    session = get_session()

    try:
        # Бэкап
        print("💾 Создание бэкапов...")
        paths = backup_all_tables(session, tag="import_")
        for p in paths:
            print(f"   {p}")
        if not paths:
            print("   (таблицы пусты)")

        for p in periods:
            list_m, detail_m = PERIOD_MODELS[p]

            # Определяем список отчётов для загрузки
            reports_to_load: List[dict] = []

            if report_id:
                # Загрузка по конкретным ID
                if not (date_from and date_to):
                    date_from = WB_DEFAULT_START_DATE
                    date_to = date.today().isoformat()
                    
                print(f"\n📥 Загрузка отчётов по ID: {list(report_id)}")
                all_reports = fetch_report_list(date_from, date_to, p)
                id_set = set(report_id)
                reports_to_load = [r for r in all_reports if r["reportId"] in id_set]
                
                if not reports_to_load:
                    print(f"⚠️  Отчёты {list(report_id)} не найдены в диапазоне.")
                    continue
                    
                # 1) Сохраняем списки
                mapped_lists = [map_report_list(r) for r in reports_to_load]
                n = upsert_rows(session, list_m, mapped_lists, pk_name="report_id")
                print(f"📋 Списков добавлено/обновлено: {n}")

                # 2) Детализация по каждому отчёту (отдельные запросы)
                for rep in reports_to_load:
                    rid = rep["reportId"]
                    details = fetch_detail_by_report_id(rid)
                    if not details:
                        continue
                    mapped_details = [map_report_detail(d) for d in details]
                    upsert_rows(session, detail_m, mapped_details, pk_name="rrd_id")
                    print(f"   ✅ Отчёт {rid}: {len(mapped_details):,} строк")

            else:
                # Загрузка по датам (ОПТИМИЗИРОВАНО!)
                if not (date_from and date_to):
                    print("❌ Укажите --date-from и --date-to или --report-id")
                    return
                    
                print(f"\n📥 Загрузка отчётов за период: {date_from} — {date_to} ({p})")
                print("=" * 60)
                
                # 1) Списки
                reports_to_load = fetch_report_list(date_from, date_to, p)
                if not reports_to_load:
                    print(f"📭 Нет отчётов для загрузки ({p}).")
                    continue
                    
                mapped_lists = [map_report_list(r) for r in reports_to_load]
                n = upsert_rows(session, list_m, mapped_lists, pk_name="report_id")
                print(f"📋 Списков добавлено/обновлено: {n}")

                # 2) Детализация ВСЕХ отчётов ОДНИМ запросом!
                print(f"\n📥 Загрузка детализации...")
                details = fetch_detail_by_period(date_from, date_to, p)
                
                if not details:
                    print(f"📭 Детализации нет.")
                    continue
                    
                mapped_details = [map_report_detail(d) for d in details]
                print(f"💾 Сохранение {len(mapped_details):,} строк в БД...")
                upsert_rows(session, detail_m, mapped_details, pk_name="rrd_id")
                print(f"✅ Готово!")

        print("\n" + "=" * 60)
        print("✅ Импорт завершён!")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        logger.exception("Ошибка при import")
        raise
    finally:
        session.close()


# ========== update-supplies ==========

@click.command("update-supplies")
def cmd_update_supplies():
    """Обновить данные о поставках."""
    from models import SupplyList, SupplyDetails, SupplyGoods

    # Инициализация БД (создаст таблицы поставок, если их нет)
    init_db()

    session = get_session()

    try:
        # Бэкап таблиц поставок
        print("💾 Создание бэкапов таблиц поставок...")
        paths = _backup_supply_tables(session, tag="update_")
        for p in paths:
            print(f"   {p}")
        if not paths:
            print("   (таблицы пусты)")
        
        # Определяем диапазон дат
        last_date = _get_last_supply_date(session)
        if last_date:
            date_from = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            date_from = WB_DEFAULT_START_DATE
            
        date_to = date.today().strftime("%Y-%m-%d")
        
        print(f"\n🔄 Обновление поставок: с {date_from} по {date_to}")
        print("=" * 60)
        
        # 1) Загружаем список поставок
        print("📋 Загрузка списка поставок...")
        dates_filter = [{
            "from": date_from,
            "till": date_to,
            "type": "factDate"
        }]
        
        # Только завершённые поставки (статусы 5 и 6)
        status_filter = [5, 6]
        
        supplies = fetch_supply_list(dates=dates_filter, status_ids=status_filter)
        
        if not supplies:
            print("   📭 Новых поставок нет.")
            return
        
        # 2) Сохраняем список поставок
        supply_ids = set()
        for supply in supplies:
            supply_data = {
                "supply_id": supply["supplyID"],
                "preorder_id": supply.get("preorderID"),
                "phone": supply.get("phone"),
                "create_date": _parse_datetime(supply.get("createDate")),
                "supply_date": _parse_datetime(supply.get("supplyDate")),
                "fact_date": _parse_datetime(supply.get("factDate")),
                "updated_date": _parse_datetime(supply.get("updatedDate")),
                "status_id": supply.get("statusID"),
                "box_type_id": supply.get("boxTypeID"),
                "is_box_on_pallet": supply.get("isBoxOnPallet"),
            }
            
            # UPSERT
            stmt = pg_insert(SupplyList).values(supply_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["supply_id"],
                set_={k: stmt.excluded[k] for k in supply_data if k != "supply_id"}
            )
            session.execute(stmt)
            supply_ids.add(supply["supplyID"])
        
        session.commit()
        print(f"   ✅ Поставок добавлено/обновлено: {len(supply_ids)}")
        
        # 3) Для каждой поставки загружаем детали и товары
        print(f"\n📥 Загрузка деталей и товаров для {len(supply_ids)} поставок...")
        
        for idx, supply_id in enumerate(supply_ids, 1):
            print(f"\n   [{idx}/{len(supply_ids)}] Поставка {supply_id}")
            
            # Детали поставки
            details = fetch_supply_details(supply_id)
            if details:
                details_data = {
                    "supply_id": details.get("supplyID", supply_id),
                    "phone": details.get("phone"),
                    "status_id": details.get("statusID"),
                    "virtual_type_id": details.get("virtualTypeID"),
                    "box_type_id": details.get("boxTypeID"),
                    "create_date": _parse_datetime(details.get("createDate")),
                    "supply_date": _parse_datetime(details.get("supplyDate")),
                    "fact_date": _parse_datetime(details.get("factDate")),
                    "updated_date": _parse_datetime(details.get("updatedDate")),
                    "warehouse_id": details.get("warehouseID"),
                    "warehouse_name": details.get("warehouseName"),
                    "actual_warehouse_id": details.get("actualWarehouseID"),
                    "actual_warehouse_name": details.get("actualWarehouseName"),
                    "transit_warehouse_id": details.get("transitWarehouseID"),
                    "transit_warehouse_name": details.get("transitWarehouseName"),
                    "acceptance_cost": details.get("acceptanceCost"),
                    "paid_acceptance_coefficient": details.get("paidAcceptanceCoefficient"),
                    "reject_reason": details.get("rejectReason"),
                    "supplier_assign_name": details.get("supplierAssignName"),
                    "storage_coef": details.get("storageCoef"),
                    "delivery_coef": details.get("deliveryCoef"),
                    "quantity": details.get("quantity"),
                    "ready_for_sale_quantity": details.get("readyForSaleQuantity"),
                    "accepted_quantity": details.get("acceptedQuantity"),
                    "unloading_quantity": details.get("unloadingQuantity"),
                    "depersonalized_quantity": details.get("depersonalizedQuantity"),
                    "is_box_on_pallet": details.get("isBoxOnPallet"),
                }
                
                stmt = pg_insert(SupplyDetails).values(details_data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["supply_id"],
                    set_={k: stmt.excluded[k] for k in details_data if k != "supply_id"}
                )
                session.execute(stmt)
                print(f"      ✅ Детали сохранены")
            
            # Товары поставки
            goods = fetch_supply_goods(supply_id)
            if goods:
                for good in goods:
                    good_data = {
                        "supply_id": supply_id,
                        "barcode": good.get("barcode"),
                        "vendor_code": good.get("vendorCode"),
                        "nm_id": good.get("nmID"),
                        "need_kiz": good.get("needKiz"),
                        "tnved": good.get("tnved"),
                        "tech_size": good.get("techSize"),
                        "color": good.get("color"),
                        "supplier_box_amount": good.get("supplierBoxAmount"),
                        "quantity": good.get("quantity"),
                        "ready_for_sale_quantity": good.get("readyForSaleQuantity"),
                        "accepted_quantity": good.get("acceptedQuantity"),
                        "unloading_quantity": good.get("unloadingQuantity"),
                    }
                    
                    # UPSERT для товаров — по уникальному ограничению supply_id + barcode
                    stmt = pg_insert(SupplyGoods).values(good_data)
                    stmt = stmt.on_conflict_do_update(
                        constraint="uq_supply_goods_barcode",
                        set_={k: stmt.excluded[k] for k in good_data 
                              if k not in ["supply_id", "barcode"]}
                    )
                    session.execute(stmt)
                
                print(f"      ✅ Товаров сохранено: {len(goods)}")
        
        session.commit()
        print("\n" + "=" * 60)
        print("✅ Обновление поставок завершено!")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        logger.exception("Ошибка при update-supplies")
        raise
    finally:
        session.close()


# ========== Вспомогательные функции для поставок ==========

def _get_last_supply_date(session) -> Optional[date]:
    """Получить максимальную fact_date из таблицы поставок."""
    from models import SupplyList
    stmt = select(func.max(SupplyList.fact_date))
    result = session.execute(stmt).scalar()
    return result


def _backup_supply_tables(session, tag: str = "") -> List:
    """Бэкап всех таблиц поставок."""
    from models import SupplyList, SupplyDetails, SupplyGoods
    
    paths = []
    for model, name in [
        (SupplyList, "list"),
        (SupplyDetails, "details"),
        (SupplyGoods, "goods")
    ]:
        p = _backup_table(session, model, f"{tag}{name}_")
        if p:
            paths.append(p)
    return paths


def _backup_table(session, model, tag: str = ""):
    """Сделать бэкап таблицы в CSV."""
    # Получаем все объекты
    rows = session.execute(select(model)).scalars().all()
    if not rows:
        return None
    
    # Получаем имена колонок
    mapper = inspect(model)
    columns = [c.key for c in mapper.columns]
    
    ts = datetime.now().strftime("%Y%m%d%H%M")
    filename = f"{model.__tablename__}_{tag}{ts}.csv".strip("_")
    filepath = BACKUP_DIR / filename
    
    with open(filepath, "w", newline="", encoding="windows-1251", errors="replace") as f:
        writer = csv.writer(f, delimiter=",", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(columns)
        for row in rows:
            # Извлекаем значения атрибутов
            values = [getattr(row, col) for col in columns]
            writer.writerow([_serialize(v) for v in values])
    
    return filepath


def _serialize(v):
    """Преобразование значений для CSV."""
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, datetime) else v.isoformat()
    if isinstance(v, Decimal):
        return str(v)
    if v is None:
        return ""
    return v


def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Преобразовать строку даты в datetime."""
    if not dt_str:
        return None
    try:
        # Формат: 2024-12-29T16:58:26+03:00
        dt_str = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(dt_str)
    except Exception:
        try:
            return datetime.strptime(dt_str[:19], "%Y-%m-%dT%H:%M:%S")
        except Exception:
            return None


# ========== export-list ==========

@click.command("export-list")
@click.option("--period", default="all", help="daily / weekly / all")
def cmd_export_list(period: str):
    """Экспорт списков отчётов в CSV."""
    init_db()
    periods = _resolve_period(period)
    session = get_session()

    try:
        for p in periods:
            list_m, _ = PERIOD_MODELS[p]
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = EXPORT_DIR / f"list_{p}_{ts}.csv"
            n = export_to_csv(session, list_m, filepath)
            print(f"📤 Экспорт списков ({p}): {n} строк → {filepath}")
            
    finally:
        session.close()


# ========== export-detail ==========

@click.command("export-detail")
@click.option("--period", default="all", help="daily / weekly / all")
def cmd_export_detail(period: str):
    """Экспорт детализаций в CSV."""
    init_db()
    periods = _resolve_period(period)
    session = get_session()

    try:
        for p in periods:
            _, detail_m = PERIOD_MODELS[p]
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = EXPORT_DIR / f"detail_{p}_{ts}.csv"
            n = export_to_csv(session, detail_m, filepath)
            print(f"📤 Экспорт детализаций ({p}): {n} строк → {filepath}")
            
    finally:
        session.close()


# ========== backup ==========

@click.command("backup")
def cmd_backup():
    """Ручной бэкап всех таблиц в CSV."""
    init_db()
    session = get_session()

    try:
        paths = backup_all_tables(session, tag="manual_")
        if not paths:
            print("📭 Таблицы пусты — бэкап не создан.")
            return
        print("💾 Бэкапы созданы:")
        for p in paths:
            print(f"   {p}")
            
    finally:
        session.close()


# ========== export-supplies ==========

@click.command("export-supplies")
def cmd_export_supplies():
    """Экспорт всех таблиц поставок в CSV."""
    init_db()
    session = get_session()

    try:
        print("📤 Экспорт таблиц поставок...")
        from db import export_supply_tables
        paths = export_supply_tables(session)
        if not paths:
            print("📭 Таблицы поставок пусты.")
            return
        print("\n" + "=" * 60)
        print("✅ Экспорт поставок завершён!")
    finally:
        session.close()