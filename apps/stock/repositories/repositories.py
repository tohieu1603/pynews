from typing import Dict, Iterable, Optional
from django.db.models import QuerySet, Prefetch
from apps.stock.models import Industry, ShareHolder, Symbol, Company, News, Officers, Events


# =============================
# Upsert helpers
# =============================

def get_or_create_industry(name: Optional[str]) -> Industry:
    clean_name = (name or "").strip() or "Unknown Industry"
    obj, _ = Industry.objects.get_or_create(name=clean_name)
    return obj

def upsert_industry(defaults: Dict) -> Industry:
    """
    Upsert Industry by primary key (id) if provided; otherwise by name.
    Accepts defaults like {"id": <icb_code>, "name": <icb_name>}.
    """
    ind_id = defaults.get("id") if isinstance(defaults, dict) else None
    name = defaults.get("name") if isinstance(defaults, dict) else None

    if ind_id is not None:
        # Update existing or create with specific primary key
        obj, _ = Industry.objects.update_or_create(
            id=int(ind_id),
            defaults={"name": (name or "Unknown Industry").strip()},
        )
        return obj

    # Fallback by name
    clean_name = (name or "").strip() or "Unknown Industry"
    obj, _ = Industry.objects.get_or_create(name=clean_name)
    return obj
def upsert_company(company_name: Optional[str], defaults: Dict) -> Company:
    clean_name = (company_name or "").strip() or "Unknown Company"
    company, _ = Company.objects.update_or_create(
        company_name=clean_name,
        defaults=defaults,
    )
    return company


def upsert_symbol(name: str, defaults: Dict) -> Symbol:
    clean_name = (name or "").strip().upper()
    symbol, _ = Symbol.objects.update_or_create(
        name=clean_name,
        defaults=defaults,
    )
    return symbol


def upsert_shareholders(company: Company, rows: Iterable[Dict]) -> None:
    for r in rows:
        ShareHolder.objects.update_or_create(
            share_holder=(r.get("share_holder") or "").strip(),
            company=company,
            defaults={
                "quantity": r.get("quantity"),
                "share_own_percent": r.get("share_own_percent"),
                "update_date": r.get("update_date"),
            }
        )


def upsert_news(company: Company, rows: Iterable[Dict]) -> None:
    for r in rows:
        News.objects.update_or_create(
            title=(r.get("title") or "").strip(),
            company=company,
            defaults={
                "news_image_url": r.get("news_image_url"),
                "news_source_link": r.get("news_source_link"),
                "public_date": r.get("public_date"),
                "price_change_pct": r.get("price_change_pct"),
            }
        )


def upsert_events(company: Company, rows: Iterable[Dict]) -> None:
    """
    ⚠ Model Events đang auto_now_add cho public_date/issue_date -> 
    không set được ngày từ nguồn; nếu muốn, hãy sửa model (bỏ auto_now_add).
    """
    for r in rows:
        Events.objects.update_or_create(
            event_title=(r.get("event_title") or "").strip(),
            company=company,
            defaults={
                "source_url": r.get("source_url"),
                # Nếu model đã fix auto_now_add, có thể set thêm public_date / issue_date ở đây
                # "public_date": r.get("public_date"),
                # "issue_date": r.get("issue_date"),
            }
        )


def upsert_officers(company: Company, rows: Iterable[Dict]) -> None:
    for r in rows:
        Officers.objects.update_or_create(
            officer_name=(r.get("officer_name") or "").strip(),
            company=company,
            defaults={
                "officer_position": r.get("officer_position"),
                "position_short_name": r.get("position_short_name"),
                "officer_owner_percent": r.get("officer_owner_percent"),
            }
        )


# =============================
# QuerySet helpers
# =============================

def qs_companies_with_related() -> QuerySet[Company]:
    return (
        Company.objects
        .prefetch_related("industries", "shareholders", "news", "events", "officers", "symbols")
        .only("id", "company_name")
    )


def qs_symbol_by_name(symbol: str) -> QuerySet[Symbol]:
    clean_symbol = (symbol or "").strip().upper()
    return (
        Symbol.objects
        .select_related("company")
        .prefetch_related(
            "industries",
            "company__industries",
            "company__shareholders",
            "company__news",
            "company__events",
            "company__officers",
        )
        .filter(name__iexact=clean_symbol)
    )


def qs_industries_with_symbols() -> QuerySet[Industry]:
    return (
        Industry.objects
        .prefetch_related(
            "companies",
            Prefetch(
                "companies__symbols",
                queryset=Symbol.objects.select_related("company"),
            ),
        )
    )

# =============================
# Symbol ↔ Industry (N-N)
# =============================

def upsert_symbol_industry(symbol: Symbol, industry: Industry) -> None:
    """
    Tạo hoặc update quan hệ N-N giữa Symbol và Industry
    """
    if not symbol.industries.filter(id=industry.id).exists():
        symbol.industries.add(industry)

# =============================
# Subsidiary relation
# =============================

def upsert_subsidiary_relation(parent_company: Company, sub_company: Company, own_percent: Optional[float]) -> None:
    """
    Tạo quan hệ parent ↔ subsidiary
    """
    sub_company.parent = parent_company
    if own_percent is not None:
        sub_company.sub_own_percent = own_percent
    sub_company.save()

# =============================
# Safe mappers
# =============================

def safe_int(val, default=0):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default

def safe_decimal(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default

def safe_str(val, default=""):
    return str(val).strip() if val is not None else default
