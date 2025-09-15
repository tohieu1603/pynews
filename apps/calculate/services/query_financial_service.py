from typing import List
from ninja.errors import HttpError  
from apps.calculate.repositories import qs_cash_flow, qs_income_statement
from apps.calculate.dtos.cash_flow_dto import CashFlowOut
from apps.calculate.dtos.income_statement_dto import InComeOut
from apps.calculate.dtos.income_statement_dto import SymbolOut
from apps.calculate.dtos.blance_sheet_dto import BalanceSheetOut
from apps.calculate.repositories import qs_balance_sheet
class QueryFinancialService:
    def get_cash_flow_statements(self, symbol_id: int, limit: int = 10) -> List[CashFlowOut]:
        try:
            qs = qs_cash_flow(symbol_id, limit)
            if not qs.exists():
                raise HttpError(404, f"No cash flow statements found for symbol_id={symbol_id}")
            return [
                CashFlowOut(
                    year=cf.year_report,
                    quarter=cf.length_report,
                    symbol={
                        "id": cf.symbol.id,
                        "name": cf.symbol.name,
                        "exchange": cf.symbol.exchange,
                    },
                    profits_from_other_activities=cf.profits_from_other_activities,
                    operating_profit_before_changes_in_working_capital=cf.operating_profit_before_changes_in_working_capital,
                    net_cash_flows_from_operating_activities_before_bit=cf.net_cash_flows_from_operating_activities_before_bit,
                    payment_from_reserves=cf.payment_from_reserves,
                    purchase_of_fixed_assets=cf.purchase_of_fixed_assets,
                    gain_on_dividend=cf.gain_on_dividend,
                    net_cash_flows_from_investing_activities=cf.net_cash_flows_from_investing_activities,
                    increase_in_charter_captial=cf.increase_in_charter_captial,
                    cash_flows_from_financial_activities=cf.cash_flows_from_financial_activities,
                    net_increase_decrease_in_cash_and_cash_equivalents=cf.net_increase_decrease_in_cash_and_cash_equivalents,
                    cash_and_cash_equivalents=cf.cash_and_cash_equivalents,
                    foreign_exchange_differences_adjustment=cf.foreign_exchange_differences_adjustment,
                    cash_and_cash_equivalents_at_the_end_of_period=cf.cash_and_cash_equivalents_at_the_end_of_period,
                    net_cash_inflows_outflows_from_operating_activities=cf.net_cash_inflows_outflows_from_operating_activities,
                    proceeds_from_disposal_of_fixed_assets=cf.proceeds_from_disposal_of_fixed_assets,
                    investment_in_other_entities=cf.investment_in_other_entities,
                    proceeds_from_divestment_in_other_entities=cf.proceeds_from_divestment_in_other_entities,
                    dividends_paid=cf.dividends_paid,
                )
                for cf in qs
            ]

        except Exception as e:
            raise HttpError(500, f"Lỗi hệ thống, vui lòng thử lại sau.")
    def get_income_statements(self, symbol_id: int) -> List[InComeOut]:
        try:
            qs = qs_income_statement(symbol_id)
            if not qs.exists():
                raise HttpError(404, "No income statements found for this symbol")

            return [
                InComeOut(
                    year=inc.year_report,
                    quarter=inc.length_report,
                    symbol=SymbolOut(
                        id=inc.symbol.id,
                        name=inc.symbol.name,
                        exchange=getattr(inc.symbol, "exchange", None)
                    ),
                    revenue=inc.revenue,
                    revenue_yoy=inc.revenue_yoy,
                    attribute_to_parent_company=inc.attribute_to_parent_company,
                    attribute_to_parent_company_yoy=inc.attribute_to_parent_company_yoy,
                    interest_and_similar_income=inc.interest_and_similar_income,
                    interest_and_similar_expenses=inc.interest_and_similar_expenses,
                    net_interest_income=inc.net_interest_income,
                    fees_and_comission_income=inc.fees_and_comission_income,
                    fees_and_comission_expenses=inc.fees_and_comission_expenses,
                    net_fee_and_commission_income=inc.net_fee_and_commission_income,
                    net_gain_foreign_currency_and_gold_dealings=inc.net_gain_foreign_currency_and_gold_dealings,
                    net_gain_trading_of_trading_securities=inc.net_gain_trading_of_trading_securities,
                    net_gain_disposal_of_investment_securities=inc.net_gain_disposal_of_investment_securities,
                    net_other_income=inc.net_other_income,
                    other_expenses=inc.other_expenses,
                    net_other_income_expenses=inc.net_other_income_expenses,
                    dividends_received=inc.dividends_received,
                    total_operating_revenue=inc.total_operating_revenue,
                    general_admin_expenses=inc.general_admin_expenses,
                    operating_profit_before_provision=inc.operating_profit_before_provision,
                    provision_for_credit_losses=inc.provision_for_credit_losses,
                    profit_before_tax=inc.profit_before_tax,
                    tax_for_the_year=inc.tax_for_the_year,
                    business_income_tax_current=inc.business_income_tax_current,
                    business_income_tax_deferred=inc.business_income_tax_deferred,
                    minority_interest=inc.minority_interest,
                    net_profit_for_the_year=inc.net_profit_for_the_year,
                    attributable_to_parent_company=inc.attributable_to_parent_company,
                    eps_basis=inc.eps_basis,
                )
                for inc in qs
            ]

        except Exception:
            raise HttpError(500, "Lỗi hệ thống, vui lòng thử lại sau.")
    
    def get_balance_sheets(self, symbol_id: int) -> List[BalanceSheetOut]:
        try:
            qs = qs_balance_sheet(symbol_id)
            if not qs.exists():
                raise HttpError(404, f"No balance sheets found for symbol_id={symbol_id}")

            return [
                BalanceSheetOut(
                    year=bs.year_report,
                    quarter=bs.length_report,
                    symbol=SymbolOut(
                        id=bs.symbol.id,
                        name=bs.symbol.name,
                        exchange=getattr(bs.symbol, "exchange", None)
                    ),
                    current_assets=bs.current_assets,
                    cash_and_cash_equivalents=bs.cash_and_cash_equivalents,
                    short_term_investments=bs.short_term_investments,
                    accounts_receivable=bs.accounts_receivable,
                    net_inventories=bs.net_inventories,
                    prepayments_to_suppliers=bs.prepayments_to_suppliers,
                    other_current_assets=bs.other_current_assets,
                    long_term_assets=bs.long_term_assets,
                    fixed_assets=bs.fixed_assets,
                    long_term_investments=bs.long_term_investments,
                    long_term_prepayments=bs.long_term_prepayments,
                    other_long_term_assets=bs.other_long_term_assets,
                    other_long_term_receivables=bs.other_long_term_receivables,
                    long_term_trade_receivables=bs.long_term_trade_receivables,
                    total_assets=bs.total_assets,
                    liabilities=bs.liabilities,
                    current_liabilities=bs.current_liabilities,
                    short_term_borrowings=bs.short_term_borrowings,
                    advances_from_customers=bs.advances_from_customers,
                    long_term_liabilities=bs.long_term_liabilities,
                    long_term_borrowings=bs.long_term_borrowings,
                    owners_equity=bs.owners_equity,
                    capital_and_reserves=bs.capital_and_reserves,
                    common_shares=bs.common_shares,
                    paid_in_capital=bs.paid_in_capital,
                    undistributed_earnings=bs.undistributed_earnings,
                    investment_and_development_funds=bs.investment_and_development_funds,
                    total_resources=bs.total_resources,
                )
                for bs in qs
            ]
        except Exception:
            raise HttpError(500, "Lỗi hệ thống, vui lòng thử lại sau.")