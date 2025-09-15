from typing import Optional, Dict, List, Any
import os
import logging
import time
import pandas as pd

from django.db import transaction
from apps.calculate.repositories import (
    upsert_balance_sheet,
    upsert_income_statement,
    upsert_cash_flow,
    upsert_ratio,
)
from apps.calculate.vnstock import VNStock
from apps.calculate.models import BalanceSheet, IncomeStatement, CashFlow
from apps.stock.models import Symbol
from apps.stock.utils.safe import safe_int, safe_decimal, safe_str


logger = logging.getLogger(__name__)


class CalculateService:

    def __init__(self, vnstock_client: Optional[VNStock] = None, sleep_between_symbols: int = 1):
        self.vnstock_client = vnstock_client or VNStock()
        self.sleep_between_symbols = sleep_between_symbols

    def import_all_financials(self) -> Dict[str, Any]:
        """Import financial data for ALL symbols in database."""
        symbols = Symbol.objects.all().order_by('name')

        result = {
            "total_symbols": symbols.count(),
            "successful_symbols": 0,
            "failed_symbols": 0,
            "total_balance_sheets": 0,
            "total_income_statements": 0,
            "total_cash_flows": 0,
            "errors": [],
            "details": []
        }

        print(f"Starting import for {result['total_symbols']} symbols...")
        
        # Process each symbol
        for symbol in symbols:
            print(f"Processing symbol: {symbol.name}")
            symbol_result = self._import_symbol_data(symbol)
            
            # Add to results
            result["details"].append(symbol_result)
            
            # Update counters
            if symbol_result.get("success", False):
                print(f"✓ Successfully imported {symbol.name}")
                result["successful_symbols"] += 1
                result["total_balance_sheets"] += symbol_result.get("balance_sheets", 0)
                result["total_income_statements"] += symbol_result.get("income_statements", 0)
                result["total_cash_flows"] += symbol_result.get("cash_flows", 0)
            else:
                print(f"✗ Failed to import {symbol.name}")
                result["failed_symbols"] += 1
                result["errors"].extend(symbol_result.get("errors", []))
            
            # Sleep between symbols to respect API rate limits
            if self.sleep_between_symbols > 0:
                time.sleep(self.sleep_between_symbols)

        print(f"Import completed: {result['successful_symbols']}/{result['total_symbols']} symbols successful")
        return result

    def import_income_statements_all(self) -> Dict[str, Any]:
        """Import ONLY income statements for all symbols in DB."""
        symbols = Symbol.objects.all().order_by('name')

        result = {
            "total_symbols": symbols.count(),
            "successful_symbols": 0,
            "failed_symbols": 0,
            "total_balance_sheets": 0,
            "total_income_statements": 0,
            "total_cash_flows": 0,
            "errors": [],
            "details": []
        }

        for symbol in symbols:
            detail = {
                "symbol": symbol.name,
                "success": False,
                "balance_sheets": 0,
                "income_statements": 0,
                "cash_flows": 0,
                "errors": []
            }
            try:
                ok, bundle = self.vnstock_client.get_full_financial_data(symbol.name)
                if not ok or not bundle:
                    detail["errors"].append("Failed to fetch data from vnstock")
                else:
                    with transaction.atomic():
                        cnt = self._import_income_statements(symbol, bundle)
                        detail["income_statements"] = cnt
                        detail["success"] = True
                        result["total_income_statements"] += cnt
                        result["successful_symbols"] += 1
            except Exception as e:
                detail["errors"].append(str(e))
                result["failed_symbols"] += 1
            finally:
                result["details"].append(detail)
                if self.sleep_between_symbols > 0:
                    time.sleep(self.sleep_between_symbols)

        return result

    def import_cash_flows_all(self) -> Dict[str, Any]:
        """Import ONLY cash flows for all symbols in DB."""
        symbols = Symbol.objects.all().order_by('name')

        result = {
            "total_symbols": symbols.count(),
            "successful_symbols": 0,
            "failed_symbols": 0,
            "total_balance_sheets": 0,
            "total_income_statements": 0,
            "total_cash_flows": 0,
            "errors": [],
            "details": []
        }

        for symbol in symbols:
            detail = {
                "symbol": symbol.name,
                "success": False,
                "balance_sheets": 0,
                "income_statements": 0,
                "cash_flows": 0,
                "errors": []
            }
            try:
                ok, bundle = self.vnstock_client.get_full_financial_data(symbol.name)
                if not ok or not bundle:
                    detail["errors"].append("Failed to fetch data from vnstock")
                else:
                    with transaction.atomic():
                        cnt = self._import_cash_flows(symbol, bundle)
                        detail["cash_flows"] = cnt
                        detail["success"] = True
                        result["total_cash_flows"] += cnt
                        result["successful_symbols"] += 1
            except Exception as e:
                detail["errors"].append(str(e))
                result["failed_symbols"] += 1
            finally:
                result["details"].append(detail)
                if self.sleep_between_symbols > 0:
                    time.sleep(self.sleep_between_symbols)

        return result

    def _import_symbol_data(self, symbol) -> Dict[str, Any]:
        """Import financial data for a single symbol."""
        symbol_result = {
            "symbol": symbol.name,
            "success": False,
            "balance_sheets": 0,
            "income_statements": 0,
            "cash_flows": 0,
            "errors": []
        }
        
        try:
            fetch_success, bundle = self.vnstock_client.get_full_financial_data(symbol.name)
            
            if not fetch_success or not bundle:
                symbol_result["errors"].append("Failed to fetch data from vnstock")
                return symbol_result
            
            with transaction.atomic():
                # Import balance sheets
                balance_sheet_count = self._import_balance_sheets(symbol, bundle)
                income_statement_count = self._import_income_statements(symbol, bundle)
                cash_flow_count = self._import_cash_flows(symbol, bundle)
                try:
                    _ = self._import_ratios(symbol, bundle)
                except Exception as e:
                    logger.error(f"Error importing ratios for {symbol.name}: {str(e)}")
                
                symbol_result.update({
                    "success": True,
                    "balance_sheets": balance_sheet_count,
                    "income_statements": income_statement_count,
                    "cash_flows": cash_flow_count
                })
        
        except Exception as e:
            logger.error(f"Error importing data for {symbol.name}: {str(e)}")
            symbol_result["errors"].append(f"Import error: {str(e)}")
        
        return symbol_result

    def _import_balance_sheets(self, symbol, bundle) -> int:
        """Import balance sheet data for a symbol."""
        count = 0
        balance_sheet_df = bundle.get('balance_sheet_df', pd.DataFrame())
        
        if balance_sheet_df.empty:
            return count
            
        for _, row in balance_sheet_df.iterrows():
            try:
                mapped_data = self._map_balance_sheet_data(symbol, row.to_dict())
                if mapped_data:
                    upsert_balance_sheet(mapped_data)
                    count += 1
            except Exception as e:
                logger.error(f"Error importing balance sheet for {symbol.name}: {str(e)}")
        
        return count

    def _import_income_statements(self, symbol, bundle) -> int:
        """Import income statement data for a symbol."""
        count = 0
        income_df = bundle.get('income_statement_df', pd.DataFrame())
        try:
            if not income_df.empty:
                print(f"[DEBUG] {symbol.name} income_statement first row: {income_df.head(1).to_dict(orient='records')}")
        except Exception:
            pass
        
        if income_df.empty:
            return count
            
        for _, row in income_df.iterrows():
            try:
                mapped_data = self._map_income_statement_data(symbol, row.to_dict())
                if mapped_data:
                    upsert_income_statement(mapped_data)
                    count += 1
            except Exception as e:
                logger.error(f"Error importing income statement for {symbol.name}: {str(e)}")
        
        return count

    def _import_cash_flows(self, symbol, bundle) -> int:
        """Import cash flow data for a symbol."""
        count = 0
        cash_flow_df = bundle.get('cash_flow_df', pd.DataFrame())
        # Debug: print size and sample
        try:
            print(f"[DEBUG] {symbol.name} cash_flow_df rows={len(cash_flow_df)} cols={list(cash_flow_df.columns)[:10]}")
            if not cash_flow_df.empty:
                print(f"[DEBUG] {symbol.name} cash_flow first row: {cash_flow_df.head(1).to_dict(orient='records')}")
        except Exception:
            pass
        
        if cash_flow_df.empty:
            return count
            
        for _, row in cash_flow_df.iterrows():
            try:
                mapped_data = self._map_cash_flow_data(symbol, row.to_dict())
                if mapped_data:
                    upsert_cash_flow(mapped_data)
                    count += 1
            except Exception as e:
                logger.error(f"Error importing cash flow for {symbol.name}: {str(e)}")
        
        return count

    def _map_balance_sheet_data(self, symbol, data) -> Dict[str, Any]:
        """Map vnstock balance sheet data to model fields."""
        year = safe_int(data.get('yearReport'))
        quarter = safe_int(data.get('lengthReport'))
        
        if not year or not quarter:
            return None
        
        return {
            'symbol': symbol,
            'year_report': year,
            'length_report': quarter,
            'current_assets': safe_int(data.get('CURRENT ASSETS (Bn. VND)')),
            'cash_and_cash_equivalents': safe_int(data.get('Cash and cash equivalents (Bn. VND)')),
            'short_term_investments': safe_int(data.get('Short-term investments (Bn. VND)')),
            'accounts_receivable': safe_int(data.get('Accounts receivable (Bn. VND)')),
            'net_inventories': safe_int(data.get('Net Inventories')),
            'prepayments_to_suppliers': safe_int(data.get('Prepayments to suppliers (Bn. VND)')),
            'other_current_assets': safe_int(data.get('Other current assets')),
            'long_term_assets': safe_int(data.get('LONG-TERM ASSETS (Bn. VND)')),
            'fixed_assets': safe_int(data.get('Fixed assets (Bn. VND)')),
            'long_term_investments': safe_int(data.get('Long-term investments (Bn. VND)')),
            'long_term_prepayments': safe_int(data.get('Long-term prepayments (Bn. VND)')),
            'other_long_term_assets': safe_int(data.get('Other long-term assets (Bn. VND)')),
            'other_long_term_receivables': safe_int(data.get('Other long-term receivables (Bn. VND)')),
            'long_term_trade_receivables': safe_int(data.get('Long-term trade receivables (Bn. VND)')),
            'total_assets': safe_int(data.get('TOTAL ASSETS (Bn. VND)')),
            'liabilities': safe_int(data.get('LIABILITIES (Bn. VND)')),
            'current_liabilities': safe_int(data.get('Current liabilities (Bn. VND)')),
            'short_term_borrowings': safe_int(data.get('Short-term borrowings (Bn. VND)')),
            'advances_from_customers': safe_int(data.get('Advances from customers (Bn. VND)')),
            'long_term_liabilities': safe_int(data.get('Long-term liabilities (Bn. VND)')),
            'long_term_borrowings': safe_int(data.get('Long-term borrowings (Bn. VND)')),
            'owners_equity': safe_int(data.get("OWNER'S EQUITY(Bn.VND)")),
            'capital_and_reserves': safe_int(data.get('Capital and reserves (Bn. VND)')),
            'common_shares': safe_int(data.get('Common shares (Bn. VND)')),
            'paid_in_capital': safe_int(data.get('Paid-in capital (Bn. VND)')),
            'undistributed_earnings': safe_int(data.get('Undistributed earnings (Bn. VND)')),
            'investment_and_development_funds': safe_int(data.get('Investment and development funds (Bn. VND)')),
            'total_resources': safe_int(data.get('TOTAL RESOURCES (Bn. VND)')),
        }

    def _map_income_statement_data(self, symbol, data) -> Dict[str, Any]:
        """Map vnstock income statement data to model fields."""
        
        print(data)
        year = safe_int(data.get('yearReport'))
        quarter = safe_int(data.get('lengthReport'))
        
        if not year or not quarter:
            return None
        return {
        'symbol': symbol,
        'year_report': data.get('yearReport'),
        'length_report': data.get('lengthReport'),
        'revenue': data.get('Revenue (Bn. VND)'),
        'revenue_yoy': data.get('Revenue YoY (%)'),
        'attribute_to_parent_company': data.get('Attribute to parent company (Bn. VND)') or data.get('attributeToParentCompany'),
        'attribute_to_parent_company_yoy': data.get('Attribute to parent company YoY (%)') or data.get('attributeToParentCompanyYoY'),
        'interest_and_similar_income': data.get('Financial Income') or data.get('interestAndSimilarIncome'),
        'interest_and_similar_expenses': data.get('Interest Expenses') or data.get('interestAndSimilarExpenses'),
        'net_interest_income': data.get('Net Interest Income') or data.get('netInterestIncome'),
        'fees_and_comission_income': data.get('Fees and Commission Income') or data.get('feesAndComissionIncome'),
        'fees_and_comission_expenses': data.get('Fees and Commission Expenses') or data.get('feesAndComissionExpenses'),
        'net_fee_and_commission_income': data.get('Net Fee and Commission Income') or data.get('netFeeAndCommissionIncome'),
        'net_gain_foreign_currency_and_gold_dealings': data.get('Net gain from foreign currency and gold dealings') or data.get('netGainForeignCurrencyAndGoldDealings'),
        'net_gain_trading_of_trading_securities': data.get('Net gain from trading of trading securities') or data.get('netGainTradingOfTradingSecurities'),
        'net_gain_disposal_of_investment_securities': data.get('Net gain from disposal of investment securities') or data.get('netGainDisposalOfInvestmentSecurities'),
        'net_other_income': data.get('Other Income') or data.get('netOtherIncome'),
        'other_expenses': data.get('Other Expenses') or data.get('otherExpenses'),
        'net_other_income_expenses': data.get('Net other income/expenses') or data.get('netOtherIncomeExpenses'),
        'dividends_received': data.get('Dividends Received') or data.get('dividendsReceived'),
        'total_operating_revenue': data.get('Total Operating Revenue') or data.get('totalOperatingRevenue'),
        'general_admin_expenses': data.get('General & Admin Expenses') or data.get('generalAdminExpenses'),
        'operating_profit_before_provision': data.get('Operating Profit/Loss') or data.get('operatingProfitBeforeProvision'),
        'provision_for_credit_losses': data.get('Provision for Credit Losses') or data.get('provisionForCreditLosses'),
        'profit_before_tax': data.get('Profit before tax') or data.get('profitBeforeTax'),
        'tax_for_the_year': data.get('Business income tax - current') or data.get('taxForTheYear'),
        'business_income_tax_current': data.get('Business income tax - current') or data.get('businessIncomeTaxCurrent'),
        'business_income_tax_deferred': data.get('Business income tax - deferred') or data.get('businessIncomeTaxDeferred'),
        'minority_interest': data.get('Minority Interest') or data.get('minorityInterest'),
        'net_profit_for_the_year': data.get('Net Profit For the Year') or data.get('netProfitForTheYear'),
        'attributable_to_parent_company': data.get('Attributable to parent company') or data.get('attributableToParentCompany'),
        'eps_basis': data.get('EPS Basis') or data.get('epsBasis'),
        }

    def _map_cash_flow_data(self, symbol, data) -> Dict[str, Any]:
        """Map vnstock cash flow row (dict) to CashFlow model fields."""
        year_report = safe_int(data.get('yearReport'), None)
        length_report = safe_int(data.get('lengthReport'), None)
        if year_report is None or length_report is None:
            return None

        return {
            'symbol': symbol,
            'year_report': year_report,
            'length_report': length_report,
            # Operating section
            'operating_profit_before_changes_in_working_capital': safe_int(
                data.get('Operating profit before changes in working capital'), None
            ),
            'net_cash_inflows_outflows_from_operating_activities': safe_int(
                data.get('Net cash inflows/outflows from operating activities'), None
            ),
            # Investing section
            'purchase_of_fixed_assets': safe_int(data.get('Purchase of fixed assets'), None),
            'proceeds_from_disposal_of_fixed_assets': safe_int(
                data.get('Proceeds from disposal of fixed assets'), None
            ),
            'investment_in_other_entities': safe_int(
                data.get('Investment in other entities'), None
            ),
            'proceeds_from_divestment_in_other_entities': safe_int(
                data.get('Proceeds from divestment in other entities'), None
            ),
            'gain_on_dividend': safe_int(data.get('Gain on Dividend'), None),
            'net_cash_flows_from_investing_activities': safe_int(
                data.get('Net Cash Flows from Investing Activities'), None
            ),
            # Financing section
            'increase_in_charter_captial': safe_int(data.get('Increase in charter captial'), None),
            'cash_flows_from_financial_activities': safe_int(
                data.get('Cash flows from financial activities'), None
            ),
            'dividends_paid': safe_int(data.get('Dividends paid'), None),
            # Summary and cash balance
            'net_increase_decrease_in_cash_and_cash_equivalents': safe_int(
                data.get('Net increase/decrease in cash and cash equivalents'), None
            ),
            'cash_and_cash_equivalents': safe_int(data.get('Cash and cash equivalents'), None),
            'foreign_exchange_differences_adjustment': safe_int(
                data.get('Foreign exchange differences Adjustment'), None
            ),
            'cash_and_cash_equivalents_at_the_end_of_period': safe_int(
                data.get('Cash and Cash Equivalents at the end of period'), None
            ),
        }
    def import_ratios_all(self) -> Dict[str, Any]:
        """Import ONLY ratios for all symbols in DB."""
        symbols = Symbol.objects.all().order_by('name')

        result = {
            "total_symbols": symbols.count(),
            "successful_symbols": 0,
            "failed_symbols": 0,
            "total_balance_sheets": 0,
            "total_income_statements": 0,
            "total_cash_flows": 0,
            "errors": [],
            "details": []
        }

        for symbol in symbols:
            detail = {
                "symbol": symbol.name,
                "success": False,
                "balance_sheets": 0,
                "income_statements": 0,
                "cash_flows": 0,
                "errors": []
            }
            try:
                ok, bundle = self.vnstock_client.get_full_financial_data(symbol.name)
                if not ok or not bundle:
                    detail["errors"].append("Failed to fetch data from vnstock")
                    result["failed_symbols"] += 1
                else:
                    with transaction.atomic():
                        _ = self._import_ratios(symbol, bundle)
                        detail["success"] = True
                        result["successful_symbols"] += 1
            except Exception as e:
                detail["errors"].append(str(e))
                result["failed_symbols"] += 1
            finally:
                result["details"].append(detail)
                if self.sleep_between_symbols > 0:
                    time.sleep(self.sleep_between_symbols)

        return result

    def _map_ratio_data(self, symbol, data) -> Dict[str, Any]:
        """Map vnstock ratio row into Ratio model fields. Ignores unknown columns."""
        year_report = safe_int(data.get('yearReport'), None)
        length_report = safe_int(data.get('lengthReport'), None)
        if year_report is None or length_report is None:
            return None
        return {
            'symbol': symbol,
            'year_report': year_report,
            'length_report': length_report,
            'debt_equity': safe_decimal(data.get('Debt/Equity'), None) or safe_decimal(data.get('(ST+LT borrowings)/Equity'), None),
            'fixed_asset_to_equity': safe_decimal(data.get('Fixed Asset-To-Equity'), None),
            'owners_equity_charter_capital': safe_decimal(data.get("Owners' Equity/Charter Capital"), None),
            'net_profit_margin': safe_decimal(data.get('Net Profit Margin (%)'), None),
            'roe': safe_decimal(data.get('ROE (%)'), None),
            'roic': safe_decimal(data.get('ROIC (%)'), None),
            'roa': safe_decimal(data.get('ROA (%)'), None),
            'dividend_yield': safe_decimal(data.get('Dividend yield (%)'), None),
            'financial_leverage': safe_decimal(data.get('Financial Leverage'), None),
            'market_capital': safe_int(data.get('Market Capital (Bn. VND)'), None),
            'outstanding_share': safe_int(data.get('Outstanding Share (Mil. Shares)'), None),
            'pe': safe_decimal(data.get('P/E'), None),
            'pb': safe_decimal(data.get('P/B'), None),
            'ps': safe_decimal(data.get('P/S'), None),
            'p_cash_flow': safe_decimal(data.get('P/Cash Flow'), None),
            'eps': safe_decimal(data.get('EPS (VND)'), None),
            'bvps': safe_decimal(data.get('BVPS (VND)'), None),
        }
