import math
import time
from datetime import datetime, date
from ninja import Router
from .schemas import IndustryOut, SymbolOut,CompanyOut
from django.http import JsonResponse
from typing import List, Optional
from ninja.pagination import paginate, PageNumberPagination
from .models import Industry, ShareHolder, Symbol, Company, News, Officers, Events
from vnstock import Company as VNCompany
from vnstock import Listing
from django.shortcuts import get_object_or_404

router = Router(tags=["stock"])

# === Helper functions ===
def safe_decimal(value, default=0.0):
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return float(value)
    except:
        return default

def safe_int(value, default=0):
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return int(value)
    except:
        return default

def safe_str(value, default=""):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return default
    return str(value)

def safe_date(value):
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return None
        return value
    except:
        return None

@router.post("/symbols/import_all", response=List[SymbolOut])
def import_all_symbols(request):
    try:
        listing = Listing()
        all_symbols_df = listing.all_symbols()
        created_symbols = []

        for _, row in all_symbols_df.iterrows():
            symbol_name = safe_str(row.get("symbol"))
            success = False
            retries = 0

            while not success and retries < 5:
                try:
                    vn_company = VNCompany(symbol=symbol_name)
                    overview_df = vn_company.overview()
                    share_holder_df = vn_company.shareholders()
                    news = vn_company.news()
                    officers = vn_company.officers()
                    events = vn_company.events()
                    success = True 
                except SystemExit as e:
                    wait_seconds = 60
                    print(f"Rate limit hit for {symbol_name}. Waiting {wait_seconds}s...")
                    time.sleep(wait_seconds)
                    retries += 1
                except Exception as e:
                    print(f"Failed to fetch symbol {symbol_name}: {str(e)}")
                    break

            if not success or overview_df.empty:
                continue

            data = overview_df.iloc[0]

            # Update or create Symbol
            symbol, _ = Symbol.objects.update_or_create(
                name=symbol_name,
                defaults={
                    "exchange": safe_str(row.get("exchange")),
                    "current_price": safe_decimal(data.get("current_price")),
                    "close_price": safe_decimal(data.get("close_price")),
                    "open_price": safe_decimal(data.get("open_price")),
                    "average_price": safe_decimal(data.get("average_price")),
                    "volume": safe_decimal(data.get("volume")),
                    "update_time": safe_date(data.get("update_time")),
                }
            )

            # Industry
            industry_name = safe_str(data.get("icb_name3", "Unknown Industry"))
            industry_obj, _ = Industry.objects.get_or_create(name=industry_name)

            # Company
            company, _ = Company.objects.update_or_create(
                full_name=safe_str(data.get("company_profile", "Unknown Company")),
                defaults={
                    "parent_id": data.get("parent_id") or None,
                    "company_profile": safe_str(data.get("company_profile", "Unknown")),
                    "issue_share": safe_int(data.get("issue_share")),
                    "financial_ratio_issue_share": safe_int(data.get("financial_ratio_issue_share")),
                    "charter_capital": safe_decimal(data.get("charter_capital")),
                    "industry": industry_obj,
                }
            )

            # Ensure the symbol is linked to the company
            if symbol.company_id != company.id:
                symbol.company = company
                try:
                    symbol.save(update_fields=["company", "updated_at"])
                except Exception:
                    symbol.save()

            # ShareHolders
            for _, sh_row in share_holder_df.iterrows() if not share_holder_df.empty else []:
                ShareHolder.objects.update_or_create(
                    share_holder=safe_str(sh_row.get("share_holder")),
                    company=company,
                    defaults={
                        "quantity": safe_int(sh_row.get("quantity")),
                        "share_own_percent": safe_decimal(sh_row.get("share_own_percent")),
                        "update_date": safe_date(sh_row.get("update_date")),
                    }
                )

            # News
            for _, news_row in news.iterrows() if not news.empty else []:
                News.objects.update_or_create(
                    title=safe_str(news_row.get("news_title", "No Title")),
                    company=company,
                    defaults={
                        "news_image_url": safe_str(news_row.get("news_image_url")),
                        "news_source_link": safe_str(news_row.get("news_source_link")),
                        "price_change_pct": safe_decimal(news_row.get("price_change_pct"), None),
                        "public_date": safe_date(news_row.get("public_date")),
                    }
                )

            # Events
            for _, ev_row in events.iterrows() if not events.empty else []:
                Events.objects.update_or_create(
                    event_title=safe_str(ev_row.get("event_title", "No Title")),
                    company=company,
                    defaults={
                        "source_url": safe_str(ev_row.get("source_url")),
                        "issue_date": safe_date(ev_row.get("issue_date")),
                        "public_date": safe_date(ev_row.get("public_date")),
                    }
                )

            # Officers
            for _, off_row in officers.iterrows() if not officers.empty else []:
                Officers.objects.update_or_create(
                    officer_name=safe_str(off_row.get("officer_name", "No Name")),
                    company=company,
                    defaults={
                        "officer_position": safe_str(off_row.get("officer_position")),
                        "position_short_name": safe_str(off_row.get("position_short_name")),
                        "officer_owner_percent": safe_decimal(off_row.get("officer_own_percent")),
                        "updated_at": safe_date(off_row.get("update_at")),
                    }
                )

            created_symbols.append(symbol)

            time.sleep(1)

        return created_symbols

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({"Success": False, "Error": str(e)}, status=500)

@router.get("/company", response=List[CompanyOut])
@paginate(PageNumberPagination, page_size=10)

def get_all_companies(request):
    """Danh sách tất cả company (có phân trang)."""
    # Lấy toàn bộ company và related objects
    companies = Company.objects.select_related('industry').all()
    # Lấy tất cả related objects 1 query mỗi loại
    symbols = Symbol.objects.all()
    shareholders = ShareHolder.objects.all()
    news_list = News.objects.all()
    events_list = Events.objects.all()
    officers_list = Officers.objects.all()

    # Mapping company_id -> related objects
    def map_objects(objs, company_field='company', fields=None):
        result = {}
        for o in objs:
            cid = getattr(o, f"{company_field}_id")
            item = {f: getattr(o, f) for f in fields} if fields else o.__dict__
            # Convert datetime/date sang string
            for k, v in item.items():
                if isinstance(v, (datetime, date)):
                    item[k] = v.isoformat()
            result.setdefault(cid, []).append(item)
        return result

    symbols_map = map_objects(symbols, fields=['name','exchange','current_price','close_price','open_price','average_price','volume','update_time'])
    shareholders_map = map_objects(shareholders, fields=['share_holder','quantity','share_own_percent','update_date'])
    news_map = map_objects(news_list, fields=['title','news_image_url','news_source_link','price_change_pct','public_date'])
    events_map = map_objects(events_list, fields=['event_title','public_date','issuse_date','source_url'])
    officers_map = map_objects(officers_list, fields=['officer_name','officer_position','position_short_name','officer_owner_percent','updated_at'])

    # Tạo response
    data = []
    for c in companies:
        company_data = {
            "id": c.id,
            "full_name": c.full_name,
            "parent_id": c.parent_id_id,
            "company_profile": c.company_profile,
            "history": c.history,
            "issue_share": c.issue_share,
            "financial_ratio_issue_share": c.financial_ratio_issue_share,
            "charter_capital": c.charter_capital,
            "updated_at": c.updated_at.isoformat(),
            "symbols": symbols_map.get(c.id, []),
            "shareholders": shareholders_map.get(c.id, []),
            "news": news_map.get(c.id, []),
            "events": events_map.get(c.id, []),
            "officers": officers_map.get(c.id, []),
        }
        data.append(company_data)

    return data

# @router.get("/company/{symbol}", response=List[CompanyOut])
# def get_company_by_symbol(request, symbol: str):
#     """Lấy company theo mã chứng khoán cụ thể (không phân trang)."""
#     companies = (
#         Company.objects.select_related('industry')
#         .filter(symbols__name__iexact=symbol)
#         .distinct()
#     )

#     symbols = Symbol.objects.filter(name__iexact=symbol)
#     shareholders = ShareHolder.objects.filter(company__in=companies)
#     news_list = News.objects.filter(company__in=companies)
#     events_list = Events.objects.filter(company__in=companies)
#     officers_list = Officers.objects.filter(company__in=companies)

#     def map_objects(objs, company_field='company', fields=None):
#         result = {}
#         for o in objs:
#             cid = getattr(o, f"{company_field}_id")
#             item = {f: getattr(o, f) for f in fields} if fields else o.__dict__
#             for k, v in item.items():
#                 if isinstance(v, (datetime, date)):
#                     item[k] = v.isoformat()
#             result.setdefault(cid, []).append(item)
#         return result

#     symbols_map = map_objects(symbols, fields=['name','exchange','current_price','close_price','open_price','average_price','volume','update_time'])
#     shareholders_map = map_objects(shareholders, fields=['share_holder','quantity','share_own_percent','update_date'])
#     news_map = map_objects(news_list, fields=['title','news_image_url','news_source_link','price_change_pct','public_date'])
#     events_map = map_objects(events_list, fields=['event_title','public_date','issuse_date','source_url'])
#     officers_map = map_objects(officers_list, fields=['officer_name','officer_position','position_short_name','officer_owner_percent','updated_at'])

#     data = []
#     for c in companies:
#         data.append({
#             "id": c.id,
#             "full_name": c.full_name,
#             "parent_id": c.parent_id_id,
#             "company_profile": c.company_profile,
#             "history": c.history,
#             "issue_share": c.issue_share,
#             "financial_ratio_issue_share": c.financial_ratio_issue_share,
#             "charter_capital": c.charter_capital,
#             "updated_at": c.updated_at.isoformat(),
#             "symbols": symbols_map.get(c.id, []),
#             "shareholders": shareholders_map.get(c.id, []),
#             "news": news_map.get(c.id, []),
#             "events": events_map.get(c.id, []),
#             "officers": officers_map.get(c.id, []),
#         })
#     return data


    
@router.get('/industries')
def get_all_industries(request):
    industries = Industry.objects.all()
    return JsonResponse({
        "Success": True,
        "Data": list(industries)
    }, status=200)
    
@router.get("/symbols/{symbol}", response=SymbolOut)
def get_symbol(request, symbol: str):
    symbol = symbol.upper()
    symbol = get_object_or_404(
        Symbol.objects.select_related("company__industry")
        .prefetch_related(
            "company__shareholders",
            "company__news",
            "company__events",
            "company__officers",
        ),
        name=symbol
    )
    return symbol

