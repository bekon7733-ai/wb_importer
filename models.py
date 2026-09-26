"""SQLAlchemy-модели таблиц."""
from sqlalchemy import (
    Column, BigInteger, String, Date, DateTime, Numeric, Integer,
    Boolean, ForeignKeyConstraint, Text, MetaData, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship
from config import DB_SCHEMA

metadata = MetaData(schema=DB_SCHEMA)
Base = declarative_base(metadata=metadata)


# ---------- Миксин для общих полей списков ----------
class ListMixin:
    """Общие поля для таблиц списков отчётов."""
    report_id = Column(BigInteger, primary_key=True)
    seller_finance_name = Column(String(255))
    date_from = Column(Date)
    date_to = Column(Date)
    create_date = Column(Date)
    currency = Column(String(10))
    report_type = Column(Integer)
    retail_amount_sum = Column(Numeric(18, 2))
    for_pay_sum = Column(Numeric(18, 2))
    avg_sale_percent = Column(Numeric(10, 4))
    delivery_service_sum = Column(Numeric(18, 2))
    paid_storage_sum = Column(Numeric(18, 2))
    paid_acceptance_sum = Column(Numeric(18, 2))
    deduction_sum = Column(Numeric(18, 2))
    penalty_sum = Column(Numeric(18, 2))
    additional_payment_sum = Column(Numeric(18, 2))
    cashback_amount_sum = Column(Numeric(18, 2))
    cashback_discount_sum = Column(Numeric(18, 2))
    cashback_commission_change_sum = Column(Numeric(18, 4))
    payment_schedule = Column(String(50))
    bank_payment_sum = Column(Numeric(18, 2))


# ---------- Миксин для общих полей детализаций ----------
class DetailMixin:
    """Общие поля для таблиц детализаций отчётов."""
    rrd_id = Column(BigInteger, primary_key=True)
    report_id = Column(BigInteger, nullable=False)
    date_from = Column(Date)
    date_to = Column(Date)
    create_date = Column(Date)
    currency = Column(String(10))
    report_type = Column(Integer)
    gi_id = Column(BigInteger)
    dlv_prc = Column(Numeric(10, 4))
    fix_tariff_date_from = Column(Date)
    fix_tariff_date_to = Column(Date)
    subject_name = Column(String(255))
    nm_id = Column(BigInteger)
    brand_name = Column(String(255))
    vendor_code = Column(String(100))
    title = Column(String(500))
    tech_size = Column(String(50))
    sku = Column(String(100))
    doc_type_name = Column(String(100))
    quantity = Column(Integer)
    retail_price = Column(Numeric(18, 2))
    retail_amount = Column(Numeric(18, 2))
    sale_percent = Column(Numeric(10, 4))
    commission_percent = Column(Numeric(10, 4))
    office_name = Column(String(255))
    seller_oper_name = Column(String(255))
    order_dt = Column(DateTime)
    sale_dt = Column(DateTime)
    rr_date = Column(Date)
    shk_id = Column(BigInteger)
    retail_price_with_disc = Column(Numeric(18, 2))
    delivery_amount = Column(Numeric(18, 2))
    return_amount = Column(Numeric(18, 2))
    delivery_service = Column(Numeric(18, 2))
    gi_box_type_name = Column(String(100))
    product_discount_for_report = Column(Numeric(18, 2))
    seller_promo = Column(Numeric(18, 2))
    spp = Column(Numeric(10, 4))
    kvw_base = Column(Numeric(10, 4))
    kvw = Column(Numeric(10, 4))
    sup_rating_up = Column(Integer)
    is_kgvp_v2 = Column(Integer)
    ppvz_sales_commission = Column(Numeric(18, 2))
    for_pay = Column(Numeric(18, 2))
    ppvz_reward = Column(Numeric(18, 2))
    acquiring_fee = Column(Numeric(18, 2))
    acquiring_percent = Column(Numeric(10, 4))
    payment_processing = Column(String(500))
    acquiring_bank = Column(String(255))
    vw = Column(Numeric(18, 2))
    vw_nds = Column(Numeric(18, 2))
    ppvz_office_name = Column(String(500))
    ppvz_office_id = Column(BigInteger)
    ppvz_supplier_name = Column(String(255))
    ppvz_supplier_inn = Column(String(50))
    declaration_number = Column(String(255))
    bonus_type_name = Column(Text)
    sticker_id = Column(String(50))
    country = Column(String(100))
    srv_dbs = Column(Boolean)
    penalty = Column(Numeric(18, 2))
    additional_payment = Column(Numeric(18, 2))
    rebill_logistic_cost = Column(Numeric(18, 4))
    rebill_logistic_org = Column(String(500))
    paid_storage = Column(Numeric(18, 2))
    deduction = Column(Numeric(18, 2))
    paid_acceptance = Column(Numeric(18, 2))
    order_id = Column(BigInteger)
    kiz = Column(Text)
    is_b2b = Column(Boolean)
    trbx_id = Column(String(100))
    installment_cofinancing_amount = Column(Numeric(18, 2))
    wibes_discount_percent = Column(Numeric(10, 4))
    cashback_amount = Column(Numeric(18, 2))
    cashback_discount = Column(Numeric(18, 2))
    cashback_commission_change = Column(Numeric(18, 4))
    payment_schedule = Column(String(50))
    delivery_method = Column(String(255))
    seller_promo_id = Column(BigInteger)
    seller_promo_discount = Column(Numeric(10, 4))
    loyalty_id = Column(BigInteger)
    loyalty_discount = Column(Numeric(10, 4))
    uuid_promocode = Column(String(100))
    sale_price_promocode_discount_prc = Column(Numeric(10, 4))
    article_substitution = Column(String(255))
    sale_price_affiliated_discount_prc = Column(Numeric(10, 4))
    agency_vat = Column(Numeric(10, 4))
    sale_price_wholesale_discount_prc = Column(Numeric(10, 4))
    order_uid = Column(String(100))
    srid = Column(String(255))


# ---------- Таблицы списков ----------
class ReportListDaily(ListMixin, Base):
    __tablename__ = "СписокОтчетовРеализацииСутки"
    __table_args__ = {"schema": DB_SCHEMA}
    details = relationship(
        "ReportDetailDaily",
        back_populates="report",
        cascade="all, delete-orphan",
    )


class ReportListWeekly(ListMixin, Base):
    __tablename__ = "СписокОтчетовРеализацииНеделя"
    __table_args__ = {"schema": DB_SCHEMA}
    details = relationship(
        "ReportDetailWeekly",
        back_populates="report",
        cascade="all, delete-orphan",
    )


# ---------- Таблицы детализаций (сокращённые имена!) ----------
class ReportDetailDaily(DetailMixin, Base):
    __tablename__ = "ДетализацииРеализацииСутки"
    __table_args__ = (
        ForeignKeyConstraint(
            ["report_id"],
            ["СписокОтчетовРеализацииСутки.report_id"],
            name="fk_detail_daily_report",
            ondelete="CASCADE",
        ),
        {"schema": DB_SCHEMA},
    )
    report = relationship(
        "ReportListDaily",
        back_populates="details",
    )


class ReportDetailWeekly(DetailMixin, Base):
    __tablename__ = "ДетализацииРеализацииНеделя"
    __table_args__ = (
        ForeignKeyConstraint(
            ["report_id"],
            ["СписокОтчетовРеализацииНеделя.report_id"],
            name="fk_detail_weekly_report",
            ondelete="CASCADE",
        ),
        {"schema": DB_SCHEMA},
    )
    report = relationship(
        "ReportListWeekly",
        back_populates="details",
    )


# Словарь соответствий: период -> (модель списка, модель детализации)
PERIOD_MODELS = {
    "daily":  (ReportListDaily,  ReportDetailDaily),
    "weekly": (ReportListWeekly, ReportDetailWeekly),
}


# ========== ТАБЛИЦЫ ПОСТАВОК ==========

class SupplyList(Base):
    """Список поставок."""
    __tablename__ = "СписокПоставок"
    __table_args__ = {"schema": DB_SCHEMA}
    
    supply_id = Column(BigInteger, primary_key=True)
    preorder_id = Column(BigInteger)
    phone = Column(String(50))
    create_date = Column(DateTime)
    supply_date = Column(DateTime)
    fact_date = Column(DateTime)
    updated_date = Column(DateTime)
    status_id = Column(Integer)
    box_type_id = Column(Integer)
    is_box_on_pallet = Column(Boolean)
    
    details = relationship("SupplyDetails", back_populates="supply",
                          cascade="all, delete-orphan", uselist=False)
    goods = relationship("SupplyGoods", back_populates="supply",
                        cascade="all, delete-orphan")


class SupplyDetails(Base):
    """Детали поставки."""
    __tablename__ = "ДеталиПоставки"
    __table_args__ = (
        ForeignKeyConstraint(
            ["supply_id"],
            ["СписокПоставок.supply_id"],
            name="fk_supply_details_supply",
            ondelete="CASCADE",
        ),
        {"schema": DB_SCHEMA},
    )
    
    supply_id = Column(BigInteger, primary_key=True)
    phone = Column(String(50))
    status_id = Column(Integer)
    virtual_type_id = Column(Integer)
    box_type_id = Column(Integer)
    create_date = Column(DateTime)
    supply_date = Column(DateTime)
    fact_date = Column(DateTime)
    updated_date = Column(DateTime)
    warehouse_id = Column(BigInteger)
    warehouse_name = Column(String(255))
    actual_warehouse_id = Column(BigInteger)
    actual_warehouse_name = Column(String(255))
    transit_warehouse_id = Column(BigInteger)
    transit_warehouse_name = Column(String(255))
    acceptance_cost = Column(Numeric(18, 2))
    paid_acceptance_coefficient = Column(Numeric(10, 4))
    reject_reason = Column(String(500))
    supplier_assign_name = Column(String(255))
    storage_coef = Column(String(50))
    delivery_coef = Column(String(50))
    quantity = Column(Integer)
    ready_for_sale_quantity = Column(Integer)
    accepted_quantity = Column(Integer)
    unloading_quantity = Column(Integer)
    depersonalized_quantity = Column(Integer)
    is_box_on_pallet = Column(Boolean)
    
    supply = relationship("SupplyList", back_populates="details")


class SupplyGoods(Base):
    """Товары поставки."""
    __tablename__ = "ТоварыПоставки"
    __table_args__ = (
        ForeignKeyConstraint(
            ["supply_id"],
            ["СписокПоставок.supply_id"],
            name="fk_supply_goods_supply",
            ondelete="CASCADE",
        ),
        # Уникальное ограничение: один баркод в рамках одной поставки
        UniqueConstraint(
            "supply_id", "barcode",
            name="uq_supply_goods_barcode"
        ),
        {"schema": DB_SCHEMA},
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    supply_id = Column(BigInteger, nullable=False)
    barcode = Column(String(100))
    vendor_code = Column(String(100))
    nm_id = Column(BigInteger)
    need_kiz = Column(Boolean)
    tnved = Column(String(50))
    tech_size = Column(String(50))
    color = Column(String(100))
    supplier_box_amount = Column(Integer)
    quantity = Column(Integer)
    ready_for_sale_quantity = Column(Integer)
    accepted_quantity = Column(Integer)
    unloading_quantity = Column(Integer)
    
    supply = relationship("SupplyList", back_populates="goods")


# Словарь моделей поставок
SUPPLY_MODELS = {
    "list": SupplyList,
    "details": SupplyDetails,
    "goods": SupplyGoods,
}