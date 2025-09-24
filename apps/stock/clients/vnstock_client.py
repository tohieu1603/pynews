import time
from typing import Dict, Generator, Optional, Tuple

import pandas as pd
from vnstock import Company as VNCompany
from vnstock import Listing
from vnstock.explorer.vci.company import Company as VCIExplorerCompany


class VNStockClient:
    """
    Đóng gói calls tới vnstock, có retry/backoff khi dính rate-limit (SystemExit).
    Cung cấp helper để iterate symbols và fetch thông tin công ty.
    """

    def __init__(self, max_retries: int = 5, wait_seconds: int = 60):
        self.max_retries = max_retries
        self.wait_seconds = wait_seconds

    def _df_or_empty(self, df: Optional[pd.DataFrame]) -> pd.DataFrame:
        """
        Helper to safely return a DataFrame or an empty one if the input is None.
        """
        if df is None:
            return pd.DataFrame()
        return df

    def _normalize_shareholder_df(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        df = df.copy()
        rename_map = {}
        if "owner_full_name" in df.columns and "share_holder" not in df.columns:
            rename_map["owner_full_name"] = "share_holder"
        if "percentage" in df.columns and "share_own_percent" not in df.columns:
            rename_map["percentage"] = "share_own_percent"
        if rename_map:
            df = df.rename(columns=rename_map)

        drop_cols = [col for col in ("__typename", "ticker", "en__owner_full_name") if col in df.columns]
        if drop_cols:
            df = df.drop(columns=drop_cols)

        if "update_date" in df.columns:
            df["update_date"] = pd.to_datetime(df["update_date"], errors="coerce")
            df["update_date"] = df["update_date"].dt.strftime("%Y-%m-%d")

        for col in ("share_holder", "share_own_percent", "quantity", "update_date"):
            if col not in df.columns:
                df[col] = None

        return df[["share_holder", "quantity", "share_own_percent", "update_date"]]

    def _fetch_vci_shareholders_direct(self, symbol: str) -> pd.DataFrame:
        try:
            explorer = VCIExplorerCompany(symbol=symbol, random_agent=False, to_df=True, show_log=False)
            df = explorer._process_data(explorer.raw_data, "OrganizationShareHolders")
        except Exception as exc:
            print(f"Error fetching VCI shareholders for {symbol}: {exc}")
            return pd.DataFrame()

        return self._normalize_shareholder_df(df)

    def _fetch_shareholders(self, symbol: str, *companies: VNCompany) -> pd.DataFrame:
        direct_df = self._fetch_vci_shareholders_direct(symbol)
        if not direct_df.empty:
            return direct_df

        for company in companies:
            if company is None:
                continue
            try:
                df = company.shareholders()
            except SystemExit:
                raise
            except NotImplementedError:
                continue
            except Exception as exc:
                print(f"Error fetching shareholders from provider for {symbol}: {exc}")
                continue

            normalized = self._normalize_shareholder_df(self._df_or_empty(df))
            if not normalized.empty:
                return normalized

        return pd.DataFrame()

    def iter_all_symbols(
        self, exchange: Optional[str] = "HSX"
    ) -> Generator[Tuple[str, str], None, None]:
        """
        Lấy danh sách các mã ở sàn HSX (mặc định). Nếu truyền sàn khác,
        sẽ lọc theo sàn đó.
        """
        listing = Listing()
        df = listing.symbols_by_exchange()
        exch = (exchange or "HSX").upper()
        df = df[df["exchange"] == exch]

        for _, row in df.iterrows():
            yield str(row.get("symbol")), str(row.get("exchange"))

    def fetch_company_bundle(
        self, symbol: str
    ) -> Tuple[Dict[str, pd.DataFrame], bool]:
        """
        Lấy bundle thông tin công ty từ cả 2 nguồn TCBS và VCI.
        """
        retries = 0
        while retries <= self.max_retries:
            try:
                vn_company_tcbs = VNCompany(symbol=symbol, source="TCBS")
                vn_company_vci = VNCompany(symbol=symbol, source="VCI")
                listing = Listing()

                return {
                    "overview_df_TCBS": self._df_or_empty(vn_company_tcbs.overview()),
                    "overview_df_VCI": self._df_or_empty(vn_company_vci.overview()),
                    "profile_df": self._df_or_empty(vn_company_tcbs.profile()),
                    "shareholders_df": self._fetch_shareholders(symbol, vn_company_vci, vn_company_tcbs),
                    "industries_icb_df": listing.industries_icb(),
                    "symbols_by_industries_df": listing.symbols_by_industries(),
                    "news_df": self._df_or_empty(vn_company_vci.news()),
                    "officers_df": self._df_or_empty(vn_company_vci.officers()),
                    "events_df": self._df_or_empty(vn_company_vci.events()),
                    "subsidiaries": self._df_or_empty(vn_company_tcbs.subsidiaries()),
                }, True

            except SystemExit:
                retries += 1
                print(
                    f"⚠️ Rate limit hit for {symbol}. Retry {retries}/{self.max_retries} after {self.wait_seconds}s..."
                )
                time.sleep(self.wait_seconds)

            except Exception as e:
                print(f"Error {symbol}: {e}")
                return {}, False
        return {}, False


    def fetch_company_bundle_safe(
        self, symbol: str
    ) -> Tuple[Dict[str, pd.DataFrame], bool]:
        """
        Safe/robust variant of fetch_company_bundle.
        - Wraps each VNStock call in its own try/except.
        - Returns partial bundle; ok=True if TCBS overview is available.
        """
        retries = 0
        while retries <= self.max_retries:
            try:
                listing = Listing()
                vn_company_tcbs = VNCompany(symbol=symbol, source="TCBS")
                vn_company_vci = VNCompany(symbol=symbol, source="VCI")

                # TCBS
                try:
                    overview_tcbs = self._df_or_empty(vn_company_tcbs.overview())
                except Exception:
                    overview_tcbs = pd.DataFrame()
                try:
                    profile_df = self._df_or_empty(vn_company_tcbs.profile())
                except Exception:
                    profile_df = pd.DataFrame()
                try:
                    news_df = self._df_or_empty(vn_company_vci.news())
                except Exception:
                    news_df = pd.DataFrame()
                try:
                    subs_df = self._df_or_empty(vn_company_tcbs.subsidiaries())
                except Exception:
                    subs_df = pd.DataFrame()

                # VCI
                try:
                    overview_vci = self._df_or_empty(vn_company_vci.overview())
                except Exception:
                    overview_vci = pd.DataFrame()
                shareholders_df = self._fetch_shareholders(symbol, vn_company_vci, vn_company_tcbs)
                try:
                    officers_df = self._df_or_empty(vn_company_vci.officers())
                except Exception:
                    officers_df = pd.DataFrame()
                try:
                    events_df = self._df_or_empty(vn_company_vci.events())
                except Exception:
                    events_df = pd.DataFrame()

                # Listing datasets
                try:
                    industries_icb_df = listing.industries_icb()
                except Exception:
                    industries_icb_df = pd.DataFrame()
                try:
                    symbols_by_industries_df = listing.symbols_by_industries()
                except Exception:
                    symbols_by_industries_df = pd.DataFrame()

                bundle = {
                    "overview_df_TCBS": overview_tcbs,
                    "overview_df_VCI": overview_vci,
                    "profile_df": profile_df,
                    "shareholders_df": shareholders_df,
                    "industries_icb_df": industries_icb_df,
                    "symbols_by_industries_df": symbols_by_industries_df,
                    "news_df": news_df,
                    "officers_df": officers_df,
                    "events_df": events_df,
                    "subsidiaries": subs_df,
                }

                ok = overview_tcbs is not None and not overview_tcbs.empty
                return bundle, bool(ok)

            except SystemExit:
                retries += 1
                print(
                    f"Rate limit hit for {symbol}. Retry {retries}/{self.max_retries} after {self.wait_seconds}s..."
                )
                time.sleep(self.wait_seconds)
            except Exception as e:
                print(f"Error {symbol}: {e}")
                return {}, False

        return {}, False

