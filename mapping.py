"""Преобразование JSON-ответов API в словари для SQLAlchemy."""
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional


def _to_date(v) -> Optional[date]:
    if not v:
        return None
    if isinstance(v, date):
        return v
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).date()
    except Exception:
        try:
            return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
        except Exception:
            return None


def _to_datetime(v) -> Optional[datetime]:
    if not v:
        return None
    if isinstance(v, datetime):
        return v
    try:
        s = str(v).replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _to_decimal(v) -> Optional[Decimal]:
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None


def _to_int(v) -> Optional[int]:
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def _to_bool(v) -> Optional[bool]:
    if v is None:
        return None
    return bool(v)


# Маппинг полей ответа API "Список отчётов" -> БД
LIST_MAPPING = {
    "reportId": "report_id",
    "sellerFinanceName": "seller_finance_name",
    "dateFrom": "date_from",
    "dateTo": "date_to",
    "createDate": "create_date",
    "currency": "currency",
    "reportType": "report_type",
    "retailAmountSum": "retail_amount_sum",
    "forPaySum": "for_pay_sum",
    "avgSalePercent": "avg_sale_percent",
    "deliveryServiceSum": "delivery_service_sum",
    "paidStorageSum": "paid_storage_sum",
    "paidAcceptanceSum": "paid_acceptance_sum",
    "deductionSum": "deduction_sum",
    "penaltySum": "penalty_sum",
    "additionalPaymentSum": "additional_payment_sum",
    "cashbackAmountSum": "cashback_amount_sum",
    "cashbackDiscountSum": "cashback_discount_sum",
    "cashbackCommissionChangeSum": "cashback_commission_change_sum",
    "paymentSchedule": "payment_schedule",
    "bankPaymentSum": "bank_payment_sum",
}

LIST_DATE_FIELDS = {"date_from", "date_to", "create_date"}
LIST_DECIMAL_FIELDS = {
    "retail_amount_sum", "for_pay_sum", "avg_sale_percent",
    "delivery_service_sum", "paid_storage_sum", "paid_acceptance_sum",
    "deduction_sum", "penalty_sum", "additional_payment_sum",
    "cashback_amount_sum", "cashback_discount_sum",
    "cashback_commission_change_sum", "bank_payment_sum",
}


def map_report_list(row: Dict[str, Any]) -> Dict[str, Any]:
    """Преобразовать строку ответа 'Список отчётов' в запись для БД."""
    out: Dict[str, Any] = {}
    for api_key, db_key in LIST_MAPPING.items():
        v = row.get(api_key)
        if db_key in LIST_DATE_FIELDS:
            out[db_key] = _to_date(v)
        elif db_key in LIST_DECIMAL_FIELDS:
            out[db_key] = _to_decimal(v)
        elif db_key == "report_type":
            out[db_key] = _to_int(v)
        else:
            out[db_key] = v
    return out


# Маппинг полей ответа API "Детализация" -> БД
DETAIL_MAPPING = {
    "reportId": "report_id",
    "dateFrom": "date_from",
    "dateTo": "date_to",
    "createDate": "create_date",
    "currency": "currency",
    "reportType": "report_type",
    "rrdId": "rrd_id",
    "giId": "gi_id",
    "dlvPrc": "dlv_prc",
    "fixTariffDateFrom": "fix_tariff_date_from",
    "fixTariffDateTo": "fix_tariff_date_to",
    "subjectName": "subject_name",
    "nmId": "nm_id",
    "brandName": "brand_name",
    "vendorCode": "vendor_code",
    "title": "title",
    "techSize": "tech_size",
    "sku": "sku",
    "docTypeName": "doc_type_name",
    "quantity": "quantity",
    "retailPrice": "retail_price",
    "retailAmount": "retail_amount",
    "salePercent": "sale_percent",
    "commissionPercent": "commission_percent",
    "officeName": "office_name",
    "sellerOperName": "seller_oper_name",
    "orderDt": "order_dt",
    "saleDt": "sale_dt",
    "rrDate": "rr_date",
    "shkId": "shk_id",
    "retailPriceWithDisc": "retail_price_with_disc",
    "deliveryAmount": "delivery_amount",
    "returnAmount": "return_amount",
    "deliveryService": "delivery_service",
    "giBoxTypeName": "gi_box_type_name",
    "productDiscountForReport": "product_discount_for_report",
    "sellerPromo": "seller_promo",
    "spp": "spp",
    "kvwBase": "kvw_base",
    "kvw": "kvw",
    "supRatingUp": "sup_rating_up",
    "isKgvpV2": "is_kgvp_v2",
    "ppvzSalesCommission": "ppvz_sales_commission",
    "forPay": "for_pay",
    "ppvzReward": "ppvz_reward",
    "acquiringFee": "acquiring_fee",
    "acquiringPercent": "acquiring_percent",
    "paymentProcessing": "payment_processing",
    "acquiringBank": "acquiring_bank",
    "vw": "vw",
    "vwNds": "vw_nds",
    "ppvzOfficeName": "ppvz_office_name",
    "ppvzOfficeId": "ppvz_office_id",
    "ppvzSupplierName": "ppvz_supplier_name",
    "ppvzSupplierInn": "ppvz_supplier_inn",
    "declarationNumber": "declaration_number",
    "bonusTypeName": "bonus_type_name",
    "stickerId": "sticker_id",
    "country": "country",
    "srvDbs": "srv_dbs",
    "penalty": "penalty",
    "additionalPayment": "additional_payment",
    "rebillLogisticCost": "rebill_logistic_cost",
    "rebillLogisticOrg": "rebill_logistic_org",
    "paidStorage": "paid_storage",
    "deduction": "deduction",
    "paidAcceptance": "paid_acceptance",
    "orderId": "order_id",
    "kiz": "kiz",
    "isB2b": "is_b2b",
    "trbxId": "trbx_id",
    "installmentCofinancingAmount": "installment_cofinancing_amount",
    "wibesDiscountPercent": "wibes_discount_percent",
    "cashbackAmount": "cashback_amount",
    "cashbackDiscount": "cashback_discount",
    "cashbackCommissionChange": "cashback_commission_change",
    "paymentSchedule": "payment_schedule",
    "deliveryMethod": "delivery_method",
    "sellerPromoId": "seller_promo_id",
    "sellerPromoDiscount": "seller_promo_discount",
    "loyaltyId": "loyalty_id",
    "loyaltyDiscount": "loyalty_discount",
    "uuidPromocode": "uuid_promocode",
    "salePricePromocodeDiscountPrc": "sale_price_promocode_discount_prc",
    "articleSubstitution": "article_substitution",
    "salePriceAffiliatedDiscountPrc": "sale_price_affiliated_discount_prc",
    "agencyVat": "agency_vat",
    "salePriceWholesaleDiscountPrc": "sale_price_wholesale_discount_prc",
    "orderUid": "order_uid",
    "srid": "srid",
}

DETAIL_DATE_FIELDS = {
    "date_from", "date_to", "create_date", "rr_date",
    "fix_tariff_date_from", "fix_tariff_date_to",
}
DETAIL_DATETIME_FIELDS = {"order_dt", "sale_dt"}
DETAIL_DECIMAL_FIELDS = {
    "dlv_prc", "retail_price", "retail_amount", "sale_percent",
    "commission_percent", "retail_price_with_disc", "delivery_amount",
    "return_amount", "delivery_service", "product_discount_for_report",
    "seller_promo", "spp", "kvw_base", "kvw", "ppvz_sales_commission",
    "for_pay", "ppvz_reward", "acquiring_fee", "acquiring_percent",
    "vw", "vw_nds", "penalty", "additional_payment", "rebill_logistic_cost",
    "paid_storage", "deduction", "paid_acceptance",
    "installment_cofinancing_amount", "wibes_discount_percent",
    "cashback_amount", "cashback_discount", "cashback_commission_change",
    "seller_promo_discount", "loyalty_discount",
    "sale_price_promocode_discount_prc", "sale_price_affiliated_discount_prc",
    "agency_vat", "sale_price_wholesale_discount_prc",
}
DETAIL_INT_FIELDS = {
    "report_type", "quantity", "sup_rating_up", "is_kgvp_v2",
    "gi_id", "nm_id", "shk_id", "ppvz_office_id", "order_id",
    "seller_promo_id", "loyalty_id",
}
DETAIL_BOOL_FIELDS = {"srv_dbs", "is_b2b"}


def map_report_detail(row: Dict[str, Any]) -> Dict[str, Any]:
    """Преобразовать строку ответа 'Детализация' в запись для БД."""
    out: Dict[str, Any] = {}
    for api_key, db_key in DETAIL_MAPPING.items():
        v = row.get(api_key)
        if db_key in DETAIL_DATE_FIELDS:
            out[db_key] = _to_date(v)
        elif db_key in DETAIL_DATETIME_FIELDS:
            out[db_key] = _to_datetime(v)
        elif db_key in DETAIL_DECIMAL_FIELDS:
            out[db_key] = _to_decimal(v)
        elif db_key in DETAIL_INT_FIELDS:
            out[db_key] = _to_int(v)
        elif db_key in DETAIL_BOOL_FIELDS:
            out[db_key] = _to_bool(v)
        else:
            out[db_key] = v
    return out