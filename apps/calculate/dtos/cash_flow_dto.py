

from datetime import date
from typing import Optional, List
from pydantic import BaseModel
from ninja import Schema
class SymbolOut(Schema):
    id: int
    name: str
    exchange: Optional[str]

class CashFlowOut(Schema):
    year: int
    quarter: int
    symbol: SymbolOut  # Thêm symbol vào
    profits_from_other_activities: Optional[int]
    operating_profit_before_changes_in_working_capital: Optional[int]
    net_cash_flows_from_operating_activities_before_bit: Optional[int]
    payment_from_reserves: Optional[int]
    purchase_of_fixed_assets: Optional[int]
    gain_on_dividend: Optional[int]
    net_cash_flows_from_investing_activities: Optional[int]
    increase_in_charter_captial: Optional[int]
    cash_flows_from_financial_activities: Optional[int]
    net_increase_decrease_in_cash_and_cash_equivalents: Optional[int]
    cash_and_cash_equivalents: Optional[int]
    foreign_exchange_differences_adjustment: Optional[int]
    cash_and_cash_equivalents_at_the_end_of_period: Optional[int]
    net_cash_inflows_outflows_from_operating_activities: Optional[int]
    proceeds_from_disposal_of_fixed_assets: Optional[int]
    investment_in_other_entities: Optional[int]
    proceeds_from_divestment_in_other_entities: Optional[int]
    dividends_paid: Optional[int]