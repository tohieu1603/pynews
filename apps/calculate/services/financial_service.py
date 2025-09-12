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
            # Get financial data from vnstock
            fetch_success, bundle = self.vnstock_client.get_full_financial_data(symbol.name)
            
            if not fetch_success or not bundle:
                symbol_result["errors"].append("Failed to fetch data from vnstock")
                return symbol_result
            
            # Import data in transaction for atomicity
            with transaction.atomic():
                # Import balance sheets
                balance_sheet_count = self._import_balance_sheets(symbol, bundle)
                income_statement_count = self._import_income_statements(symbol, bundle)
                cash_flow_count = self._import_cash_flows(symbol, bundle)
                
                # Update counts
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
                # Map vnstock data to model fields
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
        year = safe_int(data.get('year'))
        quarter = safe_int(data.get('quarter'))
        
        if not year or not quarter:
            return None
        
        return {
            'symbol': symbol,
            'year': year,
            'quarter': quarter,
            'revenue': safe_int(data.get('revenue')),
            'year_revenue_growth': safe_decimal(data.get('yearRevenueGrowth')),
            'quarter_revenue_growth': safe_decimal(data.get('quarterRevenueGrowth')),
            'cost_of_good_sold': safe_int(data.get('costOfGoodSold')),
            'gross_profit': safe_int(data.get('grossProfit')),
            'operating_expense': safe_int(data.get('operatingExpense')),
            'operating_profit': safe_int(data.get('operatingProfit')),
            'year_operating_profit_growth': safe_decimal(data.get('yearOperatingProfitGrowth')),
            'quarter_operating_profit_growth': safe_decimal(data.get('quarterOperatingProfitGrowth')),
            'interest_expense': safe_int(data.get('interestExpense')),
            'pre_tax_profit': safe_int(data.get('preTaxProfit')),
            'post_tax_profit': safe_int(data.get('postTaxProfit')),
            'share_holder_income': safe_int(data.get('shareHolderIncome')),
            'year_share_holder_income_growth': safe_decimal(data.get('yearShareHolderIncomeGrowth')),
            'quarter_share_holder_income_growth': safe_decimal(data.get('quarterShareHolderIncomeGrowth')),
            'investment_profit': safe_int(data.get('investmentProfit')),
            'service_profit': safe_int(data.get('serviceProfit')),
            'other_profit': safe_int(data.get('otherProfit')),
            'provision_expense': safe_int(data.get('provisionExpense')),
            'operating_profit_pre_provision': safe_int(data.get('operatingProfitPreProvision')),
            'non_interest_income': safe_int(data.get('nonInterestIncome')),
            'non_interest_expense': safe_int(data.get('nonInterestExpense')),
            'insurance_revenue': safe_int(data.get('insuranceRevenue')),
            'insurance_expense': safe_int(data.get('insuranceExpense')),
        }

    def _map_cash_flow_data(self, symbol, data) -> Dict[str, Any]:
        """Map vnstock cash flow data to model fields."""
        year = safe_int(data.get('year'))
        quarter = safe_int(data.get('quarter'))
        
        if not year or not quarter:
            return None
        
        return {
            'symbol': symbol,
            'year': year,
            'quarter': quarter,
            'invest_cost': safe_int(data.get('investCost')),
            'from_invest': safe_int(data.get('fromInvest')),
            'from_financial': safe_int(data.get('fromFinancial')),
            'from_sale': safe_int(data.get('fromSale')),
            'free_cash_flow': safe_int(data.get('freeCashFlow')),
        }