import time
from typing import Any, Dict, List, Optional

import pandas as pd
from django.db import transaction
from django.shortcuts import get_object_or_404
from vnstock import Company as VNCompany
from vnstock import Listing

from apps.stock.clients.vnstock_client import VNStockClient
from apps.stock.models import Symbol
from apps.stock.repositories import repositories as repo
from apps.stock.utils.safe import (
    iso_str_or_none,
    safe_date_passthrough,
    safe_decimal,
    safe_int,
    safe_str,
    to_datetime,
    to_epoch_seconds,
)


class SymbolService:
    def __init__(
        self, vn_client: Optional[VNStockClient] = None, per_symbol_sleep: float = 1.0
    ):
        self.vn_client = vn_client or VNStockClient()
        self.per_symbol_sleep = per_symbol_sleep

    # -------- Mapping helpers --------
    def _map_shareholders(self, df) -> List[Dict]:
        if df is None or df.empty:
            return []
        rows = []
        for _, r in df.iterrows():
            rows.append(
                {
                    "share_holder": safe_str(r.get("share_holder")),
                    "quantity": safe_int(r.get("quantity")),
                    "share_own_percent": safe_decimal(r.get("share_own_percent")),
                    "update_date": safe_date_passthrough(r.get("update_date")),
                }
            )
        return rows

    def _map_news(self, df) -> List[Dict]:
        if df is None or df.empty:
            return []
        rows = []
        for _, r in df.iterrows():
            rows.append(
                {
                    "title": safe_str(r.get("news_title", "No Title")),
                    "news_image_url": safe_str(r.get("news_image_url")),
                    "news_source_link": safe_str(r.get("news_source_link")),
                    "price_change_pct": safe_decimal(r.get("price_change_pct"), None),
                    "public_date": to_epoch_seconds(r.get("public_date")),
                }
            )
        return rows

    def _map_events(self, df) -> List[Dict]:
        if df is None or df.empty:
            return []
        rows = []
        for _, r in df.iterrows():
            rows.append(
                {
                    "event_title": safe_str(r.get("event_title", "No Title")),
                    "source_url": safe_str(r.get("source_url")),
                    "issue_date": safe_date_passthrough(r.get("issue_date")),
                    "public_date": safe_date_passthrough(r.get("public_date")),
                }
            )
        return rows

    def _map_sub_company(self, df) -> List[Dict]:
        if df is None or df.empty:
            return []
        rows = []
        for _, r in df.iterrows():
            rows.append(
                {
                    "company_name": safe_str(r.get("sub_company_name", "No Name")),
                    "sub_own_percent": safe_decimal(r.get("sub_own_percent"), None),
                }
            )
        return rows

    def _map_officers(self, df) -> List[Dict]:
        if df is None or df.empty:
            return []
        rows = []
        for _, r in df.iterrows():
            rows.append(
                {
                    "officer_name": safe_str(r.get("officer_name", "No Name")),
                    "officer_position": safe_str(r.get("officer_position")),
                    "position_short_name": safe_str(r.get("position_short_name")),
                    "officer_owner_percent": safe_decimal(r.get("officer_own_percent")),
                }
            )
        return rows

    # -------- Shareholder import helpers --------
    def _fetch_shareholders_df(self, symbol_name: str) -> pd.DataFrame:
        """Fetch shareholders DataFrame with retry/backoff using vn_client settings."""
        retries = 0
        while retries <= self.vn_client.max_retries:
            try:
                vn_company = VNCompany(symbol=symbol_name, source="VCI")
                df: Optional[pd.DataFrame] = vn_company.shareholders()
                return df if df is not None else pd.DataFrame()
            except SystemExit:
                # Rate limited; backoff and retry
                retries += 1
                wait = getattr(self.vn_client, "wait_seconds", 60)
                print(
                    f"Rate limit when fetching shareholders for {symbol_name}. "
                    f"Retry {retries}/{self.vn_client.max_retries} after {wait}s"
                )
                time.sleep(wait)
            except Exception as e:
                print(f"Error fetching shareholders for {symbol_name}: {e}")
                return pd.DataFrame()
        return pd.DataFrame()

    def _build_shareholder_rows(self, company_obj, df: pd.DataFrame) -> List[Dict]:
        if df is None or df.empty:
            return []
        rows: List[Dict] = []
        for _, r in df.iterrows():
            rows.append(
                {
                    "share_holder": safe_str(r.get("share_holder") or "").strip(),
                    "quantity": safe_int(r.get("quantity")),
                    "share_own_percent": safe_decimal(r.get("share_own_percent") or 0),
                    "update_date": safe_date_passthrough(r.get("update_date")),
                    "company": company_obj,
                }
            )
        return rows

    # -------- Events/Officers import helpers --------
    def _fetch_events_df(self, symbol_name: str) -> pd.DataFrame:
        retries = 0
        while retries <= self.vn_client.max_retries:
            try:
                vn_company = VNCompany(symbol=symbol_name, source="VCI")
                df: Optional[pd.DataFrame] = vn_company.events()
                return df if df is not None else pd.DataFrame()
            except SystemExit:
                retries += 1
                wait = getattr(self.vn_client, "wait_seconds", 60)
                print(
                    f"Rate limit when fetching events for {symbol_name}. "
                    f"Retry {retries}/{self.vn_client.max_retries} after {wait}s"
                )
                time.sleep(wait)
            except Exception as e:
                print(f"Error fetching events for {symbol_name}: {e}")
                return pd.DataFrame()
        return pd.DataFrame()

    def _build_event_rows(self, df: pd.DataFrame) -> List[Dict]:
        return self._map_events(df)

    def _fetch_officers_df(self, symbol_name: str) -> pd.DataFrame:
        retries = 0
        while retries <= self.vn_client.max_retries:
            try:
                vn_company = VNCompany(symbol=symbol_name, source="VCI")
                df: Optional[pd.DataFrame] = vn_company.officers()
                return df if df is not None else pd.DataFrame()
            except SystemExit:
                retries += 1
                wait = getattr(self.vn_client, "wait_seconds", 60)
                print(
                    f"Rate limit when fetching officers for {symbol_name}. "
                    f"Retry {retries}/{self.vn_client.max_retries} after {wait}s"
                )
                time.sleep(wait)
            except Exception as e:
                print(f"Error fetching officers for {symbol_name}: {e}")
                return pd.DataFrame()
        return pd.DataFrame()

    def _build_officer_rows(self, df: pd.DataFrame) -> List[Dict]:
        return self._map_officers(df)

    # -------- Public APIs --------
    def import_shareholders_for_symbol(self, symbol_name: str) -> List[Dict]:
        """Import shareholders for a single symbol; returns payload list."""
        symbol_obj = get_object_or_404(Symbol, name__iexact=symbol_name)
        company_obj = symbol_obj.company
        if not company_obj:
            print(f"Skip {symbol_name}: no linked company")
            return []

        df = self._fetch_shareholders_df(symbol_name)
        if df is None or df.empty:
            print(f"No shareholder data for {symbol_name}")
            return []

        rows = self._build_shareholder_rows(company_obj, df)
        if not rows:
            print(f"No valid shareholder rows for {symbol_name}")
            return []

        repo.upsert_shareholders(company_obj, rows)
        print(f"Imported {len(rows)} shareholders for {symbol_name}")
        return rows

    def import_all_shareholders(self) -> int:
        """Import shareholders for all symbols; returns total upserted rows."""
        symbols = repo.qs_all_symbols()
        total = 0
        for sym in symbols:
            rows = self.import_shareholders_for_symbol(sym.name)
            total += len(rows)
            print(f"Accumulated shareholders: {total} after {sym.name}")
            if self.per_symbol_sleep > 0:
                time.sleep(self.per_symbol_sleep)
        return total

    def import_all_industries(self) -> int:
        """Import all industries (ICB) from vnstock Listing."""
        try:
            listing = Listing()
            df = listing.industries_icb()
        except Exception as e:
            print(f"Error fetching industries_icb: {e}")
            return 0

        if df is None or df.empty:
            print("No industries_icb data")
            return 0

        count = 0
        for _, r in df.iterrows():
            ind_id = safe_int(r.get("icb_code"))
            ind_name = safe_str(r.get("icb_name"))
            if ind_id is None and not ind_name:
                continue
            repo.upsert_industry({"id": ind_id, "name": ind_name})
            count += 1
        print(f"Imported/updated {count} industries")
        return count

    def import_events_for_symbol(self, symbol_name: str) -> List[Dict]:
        symbol_obj = get_object_or_404(Symbol, name__iexact=symbol_name)
        company_obj = symbol_obj.company
        if not company_obj:
            print(f"Skip {symbol_name}: no linked company")
            return []

        df = self._fetch_events_df(symbol_name)
        if df is None or df.empty:
            print(f"No event data for {symbol_name}")
            return []

        rows = self._build_event_rows(df)
        if not rows:
            print(f"No valid event rows for {symbol_name}")
            return []

        repo.upsert_events(company_obj, rows)
        print(f"Imported/updated {len(rows)} events for {symbol_name}")
        return rows

    def import_all_events(self) -> int:
        symbols = repo.qs_all_symbols()
        total = 0
        for sym in symbols:
            rows = self.import_events_for_symbol(sym.name)
            total += len(rows)
            print(f"Accumulated events: {total} after {sym.name}")
            if self.per_symbol_sleep > 0:
                time.sleep(self.per_symbol_sleep)
        return total

    def import_officers_for_symbol(self, symbol_name: str) -> List[Dict]:
        symbol_obj = get_object_or_404(Symbol, name__iexact=symbol_name)
        company_obj = symbol_obj.company
        if not company_obj:
            print(f"Skip {symbol_name}: no linked company")
            return []

        df = self._fetch_officers_df(symbol_name)
        if df is None or df.empty:
            print(f"No officer data for {symbol_name}")
            return []

        rows = self._build_officer_rows(df)
        if not rows:
            print(f"No valid officer rows for {symbol_name}")
            return []

        repo.upsert_officers(company_obj, rows)
        print(f"Imported/updated {len(rows)} officers for {symbol_name}")
        return rows

    def import_all_officers(self) -> int:
        symbols = repo.qs_all_symbols()
        total = 0
        for sym in symbols:
            rows = self.import_officers_for_symbol(sym.name)
            total += len(rows)
            print(f"Accumulated officers: {total} after {sym.name}")
            if self.per_symbol_sleep > 0:
                time.sleep(self.per_symbol_sleep)
        return total

    def import_all_symbols(self) -> List[Dict[str, Any]]:
        """
        Import toàn bộ symbols theo tất cả sàn (HSX).
        Trả về danh sách payload theo SymbolOut (tối giản).
        """
        results: List[Dict[str, Any]] = []

        for symbol_name, exch in self.vn_client.iter_all_symbols(exchange="HSX"):
            bundle, ok = self.vn_client.fetch_company_bundle(symbol_name)
            if not ok or not bundle:
                print(f"Skip {symbol_name} ({exch}): no bundle")
                continue
            subsidiaries_df = bundle.get("subsidiaries")
            overview_df = bundle.get("overview_df_TCBS")
            overview_df_vci = bundle.get("overview_df_VCI")

            if overview_df is None or overview_df.empty:
                print(f"Skip {symbol_name} ({exch}): empty overview_df")
                continue

            data = overview_df.iloc[0]

            try:
                with transaction.atomic():
                    symbol = repo.upsert_symbol(
                        symbol_name, defaults={"exchange": exch}
                    )

                    # Industry
                    industry_df = bundle.get("industries_icb_df")
                  #  print(industry_df)
                    if industry_df is not None and not industry_df.empty:
                        industries = []
                        for _, row in industry_df.iterrows():
                            industry_id = safe_int(row.get("icb_code"))
                            industry_name = safe_str(row.get("icb_name"))
                            level = safe_int(row.get("level"))
                            industry = repo.upsert_industry(
                                {
                                    "id": industry_id,
                                    "name": industry_name,
                                    "level": level,
                                }
                            )
                            industries.append(industry)

                        for industry in industries:
                            repo.upsert_symbol_industry(symbol, industry)
                    else:
                        industry = repo.get_or_create_industry("Unknown Industry")
                        repo.upsert_symbol_industry(symbol, industry)

                    # Company
                    profile_df = bundle.get("profile_df")
                    company_name = (
                        safe_str(profile_df.iloc[0].get("company_name"))
                        if profile_df is not None and not profile_df.empty
                        else "Unknown Company"
                    )

                    if overview_df_vci is not None and not overview_df_vci.empty:
                        overview_data = overview_df_vci.iloc[0]
                        company_profile = safe_str(overview_data.get("company_profile"))
                        history = safe_str(overview_data.get("history"))
                        fin_ratio_share = safe_int(
                            overview_data.get("financial_ratio_issue_share")
                        )
                        charter_cap = safe_int(overview_data.get("charter_capital"))
                    else:
                        company_profile = ""
                        history = ""
                        fin_ratio_share = None
                        charter_cap = None

                    company = repo.upsert_company(
                        company_name,
                        defaults={
                            "company_profile": company_profile,
                            "history": history,
                            "issue_share": safe_int(data.get("issue_share")),
                            "stock_rating": safe_decimal(
                                data.get("stock_rating"), None
                            ),
                            "no_employees": data.get("no_employees", None),
                            "website": safe_str(data.get("website", "")),
                            "financial_ratio_issue_share": fin_ratio_share,
                            "charter_capital": charter_cap,
                            "outstanding_share": safe_int(
                                data.get("outstanding_shares", 0)
                            ),
                            "foreign_percent": safe_decimal(
                                data.get("foreign_percent", 0)
                            ),
                            "established_year": safe_int(
                                data.get("established_year", 0)
                            ),
                            "delta_in_week": safe_int(data.get("delta_in_week", 0)),
                            "delta_in_month": safe_int(data.get("delta_in_month", 0)),
                            "delta_in_year": safe_int(data.get("delta_in_year", 0)),
                            "no_employees": safe_int(data.get("no_employees", 0)),
                        },
                    )
                    print(f"Upsert company '{company_name}' ({company.id})")

                    symbol.company = company
                    symbol.save()
                    print(f"Upsert symbol {symbol_name} ({symbol.id})")
                    a = bundle.get("shareholders_df")
                    print("shareholders_df", a)
                    repo.upsert_shareholders(
                        company, self._map_shareholders(bundle.get("shareholders_df"))
                    )
                    repo.upsert_events(
                        company, self._map_events(bundle.get("events_df"))
                    )
                    repo.upsert_officers(
                        company, self._map_officers(bundle.get("officers_df"))
                    )
                    print("subsidiaries_df", subsidiaries_df)
                    repo.upsert_sub_company(
                        self._map_sub_company(subsidiaries_df), company
                    )

                    company_payload = {
                        "id": company.id,
                        "company_name": company.company_name,
                        "company_profile": company.company_profile,
                        "history": company.history,
                        "issue_share": company.issue_share,
                        "financial_ratio_issue_share": company.financial_ratio_issue_share,
                        "charter_capital": company.charter_capital,
                        "outstanding_share": company.outstanding_share,
                        "foreign_percent": company.foreign_percent,
                        "established_year": company.established_year,
                        "no_employees": company.no_employees,
                        "stock_rating": company.stock_rating,
                        "website": company.website,
                        "updated_at": to_datetime(company.updated_at),
                    }

                    results.append(
                        {
                            "id": symbol.id,
                            "name": symbol.name,
                            "exchange": exch,
                            "company": company_payload,
                        }
                    )

            except Exception as e:
                print(f"Error inserting {symbol_name}: {e}")

            if self.per_symbol_sleep > 0:
                time.sleep(self.per_symbol_sleep)

        return results

    def import_industry_company_symbol(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        for symbol_name, exch in self.vn_client.iter_all_symbols(exchange="HSX"):
            bundle, ok = self.vn_client.fetch_company_bundle(symbol_name)
            if not ok or not bundle:
                print(f"Skip {symbol_name} ({exch}): no bundle")
                continue
            subsidiaries_df = bundle.get("subsidiaries")
            overview_df = bundle.get("overview_df_TCBS")
            overview_df_vci = bundle.get("overview_df_VCI")

            if overview_df is None or overview_df.empty:
                print(f"Skip {symbol_name} ({exch}): empty overview_df")
                continue

            data = overview_df.iloc[0]

            try:
                with transaction.atomic():
                    # Industry
                    industry_df = bundle.get("industries_icb_df")
                    print(industry_df)
                    if industry_df is not None and not industry_df.empty:
                        industry_id = safe_int(industry_df.iloc[0].get("icb_code"))
                        industry_name = safe_str(industry_df.iloc[0].get("icb_name"))
                        level = safe_int(industry_df.iloc[0].get("level"))
                        industry = repo.upsert_industry(
                            {"id": industry_id, "name": industry_name, "level": level}
                        )
                    else:
                        industry = repo.get_or_create_industry("Unknown Industry")

                    # Company
                    profile_df = bundle.get("profile_df")
                    company_name = (
                        safe_str(profile_df.iloc[0].get("company_name"))
                        if profile_df is not None and not profile_df.empty
                        else "Unknown Company"
                    )

                    if overview_df_vci is not None and not overview_df_vci.empty:
                        overview_data = overview_df_vci.iloc[0]
                        company_profile = safe_str(overview_data.get("company_profile"))
                        history = safe_str(overview_data.get("history"))
                        fin_ratio_share = safe_int(
                            overview_data.get("financial_ratio_issue_share")
                        )
                        charter_cap = safe_int(overview_data.get("charter_capital"))
                    else:
                        company_profile = ""
                        history = ""
                        fin_ratio_share = None
                        charter_cap = None

                    company = repo.upsert_company(
                        company_name,
                        defaults={
                            "company_profile": company_profile,
                            "history": history,
                            "issue_share": safe_int(data.get("issue_share")),
                            "stock_rating": safe_decimal(
                                data.get("stock_rating"), None
                            ),
                            "no_employees": data.get("no_employees", None),
                            "website": safe_str(data.get("website", "")),
                            "financial_ratio_issue_share": fin_ratio_share,
                            "charter_capital": charter_cap,
                            "outstanding_share": safe_int(
                                data.get("outstanding_shares", 0)
                            ),
                            "foreign_percent": safe_decimal(
                                data.get("foreign_percent", 0)
                            ),
                            "established_year": safe_int(
                                data.get("established_year", 0)
                            ),
                            "delta_in_week": safe_int(data.get("delta_in_week", 0)),
                            "delta_in_month": safe_int(data.get("delta_in_month", 0)),
                            "delta_in_year": safe_int(data.get("delta_in_year", 0)),
                            "no_employees": safe_int(data.get("no_employees", 0)),
                        },
                    )
                    print(f"Upsert company '{company_name}' ({company.id})")

                    # Symbol
                    symbol = repo.upsert_symbol(
                        symbol_name,
                        defaults={"exchange": exch, "company": company},
                    )
                    print(f"Upsert symbol {symbol_name} ({symbol.id})")

                    if industry:
                        repo.upsert_symbol_industry(symbol, industry)

                    repo.upsert_sub_company(
                        self._map_sub_company(subsidiaries_df), company
                    )

                    company_payload = {
                        "id": company.id,
                        "company_name": company.company_name,
                        "company_profile": company.company_profile,
                        "history": company.history,
                        "issue_share": company.issue_share,
                        "financial_ratio_issue_share": company.financial_ratio_issue_share,
                        "charter_capital": company.charter_capital,
                        "outstanding_share": company.outstanding_share,
                        "foreign_percent": company.foreign_percent,
                        "established_year": company.established_year,
                        "no_employees": company.no_employees,
                        "stock_rating": company.stock_rating,
                        "website": company.website,
                        "updated_at": to_datetime(company.updated_at),
                    }

                    results.append(
                        {
                            "id": symbol.id,
                            "name": symbol.name,
                            "exchange": exch,
                            "company": company_payload,
                        }
                    )

            except Exception as e:
                print(f"Error inserting {symbol_name}: {e}")

            if self.per_symbol_sleep > 0:
                time.sleep(self.per_symbol_sleep)

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

    def get_symbol_payload(self, symbol: str) -> Dict[str, Any]:
        sym: Symbol = get_object_or_404(repo.qs_symbol_by_name(symbol))
        c = sym.company

        industries = [
            {
                "id": ind.id,
                "name": ind.name,
                "level": ind.level,
                "updated_at": to_datetime(ind.updated_at),
            }
            for ind in sym.industries.filter(level=1)
        ]

        shareholders = []
        news_list = []
        events_list = []
        officers_list = []

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
                for sh in c.shareholders.all()[:5]
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
                for e in c.events.all()[:5]
            ]

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
                for o in c.officers.all()[:5]
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
