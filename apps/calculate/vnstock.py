
from typing import Optional, Generator, Tuple, Dict
from vnstock import Listing, Finance, Company
import pandas as pd


class VNStock:
    
    def __init__(self, max_retries = 5, wait_seconds: int = 60):
        self.max_retries = max_retries
        self.wait_seconds = wait_seconds
    
    def _df_or_empty(self, df: Optional[pd.DataFrame]) -> pd.DataFrame:
        if df is None:
            return pd.DataFrame()
        return df
    def inter_all_symbols(self, exchange: Optional[str] = "HSX") -> Generator[Tuple[str, str], None, None]:
        listing = Listing()
        df = listing.symbols_by_exchange()
        exch = (exchange or "HSX").upper()
        df = df[df["exchange"] == exch]
        
        for _, row in df.iterrows():
            yield str(row.get("symbol")), str(row.get("exchange"))
    
    def fetch_bundle(
        self, symbol: str
    ) -> Tuple[Dict[str, pd.DataFrame], bool]:
        retries = 0
        while retries <= self.max_retries:
            try:
                print(f"Trying to fetch data for {symbol}, attempt {retries + 1}")
                finance = Finance(symbol=symbol, source="VCI")
                
                bundle = {
                    "balance_sheet_df": self._df_or_empty(finance.balance_sheet()),
                    "income_statement_df": self._df_or_empty(finance.income_statement()),
                    "cash_flow_df": self._df_or_empty(finance.cash_flow()),
                    "ratios_df": pd.DataFrame(),  # Not available in this version
                    "profile_df": pd.DataFrame(),  # Not available in this version
                }
                
                print(f"Successfully fetched data for {symbol}")
                return bundle, True
                
            except SystemExit:
                print(f"SystemExit occurred for {symbol}, retrying...")
                retries += 1
                
            except Exception as e:
                print(f"Exception occurred for {symbol}: {e}")
                return {}, False
                
        print(f"Max retries exceeded for {symbol}")
        return {}, False

    def get_full_financial_data(self, symbol: str) -> Tuple[bool, Dict]:
        """Alias for fetch_bundle to match service expectations."""
        bundle, success = self.fetch_bundle(symbol)
        return success, bundle
                