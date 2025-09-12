class VNStockFields:
    """Constants for vnstock API field names."""
    
    YEAR_REPORT = "yearReport"
    LENGTH_REPORT = "lengthReport"
    
    TOTAL_ASSETS = "TOTAL ASSETS (Bn. VND)"
    CASH_AND_CASH_EQUIVALENTS = "Cash and cash equivalents (Bn. VND)"
    FIXED_ASSETS = "Fixed assets (Bn. VND)"
    LONG_TERM_INVESTMENTS = "Long-term investments (Bn. VND)"
    OTHER_CURRENT_ASSETS = "Other current assets (Bn. VND)"
    OTHER_LONG_TERM_ASSETS = "Other long-term assets (Bn. VND)"
    SHORT_TERM_INVESTMENTS = "Short-term investments (Bn. VND)"
    
    LIABILITIES = "LIABILITIES (Bn. VND)"
    CURRENT_LIABILITIES = "Current liabilities (Bn. VND)"
    
    OWNERS_EQUITY = "OWNER'S EQUITY(Bn.VND)"
    CAPITAL_AND_RESERVES = "Capital and reserves (Bn. VND)"
    UNDISTRIBUTED_EARNINGS = "Undistributed earnings (Bn. VND)"
    PAID_IN_CAPITAL = "Paid-in capital (Bn. VND)"
    
    TOTAL_RESOURCES = "TOTAL RESOURCES (Bn. VND)"
    
    REVENUE = "revenue"
    NET_PROFIT = "net_profit"
    
    CASH_FLOW = "cash_flow"
    
    ROE = "roe"
    ROA = "roa"
    PE = "pe"
    PB = "pb"

class ConversionConstants:
    """Constants for data type conversions."""
    BILLION_TO_UNITS = 1_000_000_000