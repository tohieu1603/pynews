import logging
from typing import Dict, Any, Optional
from django.db import transaction
from apps.calculate.models import BalanceSheet, IncomeStatement, CashFlow, Ratio
from apps.stock.models import Symbol

logger = logging.getLogger(__name__)  

def upsert_balance_sheet(data: Dict[str, Any]) -> Optional[BalanceSheet]:
    try:
        symbol = data.pop('symbol')
        year_report = data.pop('year_report')
        length_report = data.pop('length_report')

        with transaction.atomic():
            obj, _ = BalanceSheet.objects.update_or_create(
                symbol=symbol,
                year_report=year_report,
                length_report=length_report,
                defaults=data
            )
        return obj
    except Exception as e:
        logger.error(f"[upsert_balance_sheet] {e}")
        return None

def upsert_income_statement(data: Dict[str, Any]) -> Optional[IncomeStatement]:
    try:
        symbol = data.pop('symbol')
        year_report = data.pop('year_report')
        length_report = data.pop('length_report')

        with transaction.atomic():
            obj, _ = IncomeStatement.objects.update_or_create(
                symbol=symbol,
                year_report=year_report,
                length_report=length_report,
                defaults=data
            )
        return obj
    except Exception as e:
        logger.error(f"[upsert_income_statement] {e}")
        return None

def upsert_cash_flow(data: Dict[str, Any]) -> Optional[CashFlow]:
    try:
        symbol = data.pop('symbol')
        year_report = data.pop('year_report')
        length_report = data.pop('length_report')

        with transaction.atomic():
            obj, _ = CashFlow.objects.update_or_create(
                symbol=symbol,
                year_report=year_report,
                length_report=length_report,
                defaults=data
            )
        return obj
    except Exception as e:
        logger.error(f"[upsert_cash_flow] {e}")
        return None

def upsert_ratio(data: Dict[str, Any]) -> Optional[Ratio]:
    try:
        symbol = data.pop('symbol')
        year_report = data.pop('year_report')
        length_report = data.pop('length_report')

        with transaction.atomic():
            obj, _ = Ratio.objects.update_or_create(
                symbol=symbol,
                year_report=year_report,
                length_report=length_report,
                defaults=data
            )
        return obj
    except Exception as e:
        logger.error(f"[upsert_ratio] {e}")
        return None

def qs_cash_flow(symbol_id: int, limit: Optional[int] = None):
    try:
        qs = CashFlow.objects.filter(symbol_id=symbol_id).select_related('symbol').order_by('-year_report', '-length_report')
        if limit:
            qs = qs[:limit]
        return qs
    except Exception as e:
        logger.error(f"[qs_cash_flow] Error fetching cash flows for symbol_id={symbol_id}: {e}")
        return CashFlow.objects.none() 

def qs_income_statement(symbol: Symbol):
    try:
        return IncomeStatement.objects.filter(symbol=symbol).order_by('-year_report', '-length_report')
    except Exception as e:
        logger.error(f"[qs_income_statement] Error fetching income statements for symbol={symbol.id}: {e}")
        return IncomeStatement.objects.none()
def qs_income_statement(symbol_id: int):
    try:
        return IncomeStatement.objects.filter(symbol_id=symbol_id).order_by('-year_report', '-length_report')
    except Exception as e:
        logger.error(f"[qs_income_statement] Error fetching income statements for symbol_id={symbol_id}: {e}")
        return IncomeStatement.objects.none()
def qs_balance_sheet(symbol_id: int):
    try:
        return BalanceSheet.objects.filter(symbol_id=symbol_id).order_by('-year_report', '-length_report')
    except Exception as e:
        logger.error(f"[qs_balance_sheet] Error fetching balance sheets for symbol_id={symbol_id}: {e}")
        return BalanceSheet.objects.none()
def qs_ratio(symbol_id: int):
    try:
        return Ratio.objects.filter(symbol_id=symbol_id).order_by('-year_report', '-length_report')
    except Exception as e:
        logger.error(f"[qs_ratio] Error fetching ratios for symbol_id={symbol_id}: {e}")
        return Ratio.objects.none()