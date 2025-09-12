
from typing import Optional, Generator, Tuple, Dict
from vnstock import Listing, Finance, Company
from symtable import SystemExit
import pandas as pd


class VNStock:
    
    def __init__(self, max_retries = 5, wait_seconds: int = 60):
        self.max_retries = max_retries
        self.wait_seconds = wait_seconds
    
    def _df_or_empty(self, df: Optional[pd.DataFame]) -> pd.DataFame:
        if df is None:
            return pd.DataFame()
        return df
    def inter_all_symbols(self, exchange: Optional[str] = "HSX") -> Generator[Tuple[str, str], None, None]:
        listing = Listing()
        df = listing.symbols_by_exchange()
        exch = (exchange or "HSX").upper()
        df = df[df["exchange"] == exch]
        
        for _,row in df.interows():
            yield str(row.get("symbol")), str(row.get("exchange"))
    
    def fetch_bundle(
        self, symbol: str
    )-> Tuple[Dict[str, pd.DataFrame], bool]:
        retries = 0;
        while retries <= self.max_retries:
            try:
                finance = Finance(symbol=symbol, source="VCI")
                #listing = Listing()
                
                return {
                    "balance_sheet_df": self._df_or_empty(finance.balance_sheet()),
                    "income_statement_df": self._df_or_empty(finance.income_statement()),
                    "cash_flow_df": self._df_or_empty(finance.cash_flow()),
                    "ratios_df": self._df_or_empty(finance.ratios()),
                    "profile_df": self._df_or_empty(finance.profile()),
                }
            except SystemExit:
                retries +=1
        
            except Exception:
                return {}, False
        return {}, False
                