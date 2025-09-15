

from datetime import date
from typing import Optional, List
from pydantic import BaseModel

class CashFlowOut(BaseModel):
    symbol: str
    fiscal_date_ending: date
    reported_currency: Optional[str] = None
    operating_cashflow: Optional[float] = None
    payments_for_operating_activities: Optional[float] = None
    proceeds_from_operating_activities: Optional[float] = None
    change_in_operating_liabilities: Optional[float] = None
    change_in_operating_assets: Optional[float] = None
    depreciation_depletion_and_amortization: Optional[float] = None
    capital_expenditures: Optional[float] = None
    change_in_receivables: Optional[float] = None
    change_in_inventory: Optional[float] = None
    profit_loss: Optional[float] = None
    cashflow_from_investment: Optional[float] = None
    cashflow_from_financing: Optional[float] = None
    proceeds_from_repurchase_of_equity: Optional[float] = None
    payments_for_repurchase_of_equity: Optional[float] = None
    proceeds_from_issuance_of_equity: Optional[float] = None
    payments_for_issuance_of_equity: Optional[float] = None
    proceeds_from_borrowings: Optional[float] = None
    repayments_of_borrowings: Optional[float] = None
    effect_of_forex_changes_on_cash: Optional[float] = None
    net_change_in_cash: Optional[float] = None
    cash_at_beginning_of_period: Optional[float] = None
    cash_at_end_of_period: Optional[float] = None
    operating_cash_flow_per_share: Optional[float] = None

    class Config:
        orm_mode = True