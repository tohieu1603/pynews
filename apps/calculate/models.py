
from django.db import models

# Constants
STOCK_SYMBOL_MODEL = 'stock.Symbol'


class IncomeStatement(models.Model):
    """Báo cáo kết quả kinh doanh"""
    year_report = models.IntegerField(help_text="Năm")
    length_report = models.IntegerField(help_text="Kỳ")
    revenue = models.BigIntegerField(null=True, blank=True, help_text="Doanh thu (đồng)")
    revenue_yoy = models.FloatField(null=True, blank=True, help_text="Tăng trưởng doanh thu (%)")
    attribute_to_parent_company = models.BigIntegerField(null=True, blank=True, help_text="Lợi nhuận sau thuế của Cổ đông công ty mẹ (đồng)")
    attribute_to_parent_company_yoy = models.FloatField(null=True, blank=True, help_text="Tăng trưởng lợi nhuận (%)")
    interest_and_similar_income = models.BigIntegerField(null=True, blank=True, help_text="Thu nhập lãi và các khoản tương tự")
    interest_and_similar_expenses = models.BigIntegerField(null=True, blank=True, help_text="Chi phí lãi và các khoản tương tự")
    net_interest_income = models.BigIntegerField(null=True, blank=True, help_text="Thu nhập lãi thuần")
    fees_and_comission_income = models.BigIntegerField(null=True, blank=True, help_text="Thu nhập từ hoạt động dịch vụ")
    fees_and_comission_expenses = models.BigIntegerField(null=True, blank=True, help_text="Chi phí hoạt động dịch vụ")
    net_fee_and_commission_income = models.BigIntegerField(null=True, blank=True, help_text="Lãi thuần từ hoạt động dịch vụ")
    net_gain_foreign_currency_and_gold_dealings = models.BigIntegerField(null=True, blank=True, help_text="Kinh doanh ngoại hối và vàng")
    net_gain_trading_of_trading_securities = models.BigIntegerField(null=True, blank=True, help_text="Chứng khoán kinh doanh")
    net_gain_disposal_of_investment_securities = models.BigIntegerField(null=True, blank=True, help_text="Chứng khoán đầu tư")
    net_other_income = models.BigIntegerField(null=True, blank=True, help_text="Hoạt động khác")
    other_expenses = models.BigIntegerField(null=True, blank=True, help_text="Chi phí hoạt động khác")
    net_other_income_expenses = models.BigIntegerField(null=True, blank=True, help_text="Lãi/lỗ thuần từ hoạt động khác")
    dividends_received = models.BigIntegerField(null=True, blank=True, help_text="Cố tức đã nhận")
    total_operating_revenue = models.BigIntegerField(null=True, blank=True, help_text="Tổng thu nhập hoạt động")
    general_admin_expenses = models.BigIntegerField(null=True, blank=True, help_text="Chi phí quản lý DN")
    operating_profit_before_provision = models.BigIntegerField(null=True, blank=True, help_text="LN từ HĐKD trước CF dự phòng")
    provision_for_credit_losses = models.BigIntegerField(null=True, blank=True, help_text="Chi phí dự phòng rủi ro tín dụng")
    profit_before_tax = models.BigIntegerField(null=True, blank=True, help_text="LN trước thuế")
    tax_for_the_year = models.BigIntegerField(null=True, blank=True, help_text="Thuế TNDN")
    business_income_tax_current = models.BigIntegerField(null=True, blank=True, help_text="Chi phí thuế TNDN hiện hành")
    business_income_tax_deferred = models.BigIntegerField(null=True, blank=True, help_text="Chi phí thuế TNDN hoãn lại")
    minority_interest = models.BigIntegerField(null=True, blank=True, help_text="Cổ đông thiểu số")
    net_profit_for_the_year = models.BigIntegerField(null=True, blank=True, help_text="Lợi nhuận thuần")
    attributable_to_parent_company = models.BigIntegerField(null=True, blank=True, help_text="Cổ đông của Công ty mẹ")
    eps_basis = models.IntegerField(null=True, blank=True, help_text="Lãi cơ bản trên cổ phiếu")
    
    # Quan hệ với Symbol
    symbol = models.ForeignKey(
        STOCK_SYMBOL_MODEL,
        on_delete=models.CASCADE,
        related_name='income_statements'
    )
    
    class Meta:
        unique_together = ('symbol', 'year_report', 'length_report')
        ordering = ['-year_report', '-length_report']
    
    def __str__(self):
        return f"{self.symbol.name} - {self.year_report}Q{self.length_report}"


class CashFlow(models.Model):
    """Báo cáo lưu chuyển tiền tệ"""
    year_report = models.IntegerField(help_text="Năm")
    length_report = models.IntegerField(help_text="Kỳ")
    profits_from_other_activities = models.BigIntegerField(null=True, blank=True, help_text="(Lãi)/lỗ các hoạt động khác")
    operating_profit_before_changes_in_working_capital = models.BigIntegerField(null=True, blank=True, help_text="Lưu chuyển tiền thuần từ HĐKD trước thay đổi VLĐ")
    net_cash_flows_from_operating_activities_before_bit = models.BigIntegerField(null=True, blank=True, help_text="Lưu chuyển tiền thuần từ HĐKD trước thuế")
    payment_from_reserves = models.BigIntegerField(null=True, blank=True, help_text="Chi từ các quỹ của TCTD")
    purchase_of_fixed_assets = models.BigIntegerField(null=True, blank=True, help_text="Mua sắm TSCĐ")
    gain_on_dividend = models.BigIntegerField(null=True, blank=True, help_text="Tiền thu cổ tức và lợi nhuận được chia")
    net_cash_flows_from_investing_activities = models.BigIntegerField(null=True, blank=True, help_text="Lưu chuyển từ hoạt động đầu tư")
    increase_in_charter_captial = models.BigIntegerField(null=True, blank=True, help_text="Tăng vốn cổ phần từ góp vốn và/hoặc phát hành cổ phiếu")
    cash_flows_from_financial_activities = models.BigIntegerField(null=True, blank=True, help_text="Lưu chuyển tiền từ hoạt động tài chính")
    net_increase_decrease_in_cash_and_cash_equivalents = models.BigIntegerField(null=True, blank=True, help_text="Lưu chuyển tiền thuần trong kỳ")
    cash_and_cash_equivalents = models.BigIntegerField(null=True, blank=True, help_text="Tiền và tương đương tiền")
    foreign_exchange_differences_adjustment = models.BigIntegerField(null=True, blank=True, help_text="Ảnh hưởng của chênh lệch tỷ giá")
    cash_and_cash_equivalents_at_the_end_of_period = models.BigIntegerField(null=True, blank=True, help_text="Tiền và tương đương tiền cuối kỳ")
    net_cash_inflows_outflows_from_operating_activities = models.BigIntegerField(null=True, blank=True, help_text="Lưu chuyển tiền tệ ròng từ các hoạt động SXKD")
    proceeds_from_disposal_of_fixed_assets = models.BigIntegerField(null=True, blank=True, help_text="Tiền thu được từ thanh lý tài sản cố định")
    investment_in_other_entities = models.BigIntegerField(null=True, blank=True, help_text="Đầu tư vào các doanh nghiệp khác")
    proceeds_from_divestment_in_other_entities = models.BigIntegerField(null=True, blank=True, help_text="Tiền thu từ việc bán các khoản đầu tư vào doanh nghiệp khác")
    dividends_paid = models.BigIntegerField(null=True, blank=True, help_text="Cổ tức đã trả")
    
    # Quan hệ với Symbol
    symbol = models.ForeignKey(
        STOCK_SYMBOL_MODEL,
        on_delete=models.CASCADE,
        related_name='cash_flows'
    )
    
    class Meta:
        unique_together = ('symbol', 'year_report', 'length_report')
        ordering = ['-year_report', '-length_report']
    
    def __str__(self):
        return f"{self.symbol.name} - Cash Flow {self.year_report}Q{self.length_report}"


class BalanceSheet(models.Model):
    """Bảng cân đối kế toán"""
    year_report = models.IntegerField(help_text="Năm")
    length_report = models.IntegerField(help_text="Kỳ")
    
    # Tài sản
    total_assets = models.BigIntegerField(null=True, blank=True, help_text="TỔNG CỘNG TÀI SẢN (đồng)")
    cash_and_cash_equivalents = models.BigIntegerField(null=True, blank=True, help_text="Tiền và tương đương tiền (đồng)")
    balances_with_the_sbv = models.BigIntegerField(null=True, blank=True, help_text="Tiền gửi tại ngân hàng nhà nước Việt Nam")
    placements_with_and_loans_to_other_credit_institutions = models.BigIntegerField(null=True, blank=True, help_text="Tiền gửi tại các TCTD khác và cho vay các TCTD khác")
    trading_securities_net = models.BigIntegerField(null=True, blank=True, help_text="Chứng khoán kinh doanh thuần")
    trading_securities = models.BigIntegerField(null=True, blank=True, help_text="Chứng khoán kinh doanh")
    provision_for_diminution_in_value_of_trading_securities = models.BigIntegerField(null=True, blank=True, help_text="Dự phòng giảm giá chứng khoán kinh doanh")
    derivatives_and_other_financial_liabilities = models.BigIntegerField(null=True, blank=True, help_text="Các công cụ tài chính phái sinh và khoản nợ tài chính khác")
    loans_and_advances_to_customers_net = models.BigIntegerField(null=True, blank=True, help_text="Cho vay khách hàng thuần")
    loans_and_advances_to_customers = models.BigIntegerField(null=True, blank=True, help_text="Cho vay khách hàng")
    less_provision_for_losses_on_loans_and_advances_to_customers = models.BigIntegerField(null=True, blank=True, help_text="Dự phòng rủi ro cho vay khách hàng")
    investment_securities = models.BigIntegerField(null=True, blank=True, help_text="Chứng khoán đầu tư")
    available_for_sales_securities = models.BigIntegerField(null=True, blank=True, help_text="Chứng khoán đầu tư sẵn sàng để bán")
    held_to_maturity_securities = models.BigIntegerField(null=True, blank=True, help_text="Chứng khoán đầu tư giữ đến ngày đáo hạn")
    less_provision_for_diminution_in_value_of_investment_securities = models.BigIntegerField(null=True, blank=True, help_text="Dự phòng giảm giá chứng khoán đầu tư")
    long_term_investments = models.BigIntegerField(null=True, blank=True, help_text="Đầu tư dài hạn (đồng)")
    investment_in_joint_ventures = models.BigIntegerField(null=True, blank=True, help_text="Đầu tư vào công ty con")
    investments_in_associate_companies = models.BigIntegerField(null=True, blank=True, help_text="Đầu tư vào công ty liên doanh")
    other_long_term_assets = models.BigIntegerField(null=True, blank=True, help_text="Tài sản dài hạn khác (đồng)")
    less_provision_for_diminution_in_value_of_long_term_investments = models.BigIntegerField(null=True, blank=True, help_text="Dự phòng giảm giá đầu tư dài hạn")
    fixed_assets = models.BigIntegerField(null=True, blank=True, help_text="Tài sản cố định (đồng)")
    tangible_fixed_assets = models.BigIntegerField(null=True, blank=True, help_text="Tài sản cố định hữu hình")
    intangible_fixed_assets = models.BigIntegerField(null=True, blank=True, help_text="Tài sản cố định vô hình")
    other_assets = models.BigIntegerField(null=True, blank=True, help_text="Tài sản Có khác")
    
    # Nguồn vốn và nợ phải trả
    total_resources = models.BigIntegerField(null=True, blank=True, help_text="TỔNG CỘNG NGUỒN VỐN (đồng)")
    liabilities = models.BigIntegerField(null=True, blank=True, help_text="NỢ PHẢI TRẢ (đồng)")
    due_to_gov_and_borrowings_from_sbv = models.BigIntegerField(null=True, blank=True, help_text="Các khoản nợ chính phủ và NHNN Việt Nam")
    deposits_and_borrowings_from_other_credit_institutions = models.BigIntegerField(null=True, blank=True, help_text="Tiền gửi và vay các Tổ chức tín dụng khác")
    deposits_from_customers = models.BigIntegerField(null=True, blank=True, help_text="Tiền gửi của khách hàng")
    derivatives_and_other_financial_liabilities_2 = models.BigIntegerField(null=True, blank=True, help_text="Các công cụ tài chính phái sinh và khoản nợ tài chính khác")
    funds_received_from_gov_international_and_other_institutions = models.BigIntegerField(null=True, blank=True, help_text="Vốn tài trợ, uỷ thác đầu tư của CP và các tổ chức TD khác")
    convertible_bonds_cds_and_other_valuable_papers_issued = models.BigIntegerField(null=True, blank=True, help_text="Phát hành giấy tờ có giá")
    other_liabilities = models.BigIntegerField(null=True, blank=True, help_text="Các khoản nợ khác")
    
    # Vốn chủ sở hữu
    owners_equity = models.BigIntegerField(null=True, blank=True, help_text="VỐN CHỦ SỞ HỮU (đồng)")
    capital = models.BigIntegerField(null=True, blank=True, help_text="Vốn của tổ chức tín dụng")
    reserves = models.BigIntegerField(null=True, blank=True, help_text="Quỹ của tổ chức tín dụng")
    foreign_currency_difference_reserve = models.BigIntegerField(null=True, blank=True, help_text="Chênh lệch tỷ giá hối đoái")
    difference_upon_assets_revaluation = models.BigIntegerField(null=True, blank=True, help_text="Chênh lệch đánh giá lại tài sản")
    undistributed_earnings = models.BigIntegerField(null=True, blank=True, help_text="Lãi chưa phân phối (đồng)")
    minority_interest = models.BigIntegerField(null=True, blank=True, help_text="Cổ đông thiểu số")
    paid_in_capital = models.BigIntegerField(null=True, blank=True, help_text="Vốn góp của chủ sở hữu (đồng)")
    other_reserves = models.BigIntegerField(null=True, blank=True, help_text="Các quỹ khác")
    minority_interests = models.BigIntegerField(null=True, blank=True, help_text="LỢI ÍCH CỦA CỔ ĐÔNG THIỂU SỐ")
    
    # Quan hệ với Symbol
    symbol = models.ForeignKey(
        STOCK_SYMBOL_MODEL,
        on_delete=models.CASCADE,
        related_name='balance_sheets'
    )
    
    class Meta:
        unique_together = ('symbol', 'year_report', 'length_report')
        ordering = ['-year_report', '-length_report']
    
    def __str__(self):
        return f"{self.symbol.name} - Balance Sheet {self.year_report}Q{self.length_report}"


class Ratio(models.Model):
    """Các chỉ số tài chính"""
    year_report = models.IntegerField(help_text="Năm")
    length_report = models.IntegerField(help_text="Kỳ")
    
    # Chỉ tiêu cơ cấu nguồn vốn
    debt_equity = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True, help_text="Nợ/VCSH")
    fixed_asset_to_equity = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True, help_text="TSCĐ / Vốn CSH")
    owners_equity_charter_capital = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True, help_text="Vốn CSH/Vốn điều lệ")
    
    # Chỉ tiêu khả năng sinh lợi
    net_profit_margin = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True, help_text="Biên lợi nhuận ròng (%)")
    roe = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True, help_text="ROE (%)")
    roic = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True, help_text="ROIC (%)")
    roa = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True, help_text="ROA (%)")
    dividend_yield = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True, help_text="Tỷ suất cổ tức (%)")
    
    # Đòn bẩy tài chính
    financial_leverage = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True, help_text="Đòn bẩy tài chính")
    
    # Giá trị thị trường
    market_capital = models.BigIntegerField(null=True, blank=True, help_text="Vốn hóa (Tỷ đồng)")
    outstanding_share = models.BigIntegerField(null=True, blank=True, help_text="Số CP lưu hành (Triệu CP)")
    
    # Chỉ tiêu định giá
    pe = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True, help_text="P/E")
    pb = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True, help_text="P/B")
    ps = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True, help_text="P/S")
    p_cash_flow = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True, help_text="P/Cash Flow")
    
    # Thu nhập / Giá trị sổ sách
    eps = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True, help_text="EPS (VND)")
    bvps = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True, help_text="BVPS (VND)")
    
    # Quan hệ với Symbol
    symbol = models.ForeignKey(
        STOCK_SYMBOL_MODEL,
        on_delete=models.CASCADE,
        related_name='ratios'
    )
    
    class Meta:
        unique_together = ('symbol', 'year_report', 'length_report')
        ordering = ['-year_report', '-length_report']
    
    def __str__(self):
        return f"{self.symbol.name} - Ratios {self.year_report}Q{self.length_report}"
    