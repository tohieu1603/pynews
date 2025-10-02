import time
from typing import Any, Dict, List, Optional
from django.http import Http404
import pandas as pd
from django.db import transaction
from django.shortcuts import get_object_or_404
from vnstock import Listing
from ninja.errors import HttpError
from apps.stock.clients.vnstock_client import VNStockClient
from apps.stock.models import Symbol, Events
from apps.stock.repositories import repositories as repo
from apps.stock.services.mappers import DataMappers
from apps.stock.services.industry_resolver import IndustryResolver
from apps.stock.services.company_processor import CompanyProcessor
from apps.stock.services.payload_builder import PayloadBuilder
from apps.stock.services.fetch_service import FetchService
from apps.stock.services.cache_service import VNStockCacheService
from apps.stock.utils.safe import (
    safe_str,
    to_datetime,
    to_epoch_seconds,
)
from django.utils import timezone
from datetime import timedelta
from apps.stock.schemas import SymbolList, SymbolOutBasic
from core.db_utils import ensure_django_connection_closed
from django.db import reset_queries

class SymbolService:
    def __init__(
        self, vn_client: Optional[VNStockClient] = None, per_symbol_sleep: float = 0.2,
        max_workers: int = 10, batch_size: int = 20
    ):
        self.vn_client = vn_client or VNStockClient()
        self.per_symbol_sleep = per_symbol_sleep
        self.max_workers = max_workers
        self.batch_size = batch_size
        # Initialize helper services
        self.industry_resolver = IndustryResolver()
        self.company_processor = CompanyProcessor()
        self.payload_builder = PayloadBuilder()
        self.fetch_service = FetchService(
            max_retries=getattr(self.vn_client, 'max_retries', 5),
            wait_seconds=getattr(self.vn_client, 'wait_seconds', 60)
        )
        # Initialize cache service for better performance
        self.cache_service = VNStockCacheService()

    # -------- Delegation methods to helper services --------
    def _fetch_shareholders_df(self, symbol_name: str) -> pd.DataFrame:
        """Delegate to fetch service."""
        return self.fetch_service.fetch_shareholders_df(symbol_name)

    def _fetch_events_df(self, symbol_name: str) -> pd.DataFrame:
        """Delegate to fetch service."""
        return self.fetch_service.fetch_events_df(symbol_name)

    def _fetch_officers_df(self, symbol_name: str) -> pd.DataFrame:
        """Delegate to fetch service."""
        return self.fetch_service.fetch_officers_df(symbol_name)
    def _fetch_news_df(self, symbol_name: str) -> pd.DataFrame:
        """Delegate to fetch service."""
        return self.fetch_service.fetch_news_df(symbol_name)
    def _build_shareholder_rows(self, company_obj, df: pd.DataFrame) -> List[Dict]:
        return DataMappers.build_shareholder_rows(company_obj, df)

    def _build_event_rows(self, df: pd.DataFrame) -> List[Dict]:
        return DataMappers.map_events(df)
    def _build_news_rows(self, df: pd.DataFrame) -> List[Dict]:
        return DataMappers.map_news(df)

    def _build_officer_rows(self, df: pd.DataFrame) -> List[Dict]:
        return DataMappers.map_officers(df)
    
    
    def import_all_symbols(self) -> List[Dict[str, Any]]:
        """
        Import toàn bộ symbols đơn giản, không dùng batch, rate limit hay bulk.
        """
        print("Starting import_all_symbols with DB-first seeding...")
        results = []
        
        try:
            if not hasattr(self.vn_client, 'fetch_company_bundle_safe'):
                print("Warning: fetch_company_bundle_safe not available, using fetch_company_bundle")
                fetch_method = self.vn_client.fetch_company_bundle
            else:
                fetch_method = self.vn_client.fetch_company_bundle_safe
                
        except Exception as e:
            print(f"Error initializing client method: {e}")
            return results
        # Seed DB with all symbols once if empty
        try:
            db_symbols = list(repo.qs_all_symbols())
            if not db_symbols or all(not safe_str(s.name) for s in db_symbols):
                seeded = 0
                for symbol_name, exchange in self.vn_client.iter_all_symbols(exchange="HSX"):
                    repo.upsert_symbol(symbol_name, defaults={"exchange": exchange})
                    seeded += 1
                print(f"Seeded {seeded} symbols from vnstock")
                db_symbols = list(repo.qs_all_symbols())
            else:
                print(f"Found {len(db_symbols)} symbols in DB. Skipping vnstock seed.")
        except Exception as e:
            print(f"Error during symbol seeding/check: {e}")
            db_symbols = list(repo.qs_all_symbols())

        for idx, sym in enumerate(db_symbols):
            symbol_name = sym.name
            exchange = getattr(sym, 'exchange', None)
            try:
                bundle, ok = fetch_method(symbol_name)
                if not ok or not bundle:
                    print(f"Skip {symbol_name} ({exchange}): no bundle")
                    continue

                overview_df = bundle.get("overview_df_TCBS")
                if overview_df is None or overview_df.empty:
                    overview_df = bundle.get("overview_df_VCI")
                if overview_df is None or overview_df.empty:
                    print(f"Skip {symbol_name} ({exchange}): empty overview_df")
                    continue

                data = overview_df.iloc[0]

                with transaction.atomic():
                    symbol = repo.upsert_symbol(symbol_name, defaults={"exchange": exchange})

                    try:
                        industries = self.industry_resolver.resolve_symbol_industries(bundle, symbol_name)
                        for industry in industries:
                            repo.upsert_symbol_industry(symbol, industry)
                    except Exception as e:
                        print(f"Error processing industries for {symbol_name}: {e}")
                        default_industry = repo.get_or_create_industry("Unknown Industry")
                        repo.upsert_symbol_industry(symbol, default_industry)

                    try:
                        company = self.company_processor.process_company_data(bundle, data)
                        symbol.company = company
                        symbol.save()
                    except Exception as e:
                        print(f"Error processing company for {symbol_name}: {e}")
                        continue

                    try:
                        self.company_processor.process_related_data(company, bundle)
                    except Exception as e:
                        print(f"Error processing related data for {symbol_name}: {e}")

                    try:
                        result = self.payload_builder.build_symbol_payload(symbol, company)
                        results.append(result)
                        print(f"Processed {symbol_name} successfully")
                    except Exception as e:
                        print(f"Error building payload for {symbol_name}: {e}")
                        continue

                ensure_django_connection_closed()
                reset_queries()

                if self.per_symbol_sleep > 0:
                    time.sleep(self.per_symbol_sleep)

            except Exception as e:
                print(f"Error processing {symbol_name}: {e}")
                ensure_django_connection_closed()
                reset_queries()
                continue
        
        print(f"Import completed! {len(results)} symbols processed")
        return results
    
    def list_symbols_payload(self) -> List[Dict[str, Any]]:
        """List all symbols with industries and minimal company info."""
        symbols = repo.qs_symbols_with_industries()
        data: List[Dict[str, Any]] = []
        for s in symbols:
            industries = [
                {
                    "id": ind.id,
                    "name": ind.name,
                    "updated_at": to_datetime(ind.updated_at),
                }
                for ind in s.industries.all()
            ]
            company_payload = None
            if s.company:
                company_payload = {
                    "id": s.company.id,
                    "company_name": s.company.company_name,
                    "updated_at": to_datetime(s.company.updated_at),
                }
            data.append(
                {
                    "id": s.id,
                    "name": s.name,
                    "exchange": s.exchange,
                    "updated_at": to_datetime(s.updated_at),
                    "industries": industries,
                    "company": company_payload,
                }
            )
        return data
    
    def get_symbols(self, limit: int = 10) -> List[SymbolList]:
        
        symbols = repo.qs_symbols(limit=limit)
        return [
            SymbolList(
                id=s.id,
                name=s.name,
                exchange=s.exchange,
                updated_at=to_datetime(s.updated_at),
            )
            for s in symbols
        ]
    
    def get_symbol_payload(self, symbol: int) -> Dict[str, Any]:
        sym: Symbol = get_object_or_404(repo.qs_symbol_by_name(symbol))
        c = sym.company

        industries = []
        try:
            industries = [
                {
                    "id": ind.id,
                    "name": ind.name,
                    "level": ind.level,
                    "updated_at": to_datetime(ind.updated_at),
                }
                for ind in sym.industries.all()
            ]
        except AttributeError as e:
            print(f"Error accessing industries for symbol {symbol}: {e}")
            try:
                from apps.stock.models import Industry
                symbol_industries = Industry.objects.filter(id = symbol)
                industries = [
                    {
                        "id": ind.id,
                        "name": ind.name,
                        "level": ind.level,
                        "updated_at": to_datetime(ind.updated_at),
                    }
                    for ind in symbol_industries
                ]
            except Exception as e2:
                print(f"Alternative industries access failed: {e2}")
                industries = []

        shareholders = []
        news_list = []
        events_list = []
        officers_list = []
        subsidiaries_list = []

        if c:
            shareholders = [
                {
                    "id": sh.id,
                    "share_holder": sh.share_holder,
                    "quantity": sh.quantity,
                    "share_own_percent": (
                        float(sh.share_own_percent)
                        if sh.share_own_percent is not None
                        else None
                    ),
                    "update_date": to_datetime(sh.update_date),
                }
                for sh in c.shareholders.all().order_by('-share_own_percent')[:7]   
            ]

            news_list = [
                {
                    "id": n.id,
                    "title": n.title,
                    "news_image_url": n.news_image_url,
                    "news_source_link": n.news_source_link,
                    "price_change_pct": (
                        float(n.price_change_pct) if n.price_change_pct is not None else None
                    ),
                    "public_date": to_epoch_seconds(n.public_date),
                }
                for n in c.news.all()[:5]
            ]

            events_list = [
                {
                    "id": e.id,
                    "event_title": e.event_title,
                    "public_date": to_datetime(e.public_date),
                    "issue_date": to_datetime(e.issue_date),
                    "source_url": e.source_url,
                }
                for e in c.events.all().order_by('-public_date')[:6]
            ]

            three_years_ago = timezone.now() - timedelta(days=3*365)

            
            officers_list = [
                {
                    "id": o.id,
                    "officer_name": o.officer_name,
                    "officer_position": o.officer_position,
                    "position_short_name": o.position_short_name,
                    "officer_owner_percent": (
                        float(o.officer_owner_percent)
                        if o.officer_owner_percent is not None
                        else None
                    ),
                    "updated_at": to_datetime(o.updated_at),
                }
                 for o in c.officers.filter(updated_at__gte=three_years_ago)
                       .order_by('-updated_at')
            ]
            subsidiaries_list = [
                {
                    "id": sc.id,
                    "company_name": sc.company_name,
                    "sub_own_percent": (
                        float(sc.sub_own_percent) if sc.sub_own_percent is not None else None
                    ),
                }
                for sc in c.subsidiaries.all()[:5]
            ]

            company_payload = {
                "id": c.id,
                "company_name": c.company_name,
                "company_profile": c.company_profile,
                "history": c.history,
                "issue_share": c.issue_share,
                "financial_ratio_issue_share": c.financial_ratio_issue_share,
                "charter_capital": c.charter_capital,
                "outstanding_share": c.outstanding_share,
                "foreign_percent": (
                    float(c.foreign_percent) if c.foreign_percent is not None else None
                ),
                "established_year": c.established_year,
                "no_employees": c.no_employees,
                "stock_rating": float(c.stock_rating) if c.stock_rating is not None else None,
                "website": c.website,
                "updated_at": to_datetime(c.updated_at),
                "shareholders": shareholders,
                "news": news_list,
                "events": events_list,
                "officers": officers_list,
                "subsidiaries": subsidiaries_list,
            }
        else:
            company_payload = None

        return {
            "id": sym.id,
            "name": sym.name,
            "exchange": sym.exchange,
            "updated_at": to_datetime(sym.updated_at),
            "industries": industries,
            "company": company_payload,
        }

    def search_symbols_by_name(self, symbol_name: str, limit: int = 20) -> List[SymbolOutBasic]:
        term = (symbol_name or "").strip()
        if not term:
            return []
        queryset = repo.qs_symbols_like(term).order_by('name', 'id')
        if limit:
            queryset = queryset[:limit]
        return [
            SymbolOutBasic(id=sym.id, name=sym.name, exchange=sym.exchange)
            for sym in queryset
        ]

    def get_symbol_payload_by_name(self, symbol_name: str) -> Dict[str, Any]:
        symbol_key = symbol_name.strip()
        if not symbol_key:
            raise HttpError(400, "Symbol name cannot be empty")

        symbol_obj = repo.qs_symbol_name(symbol_key).first()
        if not symbol_obj:
            raise HttpError(404, "Symbol not found")

        return {
            "id": symbol_obj.id,
            "name": symbol_obj.name,
            "exchange": symbol_obj.exchange,
        }

