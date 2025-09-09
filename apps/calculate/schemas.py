from ninja import Schema
from datetime import date, datetime
from typing import Optional


class PeriodSchema(Schema):
    id: int
    symbol_id: int
    type: str
    year: int
    quarter: Optional[int]
    start_date: Optional[date]
    end_date: Optional[date]
    created_at: datetime


class BalanceSheetSchema(Schema):
    id: int
    period_id: int
    short_asset: Optional[float]
    cash: Optional[float]
    short_invest: Optional[float]
    short_receivable: Optional[float]
    inventory: Optional[float]
    long_asset: Optional[float]
    fixed_asset: Optional[float]
    asset: Optional[float]
    debt: Optional[float]
    short_debt: Optional[float]
    long_debt: Optional[float]
    equity: Optional[float]
    capital: Optional[float]
    other_debt: Optional[float]
    un_distributed_income: Optional[float]
    minor_share_holder_profit: Optional[float]
    payable: Optional[float]


class IncomeStatementSchema(Schema):
    id: int
    period_id: int
    revenue: Optional[float]
    year_revenue_growth: Optional[float]
    cost_of_good_sold: Optional[float]
    gross_profit: Optional[float]
    operation_expense: Optional[float]
    operation_profit: Optional[float]
    year_operation_profit_growth: Optional[float]
    interest_expense: Optional[float]
    pre_tax_profit: Optional[float]
    post_tax_profit: Optional[float]
    share_holder_income: Optional[float]
    year_share_holder_income_growth: Optional[float]
    ebitda: Optional[float]


class CashFlowSchema(Schema):
    id: int
    period_id: int
    invest_cost: Optional[float]
    from_invest: Optional[float]
    from_financial: Optional[float]
    from_sale: Optional[float]
    free_cash_flow: Optional[float]


class FinancialRatioSchema(Schema):
    id: int
    period_id: int
    price_to_earning: Optional[float]
    price_to_book: Optional[float]
    value_before_ebitda: Optional[float]
    dividend: Optional[float]
    roe: Optional[float]
    roa: Optional[float]
    days_receivable: Optional[float]
    days_payable: Optional[float]
    earning_per_share: Optional[float]
    book_value_per_share: Optional[float]
    equity_on_total_asset: Optional[float]
    equity_on_liability: Optional[float]
    current_payment: Optional[float]
    quick_payment: Optional[float]
    eps_change: Optional[float]
    ebitda_on_stock: Optional[float]
    gross_profit_margin: Optional[float]
    operating_profit_margin: Optional[float]
    post_tax_margin: Optional[float]
    debt_on_equity: Optional[float]
    debt_on_asset: Optional[float]
    debt_on_ebitda: Optional[float]
    asset_on_equity: Optional[float]
    capital_balance: Optional[float]
    cash_on_equity: Optional[float]
    cash_on_capitalize: Optional[float]
    revenue_on_work_capital: Optional[float]
    capex_on_fixed_asset: Optional[float]
    revenue_on_asset: Optional[float]
    post_tax_on_pre_tax: Optional[float]
    ebit_on_revenue: Optional[float]
    pre_tax_on_ebit: Optional[float]
    payable_on_equity: Optional[float]
    ebitda_on_stock_change: Optional[float]
    book_value_per_share_change: Optional[float]
