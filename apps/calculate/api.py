from ninja import Router
from apps.calculate.models import Period, BalanceSheet, IncomeStatement, CashFlow, FinancialRatio
from apps.stock.models import Symbol
from vnstock import Finance
from datetime import datetime
import asyncio
from typing import Dict, Optional
import re

router = Router()


def _get(row: Dict, key: str) -> Optional[float]:
    try:
        val = row.get(key)
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        return float(val)
    except Exception:
        return None


async def _call_finance_with_rate_limit(method, max_retries: int = 3, sleep_fallback: int = 35, **kwargs):
    """Call a Finance method in thread, handling VCI rate-limit SystemExit.

    Retries a few times after waiting the provider-suggested seconds.
    """
    attempt = 0
    while True:
        try:
            return await asyncio.to_thread(method, **kwargs)
        except SystemExit as e:
            msg = str(e)
            m = re.search(r"sau\s+(\d+)\s+giây", msg)
            wait_s = int(m.group(1)) if m else sleep_fallback
            attempt += 1
            if attempt > max_retries:
                raise
            await asyncio.sleep(wait_s)
        except BaseException:
            raise


async def fetch_and_save_symbol(symbol_obj: Symbol):
    symbol = symbol_obj.name
    try:
        f = Finance(source="vci", symbol=symbol, period="quarter", get_all=True)

        balance_sheets = await _call_finance_with_rate_limit(
            f.balance_sheet, period="quarter", lang="en", dropna=True
        )
        income_statements = await _call_finance_with_rate_limit(
            f.income_statement, period="quarter", lang="en", dropna=True
        )
        cash_flows = await _call_finance_with_rate_limit(
            f.cash_flow, period="quarter", lang="en", dropna=True
        )
        financial_ratios = await _call_finance_with_rate_limit(
            f.ratio,
            period="quarter",
            lang="en",
            dropna=True,
            flatten_columns=True,
            separator="_",
        )

        print(f"[{datetime.now()}] Fetched data for {symbol}")

        bs_map = {
            "short_asset": "CURRENT ASSETS (Bn. VND)",
            "cash": "Cash and cash equivalents (Bn. VND)",
            "short_invest": "Short-term investments (Bn. VND)",
            "short_receivable": "Accounts receivable (Bn. VND)",
            "inventory": "Inventories, Net (Bn. VND)",
            "long_asset": "LONG-TERM ASSETS (Bn. VND)",
            "fixed_asset": "Fixed assets (Bn. VND)",
            "asset": "TOTAL ASSETS (Bn. VND)",
            "debt": "LIABILITIES (Bn. VND)",
            "short_debt": "Current liabilities (Bn. VND)",
            "long_debt": "Long-term liabilities (Bn. VND)",
            "equity": "OWNER'S EQUITY(Bn.VND)",
            "capital": "Capital and reserves (Bn. VND)",
            "other_debt": "Other Reserves",
            "un_distributed_income": "Undistributed earnings (Bn. VND)",
            "minor_share_holder_profit": "Minority Interest",
        }

        is_map = {
            "revenue": "Revenue (Bn. VND)",
            "year_revenue_growth": "Revenue YoY (%)",
            "cost_of_good_sold": "Cost of Sales",
            "gross_profit": "Gross Profit",
            "operation_expense": "General & Admin Expenses",
            "operation_profit": "Operating Profit/Loss",
            "interest_expense": "Interest Expenses",
            "pre_tax_profit": "Profit before tax",
            "post_tax_profit": "Net Profit For the Year",
            "share_holder_income": "Attribute to parent company (Bn. VND)",
            "year_share_holder_income_growth": "Attribute to parent company YoY (%)",
        }

        def _resolve_key(row_like, preferred: str, fallbacks: list[str] = None) -> Optional[str]:
            cols = set(getattr(row_like, "index", getattr(row_like, "columns", [])))
            if preferred in cols:
                return preferred
            if fallbacks:
                for fb in fallbacks:
                    if fb in cols:
                        return fb
            return None

        for _, row in balance_sheets.iterrows():
            year = int(row.get("yearReport"))
            quarter = int(row.get("lengthReport"))

            period_obj, _ = await asyncio.to_thread(
                Period.objects.get_or_create,
                symbol=symbol_obj,
                type="quarter",
                year=year,
                quarter=quarter,
            )

            bs_defaults: Dict[str, Optional[float]] = {}
            for field, col in bs_map.items():
                use_col = col
                if field == "inventory" and col not in row.index:
                    use_col = "Net Inventories" if "Net Inventories" in row.index else None
                if field == "minor_share_holder_profit" and col not in row.index:
                    use_col = "MINORITY INTERESTS" if "MINORITY INTERESTS" in row.index else None
                if use_col:
                    bs_defaults[field] = _get(row, use_col)

            await asyncio.to_thread(
                BalanceSheet.objects.update_or_create,
                period=period_obj,
                defaults=bs_defaults,
            )

            inc_row = income_statements.loc[
                (income_statements["yearReport"] == year)
                & (income_statements["lengthReport"] == quarter)
            ]
            if not inc_row.empty:
                inc_row = inc_row.squeeze()
                is_defaults: Dict[str, Optional[float]] = {}
                for field, col in is_map.items():
                    use_col = _resolve_key(inc_row, col, [
                        "Attributable to parent company",
                    ]) if field in ("share_holder_income", "year_share_holder_income_growth") else col
                    if use_col:
                        is_defaults[field] = _get(inc_row, use_col)

                if is_defaults.get("ebitda") is None:
                    ratio_cols = list(financial_ratios.columns
                                      )
                    ebitda_cols = [c for c in ratio_cols if str(c).endswith("EBITDA (Bn. VND)")]
                    if ebitda_cols:
                        rat_row = financial_ratios.loc[
                            (financial_ratios["Meta_yearReport"] == year)
                            & (financial_ratios["Meta_lengthReport"] == quarter)
                        ]
                        if not rat_row.empty:
                            rat_row = rat_row.squeeze()
                            is_defaults["ebitda"] = _get(rat_row, ebitda_cols[0])

                await asyncio.to_thread(
                    IncomeStatement.objects.update_or_create,
                    period=period_obj,
                    defaults=is_defaults,
                )

            cf_row = cash_flows.loc[
                (cash_flows["yearReport"] == year)
                & (cash_flows["lengthReport"] == quarter)
            ]
            if not cf_row.empty:
                cf_row = cf_row.squeeze()
                cfo = _get(cf_row, "Net cash inflows/outflows from operating activities")
                capex = _get(cf_row, "Purchase of fixed assets")
                cfi = _get(cf_row, "Net Cash Flows from Investing Activities")
                cff = _get(cf_row, "Cash flows from financial activities")
                fcf = None
                if cfo is not None and capex is not None:
                    try:
                        fcf = float(cfo) - float(capex)
                    except Exception:
                        fcf = None

                await asyncio.to_thread(
                    CashFlow.objects.update_or_create,
                    period=period_obj,
                    defaults={
                        "invest_cost": capex,
                        "from_invest": cfi,
                        "from_financial": cff,
                        "from_sale": cfo,
                        "free_cash_flow": fcf,
                    },
                )

            rat_row = financial_ratios.loc[
                (financial_ratios["Meta_yearReport"] == year)
                & (financial_ratios["Meta_lengthReport"] == quarter)
            ]
            if not rat_row.empty:
                rat_row = rat_row.squeeze()
                def find_col(suffix: str) -> Optional[str]:
                    for c in financial_ratios.columns:
                        if str(c).endswith(suffix):
                            return c
                    return None

                fr_defaults = {
                    "price_to_earning": _get(rat_row, find_col("P/E")),
                    "price_to_book": _get(rat_row, find_col("P/B")),
                    "roe": _get(rat_row, find_col("ROE (%)")),
                    "roa": _get(rat_row, find_col("ROA (%)")),
                    "earning_per_share": _get(rat_row, find_col("EPS (VND)")),
                    "book_value_per_share": _get(rat_row, find_col("BVPS (VND)")),
                    "current_payment": _get(rat_row, find_col("Current Ratio")),
                    "quick_payment": _get(rat_row, find_col("Quick Ratio")),
                    "days_receivable": _get(rat_row, find_col("Days Sales Outstanding")),
                    "days_payable": _get(rat_row, find_col("Days Payable Outstanding")),
                    "gross_profit_margin": _get(rat_row, find_col("Gross Profit Margin (%)")),
                    "operating_profit_margin": _get(rat_row, find_col("EBIT Margin (%)")),
                    "post_tax_margin": _get(rat_row, find_col("Net Profit Margin (%)")),
                    "dividend": _get(rat_row, find_col("Dividend yield (%)")),
                    "value_before_ebitda": _get(rat_row, find_col("EV/EBITDA")),
                }

                await asyncio.to_thread(
                    FinancialRatio.objects.update_or_create,
                    period=period_obj,
                    defaults=fr_defaults,
                )

        return {"symbol": symbol, "status": "success"}

    except Exception as e:
        print(f"[{datetime.now()}] Failed {symbol}: {e}")
        return {"symbol": symbol, "status": "failed", "error": str(e)}


@router.post("/import-finance")
async def import_finance(request):
    symbols = await asyncio.to_thread(lambda: list(Symbol.objects.all()))
    print(f"Starting import for {len(symbols)} symbols at {datetime.now()}")

    results = []
    for idx, symbol in enumerate(symbols, start=1):
        try:
            res = await fetch_and_save_symbol(symbol)
        except SystemExit as e:
            res = {"symbol": getattr(symbol, "name", str(symbol)), "status": "failed", "error": str(e)}
        except BaseException as e:
            res = {"symbol": getattr(symbol, "name", str(symbol)), "status": "failed", "error": str(e)}
        results.append(res)
        await asyncio.sleep(1)

    total_imported = sum(1 for r in results if r.get('status') == "success")
    failed_symbols = [r for r in results if r.get('status') == "failed"]

    return {
        "total_symbols": len(symbols),
        "imported": total_imported,
        "failed": failed_symbols,
    }


@router.post("/import-finance/symbol/{symbol}")
async def import_finance_symbol(request, symbol: str):
    symbol_obj = await asyncio.to_thread(lambda: Symbol.objects.filter(name=symbol).first())
    if not symbol_obj:
        return {"symbol": symbol, "status": "failed", "error": "Symbol not found"}

    res = await fetch_and_save_symbol(symbol_obj)
    return res
