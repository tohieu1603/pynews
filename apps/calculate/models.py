from django.db import models

class Period(models.Model):
    TYPE_CHOICES = [
        ("quarter", "Quarter"),
        ("year", "Year"),
    ]
    symbol = models.ForeignKey('stock.Symbol', on_delete=models.CASCADE, related_name="periods")
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    year = models.IntegerField()
    quarter = models.IntegerField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.symbol.code} - {self.type} {self.year} Q{self.quarter or ''}"


class BalanceSheet(models.Model):
    period = models.ForeignKey(Period, on_delete=models.CASCADE, related_name="balance_sheets")
    short_asset = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    cash = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    short_invest = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    short_receivable = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    inventory = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    long_asset = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    fixed_asset = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    asset = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    debt = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    short_debt = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    long_debt = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    equity = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    capital = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    other_debt = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    un_distributed_income = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    minor_share_holder_profit = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    payable = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)


class IncomeStatement(models.Model):
    period = models.ForeignKey(Period, on_delete=models.CASCADE, related_name="income_statements")
    revenue = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    year_revenue_growth = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cost_of_good_sold = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    gross_profit = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    operation_expense = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    operation_profit = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    year_operation_profit_growth = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    interest_expense = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    pre_tax_profit = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    post_tax_profit = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    share_holder_income = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    year_share_holder_income_growth = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ebitda = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)


class CashFlow(models.Model):
    period = models.ForeignKey(Period, on_delete=models.CASCADE, related_name="cash_flows")
    invest_cost = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    from_invest = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    from_financial = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    from_sale = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    free_cash_flow = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)


class FinancialRatio(models.Model):
    period = models.ForeignKey(Period, on_delete=models.CASCADE, related_name="financial_ratios")
    price_to_earning = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    price_to_book = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    value_before_ebitda = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    dividend = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    roe = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    roa = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    days_receivable = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    days_payable = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    earning_per_share = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    book_value_per_share = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    equity_on_total_asset = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    equity_on_liability = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    current_payment = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    quick_payment = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    eps_change = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    ebitda_on_stock = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    gross_profit_margin = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    operating_profit_margin = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    post_tax_margin = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    debt_on_equity = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    debt_on_asset = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    debt_on_ebitda = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    asset_on_equity = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    capital_balance = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    cash_on_equity = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    cash_on_capitalize = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    revenue_on_work_capital = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    capex_on_fixed_asset = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    revenue_on_asset = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    post_tax_on_pre_tax = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    ebit_on_revenue = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    pre_tax_on_ebit = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    payable_on_equity = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    ebitda_on_stock_change = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    book_value_per_share_change = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"FinancialRatio {self.period.symbol.code} {self.period.year}-{self.period.quarter or ''}"
