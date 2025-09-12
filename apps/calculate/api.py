
from apps.calculate.vnstock import VNStock
from typing import Optional, Dict, List
from django.db import transaction
class CalculateService:
    def __init__(self, vnstock_client: Optional[VNStock] = None, per_symbol_sleep: float = 1.0):
        self.vnstock_client = vnstock_client or VNStock()
        self.per_symbol_sleep = per_symbol_sleep
    def import_financials_from_symbols(self) -> List[Dict[str, Any]]:
        results = Dict[str, Any] = []
        for symbol, exchange in self.vnstock_client.inter_all_symbols(exchange="HSX"):
            bundle, success = self.vnstock_client.fetch_bundle(symbol=symbol)
            if not success:
                continue
            balance_sheet_df = bundle.get("balance_sheet_df")
            income_statement_df = bundle.get("income_statement_df")
            cash_flow_df = bundle.get("cash_flow_df")
            ratios_df = bundle.get("ratios_df")
            profile_df = bundle.get("profile_df")
            
            
            data = balance_sheet_df.iloc[0]
            try:
                with transaction.atomic():
                    
        
        