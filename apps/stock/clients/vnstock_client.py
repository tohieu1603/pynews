import time
from typing import Dict, Generator, Optional, Tuple

import pandas as pd
from vnstock import Company as VNCompany
from vnstock import Listing


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

    def iter_all_symbols(
        self, exchange: Optional[str] = None
    ) -> Generator[Tuple[str, str], None, None]:
        """
        Yield (symbol, exchange).
        - If exchange=None -> get all symbols.
        - If exchange="HSX"/"HNX"/"UPCOM" -> filter by exchange.
        """
        listing = Listing()
        df = listing.symbols_by_exchange()
        if exchange:
            df = df[df["exchange"] == exchange]

        for _, row in df.iterrows():
            yield str(row.get("symbol")), str(row.get("exchange"))

    def fetch_company_bundle(
        self, symbol: str
    ) -> Tuple[Dict[str, pd.DataFrame], bool]:
        """
        Returns a dictionary containing multiple DataFrames for a given symbol.
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
                    "shareholders_df": self._df_or_empty(
                        vn_company_tcbs.shareholders()
                    ),
                    "industries_icb_df": listing.industries_icb(),
                    "news_df": self._df_or_empty(vn_company_tcbs.news()),
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
                # Catching the error here is fine, the ambiguity error won't happen anymore
                print(f"❌ Error fetching {symbol}: {e}")
                return {}, False

        return {}, False