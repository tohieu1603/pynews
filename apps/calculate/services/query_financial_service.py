from typing import List
from ninja.errors import HttpError  
from apps.calculate.repositories import qs_cash_flow, qs_income_statement
from apps.calculate.dtos.cash_flow_dto import CashFlowOut, SymbolOut as CashFlowSymbolOut
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
                    symbol=CashFlowSymbolOut(
                        id=cf.symbol.id,
                        name=cf.symbol.name,
                        exchange=getattr(cf.symbol, "exchange", None),
                    ),
                    # Map all fields from CashFlow model
                    net_profit_loss_before_tax=cf.net_profit_loss_before_tax,
                    depreciation_and_amortisation=cf.depreciation_and_amortisation,
                    provision_for_credit_losses=cf.provision_for_credit_losses,
                    unrealized_foreign_exchange_gain_loss=cf.unrealized_foreign_exchange_gain_loss,
                    profit_loss_from_investing_activities=cf.profit_loss_from_investing_activities,
                    interest_expense=cf.interest_expense,
                    operating_profit_before_changes_in_working_capital=cf.operating_profit_before_changes_in_working_capital,
                    increase_decrease_in_receivables=cf.increase_decrease_in_receivables,
                    increase_decrease_in_inventories=cf.increase_decrease_in_inventories,
                    increase_decrease_in_payables=cf.increase_decrease_in_payables,
                    increase_decrease_in_prepaid_expenses=cf.increase_decrease_in_prepaid_expenses,
                    interest_paid=cf.interest_paid,
                    business_income_tax_paid=cf.business_income_tax_paid,
                    net_cash_inflows_outflows_from_operating_activities=cf.net_cash_inflows_outflows_from_operating_activities,
                    purchase_of_fixed_assets=cf.purchase_of_fixed_assets,
                    proceeds_from_disposal_of_fixed_assets=cf.proceeds_from_disposal_of_fixed_assets,
                    loans_granted_purchases_of_debt_instruments_bn_vnd=cf.loans_granted_purchases_of_debt_instruments_bn_vnd,
                    collection_of_loans_proceeds_sales_instruments_vnd=cf.collection_of_loans_proceeds_sales_instruments_vnd,
                    investment_in_other_entities=cf.investment_in_other_entities,
                    proceeds_from_divestment_in_other_entities=cf.proceeds_from_divestment_in_other_entities,
                    gain_on_dividend=cf.gain_on_dividend,
                    net_cash_flows_from_investing_activities=cf.net_cash_flows_from_investing_activities,
                    increase_in_charter_captial=cf.increase_in_charter_captial,
                    payments_for_share_repurchases=cf.payments_for_share_repurchases,
                    proceeds_from_borrowings=cf.proceeds_from_borrowings,
                    repayment_of_borrowings=cf.repayment_of_borrowings,
                    finance_lease_principal_payments=cf.finance_lease_principal_payments,
                    dividends_paid=cf.dividends_paid,
                    cash_flows_from_financial_activities=cf.cash_flows_from_financial_activities,
                    net_increase_decrease_in_cash_and_cash_equivalents=cf.net_increase_decrease_in_cash_and_cash_equivalents,
                    cash_and_cash_equivalents=cf.cash_and_cash_equivalents,
                    foreign_exchange_differences_adjustment=cf.foreign_exchange_differences_adjustment,
                    cash_and_cash_equivalents_at_the_end_of_period=cf.cash_and_cash_equivalents_at_the_end_of_period,
                )
                for cf in qs
            ]

        except Exception as e:
            import traceback
            print(f"Error in get_cash_flow_statements: {e}")
            print(traceback.format_exc())
            raise HttpError(500, "Lỗi hệ thống, vui lòng thử lại sau.")
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
                    # Map model fields to DTO fields correctly
                    revenue=inc.revenue_bn_vnd,
                    revenue_yoy=inc.revenue_yoy_percent,
                    attribute_to_parent_company=inc.attribute_to_parent_company_bn_vnd,
                    attribute_to_parent_company_yoy=inc.attribute_to_parent_company_yo_y_percent,
                    # Map available fields
                    general_admin_expenses=inc.general_admin_expenses,
                    profit_before_tax=inc.profit_before_tax,
                    business_income_tax_current=inc.business_income_tax_current,
                    business_income_tax_deferred=inc.business_income_tax_deferred,
                    minority_interest=inc.minority_interest,
                    net_profit_for_the_year=inc.net_profit_for_the_year,
                    attributable_to_parent_company=inc.attributable_to_parent_company,
                    # Set unavailable fields to None
                    interest_and_similar_income=None,
                    interest_and_similar_expenses=None,
                    net_interest_income=None,
                    fees_and_comission_income=None,
                    fees_and_comission_expenses=None,
                    net_fee_and_commission_income=None,
                    net_gain_foreign_currency_and_gold_dealings=None,
                    net_gain_trading_of_trading_securities=None,
                    net_gain_disposal_of_investment_securities=None,
                    net_other_income=inc.net_other_income_expenses,
                    other_expenses=None,
                    net_other_income_expenses=inc.net_other_income_expenses,
                    dividends_received=None,
                    total_operating_revenue=None,
                    operating_profit_before_provision=None,
                    provision_for_credit_losses=None,
                    tax_for_the_year=None,
                    eps_basis=None,
                )
                for inc in qs
            ]

        except Exception as e:
            import traceback
            print(f"Error in get_income_statements: {e}")
            print(traceback.format_exc())
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
                    # Map model fields to DTO fields correctly
                    current_assets=bs.current_assets_bn_vnd,
                    cash_and_cash_equivalents=bs.cash_and_cash_equivalents_bn_vnd,
                    short_term_investments=bs.short_term_investments_bn_vnd,
                    accounts_receivable=bs.accounts_receivable_bn_vnd,
                    net_inventories=bs.net_inventories,
                    prepayments_to_suppliers=bs.prepayments_to_suppliers_bn_vnd,
                    other_current_assets=bs.other_current_assets_bn_vnd,
                    long_term_assets=bs.long_term_assets_bn_vnd,
                    fixed_assets=bs.fixed_assets_bn_vnd,
                    long_term_investments=bs.long_term_investments_bn_vnd,
                    long_term_prepayments=bs.long_term_prepayments_bn_vnd,
                    other_long_term_assets=bs.other_long_term_assets_bn_vnd,
                    other_long_term_receivables=bs.other_long_term_receivables_bn_vnd,
                    long_term_trade_receivables=bs.long_term_trade_receivables_bn_vnd,
                    total_assets=bs.total_assets_bn_vnd,
                    liabilities=bs.liabilities_bn_vnd,
                    current_liabilities=bs.current_liabilities_bn_vnd,
                    short_term_borrowings=bs.short_term_borrowings_bn_vnd,
                    advances_from_customers=bs.advances_from_customers_bn_vnd,
                    long_term_liabilities=bs.long_term_liabilities_bn_vnd,
                    long_term_borrowings=bs.long_term_borrowings_bn_vnd,
                    owners_equity=bs.owners_equitybn_vnd,  # Note: typo in model field name
                    capital_and_reserves=bs.capital_and_reserves_bn_vnd,
                    common_shares=bs.common_shares_bn_vnd,
                    paid_in_capital=bs.paid_in_capital_bn_vnd,
                    undistributed_earnings=bs.undistributed_earnings_bn_vnd,
                    investment_and_development_funds=bs.investment_and_development_funds_bn_vnd,
                    total_resources=bs.total_resources_bn_vnd,
                )
                for bs in qs
            ]

        except Exception as e:
            import traceback
            print(f"Error in get_balance_sheets: {e}")
            print(traceback.format_exc())
            raise HttpError(500, "Lỗi hệ thống, vui lòng thử lại sau.")