# apps/stock/routers/stock.py
from typing import List
from ninja import Router
from ninja.pagination import paginate, PageNumberPagination

from apps.stock.schemas import IndustryOut, SymbolOut, CompanyOut
from apps.stock.services.symbol_service import SymbolService
from apps.stock.services.company_service import CompanyService
from apps.stock.services.industry_service import IndustryService

router = Router(tags=["stock"])

@router.post("/symbols/import_all", response=List[SymbolOut])
def import_all_symbols(request):
    """
    Import toàn bộ symbol từ vnstock và trả về danh sách SymbolOut (tối giản).
    """
    service = SymbolService()
    return service.import_all_symbols()

@router.get("/company", response=List[CompanyOut])
@paginate(PageNumberPagination, page_size=10)
def get_all_companies(request):
    """
    Danh sách tất cả company (có phân trang) – build payload ở service.
    """
    service = CompanyService()
    return service.list_companies_payload()

@router.get("/industries", response=List[IndustryOut])
def get_all_industries(request):
    """
    Trả về list[IndustryOut] kèm symbols (được build ở service).
    """
    service = IndustryService()
    return service.list_industries_payload()

@router.get("/symbols/{symbol}", response=SymbolOut)
def get_symbol(request, symbol: str):
    """
    Lấy 1 symbol theo schema SymbolOut (đã map nested company & related).
    """
    service = SymbolService()
    return service.get_symbol_payload(symbol.upper())
