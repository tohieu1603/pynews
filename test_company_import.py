#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.stock.services.vnstock_import_service import VnstockImportService
from apps.stock.models import Symbol

def test_company_import():
    print("=== Testing Company Import ===")
    
    # Test với 3 symbols đầu tiên
    symbols = Symbol.objects.all()[:3]
    print(f"Testing with symbols: {[s.name for s in symbols]}")
    
    service = VnstockImportService(per_symbol_sleep=0.5)
    
    # Test lấy company info của 1 symbol
    try:
        symbol = symbols[0]
        print(f"\nTesting symbol: {symbol.name}")
        
        company_info = service._fetch_company_info_from_vnstock(symbol.name)
        if company_info:
            print("✓ Company info found!")
            print(f"Company name: {company_info.get('company_name')}")
            print(f"Fields: {list(company_info.keys())}")
        else:
            print("✗ No company info found")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_company_import()