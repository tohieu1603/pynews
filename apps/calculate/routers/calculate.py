# apps/calculate/routers/calculate.py
"""Calculate API routes for importing financial data."""

from typing import List
from ninja import Router, Schema
from ninja.errors import HttpError
import time

from apps.calculate.services.financial_service import CalculateService

router = Router(tags=["calculate"])


# Output schemas  
class ImportResultSchema(Schema):
    symbol: str
    success: bool
    balance_sheets: int = 0
    income_statements: int = 0
    cash_flows: int = 0
    errors: List[str] = []


class ImportSummarySchema(Schema):
    total_symbols: int
    successful_imports: int
    failed_imports: int
    total_balance_sheets: int
    total_income_statements: int
    total_cash_flows: int
    processing_time: float
    results: List[ImportResultSchema]


@router.post("/import/all", response=ImportSummarySchema)
def import_all_financials(request):
    """Import financial data for ALL symbols in database."""
    try:
        start_time = time.time()
        service = CalculateService()
        result = service.import_all_financials()
        processing_time = time.time() - start_time
        
        return ImportSummarySchema(
            total_symbols=result["total_symbols"],
            successful_imports=result["successful_symbols"],
            failed_imports=result["failed_symbols"],
            total_balance_sheets=result["total_balance_sheets"],
            total_income_statements=result["total_income_statements"],
            total_cash_flows=result["total_cash_flows"],
            processing_time=round(processing_time, 2),
            results=[
                ImportResultSchema(
                    symbol=detail["symbol"],
                    success=detail["success"],
                    balance_sheets=detail["balance_sheets"],
                    income_statements=detail["income_statements"],
                    cash_flows=detail["cash_flows"],
                    errors=detail["errors"]
                ) for detail in result["details"]
            ]
        )
        
    except Exception as e:
        raise HttpError(500, f"Error importing all financials: {str(e)}")