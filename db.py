"""Работа с базой данных."""
import csv
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, select, func, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from config import DATABASE_URL, DB_SCHEMA, BACKUP_DIR, EXPORT_DIR
from models import Base, metadata, PERIOD_MODELS, ReportListDaily, ReportListWeekly

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db() -> None:
    """Создать схему и таблицы, если их нет."""
    with engine.connect() as conn:
        conn.execute(
            __import__("sqlalchemy").text(f'CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}"')
        )
        conn.commit()
    Base.metadata.create_all(bind=engine)
    print(f"✅ Схема '{DB_SCHEMA}' и таблицы инициализированы.")


def get_session() -> Session:
    return SessionLocal()


def get_last_report_date(session: Session, list_model) -> Optional[date]:
    """Получить максимальную date_to из таблицы списка."""
    stmt = select(func.max(list_model.date_to))
    result = session.execute(stmt).scalar()
    return result


def get_existing_report_ids(session: Session, list_model) -> set:
    """Получить множество report_id, уже загруженных в БД."""
    stmt = select(list_model.report_id)
    return {row[0] for row in session.execute(stmt).all()}


def upsert_rows(session: Session, model, rows: List[Dict[str, Any]],
                pk_name: str = "report_id") -> int:
    """UPSERT списка строк. Возвращает количество обработанных."""
    if not rows:
        return 0
    stmt = pg_insert(model).values(rows)
    update_cols = {c.name: c for c in stmt.excluded if c.name != pk_name}
    stmt = stmt.on_conflict_do_update(
        index_elements=[pk_name],
        set_=update_cols,
    )
    session.execute(stmt)
    session.commit()
    return len(rows)


def backup_table(session: Session, model, tag: str = "") -> Optional[Path]:
    """Сделать бэкап таблицы в CSV."""
    # Получаем все объекты
    rows = session.execute(select(model)).scalars().all()
    if not rows:
        return None
    
    # Получаем имена колонок
    mapper = inspect(model)
    columns = [c.key for c in mapper.columns]
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
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


def backup_all_tables(session: Session, tag: str = "") -> List[Path]:
    """Бэкап всех 4 таблиц."""
    paths = []
    for period in ("daily", "weekly"):
        list_m, detail_m = PERIOD_MODELS[period]
        p1 = backup_table(session, list_m, tag)
        p2 = backup_table(session, detail_m, tag)
        if p1:
            paths.append(p1)
        if p2:
            paths.append(p2)
    return paths


def export_to_csv(session: Session, model, filepath: Path) -> int:
    """Экспорт таблицы в CSV. Возвращает число строк."""
    # Получаем все объекты
    rows = session.execute(select(model)).scalars().all()
    
    # Получаем имена колонок
    mapper = inspect(model)
    columns = [c.key for c in mapper.columns]
    
    with open(filepath, "w", newline="", encoding="windows-1251", errors="replace") as f:
        writer = csv.writer(f, delimiter=",", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(columns)
        for row in rows:
            # Извлекаем значения атрибутов
            values = [getattr(row, col) for col in columns]
            writer.writerow([_serialize(v) for v in values])
    
    return len(rows)


def _serialize(v):
    """Преобразование значений для CSV."""
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, datetime) else v.isoformat()
    if isinstance(v, Decimal):
        # Заменяем точку на запятую для совместимости с Excel (как в DBeaver)
        return str(v).replace(".", ",")
    if v is None:
        return ""
    return v


# ========== ФУНКЦИИ ДЛЯ ПОСТАВОК ==========

def get_last_supply_date(session: Session) -> Optional[date]:
    """Получить максимальную fact_date из таблицы поставок."""
    from models import SupplyList
    stmt = select(func.max(SupplyList.fact_date))
    result = session.execute(stmt).scalar()
    return result


def get_existing_supply_ids(session: Session) -> set:
    """Получить множество supply_id, уже загруженных в БД."""
    from models import SupplyList
    stmt = select(SupplyList.supply_id)
    return {row[0] for row in session.execute(stmt).all()}


def backup_supply_tables(session: Session, tag: str = "") -> List[Path]:
    """Бэкап всех таблиц поставок."""
    from models import SupplyList, SupplyDetails, SupplyGoods
    paths = []
    for model, name in [
        (SupplyList, "list"),
        (SupplyDetails, "details"),
        (SupplyGoods, "goods")
    ]:
        p = backup_table(session, model, f"{tag}{name}_")
        if p:
            paths.append(p)
    return paths


def export_supply_tables(session: Session) -> List[Path]:
    """Экспорт всех таблиц поставок в CSV."""
    from models import SupplyList, SupplyDetails, SupplyGoods
    paths = []
    for model, name in [
        (SupplyList, "list"),
        (SupplyDetails, "details"),
        (SupplyGoods, "goods")
    ]:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = EXPORT_DIR / f"supply_{name}_{ts}.csv"
        n = export_to_csv(session, model, filepath)
        print(f"📤 Экспорт {name}: {n} строк → {filepath}")
        paths.append(filepath)
    return paths