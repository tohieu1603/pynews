
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
                
                bs_df = self._df_or_empty(finance.balance_sheet())
                inc_df = self._df_or_empty(finance.income_statement())
                cf_df = self._df_or_empty(finance.cash_flow())
                ratios_df = pd.DataFrame()
                try:
                    ratio_methods = [
                        'ratios',
                        'ratio',
                        'financial_ratios',
                        'financial_ratio',
                        'ratios_quarterly',
                        'ratios_ttm',
                    ]
                    for m in ratio_methods:
                        if hasattr(finance, m):
                            fn = getattr(finance, m)
                            try:
                                tmp = fn()
                                tmp = self._df_or_empty(tmp)
                                if not tmp.empty:
                                    ratios_df = tmp
                                    break
                            except Exception:
                                continue
                    if ratios_df.empty:
                        for src in ["VCI", "TCBS"]:
                            try:
                                comp = Company(symbol=symbol, source=src)
                            except Exception:
                                continue
                            for m in ratio_methods:
                                if hasattr(comp, m):
                                    try:
                                        tmp = getattr(comp, m)()
                                        tmp = self._df_or_empty(tmp)
                                        if not tmp.empty:
                                            ratios_df = tmp
                                            raise StopIteration
                                    except Exception:
                                        continue
                except StopIteration:
                    pass
                except Exception:
                    ratios_df = pd.DataFrame()

                try:
                    print(f"{symbol} balance_sheet: rows={len(bs_df)} cols={list(bs_df.columns)[:8]}")
                    if not bs_df.empty:
                        print(f"{symbol} balance_sheet sample: {bs_df.head(1).to_dict(orient='records')}")
                except Exception:
                    pass
                try:
                    print(f"{symbol} income_statement: rows={len(inc_df)} cols={list(inc_df.columns)[:8]}")
                    if not inc_df.empty:
                        print(f"{symbol} income_statement sample: {inc_df.head(1).to_dict(orient='records')}")
                except Exception:
                    pass
                try:
                    print(f"{symbol} cash_flow: rows={len(cf_df)} cols={list(cf_df.columns)[:8]}")
                    if not cf_df.empty:
                        print(f"{symbol} cash_flow sample: {cf_df.head(1).to_dict(orient='records')}")
                except Exception:
                    pass
                try:
                    print(f"{symbol} ratios: rows={len(ratios_df)} cols={list(ratios_df.columns)[:8]}")
                    if ratios_df.empty:
                        try:
                            methods_fin = [n for n in dir(finance) if not n.startswith('_')]
                            print(f"{symbol} Finance methods: {methods_fin}")
                        except Exception:
                            pass
                        try:
                            comp_dbg = Company(symbol=symbol, source="VCI")
                            methods_comp = [n for n in dir(comp_dbg) if not n.startswith('_')]
                            print(f"{symbol} Company methods: {methods_comp}")
                        except Exception:
                            pass
                    else:
                        print(f"{symbol} ratios sample: {ratios_df.head(1).to_dict(orient='records')}")
                except Exception:
                    pass

                bundle = {
                    "balance_sheet_df": bs_df,
                    "income_statement_df": inc_df,
                    "cash_flow_df": cf_df,
                    "ratios_df": ratios_df,
                    "profile_df": pd.DataFrame(), 
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
                
