# apps/stock/routers/vnstock_import.py
"""VNStock Import API routes."""

from typing import Dict, Any
from ninja import Router, Query
from ninja.pagination import paginate, PageNumberPagination
from apps.stock.schemas import SymbolOut, CompanyOut, SymbolList, SubCompanyOut
from apps.stock.services.symbol_service import SymbolService
from typing import List
from apps.stock.services.vnstock_import_service import VnstockImportService

router = Router(tags=["vnstock-import"])


@router.post("/symbols/import_all", response=List[SymbolOut])
def import_all_symbols(request):
    service = SymbolService()
    return service.import_all_symbols()


@router.post("/import/symbols")
def import_symbols_from_vnstock(request, exchange: str = "HSX"):
    """Import tất cả symbols từ vnstock theo exchange"""
    service = VnstockImportService()
    return service.import_all_symbols_from_vnstock(exchange)


@router.post("/import/companies") 
def import_companies_for_symbols(request, exchange: str = "HSX"):
    """Import company data cho tất cả symbols có trong database"""
    service = VnstockImportService()
    return service.import_companies_from_vnstock(exchange)


@router.post("/import/industries")
def import_industries_for_symbols(request):
    """Import industry data và tạo quan hệ với symbols"""
    service = VnstockImportService()
    return service.import_industries_for_symbols()


@router.post("/import/shareholders")
def import_shareholders_for_all_symbols(request):
    """Import shareholders cho tất cả symbols có company"""
    service = VnstockImportService()
    return service.import_shareholders_for_all_symbols()


@router.post("/import/officers")
def import_officers_for_all_symbols(request):
    """Import officers cho tất cả symbols có company"""
    service = VnstockImportService()
    return service.import_officers_for_all_symbols()


@router.post("/import/events")
def import_events_for_all_symbols(request):
    """Import events cho tất cả symbols có company"""
    service = VnstockImportService()
    return service.import_events_for_all_symbols()


@router.post("/import/sub_companies")
def import_sub_companies_for_all_symbols(request):
    """Import sub companies (subsidiaries) cho tất cả symbols có company"""
    service = VnstockImportService()
    results = service.import_sub_companies_for_all_symbols()
    total_sub_companies = sum(r.get('sub_companies_count', 0) for r in results)
    return {
        "symbols_processed": len(results),
        "total_sub_companies": total_sub_companies,
        "results": results
    }

@router.get("/symbols/{symbol}")
def get_symbol_with_all_relations(request, symbol: int):
    """Lấy thông tin symbol với tất cả bảng liên quan: company, industries, shareholders, officers, events, sub_companies"""
    from apps.stock.services.symbol_service import SymbolService
    service = SymbolService()
    return service.get_symbol_payload(symbol)


@router.get("/symbols")
def list_symbols_with_basic_info(request, limit: int = 10):
    """Lấy danh sách symbols với thông tin cơ bản"""
    from apps.stock.services.symbol_service import SymbolService
    service = SymbolService()
    return service.get_symbols(limit=limit)


@router.get("/symbols/search")
def search_symbols_by_name(request, q: str = "", limit: int = 10):
    """Tìm kiếm symbols theo tên (pattern matching)"""
    from apps.stock.models import Symbol
    from apps.stock.schemas import SymbolList
    from apps.stock.utils.safe import to_datetime
    
    symbols = Symbol.objects.filter(
        name__icontains=q.upper()
    ).select_related('company')[:limit]
    
    return [
        SymbolList(
            id=s.id,
            name=s.name,
            full_name=s.full_name or "",
            exchange=s.exchange,
            company_name=s.company.company_name if s.company else "",
            updated_at=to_datetime(s.updated_at),
        )
        for s in symbols
    ]


@router.get("/stats")
def get_database_stats(request):
    """Lấy thống kê tổng quan về dữ liệu trong database"""
    from apps.stock.models import Symbol, Company, Industry, ShareHolder, Officers, Events, SubCompany
    from django.db.models import Count, Q
    
    # Basic counts
    symbols_count = Symbol.objects.count()
    companies_count = Company.objects.count()
    industries_count = Industry.objects.count()
    shareholders_count = ShareHolder.objects.count()
    officers_count = Officers.objects.count()
    events_count = Events.objects.count()
    sub_companies_count = SubCompany.objects.count()
    
    # Relationship stats
    symbols_with_company = Symbol.objects.filter(company__isnull=False).count()
    symbols_with_industries = Symbol.objects.filter(industries__isnull=False).distinct().count()
    symbols_with_shareholders = Symbol.objects.filter(company__shareholders__isnull=False).distinct().count()
    symbols_with_officers = Symbol.objects.filter(company__officers__isnull=False).distinct().count()
    symbols_with_events = Symbol.objects.filter(company__events__isnull=False).distinct().count()
    symbols_with_sub_companies = Symbol.objects.filter(company__subsidiaries__isnull=False).distinct().count()
    
    # Coverage percentages
    company_coverage = (symbols_with_company / symbols_count * 100) if symbols_count > 0 else 0
    industries_coverage = (symbols_with_industries / symbols_count * 100) if symbols_count > 0 else 0
    shareholders_coverage = (symbols_with_shareholders / symbols_count * 100) if symbols_count > 0 else 0
    officers_coverage = (symbols_with_officers / symbols_count * 100) if symbols_count > 0 else 0
    events_coverage = (symbols_with_events / symbols_count * 100) if symbols_count > 0 else 0
    sub_companies_coverage = (symbols_with_sub_companies / symbols_count * 100) if symbols_count > 0 else 0
    
    # Exchange breakdown
    exchange_stats = Symbol.objects.values('exchange').annotate(
        count=Count('id'),
        with_company=Count('id', filter=Q(company__isnull=False))
    ).order_by('-count')
    
    return {
        "overview": {
            "symbols": symbols_count,
            "companies": companies_count,
            "industries": industries_count,
            "shareholders": shareholders_count,
            "officers": officers_count,
            "events": events_count,
            "sub_companies": sub_companies_count
        },
        "coverage": {
            "company_coverage": f"{company_coverage:.1f}%",
            "industries_coverage": f"{industries_coverage:.1f}%",
            "shareholders_coverage": f"{shareholders_coverage:.1f}%",
            "officers_coverage": f"{officers_coverage:.1f}%",
            "events_coverage": f"{events_coverage:.1f}%",
            "sub_companies_coverage": f"{sub_companies_coverage:.1f}%"
        },
        "by_exchange": list(exchange_stats)
    }