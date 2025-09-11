# apps/stock/routers/stock.py
"""Stock API routes.

Static '/symbols/*' routes are declared before dynamic '/symbols/{symbol}'
to avoid method shadowing (405) on specific paths.
"""

from typing import List
from ninja import Router
from ninja.pagination import paginate, PageNumberPagination

from apps.stock.schemas import IndustryOut, SymbolOut, CompanyOut
from apps.stock.services.symbol_service import SymbolService
from apps.stock.services.company_service import CompanyService
from apps.stock.services.industry_service import IndustryService

router = Router(tags=["stock"])

# ---------- Symbols (bulk) ----------
@router.post("/symbols/import_all", response=List[SymbolOut])
def import_all_symbols(request):
    service = SymbolService()
    return service.import_all_symbols()

@router.get("/symbols", response=List[SymbolOut])
def list_symbols(request):
    service = SymbolService()
    return service.list_symbols_payload()

# ---------- Imports by industry ----------
@router.post("/symbols/import_by_industry/{icb_code}", response=dict)
def import_symbols_by_industry(request, icb_code: int, level: int = 4):
    service = SymbolService()
    return service.import_symbols_by_industry(icb_code=icb_code, level=level)

@router.post("/symbols/import_by_industry/all", response=dict)
def import_symbols_by_all_industries(request):
    service = SymbolService()
    return service.import_symbols_by_all_industries(level=4)

# ---------- Full pipelines ----------
@router.post("/symbols/create_symbol_industry", response=dict)
def create_symbol_industry(request):
    service = SymbolService()
    return service.create_symbol_industry(level=4)

@router.get("/symbols/create_symbol_industry", response=dict)
def create_symbol_industry_get(request):
    service = SymbolService()
    return service.create_symbol_industry(level=4)

@router.post("/symbols/import_industry_company_symbol", response=dict)
def import_industry_company_symbol(request):
    service = SymbolService()
    return service.import_industry_company_symbol(level=level)

@router.get("/symbols/import_industry_company_symbol", response=dict)
def import_industry_company_symbol_get(request, level: int = 4):
    service = SymbolService()
    return service.import_industry_company_symbol(level=level)

# ---------- Other collections ----------
@router.post("/shareholders", response=dict)
def import_shareholders(request):
    service = SymbolService()
    count = service.import_all_shareholders()
    return {"imported_shareholders_count": count}

@router.post("/events", response=dict)
def import_events(request):
    service = SymbolService()
    count = service.import_all_events()
    return {"imported_events_count": count}

@router.post("/officers", response=dict)
def import_officers(request):
    service = SymbolService()
    count = service.import_all_officers()
    return {"imported_officers_count": count}

@router.post("/industries/import_all", response=dict)
def import_all_industries(request):
    service = SymbolService()
    count = service.import_all_industries()
    return {"imported_industries_count": count}

# ---------- Listing endpoints ----------
@router.get("/company", response=List[CompanyOut])
@paginate(PageNumberPagination, page_size=10)
def get_all_companies(request):
    service = CompanyService()
    return service.list_companies_payload()

@router.get("/industries", response=List[IndustryOut])
def get_all_industries(request):
    service = IndustryService()
    return service.list_industries_payload()

# ---------- Dynamic routes (placed last) ----------
@router.get("/symbols/{symbol}", response=SymbolOut)
def get_symbol(request, symbol: str):
    service = SymbolService()
    return service.get_symbol_payload(symbol.upper())

