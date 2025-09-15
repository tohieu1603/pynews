
from typing import Dict, Any
from django.db import transaction
from apps.calculate.models import BalanceSheet, IncomeStatement, CashFlow, Ratio
from apps.stock.models import Symbol

def upsert_balance_sheet(data: Dict[str, Any]) -> BalanceSheet:
    """
    Tạo hoặc update bảng cân đối kế toán cho một Symbol
    """
    symbol = data.pop('symbol')
    year_report = data.pop('year_report')
    length_report = data.pop('length_report')
    
    with transaction.atomic():
        balance_sheet, _ = BalanceSheet.objects.update_or_create(
            symbol=symbol,
            year_report=year_report,
            length_report=length_report,
            defaults=data
        )
        return balance_sheet

def upsert_income_statement(data: Dict[str, Any]) -> IncomeStatement:
    """
    Tạo hoặc update báo cáo kết quả kinh doanh cho một Symbol
    """
    symbol = data.pop('symbol')
    year_report = data.pop('year_report')
    length_report = data.pop('length_report')
    with transaction.atomic():
        income_statement, _ = IncomeStatement.objects.update_or_create(
            symbol=symbol,
            year_report=year_report,
            length_report=length_report,
            defaults=data,
        )
        return income_statement

def upsert_cash_flow(data: Dict[str, Any]) -> CashFlow:
    """
    Tạo hoặc update báo cáo lưu chuyển tiền tệ cho một Symbol
    """
    symbol = data.pop('symbol')
    year_report = data.pop('year_report')
    length_report = data.pop('length_report')
    with transaction.atomic():
        cash_flow, _ = CashFlow.objects.update_or_create(
            symbol=symbol,
            year_report=year_report,
            length_report=length_report,
            defaults=data,
        )
        return cash_flow
    
def upsert_ratio(data: Dict[str, Any]) -> Ratio:
    """Create or update Ratio for a Symbol by year_report + length_report."""
    symbol = data.pop('symbol')
    year_report = data.pop('year_report')
    length_report = data.pop('length_report')
    with transaction.atomic():
        ratio, _ = Ratio.objects.update_or_create(
            symbol=symbol,
            year_report=year_report,
            length_report=length_report,
            defaults=data,
        )
        return ratio
    
def qs_cash_flow(symbol: Symbol):
    return CashFlow.objects.filter(symbol=symbol).order_by('-year_report', '-length_report')

def qs_income_statement(symbol: Symbol):
    return IncomeStatement.objects.filter(symbol=symbol).order_by('-year_report', '-length_report')